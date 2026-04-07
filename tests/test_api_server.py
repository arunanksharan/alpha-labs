"""Tests for the FastAPI server endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from fastapi.testclient import TestClient

from api.server import app
from core.backtest import BacktestResult


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_backtest_result() -> BacktestResult:
    """Minimal BacktestResult for mocking pipeline outputs."""
    return BacktestResult(
        strategy_name="mean_reversion",
        start_date="2020-01-01",
        end_date="2024-12-31",
        total_return=0.42,
        annualized_return=0.08,
        sharpe_ratio=1.25,
        sortino_ratio=1.8,
        max_drawdown=-0.12,
        calmar_ratio=0.67,
        win_rate=0.55,
        profit_factor=1.4,
        equity_curve=pl.DataFrame({"date": ["2020-01-01"], "equity": [100_000.0]}),
        trades=pl.DataFrame(
            {
                "date": ["2020-06-01"],
                "ticker": ["AAPL"],
                "side": ["buy"],
                "price": [150.0],
                "quantity": [10.0],
                "pnl": [200.0],
            }
        ),
        monthly_returns=pl.DataFrame(
            {"year": [2020], "month": [1], "return": [0.02]}
        ),
    )


# ---------------------------------------------------------------------------
# Health & strategies
# ---------------------------------------------------------------------------


def test_health_endpoint(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["platform"] == "Agentic Alpha Lab"



def test_list_strategies_integration(client: TestClient) -> None:
    """Strategies endpoint returns a dict with a 'strategies' key.

    Uses a mock to avoid importing the real orchestrator which may have
    heavy dependencies.
    """
    with patch("core.orchestrator.ResearchOrchestrator") as mock_cls:
        instance = MagicMock()
        instance.list_strategies.return_value = ["mean_reversion", "momentum"]
        mock_cls.return_value = instance
        resp = client.get("/api/strategies")

    assert resp.status_code == 200
    data = resp.json()
    assert "strategies" in data
    assert isinstance(data["strategies"], list)


# ---------------------------------------------------------------------------
# Research endpoint
# ---------------------------------------------------------------------------


def test_research_endpoint_returns_json(
    client: TestClient, mock_backtest_result: BacktestResult
) -> None:
    """POST /api/research returns JSON-serialized result."""
    mock_research_result = MagicMock()
    mock_research_result.to_json.return_value = mock_backtest_result.to_json()

    with patch("core.orchestrator.ResearchOrchestrator") as mock_cls:
        instance = MagicMock()
        instance.run.return_value = mock_research_result
        mock_cls.return_value = instance

        resp = client.post(
            "/api/research",
            json={
                "ticker": "AAPL",
                "strategy": "mean_reversion",
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "sharpe_ratio" in data
    assert data["strategy_name"] == "mean_reversion"


# ---------------------------------------------------------------------------
# Backtest endpoint
# ---------------------------------------------------------------------------


def test_backtest_endpoint(
    client: TestClient, mock_backtest_result: BacktestResult
) -> None:
    """POST /api/backtest returns JSON-serialized BacktestResult."""
    mock_engine = MagicMock()
    mock_engine.run.return_value = mock_backtest_result

    with (
        patch("core.adapters.csv_to_dataframe", return_value=pl.DataFrame()),
        patch(
            "core.backtest.BacktestEngineRegistry.get", return_value=mock_engine
        ),
    ):
        resp = client.post(
            "/api/backtest",
            json={
                "signals_csv": "date,ticker,direction,confidence\n2020-01-02,AAPL,1.0,0.8",
                "prices_csv": "date,ticker,close\n2020-01-02,AAPL,150.0",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "sharpe_ratio" in data
    assert "equity_curve" in data


# ---------------------------------------------------------------------------
# Signal decay endpoint
# ---------------------------------------------------------------------------


def test_signal_decay_endpoint(client: TestClient) -> None:
    """POST /api/signal-decay returns IC curve and half-life."""
    mock_analyzer = MagicMock()
    mock_ic_curve = MagicMock()
    mock_ic_curve.to_dicts.return_value = [
        {"horizon": 1, "ic": 0.05},
        {"horizon": 5, "ic": 0.03},
    ]
    mock_analyzer.compute_ic_curve.return_value = mock_ic_curve
    mock_analyzer.compute_ic_half_life.return_value = 10.5
    mock_analyzer.decay_summary.return_value = "Signal decays over ~10 days"

    with (
        patch("core.adapters.csv_to_dataframe", return_value=pl.DataFrame()),
        patch(
            "analytics.signal_decay.SignalDecayAnalyzer",
            return_value=mock_analyzer,
        ),
    ):
        resp = client.post(
            "/api/signal-decay",
            json={
                "signals_csv": "date,ticker,signal_value\n2020-01-02,AAPL,0.5",
                "prices_csv": "date,ticker,close\n2020-01-02,AAPL,150.0",
                "max_horizon": 30,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "ic_curve" in data
    assert "half_life" in data
    assert "summary" in data
    assert data["half_life"] == 10.5
