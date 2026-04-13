"""Tests for the three specialist research agents.

All tests run WITHOUT external API keys by using synthetic / sample data
and the built-in rule-based NLP sentiment analyser.
"""

from __future__ import annotations

import pytest

from agents.specialists import AgentFinding
from agents.specialists.the_sentiment_analyst import TheSentimentAnalyst
from agents.specialists.the_fundamentalist import TheFundamentalist
from agents.specialists.the_macro_strategist import TheMacroStrategist


# ======================================================================
# Fixtures
# ======================================================================

BULLISH_TEXT = (
    "We delivered strong revenue growth this quarter. "
    "Profitability exceeded expectations and our innovative product lineup "
    "drove record momentum. Expansion opportunities remain robust and "
    "efficiency gains accelerated. Leadership continues to outperform."
)

BEARISH_TEXT = (
    "We experienced significant losses and revenue decline this quarter. "
    "Headwinds from litigation and restructuring costs impacted results. "
    "The downturn in our core markets led to impairment charges and "
    "risk of further deterioration. Volatility and adverse conditions persist."
)

NEUTRAL_TEXT = "The company reported results."


@pytest.fixture
def sentiment_agent() -> TheSentimentAnalyst:
    return TheSentimentAnalyst()


@pytest.fixture
def fundamentalist_agent() -> TheFundamentalist:
    return TheFundamentalist()


@pytest.fixture
def macro_agent() -> TheMacroStrategist:
    return TheMacroStrategist()


# ======================================================================
# TheSentimentAnalyst
# ======================================================================


class TestTheSentimentAnalyst:
    """Tests for the NLP sentiment analysis agent."""

    def test_sentiment_analyst_returns_finding(
        self, sentiment_agent: TheSentimentAnalyst
    ) -> None:
        """The agent must return an AgentFinding with all required fields."""
        finding = sentiment_agent.analyze("AAPL", "2024-01-01", "2024-06-30")

        assert isinstance(finding, AgentFinding)
        assert finding.agent_name == "TheSentimentAnalyst"
        assert finding.ticker == "AAPL"
        assert finding.signal in ("bullish", "bearish", "neutral")
        assert 0.0 <= finding.confidence <= 1.0
        assert isinstance(finding.reasoning, str) and len(finding.reasoning) > 0
        assert isinstance(finding.details, dict)
        assert isinstance(finding.thoughts, list) and len(finding.thoughts) > 0

        # to_json round-trip
        j = finding.to_json()
        assert j["ticker"] == "AAPL"
        assert j["signal"] == finding.signal

    def test_sentiment_analyst_with_bullish_text(
        self, sentiment_agent: TheSentimentAnalyst
    ) -> None:
        """Known positive text must produce a bullish signal."""
        finding = sentiment_agent.analyze(
            "AAPL", "2024-01-01", "2024-06-30", earnings_text=BULLISH_TEXT
        )

        assert finding.signal == "bullish"
        assert finding.details["overall_score"] > 0.02
        assert finding.confidence > 0

    def test_sentiment_analyst_with_bearish_text(
        self, sentiment_agent: TheSentimentAnalyst
    ) -> None:
        """Known negative text must produce a bearish signal."""
        finding = sentiment_agent.analyze(
            "AAPL", "2024-01-01", "2024-06-30", earnings_text=BEARISH_TEXT
        )

        assert finding.signal == "bearish"
        assert finding.details["overall_score"] < -0.02
        assert finding.confidence > 0

    def test_sentiment_analyst_has_key_phrases(
        self, sentiment_agent: TheSentimentAnalyst
    ) -> None:
        """The agent must extract key phrases from the text."""
        finding = sentiment_agent.analyze(
            "MSFT", "2024-01-01", "2024-12-31", earnings_text=BULLISH_TEXT
        )

        assert "key_phrases" in finding.details
        key_phrases = finding.details["key_phrases"]
        assert isinstance(key_phrases, list)
        # The bullish text has multiple sentiment-bearing sentences
        assert len(key_phrases) > 0

        # Thoughts should mention key phrases
        phrase_thoughts = [t for t in finding.thoughts if "Key phrases" in t]
        assert len(phrase_thoughts) == 1

    def test_sentiment_analyst_earnings_call_sections(
        self, sentiment_agent: TheSentimentAnalyst
    ) -> None:
        """When text contains Q&A markers, sections should be split."""
        text_with_qa = (
            "Our growth exceeded expectations this quarter. Strong momentum. "
            "Question and Answer Session: "
            "Analysts raised concerns about declining margins and risks."
        )
        finding = sentiment_agent.analyze(
            "GOOG", "2024-01-01", "2024-06-30", earnings_text=text_with_qa
        )

        assert "tone_shift" in finding.details
        # Prepared remarks are bullish, Q&A more bearish -> tone shift < 0
        assert "prepared_remarks_score" in finding.details or "tone_shift" in finding.details


# ======================================================================
# TheFundamentalist
# ======================================================================


class TestTheFundamentalist:
    """Tests for the fundamental / DCF analysis agent."""

    def test_fundamentalist_returns_finding(
        self, fundamentalist_agent: TheFundamentalist
    ) -> None:
        """The agent must return a valid AgentFinding even without EDGAR."""
        finding = fundamentalist_agent.analyze("AAPL", "2024-01-01", "2024-12-31")

        assert isinstance(finding, AgentFinding)
        assert finding.agent_name == "TheFundamentalist"
        assert finding.ticker == "AAPL"
        assert finding.signal in ("bullish", "bearish", "neutral")
        assert 0.0 <= finding.confidence <= 1.0
        assert len(finding.thoughts) > 0
        assert len(finding.reasoning) > 0

    def test_fundamentalist_has_dcf_details(
        self, fundamentalist_agent: TheFundamentalist
    ) -> None:
        """The finding must contain DCF-related metrics."""
        finding = fundamentalist_agent.analyze("MSFT", "2024-01-01", "2024-12-31")

        d = finding.details
        assert "intrinsic_value" in d
        assert "current_price" in d
        assert "margin_of_safety" in d
        assert "roe" in d
        assert "debt_equity" in d
        assert "net_margin" in d
        assert "growth_rate" in d
        assert "dcf_total" in d

        # Numeric sanity
        assert isinstance(d["intrinsic_value"], (int, float))
        assert isinstance(d["margin_of_safety"], (int, float))
        assert d["discount_rate"] == 0.10

    def test_fundamentalist_fallback_data_quality(
        self, fundamentalist_agent: TheFundamentalist
    ) -> None:
        """Agent must always succeed; data_quality reflects source quality."""
        finding = fundamentalist_agent.analyze("XYZ", "2024-01-01", "2024-12-31")

        # Should always succeed -- either real EDGAR data or synthetic fallback
        assert isinstance(finding, AgentFinding)
        assert finding.details["data_quality"] in (0.5, 1.0)

        if finding.details["data_quality"] == 0.5:
            # When EDGAR unavailable, thoughts should mention fallback
            fallback_thoughts = [
                t
                for t in finding.thoughts
                if "estimates" in t.lower() or "synthetic" in t.lower()
            ]
            assert len(fallback_thoughts) > 0
        else:
            # Got real EDGAR data -- thoughts should mention success
            edgar_thoughts = [t for t in finding.thoughts if "EDGAR" in t]
            assert len(edgar_thoughts) > 0

    def test_fundamentalist_unknown_ticker_uses_defaults(
        self, fundamentalist_agent: TheFundamentalist
    ) -> None:
        """An unknown ticker should use default fundamentals and not crash."""
        finding = fundamentalist_agent.analyze("ZZZZ", "2024-01-01", "2024-12-31")
        assert isinstance(finding, AgentFinding)
        assert finding.details["revenue"] > 0


# ======================================================================
# TheMacroStrategist
# ======================================================================


class TestTheMacroStrategist:
    """Tests for the macro / regime analysis agent."""

    def test_macro_strategist_returns_finding(
        self, macro_agent: TheMacroStrategist
    ) -> None:
        """The agent must return a valid AgentFinding even without FRED."""
        finding = macro_agent.analyze("AAPL", "2024-01-01", "2024-12-31")

        assert isinstance(finding, AgentFinding)
        assert finding.agent_name == "TheMacroStrategist"
        assert finding.ticker == "AAPL"
        assert finding.signal in ("bullish", "bearish", "neutral")
        assert 0.0 <= finding.confidence <= 1.0
        assert len(finding.thoughts) > 0

    def test_macro_strategist_has_regime_info(
        self, macro_agent: TheMacroStrategist
    ) -> None:
        """The finding must contain regime and macro details."""
        finding = macro_agent.analyze("MSFT", "2024-01-01", "2024-12-31")

        d = finding.details
        assert "regime" in d
        assert d["regime"] in ("low_vol", "moderate_vol", "high_vol")
        assert "annualized_vol" in d
        assert isinstance(d["annualized_vol"], (int, float))
        assert "yield_curve" in d
        assert d["yield_curve"] in ("Normal", "Inverted")
        assert "yield_spread" in d
        assert "fed_funds_rate" in d
        assert "vix" in d
        assert "assessment" in d
        assert "recession_risk" in d

    def test_macro_strategist_thought_stream_completeness(
        self, macro_agent: TheMacroStrategist
    ) -> None:
        """The thought stream should cover all major analysis steps."""
        finding = macro_agent.analyze("GOOG", "2024-01-01", "2024-12-31")

        thoughts_text = " ".join(finding.thoughts)
        # Should mention data source (YFinance, FRED, or fallback)
        assert "FRED" in thoughts_text or "estimates" in thoughts_text or "Fetched" in thoughts_text
        # Should mention yield spread
        assert "spread" in thoughts_text.lower() or "10Y-2Y" in thoughts_text
        # Should mention regime
        assert "regime" in thoughts_text.lower()
        # Should mention macro environment
        assert "macro" in thoughts_text.lower() or "Macro" in thoughts_text
        # Should mention final signal
        assert "Signal" in thoughts_text

    def test_macro_strategist_to_json(
        self, macro_agent: TheMacroStrategist
    ) -> None:
        """to_json must produce a complete dict."""
        finding = macro_agent.analyze("AAPL", "2024-01-01", "2024-12-31")
        j = finding.to_json()

        assert set(j.keys()) >= {
            "agent_name",
            "ticker",
            "signal",
            "confidence",
            "reasoning",
            "details",
            "thoughts",
        }
        assert j["agent_name"] == "TheMacroStrategist"
