"""Research pipeline wrapper with progress callbacks and per-request config.

Replicates the orchestrator's pipeline steps but adds:
1. Progress reporting between each stage
2. Per-request config overrides (commission, slippage, etc.)
3. Strategy parameter overrides

Does NOT modify core/orchestrator.py — uses the same building blocks.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import polars as pl

from config.settings import settings
from jobs.models import BacktestConfig

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float, str], None]


def _noop_progress(stage: str, pct: float, msg: str) -> None:
    pass


@dataclass(frozen=True)
class MergedBacktestConfig:
    initial_capital: float
    commission: float
    slippage: float
    risk_free_rate: float


def _merge_config(config: BacktestConfig | None) -> MergedBacktestConfig:
    """Merge per-request overrides with global defaults."""
    bt = settings.backtest
    if config is None:
        return MergedBacktestConfig(
            initial_capital=bt.initial_capital,
            commission=bt.commission,
            slippage=bt.slippage,
            risk_free_rate=bt.risk_free_rate,
        )
    return MergedBacktestConfig(
        initial_capital=config.initial_capital if config.initial_capital is not None else bt.initial_capital,
        commission=config.commission if config.commission is not None else bt.commission,
        slippage=config.slippage if config.slippage is not None else bt.slippage,
        risk_free_rate=config.risk_free_rate if config.risk_free_rate is not None else bt.risk_free_rate,
    )


def run_research_job(
    ticker: str,
    strategy_name: str,
    start_date: str,
    end_date: str,
    config: BacktestConfig | None = None,
    progress_cb: ProgressCallback | None = None,
) -> dict:
    """Execute the full research pipeline with progress reporting and per-request config.

    This wraps the same building blocks as ResearchOrchestrator.run() but adds
    progress callbacks and per-request config overrides.
    """
    cb = progress_cb or _noop_progress
    merged = _merge_config(config)
    strategy_params = (config.strategy_params or {}) if config else {}
    metadata: dict[str, Any] = {"config": {"initial_capital": merged.initial_capital, "commission": merged.commission, "slippage": merged.slippage}}
    backtest_json: dict = {}
    risk_json: dict = {}
    validation_json: dict = {}
    decay_json: dict = {}
    signals: list = []

    # --- Step 1: Load price data ---
    cb("fetching_data", 0.0, f"Loading prices for {ticker}")
    try:
        from core.adapters import fetch_and_prepare_prices
        prices = fetch_and_prepare_prices(ticker, start_date, end_date)
        cb("fetching_data", 0.12, f"Loaded {len(prices)} price bars")
    except Exception as exc:
        return _error_result(ticker, strategy_name, start_date, end_date, f"Data load failed: {exc}")

    # --- Step 2: Resolve strategy ---
    cb("resolving_strategy", 0.14, f"Resolving strategy: {strategy_name}")
    try:
        from core.strategies import StrategyRegistry
        from core.orchestrator import _ensure_strategies_loaded
        _ensure_strategies_loaded()
        strategy = StrategyRegistry.get(strategy_name, **strategy_params)
    except Exception as exc:
        return _error_result(ticker, strategy_name, start_date, end_date, f"Strategy error: {exc}")

    # --- Step 3: Compute features ---
    cb("computing_features", 0.25, "Computing features")
    try:
        # For custom windows, compute the z-score directly instead of using the registry
        # This handles cases like zscore_30 when only zscore_20 is registered
        from features.technical.zscore import ZScoreFeature
        features = prices.clone()
        for feat_name in strategy.required_features:
            if feat_name.startswith("zscore_"):
                window = int(feat_name.split("_")[1])
                feat = ZScoreFeature(window=window)
                features = feat.compute(features)
            elif feat_name.startswith("momentum_"):
                from features.technical.momentum import MomentumFeature
                parts = feat_name.split("_")
                lookback = int(parts[1]) if len(parts) > 1 else 252
                skip = int(parts[2]) if len(parts) > 2 else 21
                feat = MomentumFeature(lookback=lookback, skip_recent=skip)
                features = feat.compute(features)
            else:
                # Fall back to registry for other features
                try:
                    from core.orchestrator import _compute_features
                    features = _compute_features([feat_name], features, ticker)
                except Exception:
                    pass

        # Ensure date column is proper Date type for backtest engine
        if "date" in features.columns:
            import polars as pl
            dtype = features["date"].dtype
            if isinstance(dtype, pl.Datetime):
                features = features.with_columns(pl.col("date").dt.date().alias("date"))

        cb("computing_features", 0.35, f"Features computed")
    except Exception as exc:
        return _error_result(ticker, strategy_name, start_date, end_date, f"Feature error: {exc}")

    # --- Step 4: Generate signals ---
    cb("generating_signals", 0.40, "Generating trading signals")
    try:
        signals = strategy.generate_signals(features)
        cb("generating_signals", 0.48, f"Generated {len(signals)} signals")
    except Exception as exc:
        return _error_result(ticker, strategy_name, start_date, end_date, f"Signal error: {exc}")

    # --- Step 5: Risk evaluation ---
    cb("evaluating_risk", 0.50, "Evaluating risk")
    try:
        from risk.manager import RiskManager
        from core.serialization import risk_assessment_to_json

        risk_mgr = RiskManager()
        empty_positions = pl.DataFrame(
            schema={"ticker": pl.Utf8, "weight": pl.Float64, "target_shares": pl.Float64, "target_value": pl.Float64}
        )
        assessment = risk_mgr.evaluate(signals, empty_positions, merged.initial_capital)
        risk_json = risk_assessment_to_json(assessment)
        signals_for_backtest = assessment.approved_signals
        cb("evaluating_risk", 0.58, f"{len(signals_for_backtest)} signals approved, {len(assessment.rejected_signals)} rejected")
    except Exception as exc:
        logger.warning("Risk evaluation failed: %s", exc)
        signals_for_backtest = signals

    # --- Step 6: Run backtest (with per-request config) ---
    cb("running_backtest", 0.60, "Running backtest")
    try:
        from core.adapters import prepare_signals_for_backtest
        from backtest.engine.vectorized import VectorizedBacktestEngine

        signals_df, bt_prices = prepare_signals_for_backtest(signals_for_backtest, prices)
        engine = VectorizedBacktestEngine()
        bt_result = engine.run(
            signals_df,
            bt_prices,
            initial_capital=merged.initial_capital,
            commission=merged.commission,
            slippage=merged.slippage,
        )
        backtest_json = bt_result.to_json()
        cb("running_backtest", 0.75, f"Backtest complete: Sharpe {bt_result.sharpe_ratio:.2f}")
    except Exception as exc:
        logger.error("Backtest failed: %s", exc)
        metadata.setdefault("errors", []).append(f"backtest: {exc}")

    # --- Step 7: Validation ---
    cb("validating", 0.78, "Running validation")
    try:
        from backtest.validation import BacktestValidator
        if backtest_json and backtest_json.get("sharpe_ratio") is not None:
            sharpe = backtest_json["sharpe_ratio"]
            n_obs = len(backtest_json.get("equity_curve", []))
            vr = BacktestValidator.deflated_sharpe_ratio(sharpe=sharpe, n_trials=1, n_observations=max(n_obs, 2))
            validation_json = {
                "is_valid": vr.is_valid, "deflated_sharpe": vr.deflated_sharpe,
                "original_sharpe": vr.original_sharpe, "p_value": vr.p_value,
            }
    except Exception as exc:
        logger.warning("Validation failed: %s", exc)

    # --- Step 8: Signal decay ---
    cb("signal_decay", 0.88, "Analyzing signal decay")
    try:
        if len(signals_for_backtest) >= 5:
            from analytics.signal_decay import SignalDecayAnalyzer
            from core.serialization import signals_to_dataframe
            analyzer = SignalDecayAnalyzer()
            sig_df = signals_to_dataframe(signals_for_backtest)
            ic_curve = analyzer.compute_ic_curve(sig_df, prices)
            decay_json = analyzer.decay_summary(ic_curve)
    except Exception as exc:
        logger.warning("Signal decay failed: %s", exc)

    cb("complete", 1.0, "Pipeline complete")

    from core.orchestrator import ResearchResult
    from dataclasses import asdict
    result = ResearchResult(
        strategy_name=strategy_name,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        signals_count=len(signals),
        backtest=backtest_json,
        risk_assessment=risk_json,
        validation=validation_json,
        signal_decay=decay_json,
        metadata=metadata,
    )
    return result.to_json()


def _error_result(ticker: str, strategy: str, start: str, end: str, error: str) -> dict:
    from core.orchestrator import ResearchResult
    return ResearchResult(
        strategy_name=strategy, ticker=ticker, start_date=start, end_date=end,
        signals_count=0, backtest={}, risk_assessment={}, validation={},
        signal_decay={}, metadata={"errors": [error]},
    ).to_json()
