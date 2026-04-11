"""Tests for the NLP signal generation pipeline.

All tests run WITHOUT torch/transformers installed.  They exercise the
base abstractions, the Loughran-McDonald wrapper, the registry, and the
pipeline orchestrator -- including graceful fallback when a model's
dependencies are missing.
"""

from __future__ import annotations

import polars as pl
import pytest

from models.nlp_signals.base import BaseNLPSignalModel, NLPModelRegistry, NLPSignal
from models.nlp_signals.signal_pipeline import NLPSignalPipeline

# ---------------------------------------------------------------------------
# Sample texts (reused across tests)
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


# ---------------------------------------------------------------------------
# NLPSignal dataclass
# ---------------------------------------------------------------------------


class TestNLPSignalDataclass:
    def test_nlp_signal_dataclass(self) -> None:
        sig = NLPSignal(
            ticker="AAPL",
            date="2025-01-15",
            signal_value=0.75,
            confidence=0.9,
            model_name="test_model",
            metadata={"raw_label": "positive"},
        )
        assert sig.ticker == "AAPL"
        assert sig.date == "2025-01-15"
        assert sig.signal_value == 0.75
        assert sig.confidence == 0.9
        assert sig.model_name == "test_model"
        assert sig.metadata == {"raw_label": "positive"}

    def test_nlp_signal_default_metadata(self) -> None:
        sig = NLPSignal(
            ticker="MSFT",
            date="2025-01-15",
            signal_value=0.0,
            confidence=0.5,
            model_name="test",
        )
        assert sig.metadata == {}


# ---------------------------------------------------------------------------
# Loughran-McDonald model
# ---------------------------------------------------------------------------


class TestLoughranMcDonaldModel:
    def test_loughran_mcdonald_always_available(self) -> None:
        model = NLPModelRegistry.get("loughran_mcdonald")
        assert model.is_available is True

    def test_loughran_mcdonald_returns_nlp_signal(self) -> None:
        model = NLPModelRegistry.get("loughran_mcdonald")
        sig = model.predict_sentiment(BULLISH_TEXT, ticker="AAPL", date="2025-01-15")
        assert isinstance(sig, NLPSignal)
        assert sig.ticker == "AAPL"
        assert sig.date == "2025-01-15"
        assert sig.model_name == "loughran_mcdonald"
        assert -1.0 <= sig.signal_value <= 1.0
        assert 0.0 <= sig.confidence <= 1.0

    def test_loughran_mcdonald_bullish_text(self) -> None:
        model = NLPModelRegistry.get("loughran_mcdonald")
        sig = model.predict_sentiment(BULLISH_TEXT, ticker="AAPL", date="2025-01-15")
        assert sig.signal_value > 0, "Bullish text should produce a positive signal"
        assert sig.metadata.get("label") == "bullish"

    def test_loughran_mcdonald_bearish_text(self) -> None:
        model = NLPModelRegistry.get("loughran_mcdonald")
        sig = model.predict_sentiment(BEARISH_TEXT, ticker="AAPL", date="2025-01-15")
        assert sig.signal_value < 0, "Bearish text should produce a negative signal"
        assert sig.metadata.get("label") == "bearish"


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------


class TestModelRegistry:
    def test_model_registry_list_models(self) -> None:
        models = NLPModelRegistry.list_models()
        assert isinstance(models, list)
        assert len(models) >= 1  # At least loughran_mcdonald

        names = [m["name"] for m in models]
        assert "loughran_mcdonald" in names

        # Every entry has the expected keys
        for m in models:
            assert "name" in m
            assert "available" in m
            assert isinstance(m["available"], bool)

    def test_registry_get_unknown_model_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            NLPModelRegistry.get("nonexistent_model")


# ---------------------------------------------------------------------------
# FinBERT availability check (no loading)
# ---------------------------------------------------------------------------


class TestFinBERTAvailability:
    def test_finbert_is_available_check(self) -> None:
        """Just check the boolean -- does not attempt to load the model."""
        try:
            model = NLPModelRegistry.get("finbert")
            # is_available is a bool -- True if transformers+torch installed
            assert isinstance(model.is_available, bool)
        except KeyError:
            # FinBERT module failed to import entirely -- also acceptable
            pytest.skip("finbert_model module not importable")


# ---------------------------------------------------------------------------
# NLPSignalPipeline
# ---------------------------------------------------------------------------


class TestNLPSignalPipeline:
    def test_pipeline_fallback_when_model_unavailable(self) -> None:
        """Pipeline should fall back to loughran_mcdonald for unknown models."""
        pipeline = NLPSignalPipeline(model="totally_fake_model")
        assert pipeline.model_name == "loughran_mcdonald"

    def test_pipeline_generate_signals_returns_dataframe(self) -> None:
        pipeline = NLPSignalPipeline(model="loughran_mcdonald")
        texts = [
            {"text": BULLISH_TEXT, "ticker": "AAPL", "date": "2025-01-15"},
            {"text": BEARISH_TEXT, "ticker": "TSLA", "date": "2025-01-15"},
        ]
        df = pipeline.generate_signals(texts)
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 2

    def test_pipeline_generate_signals_schema(self) -> None:
        pipeline = NLPSignalPipeline(model="loughran_mcdonald")
        texts = [
            {"text": BULLISH_TEXT, "ticker": "AAPL", "date": "2025-01-15"},
        ]
        df = pipeline.generate_signals(texts)
        expected_columns = {"date", "ticker", "direction", "confidence"}
        assert expected_columns.issubset(set(df.columns))

    def test_pipeline_with_empty_texts(self) -> None:
        pipeline = NLPSignalPipeline(model="loughran_mcdonald")
        df = pipeline.generate_signals([])
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0
        # Schema should still be present
        expected_columns = {"date", "ticker", "direction", "confidence"}
        assert expected_columns.issubset(set(df.columns))

    def test_compare_models_returns_dataframe(self) -> None:
        pipeline = NLPSignalPipeline(model="loughran_mcdonald")
        texts = [
            {"text": BULLISH_TEXT, "ticker": "AAPL", "date": "2025-01-15"},
        ]
        # Compare just loughran_mcdonald with itself (guaranteed available)
        df = pipeline.compare_models(texts, model_names=["loughran_mcdonald"])
        assert isinstance(df, pl.DataFrame)
        assert len(df) >= 1
        assert "model" in df.columns
        assert "signal_value" in df.columns
        assert "confidence" in df.columns

    def test_pipeline_direction_mapping(self) -> None:
        """Verify that generate_signals maps signal_value to direction correctly."""
        pipeline = NLPSignalPipeline(model="loughran_mcdonald")
        texts = [
            {"text": BULLISH_TEXT, "ticker": "AAPL", "date": "2025-01-15"},
            {"text": BEARISH_TEXT, "ticker": "TSLA", "date": "2025-01-15"},
        ]
        df = pipeline.generate_signals(texts)
        directions = df["direction"].to_list()
        # Bullish text should get direction 1.0, bearish should get -1.0
        assert directions[0] == 1.0
        assert directions[1] == -1.0

    def test_pipeline_analyze_text(self) -> None:
        pipeline = NLPSignalPipeline(model="loughran_mcdonald")
        sig = pipeline.analyze_text(BULLISH_TEXT, ticker="AAPL", date="2025-01-15")
        assert isinstance(sig, NLPSignal)
        assert sig.ticker == "AAPL"
