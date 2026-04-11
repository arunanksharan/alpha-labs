"""Base abstractions for NLP-based signal generation models.

Provides :class:`BaseNLPSignalModel` (the contract every model must implement),
:class:`NLPSignal` (the unified output type), and :class:`NLPModelRegistry`
(a plug-and-play registry so new models can be added without touching existing
code).

To add a new model
-------------------
1. Subclass :class:`BaseNLPSignalModel`
2. Implement ``predict_sentiment()``
3. Optionally implement ``fine_tune()``, ``save()``, ``load()``
4. Decorate with ``@NLPModelRegistry.register`` or call it explicitly
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class NLPSignal:
    """Output from an NLP signal model."""

    ticker: str
    date: str
    signal_value: float  # -1.0 (bearish) to 1.0 (bullish)
    confidence: float  # 0.0 to 1.0
    model_name: str
    metadata: dict = field(default_factory=dict)


class BaseNLPSignalModel(ABC):
    """Base class for all NLP-based signal generation models.

    To add a new model:
    1. Subclass BaseNLPSignalModel
    2. Implement predict_sentiment()
    3. Optionally implement fine_tune()
    4. Register with NLPModelRegistry
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Model identifier."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether model dependencies are installed."""

    @abstractmethod
    def predict_sentiment(
        self, text: str, ticker: str = "", date: str = ""
    ) -> NLPSignal:
        """Predict sentiment from text. Returns NLPSignal."""

    def predict_batch(self, texts: list[dict]) -> list[NLPSignal]:
        """Batch prediction. Default: loop over predict_sentiment."""
        return [
            self.predict_sentiment(
                t["text"], ticker=t.get("ticker", ""), date=t.get("date", "")
            )
            for t in texts
        ]

    def fine_tune(self, training_data: list[dict], **kwargs) -> dict:
        """Fine-tune the model. Optional -- not all models support this."""
        raise NotImplementedError(f"{self.name} does not support fine-tuning")

    def save(self, path: str) -> None:
        """Save model weights. Optional."""
        raise NotImplementedError(f"{self.name} does not support saving")

    def load(self, path: str) -> None:
        """Load model weights. Optional."""
        raise NotImplementedError(f"{self.name} does not support loading")


class NLPModelRegistry:
    """Registry for available NLP signal models.

    Models register themselves at import time via ``register()``.  At runtime,
    callers use ``get()`` to obtain an instance by name, or ``list_models()``
    to discover what is available.
    """

    _models: dict[str, type[BaseNLPSignalModel]] = {}

    @classmethod
    def register(
        cls, model_cls: type[BaseNLPSignalModel]
    ) -> type[BaseNLPSignalModel]:
        """Register a model class. Can be used as a decorator or called directly."""
        instance = model_cls()
        cls._models[instance.name] = model_cls
        return model_cls

    @classmethod
    def get(cls, name: str, **kwargs) -> BaseNLPSignalModel:
        """Instantiate a registered model by name."""
        if name not in cls._models:
            available = ", ".join(cls._models.keys())
            raise KeyError(f"Model '{name}' not found. Available: {available}")
        return cls._models[name](**kwargs)

    @classmethod
    def list_models(cls) -> list[dict]:
        """Return metadata for every registered model."""
        result = []
        for name, model_cls in cls._models.items():
            instance = model_cls()
            result.append({"name": name, "available": instance.is_available})
        return result
