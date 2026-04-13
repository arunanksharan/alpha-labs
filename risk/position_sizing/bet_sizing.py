"""Bet sizing: convert ML classifier probabilities to optimal position sizes.

Implements the core ideas from AFML Chapter 10 (López de Prado):
- Probability → bet size via the normal CDF approach (Section 10.3)
- Linear and sigmoid alternative mappings
- Meta-labelling integration (primary direction × meta-model confidence)
- Discretization to filter marginal signals
- Full dynamic pipeline: probability → Kelly → volatility adjustment → position
- Average active bets (Section 10.4)
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


class BetSizer:
    """Convert ML classifier probabilities to optimal bet sizes.

    The key insight from AFML Ch 10: a classifier outputs P(correct direction).
    The bet size should be a function of this probability:
    - P = 0.5 → no edge → bet size = 0
    - P = 1.0 → certain → bet size = max
    - P = 0.6 → modest edge → bet size = small
    """

    def __init__(
        self,
        max_position: float = 1.0,
        discretize_step: float | None = None,
    ) -> None:
        """
        Args:
            max_position: Maximum position as fraction of portfolio (0 to 1).
            discretize_step: If set, round bet sizes to this step (e.g., 0.1).
        """
        if not 0.0 < max_position <= 1.0:
            raise ValueError("max_position must be in (0, 1]")
        if discretize_step is not None and discretize_step <= 0.0:
            raise ValueError("discretize_step must be positive")

        self.max_position = max_position
        self.discretize_step = discretize_step

    # ------------------------------------------------------------------
    # Core bet sizing methods
    # ------------------------------------------------------------------

    def bet_size_from_prob(self, prob: float, num_classes: int = 2) -> float:
        """Convert predicted probability to bet size using normal CDF approach.

        AFML Section 10.3: maps a classifier probability to [0, 1] via the
        standard normal CDF.

        For binary classification (num_classes=2):
            z = (prob - 0.5) / sqrt(prob * (1 - prob))
            m = 2 * Phi(z) - 1

        For multi-class (num_classes > 2):
            z = (prob - 1/num_classes) / sqrt(prob * (1 - prob))
            m = 2 * Phi(z) - 1

        Args:
            prob: Predicted probability in [0, 1]. For binary, this is
                  P(correct direction). Values below the no-edge threshold
                  (0.5 for binary, 1/num_classes for multi-class) are
                  mirrored — the magnitude reflects confidence, direction
                  is handled externally.
            num_classes: Number of classes (2 for binary).

        Returns:
            Bet size in [0, max_position]. Multiply by direction externally.
        """
        prob = float(np.clip(prob, 0.0, 1.0))
        no_edge = 1.0 / num_classes

        # Mirror around the no-edge point so we always get a magnitude
        p = max(prob, 1.0 - prob) if num_classes == 2 else prob

        # Degenerate cases: avoid division by zero in the variance term
        if p <= 0.0 or p >= 1.0:
            # p == 1.0 means certainty → max bet; p == 0.0 shouldn't happen
            # after mirroring, but handle gracefully
            raw = 1.0 if p >= 1.0 else 0.0
            return float(np.clip(raw, 0.0, self.max_position))

        variance = p * (1.0 - p)
        if variance < 1e-15:
            raw = 1.0
            return float(np.clip(raw, 0.0, self.max_position))

        z = (p - no_edge) / np.sqrt(variance)
        raw = 2.0 * norm.cdf(z) - 1.0

        # Clamp to [0, max_position]
        return float(np.clip(raw, 0.0, self.max_position))

    def bet_size_linear(self, prob: float) -> float:
        """Linear mapping: m = 2P - 1.

        Range: [0, 1] for P in [0.5, 1.0]. Simplest possible mapping —
        probability edge maps linearly to bet size.

        Args:
            prob: Predicted probability in [0.5, 1.0]. Values below 0.5
                  are mirrored (we use the magnitude).

        Returns:
            Bet size in [0, max_position].
        """
        prob = float(np.clip(prob, 0.0, 1.0))
        # Mirror: use distance from 0.5 regardless of direction
        p = max(prob, 1.0 - prob)
        raw = 2.0 * p - 1.0
        return float(np.clip(raw, 0.0, self.max_position))

    def bet_size_sigmoid(self, prob: float, scale: float = 1.0) -> float:
        """Sigmoid mapping for smoother, more conservative bet sizing.

        m = 2 * sigmoid(scale * (2P - 1)) - 1

        More conservative than linear for borderline probabilities (P near
        0.5–0.6), more aggressive near certainty.

        Args:
            prob: Predicted probability in [0.5, 1.0]. Mirrored for < 0.5.
            scale: Controls steepness. Higher = sharper transition. Default 1.0.

        Returns:
            Bet size in [0, max_position].
        """
        prob = float(np.clip(prob, 0.0, 1.0))
        p = max(prob, 1.0 - prob)
        x = 2.0 * p - 1.0  # edge in [0, 1]
        sigmoid_val = 1.0 / (1.0 + np.exp(-scale * x))
        raw = 2.0 * sigmoid_val - 1.0
        return float(np.clip(raw, 0.0, self.max_position))

    # ------------------------------------------------------------------
    # Meta-labelling integration
    # ------------------------------------------------------------------

    def bet_size_from_meta_label(
        self,
        direction: int,
        meta_prob: float,
    ) -> float:
        """Full pipeline: primary model direction x meta-model probability.

        The primary model determines the trade direction (+1 long, -1 short).
        The meta-labelling model outputs P(primary model is correct).
        The final bet size combines both.

        Args:
            direction: -1 or +1 from the primary model.
            meta_prob: P(primary model is correct) from the meta-model, in [0, 1].

        Returns:
            Signed bet size: direction * bet_size(meta_prob) * max_position.
            Range: [-max_position, +max_position].
        """
        if direction not in (-1, 1):
            raise ValueError("direction must be -1 or +1")

        magnitude = self.bet_size_from_prob(meta_prob, num_classes=2)
        return float(direction * magnitude)

    # ------------------------------------------------------------------
    # Discretization
    # ------------------------------------------------------------------

    def discretize(self, bet_size: float) -> float:
        """Round bet size to nearest step. Filters out marginal signals.

        m* = round(m / d) * d, clamped to [-1, 1].

        If no discretize_step was configured, returns the input unchanged.

        Args:
            bet_size: Raw bet size (signed or unsigned).

        Returns:
            Discretized bet size.
        """
        if self.discretize_step is None:
            return bet_size

        d = self.discretize_step
        discretized = round(bet_size / d) * d
        return float(np.clip(discretized, -1.0, 1.0))

    # ------------------------------------------------------------------
    # Full dynamic sizing pipeline
    # ------------------------------------------------------------------

    def dynamic_position_size(
        self,
        prob: float,
        daily_vol: float,
        risk_budget: float,
        direction: int = 1,
        fractional_kelly: float = 0.5,
    ) -> dict:
        """Full bet sizing pipeline: probability to dollar position.

        Combines:
        1. Probability → raw bet size (via bet_size_from_prob)
        2. Kelly scaling (fractional_kelly multiplier)
        3. Volatility adjustment (risk_budget / daily_vol)
        4. Discretization (if step is set)

        Args:
            prob: Classifier probability in [0, 1].
            daily_vol: Daily volatility of the asset (must be > 0).
            risk_budget: Dollar risk budget for the position.
            direction: +1 (long) or -1 (short).
            fractional_kelly: Kelly fraction to apply (e.g. 0.5 for half-Kelly).

        Returns:
            Dict with keys: direction, raw_bet_size, kelly_fraction,
            vol_adjusted, final_position_pct, reasoning.
        """
        if direction not in (-1, 1):
            raise ValueError("direction must be -1 or +1")
        if daily_vol <= 0.0:
            raise ValueError("daily_vol must be strictly positive")

        # Step 1: probability → raw bet size magnitude
        raw = self.bet_size_from_prob(prob, num_classes=2)

        # Step 2: Kelly scaling
        kelly_scaled = raw * fractional_kelly

        # Step 3: Volatility adjustment — how many units can we afford
        # given the risk budget and daily vol
        vol_adjusted = kelly_scaled * (risk_budget / daily_vol)

        # Step 4: Discretize if configured
        final_pct = self.discretize(kelly_scaled)

        # Clamp to max_position
        final_pct = float(np.clip(final_pct, 0.0, self.max_position))

        reasoning_parts = [
            f"P={prob:.3f} -> raw_bet={raw:.4f}",
            f"x {fractional_kelly:.2f} Kelly -> {kelly_scaled:.4f}",
            f"vol_adj: budget={risk_budget:.0f} / vol={daily_vol:.4f} -> ${vol_adjusted:.2f}",
            f"final_pct={final_pct:.4f} (max={self.max_position:.2f})",
        ]

        return {
            "direction": direction,
            "raw_bet_size": raw,
            "kelly_fraction": kelly_scaled,
            "vol_adjusted": vol_adjusted,
            "final_position_pct": final_pct,
            "reasoning": " | ".join(reasoning_parts),
        }

    # ------------------------------------------------------------------
    # Average active bets (Section 10.4)
    # ------------------------------------------------------------------

    def average_active_bets(self, active_signals: list[dict]) -> float:
        """Average all currently active bet sizes.

        AFML Section 10.4: when multiple signals overlap in time, the
        final position should reflect the average of all active bets,
        not just the latest one. This prevents over-concentration and
        smooths the signal.

        Args:
            active_signals: List of dicts, each containing at minimum a
                ``"bet_size"`` key (float). Other keys (``start_date``,
                ``end_date``, etc.) are informational and ignored here.

        Returns:
            Average bet size across all active signals. Returns 0.0 if
            the list is empty.
        """
        if not active_signals:
            return 0.0

        sizes = [s["bet_size"] for s in active_signals]
        return float(np.mean(sizes))
