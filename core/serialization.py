"""Serialization utilities for agent-native JSON compatibility.

Converts polars DataFrames and platform dataclasses to/from JSON-serializable dicts.
This is the bridge between the polars-native internal layer and the
JSON-native agent/API layer.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from typing import Any

import polars as pl


class DataFrameEncoder(json.JSONEncoder):
    """JSON encoder that handles pl.DataFrame and pl.Series."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, pl.DataFrame):
            return obj.to_dicts()
        if isinstance(obj, pl.Series):
            return obj.to_list()
        return super().default(obj)


def df_to_json(df: pl.DataFrame) -> list[dict]:
    """Convert DataFrame to list of row dicts (JSON-serializable)."""
    if df.is_empty():
        return []
    return df.to_dicts()


def df_from_json(data: list[dict], schema: dict[str, Any] | None = None) -> pl.DataFrame:
    """Reconstruct DataFrame from list of row dicts."""
    if not data:
        if schema:
            return pl.DataFrame(schema=schema)
        return pl.DataFrame()
    return pl.DataFrame(data)


def backtest_result_to_json(result: "BacktestResult") -> dict:
    """Serialize BacktestResult to JSON-compatible dict."""
    from core.backtest import BacktestResult

    return {
        "strategy_name": result.strategy_name,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "total_return": result.total_return,
        "annualized_return": result.annualized_return,
        "sharpe_ratio": result.sharpe_ratio,
        "sortino_ratio": result.sortino_ratio,
        "max_drawdown": result.max_drawdown,
        "calmar_ratio": result.calmar_ratio,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "equity_curve": df_to_json(result.equity_curve),
        "trades": df_to_json(result.trades),
        "monthly_returns": df_to_json(result.monthly_returns),
        "information_ratio": result.information_ratio,
        "beta": result.beta,
        "alpha": result.alpha,
        "var_95": result.var_95,
        "cvar_95": result.cvar_95,
        "transaction_costs": result.transaction_costs,
        "slippage_model": result.slippage_model,
        "metadata": result.metadata,
    }


def backtest_result_from_json(data: dict) -> "BacktestResult":
    """Deserialize JSON dict back to BacktestResult."""
    from core.backtest import BacktestResult

    return BacktestResult(
        strategy_name=data["strategy_name"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        total_return=data["total_return"],
        annualized_return=data["annualized_return"],
        sharpe_ratio=data["sharpe_ratio"],
        sortino_ratio=data["sortino_ratio"],
        max_drawdown=data["max_drawdown"],
        calmar_ratio=data["calmar_ratio"],
        win_rate=data["win_rate"],
        profit_factor=data["profit_factor"],
        equity_curve=df_from_json(data.get("equity_curve", [])),
        trades=df_from_json(data.get("trades", [])),
        monthly_returns=df_from_json(data.get("monthly_returns", [])),
        information_ratio=data.get("information_ratio"),
        beta=data.get("beta"),
        alpha=data.get("alpha"),
        var_95=data.get("var_95"),
        cvar_95=data.get("cvar_95"),
        transaction_costs=data.get("transaction_costs", 0.0),
        slippage_model=data.get("slippage_model", "none"),
        metadata=data.get("metadata", {}),
    )


def signal_to_json(signal: "Signal") -> dict:
    """Serialize Signal dataclass."""
    return {
        "ticker": signal.ticker,
        "date": signal.date,
        "direction": signal.direction,
        "confidence": signal.confidence,
        "metadata": signal.metadata,
    }


def signal_from_json(data: dict) -> "Signal":
    """Deserialize JSON to Signal."""
    from core.strategies import Signal

    return Signal(
        ticker=data["ticker"],
        date=data["date"],
        direction=data["direction"],
        confidence=data["confidence"],
        metadata=data.get("metadata"),
    )


def signals_to_dataframe(signals: list["Signal"]) -> pl.DataFrame:
    """Convert list[Signal] to DataFrame for backtest engine consumption."""
    if not signals:
        return pl.DataFrame(
            schema={"date": pl.Utf8, "ticker": pl.Utf8, "direction": pl.Float64, "confidence": pl.Float64}
        )
    return pl.DataFrame([signal_to_json(s) for s in signals]).select(
        "date", "ticker", "direction", "confidence"
    )


def risk_assessment_to_json(assessment: "RiskAssessment") -> dict:
    """Serialize RiskAssessment."""
    return {
        "approved_signals": [signal_to_json(s) for s in assessment.approved_signals],
        "rejected_signals": [signal_to_json(s) for s in assessment.rejected_signals],
        "portfolio_var": assessment.portfolio_var,
        "portfolio_cvar": assessment.portfolio_cvar,
        "max_position_size": assessment.max_position_size,
        "warnings": assessment.warnings,
    }


def portfolio_result_to_json(result: "PortfolioResult") -> dict:
    """Serialize PortfolioResult."""
    return {
        "weights": result.weights,
        "expected_return": result.expected_return,
        "expected_vol": result.expected_vol,
        "sharpe_ratio": result.sharpe_ratio,
        "method": result.method,
    }
