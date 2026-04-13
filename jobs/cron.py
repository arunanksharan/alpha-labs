"""Configurable cron scheduler for daily research cycles.

Runs the research pipeline on a schedule. Users configure:
- Time of day (e.g., 06:00 SGT)
- Tickers to process (from universe or custom list)
- Strategy to run
- Whether to auto-refresh data first

The scheduler runs in a background thread and can be started/stopped via API.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CRON_CONFIG_FILE = Path("data/cron_config.json")

DEFAULT_CONFIG = {
    "enabled": False,
    "schedule_hour": 6,
    "schedule_minute": 0,
    "timezone_offset": 8,  # SGT = UTC+8
    "strategy": "mean_reversion",
    "refresh_data": True,
    "auto_run_signals": True,
}


@dataclass
class CronConfig:
    enabled: bool = False
    schedule_hour: int = 6
    schedule_minute: int = 0
    timezone_offset: int = 8  # UTC offset in hours
    strategy: str = "mean_reversion"
    refresh_data: bool = True
    auto_run_signals: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> CronConfig:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class CronStatus:
    running: bool = False
    last_run: str | None = None
    last_result: str | None = None
    next_run: str | None = None
    tickers_processed: int = 0
    errors: list[str] = field(default_factory=list)


def load_cron_config() -> CronConfig:
    if CRON_CONFIG_FILE.exists():
        try:
            return CronConfig.from_dict(json.loads(CRON_CONFIG_FILE.read_text()))
        except Exception:
            pass
    return CronConfig()


def save_cron_config(config: CronConfig) -> None:
    CRON_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CRON_CONFIG_FILE.write_text(json.dumps(config.to_dict(), indent=2))


class CronScheduler:
    """Background scheduler that runs the research pipeline on a configurable schedule."""

    def __init__(self) -> None:
        self._config = load_cron_config()
        self._status = CronStatus()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def config(self) -> CronConfig:
        return self._config

    @property
    def status(self) -> CronStatus:
        return self._status

    def update_config(self, updates: dict) -> CronConfig:
        for k, v in updates.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
        save_cron_config(self._config)

        # Restart if running and config changed
        if self._status.running:
            self.stop()
            if self._config.enabled:
                self.start()

        return self._config

    def start(self) -> None:
        if self._status.running:
            return
        self._config.enabled = True
        save_cron_config(self._config)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="cron-scheduler")
        self._thread.start()
        self._status.running = True
        self._compute_next_run()
        logger.info("Cron scheduler started: %02d:%02d UTC%+d", self._config.schedule_hour, self._config.schedule_minute, self._config.timezone_offset)

    def stop(self) -> None:
        self._config.enabled = False
        save_cron_config(self._config)
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        self._status.running = False
        self._status.next_run = None
        logger.info("Cron scheduler stopped")

    def run_now(self) -> dict:
        """Trigger an immediate run (manual trigger from API)."""
        return self._execute_cycle()

    def _run_loop(self) -> None:
        """Main scheduler loop — checks every 30s if it's time to run."""
        while not self._stop_event.is_set():
            now = datetime.now(timezone.utc)
            local_hour = (now.hour + self._config.timezone_offset) % 24
            local_minute = now.minute

            if local_hour == self._config.schedule_hour and local_minute == self._config.schedule_minute:
                self._execute_cycle()
                # Sleep past the current minute to avoid double-trigger
                self._stop_event.wait(70)
            else:
                self._stop_event.wait(30)

            self._compute_next_run()

    def _execute_cycle(self) -> dict:
        """Run the research pipeline for all universe tickers."""
        logger.info("Starting cron cycle...")
        self._status.last_run = datetime.now(timezone.utc).isoformat()
        self._status.errors = []
        results = {}

        try:
            # Load universe
            universe_file = Path("data/universe.json")
            if universe_file.exists():
                universe = json.loads(universe_file.read_text())
                tickers = universe.get("tickers", [])
            else:
                tickers = []
                self._status.errors.append("No universe file found")

            if not tickers:
                self._status.last_result = "No tickers in universe"
                return {"status": "no_tickers"}

            # Optionally refresh data first
            if self._config.refresh_data:
                self._refresh_data(tickers)

            # Run research pipeline for each ticker
            if self._config.auto_run_signals:
                from core.orchestrator import ResearchOrchestrator
                orchestrator = ResearchOrchestrator()
                cache_dir = Path("data/cache/research")
                cache_dir.mkdir(parents=True, exist_ok=True)

                for ticker in tickers:
                    try:
                        result = orchestrator.run(
                            ticker, self._config.strategy,
                            "2023-01-01", datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        )
                        result_json = result.to_json()
                        cache_file = cache_dir / f"{ticker}__{self._config.strategy}.json"
                        cache_file.write_text(json.dumps(result_json, default=str))
                        bt = result_json.get("backtest", {})
                        results[ticker] = {
                            "signals": result_json.get("signals_count", 0),
                            "return": bt.get("total_return", 0),
                            "sharpe": bt.get("sharpe_ratio", 0),
                        }
                    except Exception as e:
                        self._status.errors.append(f"{ticker}: {e}")
                        results[ticker] = {"error": str(e)}

            self._status.tickers_processed = len(tickers)
            profitable = sum(1 for r in results.values() if r.get("return", 0) > 0)
            self._status.last_result = f"Processed {len(tickers)} tickers, {profitable} profitable"
            logger.info("Cron cycle complete: %s", self._status.last_result)
            return {"status": "completed", "results": results}

        except Exception as e:
            self._status.last_result = f"Failed: {e}"
            self._status.errors.append(str(e))
            logger.error("Cron cycle failed: %s", e)
            return {"status": "failed", "error": str(e)}

    def _refresh_data(self, tickers: list[str]) -> None:
        """Fetch latest market data for all tickers."""
        try:
            from data.fetchers.yfinance_connector import YFinanceConnector
            from data.storage.store import DataStore
            from datetime import date

            store = DataStore()
            connector = YFinanceConnector()
            start = date(2022, 1, 1)
            end = date.today()

            for ticker in tickers:
                try:
                    data = connector.fetch_ohlcv(ticker, start, end)
                    store.save_ohlcv(ticker, data, source="yfinance")
                    time.sleep(0.3)
                except Exception as e:
                    self._status.errors.append(f"Data refresh {ticker}: {e}")
        except Exception as e:
            self._status.errors.append(f"Data refresh failed: {e}")

    def _compute_next_run(self) -> None:
        if not self._config.enabled:
            self._status.next_run = None
            return
        now = datetime.now(timezone.utc)
        local_hour = (now.hour + self._config.timezone_offset) % 24
        if local_hour < self._config.schedule_hour or (local_hour == self._config.schedule_hour and now.minute < self._config.schedule_minute):
            hours_until = self._config.schedule_hour - local_hour
            mins_until = self._config.schedule_minute - now.minute
        else:
            hours_until = 24 - local_hour + self._config.schedule_hour
            mins_until = self._config.schedule_minute - now.minute

        total_mins = hours_until * 60 + mins_until
        from datetime import timedelta
        next_time = now + timedelta(minutes=total_mins)
        self._status.next_run = next_time.isoformat()


# Singleton
_scheduler: CronScheduler | None = None


def get_scheduler() -> CronScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = CronScheduler()
        # Auto-start if config says enabled
        if _scheduler.config.enabled:
            _scheduler.start()
    return _scheduler
