"""Tests for the multi-agent LangGraph research pipeline.

All tests work without LangGraph installed -- they exercise the individual
node functions and the sequential fallback runner.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.state import AgentEvent, AgentStatus, ResearchState
from agents.nodes import (
    approval_gate,
    decay_agent,
    report_agent,
    research_agent,
    risk_agent,
    validation_agent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides) -> ResearchState:
    """Create a minimal ResearchState for testing."""
    defaults = {
        "ticker": "AAPL",
        "strategy_name": "momentum",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "initial_capital": 100_000.0,
    }
    defaults.update(overrides)
    return ResearchState(**defaults)


def _make_signal_dict(
    ticker: str = "AAPL",
    date: str = "2023-06-15",
    direction: float = 1.0,
    confidence: float = 0.8,
) -> dict:
    return {
        "ticker": ticker,
        "date": date,
        "direction": direction,
        "confidence": confidence,
        "metadata": None,
    }


# ---------------------------------------------------------------------------
# State & event tests
# ---------------------------------------------------------------------------


class TestResearchState:
    def test_research_state_creation(self):
        state = _make_state()
        assert state.ticker == "AAPL"
        assert state.strategy_name == "momentum"
        assert state.start_date == "2023-01-01"
        assert state.end_date == "2023-12-31"
        assert state.initial_capital == 100_000.0
        assert state.events == []
        assert state.errors == []
        assert state.signals == []
        assert state.human_approval_required is False
        assert state.human_approved is None

    def test_add_event(self):
        state = _make_state()
        state.add_event("research", AgentStatus.RUNNING, "Starting...")
        assert len(state.events) == 1
        evt = state.events[0]
        assert evt["agent_name"] == "research"
        assert evt["status"] == "running"
        assert evt["message"] == "Starting..."
        assert evt["timestamp"]  # non-empty ISO string


class TestAgentEvent:
    def test_agent_event_to_json(self):
        event = AgentEvent(
            agent_name="risk",
            status=AgentStatus.COMPLETED,
            message="Done",
            data={"count": 5},
            timestamp="2023-06-15T12:00:00",
        )
        result = event.to_json()
        assert result == {
            "agent_name": "risk",
            "status": "completed",
            "message": "Done",
            "data": {"count": 5},
            "timestamp": "2023-06-15T12:00:00",
        }

    def test_agent_event_default_fields(self):
        event = AgentEvent(
            agent_name="test",
            status=AgentStatus.PENDING,
            message="hello",
        )
        assert event.data == {}
        assert event.timestamp == ""


# ---------------------------------------------------------------------------
# Individual node tests
# ---------------------------------------------------------------------------


class TestResearchAgent:
    @patch("agents.nodes.fetch_and_prepare_prices", create=True)
    def test_research_agent_populates_events(self, _mock_fetch):
        """research_agent emits events even when imports fail (graceful)."""
        state = _make_state()

        # The agent will try real imports which may fail in test env --
        # that is fine, we just verify it returns state with events.
        result = research_agent(state)

        assert isinstance(result, ResearchState)
        assert len(result.events) >= 1
        # First event should be the "Fetching data..." running event
        assert result.events[0]["agent_name"] == "research"
        assert result.events[0]["status"] == "running"

    @patch("agents.nodes.signal_to_json", create=True)
    @patch("agents.nodes._compute_features", create=True)
    @patch("agents.nodes._ensure_strategies_loaded", create=True)
    @patch("agents.nodes.df_to_json", create=True)
    @patch("agents.nodes.fetch_and_prepare_prices", create=True)
    def test_research_agent_success_path(
        self, mock_fetch, mock_df_json, mock_ensure, mock_features, mock_sig_json
    ):
        """Full success path with all imports mocked at module level."""
        import polars as pl

        mock_prices = pl.DataFrame({"date": ["2023-01-01"], "close": [150.0]})

        with (
            patch("core.adapters.fetch_and_prepare_prices", return_value=mock_prices),
            patch("core.serialization.df_to_json", return_value=[{"date": "2023-01-01", "close": 150.0}]),
            patch("core.orchestrator._ensure_strategies_loaded"),
            patch("core.orchestrator._compute_features", return_value=mock_prices),
            patch(
                "core.strategies.StrategyRegistry.get",
                return_value=MagicMock(
                    required_features=["rsi"],
                    generate_signals=MagicMock(return_value=[]),
                ),
            ),
        ):
            state = _make_state()
            result = research_agent(state)

            assert isinstance(result, ResearchState)
            assert len(result.events) >= 1


class TestRiskAgent:
    def test_risk_agent_populates_risk_assessment(self):
        """risk_agent handles gracefully when platform modules unavailable."""
        state = _make_state()
        state.signals = [_make_signal_dict()]

        result = risk_agent(state)

        assert isinstance(result, ResearchState)
        # Should have at least the "Evaluating risk..." event
        assert any(
            e["agent_name"] == "risk" for e in result.events
        )

    def test_risk_agent_no_signals(self):
        state = _make_state()
        state.signals = []

        result = risk_agent(state)

        assert any(
            e["message"] == "No signals to evaluate" for e in result.events
        )

    @patch("risk.manager.RiskManager", create=True)
    def test_risk_agent_sets_human_approval_on_rejection(self, mock_rm_cls):
        """When risk manager rejects signals, human_approval_required is set."""
        from core.strategies import Signal

        approved = Signal("AAPL", "2023-06-15", 1.0, 0.9)
        rejected = Signal("AAPL", "2023-06-16", -1.0, 0.3)

        mock_assessment = MagicMock()
        mock_assessment.approved_signals = [approved]
        mock_assessment.rejected_signals = [rejected]
        mock_assessment.portfolio_var = 0.02
        mock_assessment.portfolio_cvar = 0.03
        mock_assessment.max_position_size = 0.1
        mock_assessment.warnings = []

        mock_rm = MagicMock()
        mock_rm.evaluate.return_value = mock_assessment
        mock_rm_cls.return_value = mock_rm

        with patch(
            "core.serialization.risk_assessment_to_json",
            return_value={
                "approved_signals": [_make_signal_dict()],
                "rejected_signals": [_make_signal_dict(direction=-1.0)],
                "portfolio_var": 0.02,
                "portfolio_cvar": 0.03,
                "max_position_size": 0.1,
                "warnings": [],
            },
        ):
            state = _make_state()
            state.signals = [_make_signal_dict(), _make_signal_dict(direction=-1.0)]
            result = risk_agent(state)

            assert result.human_approval_required is True


# ---------------------------------------------------------------------------
# Approval gate tests
# ---------------------------------------------------------------------------


class TestApprovalGate:
    def test_approval_gate_continue_when_no_approval_needed(self):
        state = _make_state()
        state.human_approval_required = False
        assert approval_gate(state) == "continue"

    def test_approval_gate_wait_when_approval_pending(self):
        state = _make_state()
        state.human_approval_required = True
        state.human_approved = None
        assert approval_gate(state) == "wait"

    def test_approval_gate_continue_when_approved(self):
        state = _make_state()
        state.human_approval_required = True
        state.human_approved = True
        assert approval_gate(state) == "continue"

    def test_approval_gate_abort_when_rejected(self):
        state = _make_state()
        state.human_approval_required = True
        state.human_approved = False
        assert approval_gate(state) == "abort"


# ---------------------------------------------------------------------------
# Validation, decay, report agent tests
# ---------------------------------------------------------------------------


class TestValidationAgent:
    def test_validation_agent_no_signals(self):
        state = _make_state()
        result = validation_agent(state)
        assert isinstance(result, ResearchState)
        assert any(e["agent_name"] == "validation" for e in result.events)

    def test_validation_agent_handles_errors(self):
        """Does not crash with empty signals list."""
        state = _make_state()
        state.signals = []
        result = validation_agent(state)
        assert isinstance(result, ResearchState)


class TestDecayAgent:
    def test_decay_agent_no_signals(self):
        state = _make_state()
        result = decay_agent(state)
        assert isinstance(result, ResearchState)
        assert result.signal_decay.get("note")

    def test_decay_agent_few_signals(self):
        state = _make_state()
        state.signals = [_make_signal_dict() for _ in range(5)]
        result = decay_agent(state)
        assert "Too few signals" in result.signal_decay.get("note", "")


class TestReportAgent:
    def test_report_agent_generates_html(self):
        state = _make_state()
        state.signals = [_make_signal_dict()]
        result = report_agent(state)
        assert "<h1>" in result.research_report
        assert "AAPL" in result.research_report
        assert "momentum" in result.research_report

    def test_report_agent_includes_errors(self):
        state = _make_state()
        state.errors = ["Something went wrong"]
        result = report_agent(state)
        assert "Something went wrong" in result.research_report

    def test_report_agent_includes_backtest(self):
        state = _make_state()
        state.backtest_result = {
            "total_return": 0.15,
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.08,
            "win_rate": 0.55,
        }
        result = report_agent(state)
        assert "1.2" in result.research_report  # sharpe
        assert "0.15" in result.research_report  # total return


# ---------------------------------------------------------------------------
# AgentRunner integration tests (sequential fallback)
# ---------------------------------------------------------------------------


class TestAgentRunner:
    @patch("agents.graph.build_research_graph", return_value=None)
    def test_agent_runner_sequential_fallback(self, _mock_graph):
        """Runner works without LangGraph via sequential fallback."""
        from agents.graph import AgentRunner

        with (
            patch("agents.graph.research_agent", side_effect=lambda s: s) as mock_ra,
            patch("agents.graph.risk_agent", side_effect=lambda s: s) as mock_risk,
            patch("agents.graph.approval_gate", return_value="continue") as mock_gate,
            patch("agents.graph.validation_agent", side_effect=lambda s: s) as mock_va,
            patch("agents.graph.decay_agent", side_effect=lambda s: s) as mock_da,
            patch("agents.graph.report_agent", side_effect=lambda s: s) as mock_rep,
        ):
            runner = AgentRunner()
            assert runner._graph is None

            result = runner.run("AAPL", "momentum", "2023-01-01", "2023-12-31")

            assert isinstance(result, ResearchState)
            mock_ra.assert_called_once()
            mock_risk.assert_called_once()
            mock_gate.assert_called_once()
            mock_va.assert_called_once()
            mock_da.assert_called_once()
            mock_rep.assert_called_once()

    @patch("agents.graph.build_research_graph", return_value=None)
    def test_agent_runner_approve_continues_pipeline(self, _mock_graph):
        """Approving resumes validation -> decay -> report."""
        from agents.graph import AgentRunner

        with (
            patch("agents.graph.validation_agent", side_effect=lambda s: s) as mock_va,
            patch("agents.graph.decay_agent", side_effect=lambda s: s) as mock_da,
            patch("agents.graph.report_agent", side_effect=lambda s: s) as mock_rep,
        ):
            runner = AgentRunner()
            state = _make_state()
            state.human_approval_required = True
            state.human_approved = None

            result = runner.approve(state)

            assert result.human_approved is True
            assert any(e["status"] == "approved" for e in result.events)
            mock_va.assert_called_once()
            mock_da.assert_called_once()
            mock_rep.assert_called_once()

    @patch("agents.graph.build_research_graph", return_value=None)
    def test_agent_runner_reject_goes_to_report(self, _mock_graph):
        """Rejecting skips to report only."""
        from agents.graph import AgentRunner

        with (
            patch("agents.graph.validation_agent", side_effect=lambda s: s) as mock_va,
            patch("agents.graph.report_agent", side_effect=lambda s: s) as mock_rep,
        ):
            runner = AgentRunner()
            state = _make_state()
            state.human_approval_required = True

            result = runner.reject(state)

            assert result.human_approved is False
            assert any(e["status"] == "rejected" for e in result.events)
            mock_va.assert_not_called()
            mock_rep.assert_called_once()

    @patch("agents.graph.build_research_graph", return_value=None)
    def test_agent_runner_skips_validation_on_abort(self, _mock_graph):
        """When approval_gate returns 'abort', validation/decay are skipped."""
        from agents.graph import AgentRunner

        with (
            patch("agents.graph.research_agent", side_effect=lambda s: s),
            patch("agents.graph.risk_agent", side_effect=lambda s: s),
            patch("agents.graph.approval_gate", return_value="abort"),
            patch("agents.graph.validation_agent", side_effect=lambda s: s) as mock_va,
            patch("agents.graph.decay_agent", side_effect=lambda s: s) as mock_da,
            patch("agents.graph.report_agent", side_effect=lambda s: s) as mock_rep,
        ):
            runner = AgentRunner()
            result = runner.run("AAPL", "momentum", "2023-01-01", "2023-12-31")

            mock_va.assert_not_called()
            mock_da.assert_not_called()
            mock_rep.assert_called_once()


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------


class TestErrorResilience:
    def test_all_agents_handle_errors_gracefully(self):
        """Every agent returns a valid state even with empty/minimal input."""
        state = _make_state()

        # Each agent should never raise, even with no data populated
        state = research_agent(state)
        assert isinstance(state, ResearchState)

        state = risk_agent(state)
        assert isinstance(state, ResearchState)

        state = validation_agent(state)
        assert isinstance(state, ResearchState)

        state = decay_agent(state)
        assert isinstance(state, ResearchState)

        state = report_agent(state)
        assert isinstance(state, ResearchState)

        # Should have accumulated events (no crashes)
        assert len(state.events) > 0
        # Report should have been generated
        assert state.research_report != ""
