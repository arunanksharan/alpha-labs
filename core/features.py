"""Base feature interfaces for alpha factor engineering.

Features transform raw data into signals. Every feature must:
1. Declare its lookback window (to prevent look-ahead bias)
2. Return a standardized DataFrame
3. Be stateless — no future data leakage
"""

from abc import ABC, abstractmethod

import polars as pl


class BaseFeature(ABC):
    """Interface for all alpha features / factors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique feature name (e.g., 'rsi_14', 'earnings_sentiment')."""

    @property
    @abstractmethod
    def lookback_days(self) -> int:
        """Minimum lookback window required. Used to prevent look-ahead bias in backtests."""

    @property
    @abstractmethod
    def category(self) -> str:
        """Feature category: 'technical' | 'fundamental' | 'alternative' | 'ml'."""

    @abstractmethod
    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        """Compute feature values. Must add column(s) to the input DataFrame.

        CRITICAL: Must not use any future data. Only use data up to each row's date.
        """

    def validate(self, data: pl.DataFrame) -> bool:
        """Check that input data has sufficient history for this feature."""
        return len(data) >= self.lookback_days


class FeatureRegistry:
    """Registry for available features."""

    _features: dict[str, type[BaseFeature]] = {}

    @classmethod
    def register(cls, feature_cls: type[BaseFeature]) -> type[BaseFeature]:
        """Use as decorator: @FeatureRegistry.register"""
        instance = feature_cls()
        cls._features[instance.name] = feature_cls
        return feature_cls

    @classmethod
    def get(cls, name: str, **kwargs) -> BaseFeature:
        if name not in cls._features:
            available = ", ".join(cls._features.keys())
            raise KeyError(f"Feature '{name}' not found. Available: {available}")
        return cls._features[name](**kwargs)

    @classmethod
    def list_features(cls, category: str | None = None) -> list[str]:
        if category is None:
            return list(cls._features.keys())
        return [
            name
            for name, cls_ in cls._features.items()
            if cls_().category == category
        ]
