"""NLP-based signal generation models.

Provides a plug-and-play registry of NLP models that produce trading signals
from text (earnings calls, filings, news).  New models are added by
subclassing :class:`BaseNLPSignalModel` and registering with
:class:`NLPModelRegistry`.

Available models:
- ``loughran_mcdonald`` -- always available (rule-based baseline)
- ``finbert`` -- requires ``transformers`` and ``torch``
"""

from models.nlp_signals.base import (
    BaseNLPSignalModel,
    NLPModelRegistry,
    NLPSignal,
)
from models.nlp_signals.signal_pipeline import NLPSignalPipeline

# Import models to trigger registration
from models.nlp_signals import loughran_mcdonald  # noqa: F401

try:
    from models.nlp_signals import finbert_model  # noqa: F401
except ImportError:
    pass  # FinBERT deps not installed -- that's fine

__all__ = [
    "BaseNLPSignalModel",
    "NLPModelRegistry",
    "NLPSignal",
    "NLPSignalPipeline",
]
