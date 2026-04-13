"""Seed platform_config with all current hardcoded defaults.

Run: PYTHONPATH=. python db/seed.py
"""

from __future__ import annotations

import logging

from db.models import Base, PlatformConfig
from db.session import engine, get_db_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

# Every configurable value in the platform, organized by category
DEFAULTS = [
    # Backtest
    ("backtest.initial_capital", "100000.0", "backtest", "Starting capital for backtests"),
    ("backtest.commission", "0.001", "backtest", "Commission per trade (10 bps)"),
    ("backtest.slippage", "0.0005", "backtest", "Slippage per trade (5 bps)"),
    ("backtest.risk_free_rate", "0.05", "backtest", "Annual risk-free rate (5%)"),
    ("backtest.benchmark_ticker", "SPY", "backtest", "Benchmark ticker for relative metrics"),
    ("backtest.train_window", "252", "backtest", "Walk-forward training window (trading days)"),
    ("backtest.test_window", "63", "backtest", "Walk-forward test window (trading days)"),
    ("backtest.trading_days_per_year", "252", "backtest", "Trading days per year for annualization"),

    # Risk
    ("risk.max_position_pct", "0.10", "risk", "Max single position (10% of portfolio)"),
    ("risk.max_sector_pct", "0.30", "risk", "Max sector exposure (30%)"),
    ("risk.max_drawdown_pct", "0.15", "risk", "Circuit breaker drawdown (15%)"),
    ("risk.var_confidence", "0.95", "risk", "VaR confidence level"),
    ("risk.kelly_fraction", "0.25", "risk", "Kelly criterion fraction (quarter Kelly)"),
    ("risk.max_correlation", "0.85", "risk", "Max correlation between positions"),
    ("risk.max_total_exposure", "1.0", "risk", "Max total portfolio exposure (100%)"),
    ("risk.cvar_multiplier", "1.4", "risk", "CVaR = VaR * this multiplier"),
    ("risk.drawdown_fade_start", "0.5", "risk", "Start fading position size at this fraction of max DD"),

    # Mean Reversion Strategy
    ("strategy.mean_reversion.entry_threshold", "2.0", "strategy", "Z-score entry threshold"),
    ("strategy.mean_reversion.exit_threshold", "0.0", "strategy", "Z-score exit threshold"),
    ("strategy.mean_reversion.default_window", "20", "strategy", "Default lookback window (days)"),
    ("strategy.mean_reversion.min_window", "10", "strategy", "Min auto-detected window"),
    ("strategy.mean_reversion.max_window", "252", "strategy", "Max auto-detected window"),
    ("strategy.mean_reversion.confidence_divisor", "4.0", "strategy", "Confidence = min(|z| / this, 1.0)"),
    ("strategy.mean_reversion.cointegration_pvalue", "0.05", "strategy", "Cointegration test p-value threshold"),

    # Momentum Strategy
    ("strategy.momentum.lookback", "252", "strategy", "Momentum lookback window (days)"),
    ("strategy.momentum.skip_recent", "21", "strategy", "Skip recent N days (reversal filter)"),
    ("strategy.momentum.top_pct", "0.2", "strategy", "Top percentile for long signals"),
    ("strategy.momentum.bottom_pct", "0.2", "strategy", "Bottom percentile for short signals"),

    # Position Sizing
    ("sizing.risk_parity_target_vol", "0.10", "sizing", "Risk parity target annual volatility"),
    ("sizing.risk_parity_iterations", "50", "sizing", "Risk parity optimization iterations"),

    # Data
    ("data.default_start_date", "2015-01-01", "data", "Default data start date"),
    ("data.default_connector", "yfinance", "data", "Default market data connector"),
    ("data.yfinance_rate_limit", "1.0", "data", "YFinance requests per second"),

    # Signal Decay
    ("decay.min_signals", "5", "analysis", "Min signals for decay analysis"),
    ("decay.max_horizon", "60", "analysis", "Max forward horizon for IC curve"),

    # LLM
    ("llm.default_model", "gpt-5-mini", "llm", "Default LLM model for agent synthesis"),
    ("llm.temperature", "0.3", "llm", "Default LLM temperature"),
    ("llm.max_tokens", "2000", "llm", "Default max response tokens"),
]


def seed() -> None:
    """Create tables and seed platform_config with defaults."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created.")

    db = get_db_session()
    try:
        added = 0
        for key, value, category, description in DEFAULTS:
            existing = db.query(PlatformConfig).filter_by(key=key).first()
            if not existing:
                db.add(PlatformConfig(
                    key=key, value=value, category=category, description=description,
                ))
                added += 1

        db.commit()
        total = db.query(PlatformConfig).count()
        logger.info("Seeded %d new config values (%d total in platform_config)", added, total)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
