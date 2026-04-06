"""Tests for all four core registries:
- ConnectorRegistry
- FeatureRegistry
- StrategyRegistry
- BacktestEngineRegistry
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl
import pytest

from core.backtest import (
    BacktestEngineRegistry,
    BacktestResult,
    BaseBacktestEngine,
)
from core.connectors import (
    BaseConnector,
    BaseMarketDataConnector,
    ConnectorRegistry,
)
from core.features import BaseFeature, FeatureRegistry
from core.strategies import BaseStrategy, Signal, StrategyRegistry


# ---------------------------------------------------------------------------
# Concrete implementations for testing
# ---------------------------------------------------------------------------

class _AlphaConnector(BaseMarketDataConnector):
    @property
    def name(self) -> str:
        return "alpha_v1"

    def connect(self) -> None:
        pass

    def health_check(self) -> bool:
        return True

    def fetch_ohlcv(self, ticker, start, end, interval="1d") -> pl.DataFrame:
        return pl.DataFrame()

    def fetch_multiple(self, tickers, start, end, interval="1d") -> dict[str, pl.DataFrame]:
        return {}

    def supported_intervals(self) -> list[str]:
        return ["1m", "5m", "1h", "1d"]


class _BetaConnector(BaseMarketDataConnector):
    @property
    def name(self) -> str:
        return "beta_v1"

    def connect(self) -> None:
        pass

    def health_check(self) -> bool:
        return False

    def fetch_ohlcv(self, ticker, start, end, interval="1d") -> pl.DataFrame:
        return pl.DataFrame()

    def fetch_multiple(self, tickers, start, end, interval="1d") -> dict[str, pl.DataFrame]:
        return {}

    def supported_intervals(self) -> list[str]:
        return ["1d"]


class _TechnicalFeature(BaseFeature):
    @property
    def name(self) -> str:
        return "rsi_14_test"

    @property
    def lookback_days(self) -> int:
        return 14

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        return data.with_columns(pl.lit(50.0).alias("rsi_14_test"))


class _FundamentalFeature(BaseFeature):
    @property
    def name(self) -> str:
        return "pe_ratio_test"

    @property
    def lookback_days(self) -> int:
        return 1

    @property
    def category(self) -> str:
        return "fundamental"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        return data.with_columns(pl.lit(20.0).alias("pe_ratio_test"))


class _MomentumStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "momentum_test"

    @property
    def required_features(self) -> list[str]:
        return ["rsi_14_test"]

    def generate_signals(self, features: pl.DataFrame) -> list[Signal]:
        return [
            Signal(ticker="AAPL", date="2024-01-15", direction=1.0, confidence=0.9),
            Signal(ticker="MSFT", date="2024-01-15", direction=-0.5, confidence=0.6),
        ]

    def get_positions(self, signals: list[Signal], capital: float) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "ticker": [s.ticker for s in signals],
                "weight": [s.direction for s in signals],
                "target_shares": [10.0] * len(signals),
                "target_value": [capital / len(signals)] * len(signals),
            }
        )


class _MeanReversionStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "mean_reversion_test"

    @property
    def required_features(self) -> list[str]:
        return ["pe_ratio_test"]

    def generate_signals(self, features: pl.DataFrame) -> list[Signal]:
        return []

    def get_positions(self, signals: list[Signal], capital: float) -> pl.DataFrame:
        return pl.DataFrame()


class _SimpleEngine(BaseBacktestEngine):
    @property
    def name(self) -> str:
        return "simple_engine_test"

    def run(self, signals, prices, initial_capital=100_000.0, commission=0.001, slippage=0.0005) -> BacktestResult:
        return BacktestResult(
            strategy_name="test",
            start_date="2024-01-01",
            end_date="2024-12-31",
            total_return=0.10,
            annualized_return=0.10,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=-0.05,
            calmar_ratio=2.0,
            win_rate=0.55,
            profit_factor=1.3,
            equity_curve=pl.DataFrame({"date": [], "equity": []}),
            trades=pl.DataFrame(),
            monthly_returns=pl.DataFrame(),
        )

    def walk_forward(self, signals, prices, train_window=252, test_window=63, **kwargs) -> list[BacktestResult]:
        return []


class _VectorEngine(BaseBacktestEngine):
    @property
    def name(self) -> str:
        return "vector_engine_test"

    def run(self, signals, prices, initial_capital=100_000.0, commission=0.001, slippage=0.0005) -> BacktestResult:
        return BacktestResult(
            strategy_name="vector_test",
            start_date="2024-01-01",
            end_date="2024-12-31",
            total_return=0.20,
            annualized_return=0.20,
            sharpe_ratio=2.0,
            sortino_ratio=2.5,
            max_drawdown=-0.08,
            calmar_ratio=2.5,
            win_rate=0.60,
            profit_factor=1.6,
            equity_curve=pl.DataFrame({"date": [], "equity": []}),
            trades=pl.DataFrame(),
            monthly_returns=pl.DataFrame(),
        )

    def walk_forward(self, signals, prices, train_window=252, test_window=63, **kwargs) -> list[BacktestResult]:
        return [self.run(signals, prices)]


# ---------------------------------------------------------------------------
# ConnectorRegistry
# ---------------------------------------------------------------------------

class TestConnectorRegistry:
    def setup_method(self) -> None:
        ConnectorRegistry._connectors.clear()

    def test_register_stores_class(self) -> None:
        ConnectorRegistry.register("alpha", _AlphaConnector)
        assert "alpha" in ConnectorRegistry.list_connectors()

    def test_get_returns_instance_of_correct_type(self) -> None:
        ConnectorRegistry.register("alpha", _AlphaConnector)
        connector = ConnectorRegistry.get("alpha")
        assert isinstance(connector, _AlphaConnector)

    def test_get_returns_new_instance_each_call(self) -> None:
        ConnectorRegistry.register("alpha", _AlphaConnector)
        c1 = ConnectorRegistry.get("alpha")
        c2 = ConnectorRegistry.get("alpha")
        assert c1 is not c2

    def test_list_connectors_returns_all_registered(self) -> None:
        ConnectorRegistry.register("alpha", _AlphaConnector)
        ConnectorRegistry.register("beta", _BetaConnector)
        names = ConnectorRegistry.list_connectors()
        assert "alpha" in names
        assert "beta" in names

    def test_list_connectors_empty_registry(self) -> None:
        assert ConnectorRegistry.list_connectors() == []

    def test_missing_connector_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            ConnectorRegistry.get("nonexistent_xyz")

    def test_error_message_lists_available_connectors(self) -> None:
        ConnectorRegistry.register("alpha", _AlphaConnector)
        with pytest.raises(KeyError, match="alpha"):
            ConnectorRegistry.get("nonexistent_xyz")

    def test_register_overwrites_existing_key(self) -> None:
        ConnectorRegistry.register("alpha", _AlphaConnector)
        ConnectorRegistry.register("alpha", _BetaConnector)
        connector = ConnectorRegistry.get("alpha")
        assert isinstance(connector, _BetaConnector)

    def test_connector_name_property(self) -> None:
        ConnectorRegistry.register("alpha", _AlphaConnector)
        connector = ConnectorRegistry.get("alpha")
        assert connector.name == "alpha_v1"

    def test_health_check_delegates_to_connector(self) -> None:
        ConnectorRegistry.register("alpha", _AlphaConnector)
        ConnectorRegistry.register("beta", _BetaConnector)
        assert ConnectorRegistry.get("alpha").health_check() is True
        assert ConnectorRegistry.get("beta").health_check() is False

    @pytest.mark.parametrize("key", ["yfinance", "tiingo", "alpaca", "ibkr"])
    def test_register_various_keys(self, key: str) -> None:
        ConnectorRegistry.register(key, _AlphaConnector)
        assert ConnectorRegistry.get(key).name == "alpha_v1"


# ---------------------------------------------------------------------------
# FeatureRegistry
# ---------------------------------------------------------------------------

class TestFeatureRegistry:
    def setup_method(self) -> None:
        FeatureRegistry._features.clear()

    def test_register_decorator_stores_class(self) -> None:
        FeatureRegistry.register(_TechnicalFeature)
        assert "rsi_14_test" in FeatureRegistry.list_features()

    def test_register_returns_class_unchanged(self) -> None:
        result = FeatureRegistry.register(_TechnicalFeature)
        assert result is _TechnicalFeature

    def test_get_returns_instance(self) -> None:
        FeatureRegistry.register(_TechnicalFeature)
        f = FeatureRegistry.get("rsi_14_test")
        assert isinstance(f, _TechnicalFeature)

    def test_get_returns_new_instance_each_call(self) -> None:
        FeatureRegistry.register(_TechnicalFeature)
        f1 = FeatureRegistry.get("rsi_14_test")
        f2 = FeatureRegistry.get("rsi_14_test")
        assert f1 is not f2

    def test_list_features_no_filter(self) -> None:
        FeatureRegistry.register(_TechnicalFeature)
        FeatureRegistry.register(_FundamentalFeature)
        names = FeatureRegistry.list_features()
        assert "rsi_14_test" in names
        assert "pe_ratio_test" in names

    def test_list_features_filter_by_category(self) -> None:
        FeatureRegistry.register(_TechnicalFeature)
        FeatureRegistry.register(_FundamentalFeature)
        technical = FeatureRegistry.list_features(category="technical")
        fundamental = FeatureRegistry.list_features(category="fundamental")
        assert "rsi_14_test" in technical
        assert "pe_ratio_test" not in technical
        assert "pe_ratio_test" in fundamental
        assert "rsi_14_test" not in fundamental

    def test_list_features_unknown_category_returns_empty(self) -> None:
        FeatureRegistry.register(_TechnicalFeature)
        result = FeatureRegistry.list_features(category="ml")
        assert result == []

    def test_missing_feature_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            FeatureRegistry.get("nonexistent_feature_xyz")

    def test_error_message_lists_available_features(self) -> None:
        FeatureRegistry.register(_TechnicalFeature)
        with pytest.raises(KeyError, match="rsi_14_test"):
            FeatureRegistry.get("nonexistent_xyz")

    def test_validate_sufficient_data(self) -> None:
        f = _TechnicalFeature()
        df = pl.DataFrame({"close": list(range(20))})
        assert f.validate(df) is True

    def test_validate_insufficient_data(self) -> None:
        f = _TechnicalFeature()
        df = pl.DataFrame({"close": list(range(5))})
        assert f.validate(df) is False

    def test_validate_exact_lookback_boundary(self) -> None:
        f = _TechnicalFeature()
        df = pl.DataFrame({"close": list(range(14))})
        assert f.validate(df) is True

    def test_compute_adds_column(self) -> None:
        f = _TechnicalFeature()
        df = pl.DataFrame({"close": [100.0, 101.0, 102.0]})
        result = f.compute(df)
        assert "rsi_14_test" in result.columns

    def test_feature_properties(self) -> None:
        f = _TechnicalFeature()
        assert f.lookback_days == 14
        assert f.category == "technical"
        assert f.name == "rsi_14_test"


# ---------------------------------------------------------------------------
# StrategyRegistry
# ---------------------------------------------------------------------------

class TestStrategyRegistry:
    def setup_method(self) -> None:
        StrategyRegistry._strategies.clear()

    def test_register_decorator_stores_class(self) -> None:
        StrategyRegistry.register(_MomentumStrategy)
        assert "momentum_test" in StrategyRegistry.list_strategies()

    def test_register_returns_class_unchanged(self) -> None:
        result = StrategyRegistry.register(_MomentumStrategy)
        assert result is _MomentumStrategy

    def test_get_returns_instance(self) -> None:
        StrategyRegistry.register(_MomentumStrategy)
        s = StrategyRegistry.get("momentum_test")
        assert isinstance(s, _MomentumStrategy)

    def test_get_returns_new_instance_each_call(self) -> None:
        StrategyRegistry.register(_MomentumStrategy)
        s1 = StrategyRegistry.get("momentum_test")
        s2 = StrategyRegistry.get("momentum_test")
        assert s1 is not s2

    def test_list_strategies_returns_all_registered(self) -> None:
        StrategyRegistry.register(_MomentumStrategy)
        StrategyRegistry.register(_MeanReversionStrategy)
        names = StrategyRegistry.list_strategies()
        assert "momentum_test" in names
        assert "mean_reversion_test" in names

    def test_missing_strategy_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            StrategyRegistry.get("nonexistent_strategy_xyz")

    def test_error_message_lists_available_strategies(self) -> None:
        StrategyRegistry.register(_MomentumStrategy)
        with pytest.raises(KeyError, match="momentum_test"):
            StrategyRegistry.get("nonexistent_xyz")

    def test_required_features_property(self) -> None:
        s = _MomentumStrategy()
        assert "rsi_14_test" in s.required_features

    def test_generate_signals_returns_signal_list(self) -> None:
        s = _MomentumStrategy()
        signals = s.generate_signals(pl.DataFrame())
        assert isinstance(signals, list)
        assert all(isinstance(sig, Signal) for sig in signals)

    def test_signal_direction_in_range(self) -> None:
        s = _MomentumStrategy()
        signals = s.generate_signals(pl.DataFrame())
        for sig in signals:
            assert -1.0 <= sig.direction <= 1.0

    def test_signal_confidence_in_range(self) -> None:
        s = _MomentumStrategy()
        signals = s.generate_signals(pl.DataFrame())
        for sig in signals:
            assert 0.0 <= sig.confidence <= 1.0

    def test_get_positions_returns_df(self) -> None:
        s = _MomentumStrategy()
        signals = s.generate_signals(pl.DataFrame())
        positions = s.get_positions(signals, capital=100_000.0)
        assert isinstance(positions, pl.DataFrame)

    def test_get_positions_capital_allocation(self) -> None:
        s = _MomentumStrategy()
        signals = s.generate_signals(pl.DataFrame())
        positions = s.get_positions(signals, capital=200_000.0)
        assert "target_value" in positions.columns
        total = positions["target_value"].sum()
        assert total <= 200_000.0 + 1.0

    def test_empty_signal_list(self) -> None:
        s = _MeanReversionStrategy()
        signals = s.generate_signals(pl.DataFrame())
        assert signals == []

    def test_signal_dataclass_fields(self) -> None:
        sig = Signal(ticker="TSLA", date="2024-06-01", direction=0.5, confidence=0.7)
        assert sig.ticker == "TSLA"
        assert sig.date == "2024-06-01"
        assert sig.direction == 0.5
        assert sig.confidence == 0.7
        assert sig.metadata is None

    def test_signal_with_metadata(self) -> None:
        sig = Signal(
            ticker="AAPL",
            date="2024-01-01",
            direction=1.0,
            confidence=0.9,
            metadata={"model": "xgboost", "score": 0.85},
        )
        assert sig.metadata["model"] == "xgboost"


# ---------------------------------------------------------------------------
# BacktestEngineRegistry
# ---------------------------------------------------------------------------

class TestBacktestEngineRegistry:
    def setup_method(self) -> None:
        BacktestEngineRegistry._engines.clear()

    def test_register_stores_class(self) -> None:
        BacktestEngineRegistry.register(_SimpleEngine)
        assert "simple_engine_test" in BacktestEngineRegistry.list_engines()

    def test_register_returns_class_unchanged(self) -> None:
        result = BacktestEngineRegistry.register(_SimpleEngine)
        assert result is _SimpleEngine

    def test_get_returns_instance(self) -> None:
        BacktestEngineRegistry.register(_SimpleEngine)
        engine = BacktestEngineRegistry.get("simple_engine_test")
        assert isinstance(engine, _SimpleEngine)

    def test_get_returns_new_instance_each_call(self) -> None:
        BacktestEngineRegistry.register(_SimpleEngine)
        e1 = BacktestEngineRegistry.get("simple_engine_test")
        e2 = BacktestEngineRegistry.get("simple_engine_test")
        assert e1 is not e2

    def test_list_engines_returns_all_registered(self) -> None:
        BacktestEngineRegistry.register(_SimpleEngine)
        BacktestEngineRegistry.register(_VectorEngine)
        names = BacktestEngineRegistry.list_engines()
        assert "simple_engine_test" in names
        assert "vector_engine_test" in names

    def test_missing_engine_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            BacktestEngineRegistry.get("nonexistent_engine_xyz")

    def test_error_message_lists_available_engines(self) -> None:
        BacktestEngineRegistry.register(_SimpleEngine)
        with pytest.raises(KeyError, match="simple_engine_test"):
            BacktestEngineRegistry.get("nonexistent_xyz")

    def test_run_returns_backtest_result(self) -> None:
        BacktestEngineRegistry.register(_SimpleEngine)
        engine = BacktestEngineRegistry.get("simple_engine_test")
        result = engine.run(pl.DataFrame(), pl.DataFrame())
        assert isinstance(result, BacktestResult)

    def test_backtest_result_core_metrics_present(self) -> None:
        engine = _SimpleEngine()
        result = engine.run(pl.DataFrame(), pl.DataFrame())
        assert result.total_return == pytest.approx(0.10)
        assert result.sharpe_ratio == pytest.approx(1.5)
        assert result.max_drawdown == pytest.approx(-0.05)
        assert 0.0 <= result.win_rate <= 1.0

    def test_backtest_result_optional_fields_default_none(self) -> None:
        engine = _SimpleEngine()
        result = engine.run(pl.DataFrame(), pl.DataFrame())
        assert result.information_ratio is None
        assert result.beta is None
        assert result.alpha is None
        assert result.var_95 is None
        assert result.cvar_95 is None

    def test_backtest_result_transaction_costs_default(self) -> None:
        engine = _SimpleEngine()
        result = engine.run(pl.DataFrame(), pl.DataFrame())
        assert result.transaction_costs == 0.0

    def test_backtest_result_metadata_default_empty_dict(self) -> None:
        engine = _SimpleEngine()
        result = engine.run(pl.DataFrame(), pl.DataFrame())
        assert result.metadata == {}

    def test_walk_forward_returns_list(self) -> None:
        BacktestEngineRegistry.register(_VectorEngine)
        engine = BacktestEngineRegistry.get("vector_engine_test")
        results = engine.walk_forward(pl.DataFrame(), pl.DataFrame())
        assert isinstance(results, list)

    def test_walk_forward_each_item_is_backtest_result(self) -> None:
        engine = _VectorEngine()
        results = engine.walk_forward(pl.DataFrame(), pl.DataFrame())
        for r in results:
            assert isinstance(r, BacktestResult)

    def test_register_overwrites_existing_key(self) -> None:
        BacktestEngineRegistry.register(_SimpleEngine)
        BacktestEngineRegistry.register(_VectorEngine)
        BacktestEngineRegistry._engines["simple_engine_test"] = _VectorEngine
        engine = BacktestEngineRegistry.get("simple_engine_test")
        assert isinstance(engine, _VectorEngine)

    @pytest.mark.parametrize("commission,slippage", [
        (0.001, 0.0005),
        (0.0, 0.0),
        (0.01, 0.001),
    ])
    def test_run_with_various_cost_params(self, commission: float, slippage: float) -> None:
        engine = _SimpleEngine()
        result = engine.run(
            pl.DataFrame(), pl.DataFrame(),
            initial_capital=50_000.0,
            commission=commission,
            slippage=slippage,
        )
        assert isinstance(result, BacktestResult)
