"""Research orchestrator — unified entry point for the full quant research pipeline.

Designed for both human CLI usage and agent/MCP consumption.
All outputs are JSON-serializable.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

import polars as pl

from config.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ResearchResult:
    """Complete research output -- JSON-serializable via to_json()."""

    strategy_name: str
    ticker: str
    start_date: str
    end_date: str
    signals_count: int
    backtest: dict  # BacktestResult.to_json()
    risk_assessment: dict  # serialized RiskAssessment
    validation: dict  # serialized ValidationResult
    signal_decay: dict  # decay_summary
    metadata: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        """Already JSON-serializable (all fields are dicts/scalars)."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class ResearchOrchestrator:
    """Single entry point for the full quant research pipeline.

    Designed for both human CLI usage and agent/MCP consumption.
    All outputs are JSON-serializable.
    """

    def run(
        self,
        ticker: str,
        strategy_name: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100_000.0,
        **strategy_params: Any,
    ) -> ResearchResult:
        """Execute the full research pipeline.

        Steps:
            1. Load price data (DataStore -> YFinance fallback)
            2. Resolve strategy from StrategyRegistry
            3. Compute required features
            4. Generate signals
            5. Evaluate risk (RiskManager)
            6. Run backtest (VectorizedBacktestEngine)
            7. Validate (BacktestValidator -- deflated Sharpe)
            8. Analyse signal decay (if enough signals)
            9. Return ResearchResult with everything serialized

        Returns partial results with error info in metadata if a step fails.
        """
        metadata: dict[str, Any] = {}
        backtest_json: dict = {}
        risk_json: dict = {}
        validation_json: dict = {}
        decay_json: dict = {}
        signals: list = []

        # ------------------------------------------------------------------
        # 1. Load price data
        # ------------------------------------------------------------------
        try:
            from core.adapters import fetch_and_prepare_prices

            prices = fetch_and_prepare_prices(ticker, start_date, end_date)
        except Exception as exc:
            logger.error("Failed to load price data for %s: %s", ticker, exc)
            metadata["errors"] = metadata.get("errors", [])
            metadata["errors"].append(f"data_load: {exc}")
            return ResearchResult(
                strategy_name=strategy_name,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                signals_count=0,
                backtest=backtest_json,
                risk_assessment=risk_json,
                validation=validation_json,
                signal_decay=decay_json,
                metadata=metadata,
            )

        # ------------------------------------------------------------------
        # 2. Resolve strategy
        # ------------------------------------------------------------------
        try:
            from core.strategies import StrategyRegistry

            # Ensure strategy modules are imported so the registry is populated
            _ensure_strategies_loaded()
            strategy = StrategyRegistry.get(strategy_name, **strategy_params)
        except Exception as exc:
            logger.error("Failed to get strategy '%s': %s", strategy_name, exc)
            metadata.setdefault("errors", []).append(f"strategy_resolve: {exc}")
            return ResearchResult(
                strategy_name=strategy_name,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                signals_count=0,
                backtest=backtest_json,
                risk_assessment=risk_json,
                validation=validation_json,
                signal_decay=decay_json,
                metadata=metadata,
            )

        # ------------------------------------------------------------------
        # 3. Compute features
        # ------------------------------------------------------------------
        try:
            features = _compute_features(
                strategy.required_features, prices, ticker
            )
        except Exception as exc:
            logger.error("Feature computation failed: %s", exc)
            metadata.setdefault("errors", []).append(f"features: {exc}")
            return ResearchResult(
                strategy_name=strategy_name,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                signals_count=0,
                backtest=backtest_json,
                risk_assessment=risk_json,
                validation=validation_json,
                signal_decay=decay_json,
                metadata=metadata,
            )

        # ------------------------------------------------------------------
        # 4. Generate signals
        # ------------------------------------------------------------------
        try:
            signals = strategy.generate_signals(features)
            logger.info(
                "Strategy '%s' produced %d signals for %s",
                strategy_name,
                len(signals),
                ticker,
            )
        except Exception as exc:
            logger.error("Signal generation failed: %s", exc)
            metadata.setdefault("errors", []).append(f"signals: {exc}")
            return ResearchResult(
                strategy_name=strategy_name,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                signals_count=0,
                backtest=backtest_json,
                risk_assessment=risk_json,
                validation=validation_json,
                signal_decay=decay_json,
                metadata=metadata,
            )

        # ------------------------------------------------------------------
        # 5. Risk evaluation
        # ------------------------------------------------------------------
        try:
            from risk.manager import RiskManager
            from core.serialization import risk_assessment_to_json

            risk_mgr = RiskManager()
            empty_positions = pl.DataFrame(
                schema={
                    "ticker": pl.Utf8,
                    "weight": pl.Float64,
                    "target_shares": pl.Float64,
                    "target_value": pl.Float64,
                }
            )
            assessment = risk_mgr.evaluate(
                signals, empty_positions, initial_capital
            )
            risk_json = risk_assessment_to_json(assessment)
            # Use approved signals for the backtest
            signals_for_backtest = assessment.approved_signals
        except Exception as exc:
            logger.warning("Risk evaluation failed, using raw signals: %s", exc)
            metadata.setdefault("warnings", []).append(f"risk: {exc}")
            signals_for_backtest = signals

        # ------------------------------------------------------------------
        # 6. Run backtest
        # ------------------------------------------------------------------
        try:
            from core.adapters import prepare_signals_for_backtest
            from backtest.engine.vectorized import VectorizedBacktestEngine

            signals_df, bt_prices = prepare_signals_for_backtest(
                signals_for_backtest, prices
            )
            engine = VectorizedBacktestEngine()
            bt_result = engine.run(
                signals_df,
                bt_prices,
                initial_capital=initial_capital,
                commission=settings.backtest.commission,
                slippage=settings.backtest.slippage,
            )
            backtest_json = bt_result.to_json()
        except Exception as exc:
            logger.error("Backtest failed: %s", exc)
            metadata.setdefault("errors", []).append(f"backtest: {exc}")

        # ------------------------------------------------------------------
        # 7. Validate (deflated Sharpe)
        # ------------------------------------------------------------------
        try:
            from backtest.validation import BacktestValidator

            if backtest_json and backtest_json.get("sharpe_ratio") is not None:
                sharpe = backtest_json["sharpe_ratio"]
                # Use equity curve length as observation count
                n_obs = len(backtest_json.get("equity_curve", []))
                vr = BacktestValidator.deflated_sharpe_ratio(
                    sharpe=sharpe,
                    n_trials=1,
                    n_observations=max(n_obs, 2),
                )
                validation_json = {
                    "is_valid": vr.is_valid,
                    "deflated_sharpe": vr.deflated_sharpe,
                    "original_sharpe": vr.original_sharpe,
                    "p_value": vr.p_value,
                    "n_trials": vr.n_trials,
                    "warnings": vr.warnings,
                }
        except Exception as exc:
            logger.warning("Validation failed: %s", exc)
            metadata.setdefault("warnings", []).append(f"validation: {exc}")

        # ------------------------------------------------------------------
        # 8. Signal decay analysis
        # ------------------------------------------------------------------
        try:
            if len(signals_for_backtest) >= 5:
                from analytics.signal_decay import SignalDecayAnalyzer
                from core.serialization import signals_to_dataframe

                analyzer = SignalDecayAnalyzer()
                sig_df = signals_to_dataframe(signals_for_backtest)
                ic_curve = analyzer.compute_ic_curve(sig_df, prices)
                decay_json = analyzer.decay_summary(ic_curve)
            else:
                decay_json = {"note": "Too few signals for decay analysis"}
                logger.debug("Skipping decay: %d signals (need >= 5)", len(signals_for_backtest))
        except Exception as exc:
            logger.warning("Signal decay analysis failed: %s", exc)
            metadata.setdefault("warnings", []).append(f"signal_decay: {exc}")

        return ResearchResult(
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

    def quick_backtest(
        self,
        ticker: str,
        strategy_name: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100_000.0,
    ) -> dict:
        """Simplified pipeline: data -> features -> signals -> backtest -> JSON.

        Skips risk evaluation, validation, and decay analysis.
        """
        from core.adapters import fetch_and_prepare_prices, prepare_signals_for_backtest
        from core.strategies import StrategyRegistry
        from backtest.engine.vectorized import VectorizedBacktestEngine

        _ensure_strategies_loaded()

        prices = fetch_and_prepare_prices(ticker, start_date, end_date)
        strategy = StrategyRegistry.get(strategy_name)

        features = _compute_features(strategy.required_features, prices, ticker)
        signals = strategy.generate_signals(features)

        signals_df, bt_prices = prepare_signals_for_backtest(signals, prices)
        engine = VectorizedBacktestEngine()
        result = engine.run(
            signals_df,
            bt_prices,
            initial_capital=initial_capital,
            commission=settings.backtest.commission,
            slippage=settings.backtest.slippage,
        )
        return result.to_json()

    @staticmethod
    def list_strategies() -> list[dict]:
        """Return available strategies with their names and required features."""
        from core.strategies import StrategyRegistry

        _ensure_strategies_loaded()
        result = []
        for name in StrategyRegistry.list_strategies():
            try:
                strategy = StrategyRegistry.get(name)
                result.append(
                    {
                        "name": name,
                        "required_features": strategy.required_features,
                    }
                )
            except Exception:
                result.append({"name": name, "required_features": []})
        return result

    @staticmethod
    def list_connectors() -> list[str]:
        """Return available data connector names."""
        from core.connectors import ConnectorRegistry

        return ConnectorRegistry.list_connectors()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_strategies_loaded() -> None:
    """Import strategy modules so they register themselves."""
    try:
        import strategies.momentum.strategy  # noqa: F401
    except ImportError:
        pass
    try:
        import strategies.mean_reversion.strategy  # noqa: F401
    except ImportError:
        pass


def _compute_features(
    required_features: list[str],
    prices: pl.DataFrame,
    ticker: str,
) -> pl.DataFrame:
    """Compute required features and merge them onto a features DataFrame.

    Attempts to find each feature in the FeatureRegistry, computes it,
    and joins the result on ``date``.
    """
    from core.features import FeatureRegistry
    from core.utils import normalize_date_column

    # Ensure ticker column exists
    if "ticker" not in prices.columns:
        prices = prices.with_columns(pl.lit(ticker).alias("ticker"))
    prices = normalize_date_column(prices)

    features_df = prices.clone()

    for feat_name in required_features:
        try:
            feature = FeatureRegistry.get(feat_name)
            computed = feature.compute(prices)
            computed = normalize_date_column(computed)

            # Merge new columns (avoid duplicates)
            new_cols = [
                c for c in computed.columns if c not in features_df.columns
            ]
            if new_cols:
                join_cols = ["date"]
                if "ticker" in computed.columns:
                    join_cols.append("ticker")
                features_df = features_df.join(
                    computed.select(join_cols + new_cols),
                    on=join_cols,
                    how="left",
                )
        except KeyError:
            logger.warning(
                "Feature '%s' not found in registry, skipping", feat_name
            )

    return features_df
