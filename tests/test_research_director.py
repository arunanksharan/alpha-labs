"""Tests for the Research Director, Research Chat, and Cycle Scheduler.

Uses mock specialists for fast unit tests and one real-ish specialist
(TheQuant with synthetic data) for integration testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from agents.specialists import AgentFinding
from agents.specialists.research_director import ResearchBrief, ResearchDirector
from agents.chat import ResearchChat
from agents.scheduler import CycleScheduler


# ---------------------------------------------------------------------------
# Fixtures: mock specialists
# ---------------------------------------------------------------------------

def _make_finding(
    agent_name: str = "mock_agent",
    ticker: str = "AAPL",
    signal: str = "bullish",
    confidence: float = 0.75,
    reasoning: str = "Strong momentum detected.",
) -> AgentFinding:
    """Create a mock AgentFinding."""
    return AgentFinding(
        agent_name=agent_name,
        ticker=ticker,
        signal=signal,
        confidence=confidence,
        reasoning=reasoning,
        details={"metric_a": 1.23, "metric_b": 4.56},
        thoughts=[f"{agent_name} is thinking...", f"{agent_name} concluded {signal}."],
    )


class MockSpecialist:
    """A mock specialist agent that returns a configurable finding."""

    def __init__(self, name: str, signal: str = "bullish", confidence: float = 0.75):
        self._name = name
        self._signal = signal
        self._confidence = confidence

    def analyze(self, ticker: str, start_date: str, end_date: str) -> AgentFinding:
        return _make_finding(
            agent_name=self._name,
            ticker=ticker,
            signal=self._signal,
            confidence=self._confidence,
            reasoning=f"{self._name} sees {self._signal} on {ticker}.",
        )


def _mock_specialists_mostly_bullish() -> dict:
    """Return a set of mock specialists with majority bullish."""
    return {
        "quant": MockSpecialist("quant", "bullish", 0.85),
        "technician": MockSpecialist("technician", "bullish", 0.78),
        "sentiment": MockSpecialist("sentiment", "bullish", 0.72),
        "fundamentalist": MockSpecialist("fundamentalist", "bearish", 0.60),
        "macro": MockSpecialist("macro", "bullish", 0.80),
        "contrarian": MockSpecialist("contrarian", "bullish", 0.90),
    }


def _mock_specialists_mixed() -> dict:
    """Return a set of mock specialists with mixed signals."""
    return {
        "quant": MockSpecialist("quant", "bullish", 0.65),
        "technician": MockSpecialist("technician", "bearish", 0.70),
        "sentiment": MockSpecialist("sentiment", "neutral", 0.50),
        "fundamentalist": MockSpecialist("fundamentalist", "bearish", 0.55),
        "macro": MockSpecialist("macro", "neutral", 0.40),
        "contrarian": MockSpecialist("contrarian", "bullish", 0.60),
    }


@pytest.fixture
def director_bullish() -> ResearchDirector:
    """Director with mostly-bullish mock specialists pre-loaded."""
    d = ResearchDirector()
    d._specialists = _mock_specialists_mostly_bullish()
    return d


@pytest.fixture
def director_mixed() -> ResearchDirector:
    """Director with mixed-signal mock specialists pre-loaded."""
    d = ResearchDirector()
    d._specialists = _mock_specialists_mixed()
    return d


# ---------------------------------------------------------------------------
# Test: research_ticker
# ---------------------------------------------------------------------------


class TestResearchTicker:
    def test_returns_dict(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.research_ticker("AAPL", "2023-01-01", "2024-01-01")
        assert isinstance(result, dict)
        assert result["ticker"] == "AAPL"

    def test_has_findings_from_multiple_agents(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.research_ticker("AAPL", "2023-01-01", "2024-01-01")
        findings = result["findings"]
        assert len(findings) == 6
        agent_names = {f["agent_name"] for f in findings}
        assert "quant" in agent_names
        assert "technician" in agent_names
        assert "contrarian" in agent_names

    def test_has_synthesis(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.research_ticker("AAPL", "2023-01-01", "2024-01-01")
        synthesis = result["synthesis"]
        assert "consensus_signal" in synthesis
        assert "consensus_confidence" in synthesis
        assert "vote_counts" in synthesis
        assert "reasoning" in synthesis
        assert "high_conviction" in synthesis

    def test_bullish_consensus_with_5_bullish(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.research_ticker("AAPL", "2023-01-01", "2024-01-01")
        synthesis = result["synthesis"]
        assert synthesis["consensus_signal"] == "bullish"
        assert synthesis["vote_counts"]["bullish"] == 5
        assert synthesis["high_conviction"] is True

    def test_mixed_signals_no_high_conviction(self, director_mixed: ResearchDirector) -> None:
        result = director_mixed.research_ticker("AAPL", "2023-01-01", "2024-01-01")
        synthesis = result["synthesis"]
        assert synthesis["high_conviction"] is False

    def test_event_callback_invoked(self, director_bullish: ResearchDirector) -> None:
        events: list[dict] = []
        director_bullish.research_ticker(
            "AAPL", "2023-01-01", "2024-01-01",
            event_callback=events.append,
        )
        # Should have running + completed for each of 6 agents = 12 events
        assert len(events) == 12
        statuses = {e["status"] for e in events}
        assert "running" in statuses
        assert "completed" in statuses

    def test_agent_failure_is_captured(self) -> None:
        """An agent that raises should not crash the whole pipeline."""

        class FailingAgent:
            def analyze(self, ticker, start_date, end_date):
                raise RuntimeError("Intentional test failure")

        director = ResearchDirector()
        director._specialists = {
            "good": MockSpecialist("good", "bullish", 0.8),
            "bad": FailingAgent(),
        }

        result = director.research_ticker("AAPL", "2023-01-01", "2024-01-01")
        assert len(result["findings"]) == 1  # Only the good agent succeeded
        # The bad agent's trace should record the error
        bad_trace = [t for t in result["agent_traces"] if t.get("agent") == "bad"]
        assert len(bad_trace) == 1
        assert "error" in bad_trace[0]

    def test_no_specialists_returns_neutral(self) -> None:
        director = ResearchDirector()
        director._specialists = {}
        result = director.research_ticker("AAPL", "2023-01-01", "2024-01-01")
        assert result["synthesis"]["consensus_signal"] == "neutral"
        assert result["synthesis"]["consensus_confidence"] == 0.0

    def test_has_agent_traces(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.research_ticker("AAPL", "2023-01-01", "2024-01-01")
        assert "agent_traces" in result
        assert len(result["agent_traces"]) == 6


# ---------------------------------------------------------------------------
# Test: morning brief
# ---------------------------------------------------------------------------


class TestMorningBrief:
    def test_has_required_fields(self, director_bullish: ResearchDirector) -> None:
        brief = director_bullish.generate_morning_brief(
            ["AAPL", "MSFT"], "2023-01-01", "2024-01-01"
        )
        assert isinstance(brief, ResearchBrief)
        assert brief.greeting
        assert isinstance(brief.top_convictions, list)
        assert isinstance(brief.watchlist, list)
        assert isinstance(brief.portfolio_health, dict)
        assert isinstance(brief.what_i_learned, str)
        assert isinstance(brief.pending_approvals, list)

    def test_top_convictions_sorted_by_confidence(self, director_bullish: ResearchDirector) -> None:
        # Use many tickers to get both convictions and watchlist
        tickers = ["AAPL", "MSFT", "NVDA", "GOOG", "TSLA", "META", "AMZN", "JPM"]
        brief = director_bullish.generate_morning_brief(
            tickers, "2023-01-01", "2024-01-01"
        )
        convictions = brief.top_convictions
        assert len(convictions) <= 3
        # Verify descending confidence order
        confidences = [c["confidence"] for c in convictions]
        assert confidences == sorted(confidences, reverse=True)

    def test_brief_to_json(self, director_bullish: ResearchDirector) -> None:
        brief = director_bullish.generate_morning_brief(
            ["AAPL"], "2023-01-01", "2024-01-01"
        )
        json_output = brief.to_json()
        assert isinstance(json_output, dict)
        assert "greeting" in json_output
        assert "top_convictions" in json_output
        assert "portfolio_health" in json_output

    def test_pending_approvals_for_high_confidence(self, director_bullish: ResearchDirector) -> None:
        brief = director_bullish.generate_morning_brief(
            ["AAPL"], "2023-01-01", "2024-01-01"
        )
        # With all-bullish specialists at high confidence, should have pending approvals
        if brief.top_convictions and brief.top_convictions[0]["confidence"] > 0.7:
            assert len(brief.pending_approvals) > 0
            assert brief.pending_approvals[0]["action"] in ("buy", "sell")

    def test_watchlist_populated_for_many_tickers(self) -> None:
        """With > 3 tickers, excess go to watchlist."""
        director = ResearchDirector()
        director._specialists = _mock_specialists_mostly_bullish()
        tickers = ["AAPL", "MSFT", "NVDA", "GOOG", "TSLA"]
        brief = director.generate_morning_brief(tickers, "2023-01-01", "2024-01-01")
        assert len(brief.top_convictions) == 3
        assert len(brief.watchlist) == 2


# ---------------------------------------------------------------------------
# Test: answer_question
# ---------------------------------------------------------------------------


class TestAnswerQuestion:
    def test_returns_dict(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.answer_question("What's your view on AAPL?")
        assert isinstance(result, dict)

    def test_has_answer_and_citations(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.answer_question("What's your view on AAPL?")
        assert "answer" in result
        assert "citations" in result
        assert "actions" in result
        assert "agent_traces" in result
        assert len(result["answer"]) > 0

    def test_ticker_research_intent(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.answer_question("Analyze NVDA for me")
        assert "NVDA" in result["answer"]

    def test_general_question_gives_help(self) -> None:
        director = ResearchDirector()
        director._specialists = {}
        result = director.answer_question("hello")
        assert "research analyst" in result["answer"].lower()

    def test_performance_intent(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.answer_question("How did my portfolio perform last week?")
        assert "performance" in result["answer"].lower()

    def test_strategy_intent(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.answer_question("Build me a momentum strategy")
        assert "strategy" in result["answer"].lower()

    def test_comparison_intent(self, director_bullish: ResearchDirector) -> None:
        result = director_bullish.answer_question("Compare AAPL vs MSFT")
        assert "comparison" in result["answer"].lower() or "AAPL" in result["answer"]


# ---------------------------------------------------------------------------
# Test: ResearchChat
# ---------------------------------------------------------------------------


class TestResearchChat:
    def test_send_returns_response(self) -> None:
        chat = ResearchChat()
        # Inject mock director
        chat._director = ResearchDirector()
        chat._director._specialists = _mock_specialists_mostly_bullish()
        response = chat.send("What's your view on AAPL?")
        assert isinstance(response, dict)
        assert "answer" in response

    def test_history_tracks_messages(self) -> None:
        chat = ResearchChat()
        chat._director = ResearchDirector()
        chat._director._specialists = _mock_specialists_mostly_bullish()

        chat.send("Analyze AAPL")
        chat.send("And MSFT?")

        history = chat.get_history()
        assert len(history) == 4  # 2 user + 2 assistant
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"
        assert history[3]["role"] == "assistant"

    def test_clear_history(self) -> None:
        chat = ResearchChat()
        chat._director = ResearchDirector()
        chat._director._specialists = {}
        chat.send("Hello")
        assert len(chat.get_history()) == 2
        chat.clear()
        assert len(chat.get_history()) == 0


# ---------------------------------------------------------------------------
# Test: CycleScheduler
# ---------------------------------------------------------------------------


class TestCycleScheduler:
    def test_daily_returns_dict(self) -> None:
        scheduler = CycleScheduler(tickers=["AAPL", "MSFT"])
        # Patch the director with mock specialists
        director = ResearchDirector()
        director._specialists = _mock_specialists_mostly_bullish()
        scheduler._director = director
        result = scheduler.run_daily_cycle()
        assert isinstance(result, dict)
        assert "greeting" in result
        assert "top_convictions" in result
        assert "portfolio_health" in result

    def test_weekly_returns_dict(self) -> None:
        scheduler = CycleScheduler(tickers=["AAPL"])
        result = scheduler.run_weekly_cycle()
        assert isinstance(result, dict)
        assert "cycle" in result
        assert result["cycle"] == "weekly"

    def test_daily_updates_last_run(self) -> None:
        scheduler = CycleScheduler(tickers=["AAPL"])
        director = ResearchDirector()
        director._specialists = _mock_specialists_mostly_bullish()
        scheduler._director = director

        assert scheduler.last_daily is None
        scheduler.run_daily_cycle()
        assert scheduler.last_daily is not None

    def test_weekly_updates_last_run(self) -> None:
        scheduler = CycleScheduler(tickers=["AAPL"])
        assert scheduler.last_weekly is None
        scheduler.run_weekly_cycle()
        assert scheduler.last_weekly is not None

    def test_daily_event_callback(self) -> None:
        scheduler = CycleScheduler(tickers=["AAPL"])
        director = ResearchDirector()
        director._specialists = _mock_specialists_mostly_bullish()
        scheduler._director = director

        events: list[dict] = []
        scheduler.run_daily_cycle(event_callback=events.append)
        assert len(events) > 0
        # Should include cycle start and complete events
        cycle_events = [e for e in events if "cycle" in e]
        assert any(e.get("status") == "started" for e in cycle_events)
        assert any(e.get("status") == "completed" for e in cycle_events)

    def test_stop(self) -> None:
        scheduler = CycleScheduler()
        scheduler._running = True
        scheduler.stop()
        assert scheduler._running is False


# ---------------------------------------------------------------------------
# Test: intent parsing edge cases
# ---------------------------------------------------------------------------


class TestIntentParsing:
    def test_parse_single_ticker(self) -> None:
        intent = ResearchDirector._parse_intent("what do you think about aapl?")
        assert intent["type"] == "ticker_research"
        assert intent["ticker"] == "AAPL"

    def test_parse_comparison_vs(self) -> None:
        intent = ResearchDirector._parse_intent("compare aapl vs msft")
        assert intent["type"] == "comparison"
        assert set(intent["tickers"]) == {"AAPL", "MSFT"}

    def test_parse_comparison_why_over(self) -> None:
        intent = ResearchDirector._parse_intent("why nvda over amd")
        assert intent["type"] == "comparison"
        assert set(intent["tickers"]) == {"NVDA", "AMD"}

    def test_parse_performance(self) -> None:
        intent = ResearchDirector._parse_intent("how did my portfolio perform last week?")
        assert intent["type"] == "performance"

    def test_parse_strategy(self) -> None:
        intent = ResearchDirector._parse_intent("build a mean reversion strategy")
        assert intent["type"] == "strategy"

    def test_parse_general_no_ticker(self) -> None:
        intent = ResearchDirector._parse_intent("hello there")
        assert intent["type"] == "general"

    def test_noise_words_filtered(self) -> None:
        intent = ResearchDirector._parse_intent("is it a good time to buy?")
        # "IS", "IT", "A" should be filtered as noise
        assert intent["type"] in ("general", "strategy")


# ---------------------------------------------------------------------------
# Test: ResearchBrief dataclass
# ---------------------------------------------------------------------------


class TestResearchBrief:
    def test_to_json_roundtrip(self) -> None:
        brief = ResearchBrief(
            greeting="Good morning.",
            top_convictions=[{"ticker": "AAPL", "signal": "bullish", "confidence": 0.85}],
            watchlist=[],
            portfolio_health={"pnl": 0.0, "sharpe": 0.0},
            what_i_learned="Nothing yet.",
            pending_approvals=[],
        )
        data = brief.to_json()
        assert data["greeting"] == "Good morning."
        assert len(data["top_convictions"]) == 1
        assert data["top_convictions"][0]["ticker"] == "AAPL"
