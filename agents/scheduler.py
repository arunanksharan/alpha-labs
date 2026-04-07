"""Cycle scheduler -- runs daily and weekly research cycles.

Provides both synchronous (manual trigger) and async (background loop)
interfaces for running the research pipeline on a schedule.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

logger = logging.getLogger(__name__)

_DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "GOOG", "TSLA", "META"]


class CycleScheduler:
    """Runs daily and weekly research cycles."""

    def __init__(self, tickers: list[str] | None = None) -> None:
        self._tickers = tickers or list(_DEFAULT_TICKERS)
        self._director = None  # Lazy -- avoids import cost at init
        self._running = False
        self._last_daily: datetime | None = None
        self._last_weekly: datetime | None = None

    def _get_director(self):
        """Lazy-load the ResearchDirector."""
        if self._director is None:
            from agents.specialists.research_director import ResearchDirector
            self._director = ResearchDirector()
        return self._director

    def run_daily_cycle(
        self,
        event_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        """Run the daily research cycle (synchronous).

        1. Research each ticker with the full specialist panel.
        2. Generate the morning brief.
        3. Return the brief as a serializable dict.

        Parameters
        ----------
        event_callback:
            Optional callback for real-time event streaming.

        Returns
        -------
        dict
            The morning brief as a JSON-serializable dict.
        """
        director = self._get_director()
        now = datetime.now(timezone.utc)

        # Use trailing 1-year window
        end_date = now.strftime("%Y-%m-%d")
        start_date = (now - timedelta(days=365)).strftime("%Y-%m-%d")

        if event_callback:
            event_callback({
                "cycle": "daily",
                "status": "started",
                "tickers": self._tickers,
                "timestamp": now.isoformat(),
            })

        brief = director.generate_morning_brief(
            self._tickers,
            start_date,
            end_date,
            event_callback=event_callback,
        )

        self._last_daily = now

        if event_callback:
            event_callback({
                "cycle": "daily",
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return brief.to_json()

    def run_weekly_cycle(
        self,
        event_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        """Run the weekly review cycle.

        Placeholder: performance review, signal decay check, portfolio
        rebalancing suggestions.

        Parameters
        ----------
        event_callback:
            Optional callback for real-time event streaming.

        Returns
        -------
        dict
            Weekly summary with performance review and recommendations.
        """
        now = datetime.now(timezone.utc)

        if event_callback:
            event_callback({
                "cycle": "weekly",
                "status": "started",
                "timestamp": now.isoformat(),
            })

        # Placeholder weekly summary
        summary = {
            "cycle": "weekly",
            "timestamp": now.isoformat(),
            "performance_review": {
                "status": "not_implemented",
                "note": "Weekly performance review will compare signal predictions vs outcomes.",
            },
            "signal_decay_check": {
                "status": "not_implemented",
                "note": "Will compute IC half-life for active signals.",
            },
            "rebalancing_suggestions": [],
            "tickers_reviewed": self._tickers,
        }

        self._last_weekly = now

        if event_callback:
            event_callback({
                "cycle": "weekly",
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return summary

    async def start_background(self, daily_interval_hours: int = 24) -> None:
        """Start the background cycle loop (for FastAPI lifespan).

        Parameters
        ----------
        daily_interval_hours:
            Hours between daily cycle runs. Default 24.
        """
        self._running = True
        logger.info(
            "Background scheduler started (interval=%dh, tickers=%s)",
            daily_interval_hours,
            self._tickers,
        )

        while self._running:
            try:
                logger.info("Running scheduled daily cycle...")
                self.run_daily_cycle()
                logger.info("Daily cycle completed.")
            except Exception as exc:
                logger.error("Daily cycle failed: %s", exc)

            # Check weekly: run if last weekly was > 7 days ago or never
            if self._last_weekly is None or (
                datetime.now(timezone.utc) - self._last_weekly
            ).days >= 7:
                try:
                    logger.info("Running scheduled weekly cycle...")
                    self.run_weekly_cycle()
                    logger.info("Weekly cycle completed.")
                except Exception as exc:
                    logger.error("Weekly cycle failed: %s", exc)

            await asyncio.sleep(daily_interval_hours * 3600)

    def stop(self) -> None:
        """Stop the background cycle loop."""
        self._running = False
        logger.info("Background scheduler stopped.")

    @property
    def last_daily(self) -> datetime | None:
        return self._last_daily

    @property
    def last_weekly(self) -> datetime | None:
        return self._last_weekly
