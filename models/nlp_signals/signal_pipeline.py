"""End-to-end NLP signal generation pipeline.

Orchestrates: text -> model -> signal -> backtest-ready DataFrame.

Usage::

    pipeline = NLPSignalPipeline(model="finbert")  # or "loughran_mcdonald"
    signals_df = pipeline.generate_signals(texts)
    # signals_df is ready for VectorizedBacktestEngine.run()
"""

from __future__ import annotations

import logging

import polars as pl

from models.nlp_signals.base import BaseNLPSignalModel, NLPModelRegistry, NLPSignal

logger = logging.getLogger(__name__)


class NLPSignalPipeline:
    """End-to-end pipeline: text -> model -> signal -> backtest-ready DataFrame.

    Falls back to ``loughran_mcdonald`` when the requested model is missing
    or its dependencies are not installed.
    """

    def __init__(self, model: str = "loughran_mcdonald", **model_kwargs) -> None:
        self._model_name = model
        try:
            self._model: BaseNLPSignalModel = NLPModelRegistry.get(
                model, **model_kwargs
            )
            if not self._model.is_available:
                logger.warning(
                    "Model '%s' dependencies not installed. "
                    "Falling back to loughran_mcdonald.",
                    model,
                )
                self._model = NLPModelRegistry.get("loughran_mcdonald")
                self._model_name = "loughran_mcdonald"
        except KeyError:
            logger.warning(
                "Model '%s' not found. Falling back to loughran_mcdonald.",
                model,
            )
            self._model = NLPModelRegistry.get("loughran_mcdonald")
            self._model_name = "loughran_mcdonald"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_ml_model(self) -> bool:
        return self._model_name != "loughran_mcdonald"

    def analyze_text(
        self, text: str, ticker: str = "", date: str = ""
    ) -> NLPSignal:
        """Analyze a single piece of text and return an NLPSignal."""
        return self._model.predict_sentiment(text, ticker=ticker, date=date)

    def generate_signals(self, texts: list[dict]) -> pl.DataFrame:
        """Generate signals from a list of texts.

        Parameters
        ----------
        texts:
            List of ``{"text": str, "ticker": str, "date": str}``.

        Returns
        -------
        :class:`polars.DataFrame` with columns
        ``[date, ticker, direction, confidence, signal_value, model]``
        ready for ``VectorizedBacktestEngine``.
        """
        if not texts:
            return pl.DataFrame(
                schema={
                    "date": pl.Utf8,
                    "ticker": pl.Utf8,
                    "direction": pl.Float64,
                    "confidence": pl.Float64,
                    "signal_value": pl.Float64,
                    "model": pl.Utf8,
                }
            )

        signals = self._model.predict_batch(texts)

        rows = []
        for sig in signals:
            if sig.signal_value > 0.1:
                direction = 1.0
            elif sig.signal_value < -0.1:
                direction = -1.0
            else:
                direction = 0.0

            rows.append(
                {
                    "date": sig.date,
                    "ticker": sig.ticker,
                    "direction": direction,
                    "confidence": sig.confidence,
                    "signal_value": sig.signal_value,
                    "model": sig.model_name,
                }
            )

        return pl.DataFrame(rows)

    def compare_models(
        self, texts: list[dict], model_names: list[str]
    ) -> pl.DataFrame:
        """Run multiple models on the same texts and compare signals.

        Returns a DataFrame with columns
        ``[ticker, date, model, signal_value, confidence]``.
        Useful for answering: "Does FinBERT outperform Loughran-McDonald?"
        """
        all_rows: list[dict] = []
        for model_name in model_names:
            try:
                model = NLPModelRegistry.get(model_name)
                if not model.is_available:
                    logger.warning(
                        "Skipping unavailable model '%s' in comparison.",
                        model_name,
                    )
                    continue
                for t in texts:
                    sig = model.predict_sentiment(
                        t["text"],
                        t.get("ticker", ""),
                        t.get("date", ""),
                    )
                    all_rows.append(
                        {
                            "ticker": sig.ticker,
                            "date": sig.date,
                            "model": model_name,
                            "signal_value": sig.signal_value,
                            "confidence": sig.confidence,
                        }
                    )
            except Exception as e:
                logger.warning("Model %s failed: %s", model_name, e)

        if not all_rows:
            return pl.DataFrame(
                schema={
                    "ticker": pl.Utf8,
                    "date": pl.Utf8,
                    "model": pl.Utf8,
                    "signal_value": pl.Float64,
                    "confidence": pl.Float64,
                }
            )
        return pl.DataFrame(all_rows)

    def fine_tune(self, training_data: list[dict], **kwargs) -> dict:
        """Fine-tune the underlying model."""
        return self._model.fine_tune(training_data, **kwargs)
