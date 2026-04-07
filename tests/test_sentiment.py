"""Tests for financial sentiment analysis."""

from __future__ import annotations

import polars as pl
import pytest

from research.nlp.sentiment import FinancialSentimentAnalyzer, SentimentResult


@pytest.fixture
def analyzer() -> FinancialSentimentAnalyzer:
    return FinancialSentimentAnalyzer()


# ---------------------------------------------------------------------------
# Bullish / bearish / neutral text
# ---------------------------------------------------------------------------

BULLISH_TEXT = (
    "The company reported strong profit growth this quarter, with revenue exceeding "
    "expectations. Management highlighted robust demand and improved operating efficiency. "
    "The firm outperformed its peers and upgraded its full-year guidance, citing momentum "
    "across all business segments and record profitability."
)

BEARISH_TEXT = (
    "The company disclosed significant losses amid a broader downturn in the sector. "
    "Litigation risks have increased due to ongoing lawsuits, and the firm faces "
    "restructuring charges following layoffs. Management warned of further decline "
    "and acknowledged exposure to volatile markets and challenging headwinds."
)

NEUTRAL_TEXT = (
    "The company held its annual meeting on Tuesday. The board discussed the agenda "
    "items and provided an update on the quarterly timeline. No material changes were "
    "announced and the session concluded on schedule."
)


def test_analyze_positive_text(analyzer: FinancialSentimentAnalyzer) -> None:
    result = analyzer.analyze_text(BULLISH_TEXT)
    assert result.score > 0, f"Expected positive score, got {result.score}"
    assert result.label == "bullish"


def test_analyze_negative_text(analyzer: FinancialSentimentAnalyzer) -> None:
    result = analyzer.analyze_text(BEARISH_TEXT)
    assert result.score < 0, f"Expected negative score, got {result.score}"
    assert result.label == "bearish"


def test_analyze_neutral_text(analyzer: FinancialSentimentAnalyzer) -> None:
    result = analyzer.analyze_text(NEUTRAL_TEXT)
    assert abs(result.score) <= 0.01
    assert result.label == "neutral"


def test_sentiment_result_fields(analyzer: FinancialSentimentAnalyzer) -> None:
    result = analyzer.analyze_text(BULLISH_TEXT)
    assert isinstance(result, SentimentResult)
    assert isinstance(result.score, float)
    assert isinstance(result.magnitude, float)
    assert isinstance(result.label, str)
    assert isinstance(result.key_phrases, list)
    assert -1.0 <= result.score <= 1.0
    assert 0.0 <= result.magnitude <= 1.0


# ---------------------------------------------------------------------------
# Earnings call analysis
# ---------------------------------------------------------------------------

EARNINGS_TRANSCRIPT = (
    "Prepared Remarks:\n"
    "We are pleased to report strong growth and record profitability this quarter. "
    "Revenue exceeded expectations driven by robust demand and improved efficiency. "
    "Our momentum continues with innovation across all product lines.\n\n"
    "Question and Answer:\n"
    "Analyst: Can you comment on the risk of further decline in the international segment? "
    "CEO: We acknowledge the challenging environment and exposure to volatile markets. "
    "There are headwinds that may result in losses if conditions deteriorate further."
)


def test_earnings_call_sections(analyzer: FinancialSentimentAnalyzer) -> None:
    result = analyzer.analyze_earnings_call(EARNINGS_TRANSCRIPT)
    assert "overall" in result
    assert "sections" in result
    assert "tone_shift" in result

    sections = result["sections"]
    assert "prepared_remarks" in sections
    assert "qa" in sections

    assert sections["prepared_remarks"].label == "bullish"


def test_tone_shift_detection(analyzer: FinancialSentimentAnalyzer) -> None:
    result = analyzer.analyze_earnings_call(EARNINGS_TRANSCRIPT)
    # Q&A should be more negative than prepared remarks
    assert result["tone_shift"] < 0, (
        f"Expected negative tone shift, got {result['tone_shift']}"
    )


# ---------------------------------------------------------------------------
# Sentiment drift
# ---------------------------------------------------------------------------

def test_sentiment_drift_output_columns(analyzer: FinancialSentimentAnalyzer) -> None:
    texts = [
        ("2024-01-15", BULLISH_TEXT),
        ("2024-04-15", NEUTRAL_TEXT),
        ("2024-07-15", BEARISH_TEXT),
    ]
    df = analyzer.sentiment_drift(texts)
    assert isinstance(df, pl.DataFrame)
    expected_cols = {"date", "score", "magnitude", "label", "drift", "significant_shift"}
    assert expected_cols == set(df.columns)
    assert len(df) == 3
    # First drift should be zero
    assert df["drift"][0] == 0.0


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------

def test_generate_signals_from_sentiment(analyzer: FinancialSentimentAnalyzer) -> None:
    texts = [
        ("2024-01-15", BULLISH_TEXT),
        ("2024-04-15", BEARISH_TEXT),
    ]
    df = analyzer.sentiment_drift(texts)
    signals = analyzer.generate_signals(df, threshold=0.01, ticker="AAPL")
    assert len(signals) >= 1
    for sig in signals:
        assert sig.ticker == "AAPL"
        assert -1.0 <= sig.direction <= 1.0
        assert 0.0 <= sig.confidence <= 1.0


def test_signal_direction_matches_sentiment(analyzer: FinancialSentimentAnalyzer) -> None:
    texts = [
        ("2024-01-15", BULLISH_TEXT),
        ("2024-07-15", BEARISH_TEXT),
    ]
    df = analyzer.sentiment_drift(texts)
    signals = analyzer.generate_signals(df, threshold=0.005, ticker="TSLA")

    # There should be at least a long and a short signal
    directions = {s.direction for s in signals}
    assert 1.0 in directions, "Expected a long signal for bullish text"
    assert -1.0 in directions, "Expected a short signal for bearish text"
