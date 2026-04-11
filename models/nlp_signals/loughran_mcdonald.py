"""Loughran-McDonald word-list sentiment wrapped as an NLP signal model.

This is the baseline model: always available (no ML dependencies), uses the
existing :class:`FinancialSentimentAnalyzer` under the hood.
"""

from __future__ import annotations

from models.nlp_signals.base import BaseNLPSignalModel, NLPModelRegistry, NLPSignal


class LoughranMcDonaldModel(BaseNLPSignalModel):
    """Loughran-McDonald word list sentiment -- the baseline.

    Always available (no external dependencies beyond the existing
    ``research.nlp.sentiment`` module).
    """

    @property
    def name(self) -> str:
        return "loughran_mcdonald"

    @property
    def is_available(self) -> bool:
        return True  # Always available -- no ML dependencies

    def predict_sentiment(
        self, text: str, ticker: str = "", date: str = ""
    ) -> NLPSignal:
        from research.nlp.sentiment import FinancialSentimentAnalyzer

        analyzer = FinancialSentimentAnalyzer()
        result = analyzer.analyze_text(text)
        return NLPSignal(
            ticker=ticker,
            date=date,
            signal_value=result.score,
            confidence=result.magnitude,
            model_name=self.name,
            metadata={"label": result.label, "key_phrases": result.key_phrases},
        )


NLPModelRegistry.register(LoughranMcDonaldModel)
