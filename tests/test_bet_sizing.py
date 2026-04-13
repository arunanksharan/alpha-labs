"""Comprehensive tests for the bet sizing module (AFML Chapter 10)."""

from __future__ import annotations

import numpy as np
import pytest

from risk.position_sizing.bet_sizing import BetSizer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sizer() -> BetSizer:
    """Default sizer with max_position=1.0 and no discretization."""
    return BetSizer(max_position=1.0)


@pytest.fixture
def sizer_capped() -> BetSizer:
    """Sizer with max_position=0.5 for capping tests."""
    return BetSizer(max_position=0.5)


@pytest.fixture
def sizer_discrete() -> BetSizer:
    """Sizer with discretize_step=0.1."""
    return BetSizer(max_position=1.0, discretize_step=0.1)


# ===================================================================
# Constructor validation
# ===================================================================

class TestBetSizerInit:
    def test_valid_default(self) -> None:
        s = BetSizer()
        assert s.max_position == 1.0
        assert s.discretize_step is None

    def test_valid_custom(self) -> None:
        s = BetSizer(max_position=0.3, discretize_step=0.05)
        assert s.max_position == 0.3
        assert s.discretize_step == 0.05

    def test_invalid_max_position_zero(self) -> None:
        with pytest.raises(ValueError, match="max_position"):
            BetSizer(max_position=0.0)

    def test_invalid_max_position_negative(self) -> None:
        with pytest.raises(ValueError, match="max_position"):
            BetSizer(max_position=-0.1)

    def test_invalid_max_position_above_one(self) -> None:
        with pytest.raises(ValueError, match="max_position"):
            BetSizer(max_position=1.5)

    def test_invalid_discretize_step_negative(self) -> None:
        with pytest.raises(ValueError, match="discretize_step"):
            BetSizer(discretize_step=-0.1)

    def test_invalid_discretize_step_zero(self) -> None:
        with pytest.raises(ValueError, match="discretize_step"):
            BetSizer(discretize_step=0.0)


# ===================================================================
# bet_size_from_prob (normal CDF approach, AFML Section 10.3)
# ===================================================================

class TestBetSizeFromProb:
    def test_prob_half_gives_zero(self, sizer: BetSizer) -> None:
        """P=0.5 means no edge -> bet size = 0."""
        result = sizer.bet_size_from_prob(0.5)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_prob_one_gives_max(self, sizer: BetSizer) -> None:
        """P=1.0 means certainty -> bet size = max_position."""
        result = sizer.bet_size_from_prob(1.0)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_prob_zero_gives_max(self, sizer: BetSizer) -> None:
        """P=0.0 is mirrored to P=1.0 (wrong direction, but max size).
        Direction is handled externally."""
        result = sizer.bet_size_from_prob(0.0)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_prob_0_6_gives_small_bet(self, sizer: BetSizer) -> None:
        """P=0.6 should give a modest bet size, strictly between 0 and 1."""
        result = sizer.bet_size_from_prob(0.6)
        assert 0.0 < result < 1.0

    def test_prob_0_9_larger_than_0_6(self, sizer: BetSizer) -> None:
        """Higher probability -> larger bet size."""
        low = sizer.bet_size_from_prob(0.6)
        high = sizer.bet_size_from_prob(0.9)
        assert high > low

    def test_monotonically_increasing_above_half(self, sizer: BetSizer) -> None:
        """Bet size should increase monotonically for P in [0.5, 1.0]."""
        probs = np.linspace(0.5, 0.99, 20)
        sizes = [sizer.bet_size_from_prob(p) for p in probs]
        for i in range(1, len(sizes)):
            assert sizes[i] >= sizes[i - 1] - 1e-12

    def test_capped_at_max_position(self, sizer_capped: BetSizer) -> None:
        """Result should never exceed max_position."""
        result = sizer_capped.bet_size_from_prob(1.0)
        assert result <= sizer_capped.max_position + 1e-12

    def test_multiclass_no_edge(self, sizer: BetSizer) -> None:
        """For 3 classes, P=1/3 means no edge -> near zero."""
        result = sizer.bet_size_from_prob(1.0 / 3.0, num_classes=3)
        assert result == pytest.approx(0.0, abs=0.05)

    def test_multiclass_high_prob(self, sizer: BetSizer) -> None:
        """For 3 classes, P=0.9 should give a large bet."""
        result = sizer.bet_size_from_prob(0.9, num_classes=3)
        assert result > 0.5


# ===================================================================
# bet_size_linear
# ===================================================================

class TestBetSizeLinear:
    def test_prob_half_gives_zero(self, sizer: BetSizer) -> None:
        assert sizer.bet_size_linear(0.5) == pytest.approx(0.0, abs=1e-9)

    def test_prob_one_gives_max(self, sizer: BetSizer) -> None:
        assert sizer.bet_size_linear(1.0) == pytest.approx(1.0, abs=1e-9)

    def test_prob_0_75_gives_0_5(self, sizer: BetSizer) -> None:
        assert sizer.bet_size_linear(0.75) == pytest.approx(0.5, abs=1e-9)

    def test_prob_zero_mirrored(self, sizer: BetSizer) -> None:
        """P=0.0 mirrored to P=1.0 -> bet size = 1.0."""
        assert sizer.bet_size_linear(0.0) == pytest.approx(1.0, abs=1e-9)

    def test_capped(self, sizer_capped: BetSizer) -> None:
        result = sizer_capped.bet_size_linear(1.0)
        assert result <= sizer_capped.max_position + 1e-12


# ===================================================================
# bet_size_sigmoid
# ===================================================================

class TestBetSizeSigmoid:
    def test_prob_half_gives_zero(self, sizer: BetSizer) -> None:
        result = sizer.bet_size_sigmoid(0.5)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_prob_one_approaches_max(self, sizer: BetSizer) -> None:
        result = sizer.bet_size_sigmoid(1.0, scale=5.0)
        assert result > 0.9

    def test_more_conservative_than_linear_near_threshold(self, sizer: BetSizer) -> None:
        """Sigmoid should be more conservative than linear for P near 0.5-0.6."""
        for p in [0.55, 0.6, 0.65]:
            linear = sizer.bet_size_linear(p)
            sigmoid = sizer.bet_size_sigmoid(p, scale=1.0)
            assert sigmoid < linear, f"Sigmoid should be < linear at P={p}"

    def test_higher_scale_sharper_transition(self, sizer: BetSizer) -> None:
        """Higher scale -> larger bet for same probability above threshold."""
        low_scale = sizer.bet_size_sigmoid(0.8, scale=1.0)
        high_scale = sizer.bet_size_sigmoid(0.8, scale=5.0)
        assert high_scale > low_scale

    def test_scale_zero_gives_zero(self, sizer: BetSizer) -> None:
        """scale=0 -> sigmoid(0) = 0.5 -> m = 2*0.5 - 1 = 0 for any prob."""
        for p in [0.5, 0.7, 0.9]:
            result = sizer.bet_size_sigmoid(p, scale=0.0)
            assert result == pytest.approx(0.0, abs=1e-9)


# ===================================================================
# bet_size_from_meta_label
# ===================================================================

class TestBetSizeFromMetaLabel:
    def test_positive_direction_positive_size(self, sizer: BetSizer) -> None:
        """direction=+1 with meta_prob=0.7 -> positive bet size."""
        result = sizer.bet_size_from_meta_label(direction=1, meta_prob=0.7)
        assert result > 0.0

    def test_negative_direction_negative_size(self, sizer: BetSizer) -> None:
        """direction=-1 with meta_prob=0.7 -> negative bet size."""
        result = sizer.bet_size_from_meta_label(direction=-1, meta_prob=0.7)
        assert result < 0.0

    def test_magnitude_matches_direction(self, sizer: BetSizer) -> None:
        """Magnitude should be the same regardless of direction."""
        pos = sizer.bet_size_from_meta_label(direction=1, meta_prob=0.8)
        neg = sizer.bet_size_from_meta_label(direction=-1, meta_prob=0.8)
        assert pytest.approx(abs(pos)) == abs(neg)

    def test_no_edge_gives_zero(self, sizer: BetSizer) -> None:
        """meta_prob=0.5 -> no edge -> bet size = 0."""
        result = sizer.bet_size_from_meta_label(direction=1, meta_prob=0.5)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_invalid_direction_raises(self, sizer: BetSizer) -> None:
        with pytest.raises(ValueError, match="direction"):
            sizer.bet_size_from_meta_label(direction=0, meta_prob=0.7)

    def test_capped_magnitude(self, sizer_capped: BetSizer) -> None:
        """Result magnitude should not exceed max_position."""
        result = sizer_capped.bet_size_from_meta_label(direction=1, meta_prob=1.0)
        assert abs(result) <= sizer_capped.max_position + 1e-12


# ===================================================================
# discretize
# ===================================================================

class TestDiscretize:
    def test_round_down(self, sizer_discrete: BetSizer) -> None:
        """0.23 rounds to 0.2 with step=0.1."""
        assert sizer_discrete.discretize(0.23) == pytest.approx(0.2, abs=1e-9)

    def test_round_up(self, sizer_discrete: BetSizer) -> None:
        """0.47 rounds to 0.5 with step=0.1."""
        assert sizer_discrete.discretize(0.47) == pytest.approx(0.5, abs=1e-9)

    def test_filters_marginal(self, sizer_discrete: BetSizer) -> None:
        """0.04 rounds to 0.0 with step=0.1 — marginal signal filtered."""
        assert sizer_discrete.discretize(0.04) == pytest.approx(0.0, abs=1e-9)

    def test_exact_step_value(self, sizer_discrete: BetSizer) -> None:
        """0.3 stays 0.3."""
        assert sizer_discrete.discretize(0.3) == pytest.approx(0.3, abs=1e-9)

    def test_negative_value(self, sizer_discrete: BetSizer) -> None:
        """Negative bet sizes discretize correctly."""
        assert sizer_discrete.discretize(-0.47) == pytest.approx(-0.5, abs=1e-9)

    def test_clamps_to_one(self, sizer_discrete: BetSizer) -> None:
        """Values above 1.0 get clamped."""
        assert sizer_discrete.discretize(1.15) == pytest.approx(1.0, abs=1e-9)

    def test_clamps_to_neg_one(self, sizer_discrete: BetSizer) -> None:
        """Values below -1.0 get clamped."""
        assert sizer_discrete.discretize(-1.15) == pytest.approx(-1.0, abs=1e-9)

    def test_no_step_passthrough(self, sizer: BetSizer) -> None:
        """Without discretize_step, returns input unchanged."""
        assert sizer.discretize(0.23) == pytest.approx(0.23, abs=1e-12)

    def test_fine_step(self) -> None:
        """Step=0.05 works correctly."""
        s = BetSizer(discretize_step=0.05)
        assert s.discretize(0.23) == pytest.approx(0.25, abs=1e-9)
        assert s.discretize(0.12) == pytest.approx(0.10, abs=1e-9)


# ===================================================================
# dynamic_position_size
# ===================================================================

class TestDynamicPositionSize:
    def test_returns_correct_dict_structure(self, sizer: BetSizer) -> None:
        result = sizer.dynamic_position_size(
            prob=0.7, daily_vol=0.02, risk_budget=10_000.0, direction=1
        )
        expected_keys = {
            "direction", "raw_bet_size", "kelly_fraction",
            "vol_adjusted", "final_position_pct", "reasoning",
        }
        assert set(result.keys()) == expected_keys

    def test_direction_preserved(self, sizer: BetSizer) -> None:
        result = sizer.dynamic_position_size(
            prob=0.7, daily_vol=0.02, risk_budget=10_000.0, direction=-1
        )
        assert result["direction"] == -1

    def test_fractional_kelly_scales_down(self, sizer: BetSizer) -> None:
        """Half-Kelly should produce smaller kelly_fraction than full Kelly."""
        full = sizer.dynamic_position_size(
            prob=0.7, daily_vol=0.02, risk_budget=10_000.0,
            direction=1, fractional_kelly=1.0,
        )
        half = sizer.dynamic_position_size(
            prob=0.7, daily_vol=0.02, risk_budget=10_000.0,
            direction=1, fractional_kelly=0.5,
        )
        assert full["kelly_fraction"] > half["kelly_fraction"]
        assert pytest.approx(half["kelly_fraction"]) == full["kelly_fraction"] * 0.5

    def test_respects_max_position(self, sizer_capped: BetSizer) -> None:
        """final_position_pct should never exceed max_position."""
        result = sizer_capped.dynamic_position_size(
            prob=1.0, daily_vol=0.02, risk_budget=10_000.0,
            direction=1, fractional_kelly=1.0,
        )
        assert result["final_position_pct"] <= sizer_capped.max_position + 1e-12

    def test_no_edge_gives_zero_bet(self, sizer: BetSizer) -> None:
        """P=0.5 -> raw_bet_size=0 -> everything downstream is 0."""
        result = sizer.dynamic_position_size(
            prob=0.5, daily_vol=0.02, risk_budget=10_000.0, direction=1
        )
        assert result["raw_bet_size"] == pytest.approx(0.0, abs=1e-9)
        assert result["kelly_fraction"] == pytest.approx(0.0, abs=1e-9)
        assert result["final_position_pct"] == pytest.approx(0.0, abs=1e-9)

    def test_vol_adjusted_inversely_proportional(self, sizer: BetSizer) -> None:
        """Lower daily vol -> higher vol_adjusted (more units)."""
        low_vol = sizer.dynamic_position_size(
            prob=0.7, daily_vol=0.01, risk_budget=10_000.0, direction=1
        )
        high_vol = sizer.dynamic_position_size(
            prob=0.7, daily_vol=0.04, risk_budget=10_000.0, direction=1
        )
        assert low_vol["vol_adjusted"] > high_vol["vol_adjusted"]

    def test_reasoning_is_nonempty_string(self, sizer: BetSizer) -> None:
        result = sizer.dynamic_position_size(
            prob=0.7, daily_vol=0.02, risk_budget=10_000.0, direction=1
        )
        assert isinstance(result["reasoning"], str)
        assert len(result["reasoning"]) > 0

    def test_invalid_direction_raises(self, sizer: BetSizer) -> None:
        with pytest.raises(ValueError, match="direction"):
            sizer.dynamic_position_size(
                prob=0.7, daily_vol=0.02, risk_budget=10_000.0, direction=0
            )

    def test_invalid_daily_vol_raises(self, sizer: BetSizer) -> None:
        with pytest.raises(ValueError, match="daily_vol"):
            sizer.dynamic_position_size(
                prob=0.7, daily_vol=0.0, risk_budget=10_000.0, direction=1
            )

    def test_with_discretization(self, sizer_discrete: BetSizer) -> None:
        """Discretization should round the final_position_pct."""
        result = sizer_discrete.dynamic_position_size(
            prob=0.7, daily_vol=0.02, risk_budget=10_000.0, direction=1
        )
        # final_position_pct should be a multiple of 0.1
        step = sizer_discrete.discretize_step
        remainder = result["final_position_pct"] % step
        assert remainder == pytest.approx(0.0, abs=1e-9) or \
               remainder == pytest.approx(step, abs=1e-9)


# ===================================================================
# average_active_bets (Section 10.4)
# ===================================================================

class TestAverageActiveBets:
    def test_simple_average(self, sizer: BetSizer) -> None:
        signals = [
            {"bet_size": 0.3, "start_date": "2024-01-01", "end_date": "2024-01-10"},
            {"bet_size": 0.5, "start_date": "2024-01-05", "end_date": "2024-01-15"},
            {"bet_size": 0.1, "start_date": "2024-01-03", "end_date": "2024-01-12"},
        ]
        result = sizer.average_active_bets(signals)
        assert result == pytest.approx(0.3, abs=1e-9)

    def test_single_signal(self, sizer: BetSizer) -> None:
        signals = [{"bet_size": 0.7}]
        assert sizer.average_active_bets(signals) == pytest.approx(0.7, abs=1e-9)

    def test_empty_list(self, sizer: BetSizer) -> None:
        assert sizer.average_active_bets([]) == 0.0

    def test_mixed_signs(self, sizer: BetSizer) -> None:
        """Positive and negative bets should cancel partially."""
        signals = [
            {"bet_size": 0.5},
            {"bet_size": -0.3},
        ]
        result = sizer.average_active_bets(signals)
        assert result == pytest.approx(0.1, abs=1e-9)

    def test_all_negative(self, sizer: BetSizer) -> None:
        signals = [{"bet_size": -0.2}, {"bet_size": -0.4}]
        result = sizer.average_active_bets(signals)
        assert result == pytest.approx(-0.3, abs=1e-9)

    def test_zero_bets(self, sizer: BetSizer) -> None:
        signals = [{"bet_size": 0.0}, {"bet_size": 0.0}]
        assert sizer.average_active_bets(signals) == 0.0
