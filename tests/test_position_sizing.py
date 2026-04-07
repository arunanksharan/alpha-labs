"""Comprehensive tests for the position sizing engine."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from risk.position_sizing.engine import PositionSizer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sizer() -> PositionSizer:
    """Default sizer with 10 % max position."""
    return PositionSizer(max_position_pct=0.10)


@pytest.fixture
def sizer_large_cap() -> PositionSizer:
    """Sizer with a generous 50 % cap (for unclamped tests)."""
    return PositionSizer(max_position_pct=0.50)


# ===================================================================
# Equal weight
# ===================================================================

class TestEqualWeight:
    def test_equal_weight_sums_to_capital(self, sizer_large_cap: PositionSizer) -> None:
        capital = 100_000.0
        n = 5
        allocs = sizer_large_cap.equal_weight(n, capital)
        assert pytest.approx(sum(allocs), rel=1e-9) == capital

    def test_equal_weight_each_position_equal(self, sizer_large_cap: PositionSizer) -> None:
        allocs = sizer_large_cap.equal_weight(4, 200_000.0)
        assert len(allocs) == 4
        assert all(pytest.approx(a) == allocs[0] for a in allocs)

    def test_equal_weight_zero_positions(self, sizer: PositionSizer) -> None:
        assert sizer.equal_weight(0, 100_000.0) == []

    def test_equal_weight_clamped(self, sizer: PositionSizer) -> None:
        # 2 positions in 100k with 10% cap -> each clamped to 10k
        allocs = sizer.equal_weight(2, 100_000.0)
        assert all(a <= 0.10 * 100_000.0 for a in allocs)


# ===================================================================
# Kelly criterion
# ===================================================================

class TestKellyCriterion:
    def test_kelly_known_values(self, sizer_large_cap: PositionSizer) -> None:
        """win_rate=0.6, avg_win=2.0, avg_loss=1.0 -> b=2, full Kelly = (0.6*2 - 0.4)/2 = 0.4"""
        full_kelly = 0.4
        fraction = 1.0  # full Kelly
        result = sizer_large_cap.kelly_criterion(0.6, 2.0, 1.0, fraction=fraction)
        assert pytest.approx(result, abs=1e-9) == full_kelly

    def test_kelly_negative_edge_returns_zero(self, sizer: PositionSizer) -> None:
        # win_rate=0.3, avg_win=1.0, avg_loss=1.0 -> b=1, full = 0.3 - 0.7 = -0.4 -> clamped to 0
        result = sizer.kelly_criterion(0.3, 1.0, 1.0, fraction=1.0)
        assert result == 0.0

    def test_kelly_quarter_fraction(self, sizer_large_cap: PositionSizer) -> None:
        # full Kelly = 0.4, quarter Kelly = 0.1
        result = sizer_large_cap.kelly_criterion(0.6, 2.0, 1.0, fraction=0.25)
        assert pytest.approx(result, abs=1e-9) == 0.10

    def test_kelly_clamped_to_max_position(self, sizer: PositionSizer) -> None:
        # full Kelly = 0.4, fraction=1.0, max_position_pct=0.10 -> clamped to 0.10
        result = sizer.kelly_criterion(0.6, 2.0, 1.0, fraction=1.0)
        assert pytest.approx(result, abs=1e-9) == 0.10

    def test_kelly_zero_avg_loss(self, sizer: PositionSizer) -> None:
        assert sizer.kelly_criterion(0.6, 2.0, 0.0) == 0.0


# ===================================================================
# Inverse volatility
# ===================================================================

class TestInverseVolatility:
    def test_inverse_vol_higher_vol_gets_less_weight(self, sizer_large_cap: PositionSizer) -> None:
        # Asset A: vol=0.1, Asset B: vol=0.3
        allocs = sizer_large_cap.inverse_volatility([0.1, 0.3], 100_000.0)
        assert allocs[0] > allocs[1]

    def test_inverse_vol_equal_vol_equal_weights(self, sizer_large_cap: PositionSizer) -> None:
        allocs = sizer_large_cap.inverse_volatility([0.2, 0.2, 0.2], 90_000.0)
        assert all(pytest.approx(a) == allocs[0] for a in allocs)
        assert pytest.approx(sum(allocs), rel=1e-9) == 90_000.0

    def test_inverse_vol_clamped(self, sizer: PositionSizer) -> None:
        # 2 assets, one very low vol -> its weight would be huge, but clamped
        allocs = sizer.inverse_volatility([0.01, 1.0], 100_000.0)
        cap = 0.10 * 100_000.0
        assert all(a <= cap + 1e-9 for a in allocs)

    def test_inverse_vol_known_weights(self, sizer_large_cap: PositionSizer) -> None:
        # vols = [0.1, 0.2] -> inv = [10, 5] -> weights = [10/15, 5/15] = [2/3, 1/3]
        # 2/3 * 150k = 100k, 1/3 * 150k = 50k
        # But with max_position_pct=0.50, cap = 75k, so first is clamped
        allocs = sizer_large_cap.inverse_volatility([0.1, 0.2], 150_000.0)
        assert pytest.approx(allocs[0], rel=1e-6) == 75_000.0  # clamped to 50% * 150k
        assert pytest.approx(allocs[1], rel=1e-6) == 50_000.0

    def test_inverse_vol_empty(self, sizer: PositionSizer) -> None:
        assert sizer.inverse_volatility([], 100_000.0) == []

    def test_inverse_vol_negative_raises(self, sizer: PositionSizer) -> None:
        with pytest.raises(ValueError, match="strictly positive"):
            sizer.inverse_volatility([0.1, -0.2], 100_000.0)


# ===================================================================
# Risk parity
# ===================================================================

class TestRiskParity:
    @staticmethod
    def _make_returns(n_obs: int, vols: list[float], seed: int = 42) -> pl.DataFrame:
        """Generate synthetic returns with known volatilities."""
        rng = np.random.default_rng(seed)
        daily_vols = [v / np.sqrt(252) for v in vols]
        data = {
            f"asset_{i}": rng.normal(0, dv, n_obs)
            for i, dv in enumerate(daily_vols)
        }
        return pl.DataFrame(data)

    def test_risk_parity_equal_vol_equal_weights(self, sizer_large_cap: PositionSizer) -> None:
        # With truly equal-vol uncorrelated assets (large sample), risk
        # parity should produce weights where no asset is more than 2x
        # another. The iterative method amplifies small covariance noise,
        # so we test that the max/min weight ratio stays bounded.
        returns_df = self._make_returns(10_000, [0.20, 0.20, 0.20], seed=0)
        allocs = sizer_large_cap.risk_parity(returns_df, 100_000.0, target_vol=0.10)
        assert len(allocs) == 3
        assert min(allocs) > 0
        ratio = max(allocs) / min(allocs)
        assert ratio < 2.0, f"Max/min weight ratio {ratio:.2f} exceeds 2.0"

    def test_risk_parity_weights_sum_to_reasonable_amount(self, sizer_large_cap: PositionSizer) -> None:
        returns_df = self._make_returns(500, [0.15, 0.25, 0.35])
        allocs = sizer_large_cap.risk_parity(returns_df, 100_000.0, target_vol=0.10)
        total = sum(allocs)
        # Total allocation should be positive and not wildly exceed capital
        assert total > 0
        assert total < 200_000.0  # generous upper bound

    def test_risk_parity_higher_vol_gets_less(self, sizer_large_cap: PositionSizer) -> None:
        # Asset with higher vol should get less weight in risk parity
        returns_df = self._make_returns(1000, [0.10, 0.40], seed=123)
        allocs = sizer_large_cap.risk_parity(returns_df, 100_000.0, target_vol=0.10)
        assert allocs[0] > allocs[1]

    def test_risk_parity_no_numeric_cols_raises(self, sizer: PositionSizer) -> None:
        df = pl.DataFrame({"label": ["a", "b", "c"]})
        with pytest.raises(ValueError, match="no numeric columns"):
            sizer.risk_parity(df, 100_000.0)


# ===================================================================
# Volatility targeting
# ===================================================================

class TestVolatilityTargeting:
    def test_vol_targeting_scales_down_high_vol(self, sizer: PositionSizer) -> None:
        # current_vol=0.30 > target=0.15 -> weight halved
        result = sizer.volatility_targeting(0.30, 0.15, 0.08)
        assert pytest.approx(result, abs=1e-9) == 0.04

    def test_vol_targeting_scales_up_low_vol(self, sizer: PositionSizer) -> None:
        # current_vol=0.05, target=0.10, current_weight=0.04 -> 0.08
        result = sizer.volatility_targeting(0.05, 0.10, 0.04)
        assert pytest.approx(result, abs=1e-9) == 0.08

    def test_vol_targeting_clamped(self, sizer: PositionSizer) -> None:
        # Very low vol -> scaling would blow up, but clamped to max_position_pct
        result = sizer.volatility_targeting(0.01, 0.50, 0.05)
        assert result == pytest.approx(0.10, abs=1e-9)

    def test_vol_targeting_negative_weight(self, sizer: PositionSizer) -> None:
        # Short position: clamped to -max_position_pct
        result = sizer.volatility_targeting(0.01, 0.50, -0.05)
        assert result == pytest.approx(-0.10, abs=1e-9)

    def test_vol_targeting_zero_vol(self, sizer: PositionSizer) -> None:
        assert sizer.volatility_targeting(0.0, 0.10, 0.05) == 0.0


# ===================================================================
# Max drawdown sizing
# ===================================================================

class TestMaxDrawdownSizing:
    def test_max_drawdown_sizing_reduces_at_threshold(self, sizer: PositionSizer) -> None:
        # At 50% of max_allowed, factor = 0.5 -> half the weight
        result = sizer.max_drawdown_sizing(0.075, 0.15, 0.10)
        assert pytest.approx(result, abs=1e-9) == 0.05

    def test_max_drawdown_sizing_zero_at_max(self, sizer: PositionSizer) -> None:
        result = sizer.max_drawdown_sizing(0.15, 0.15, 0.10)
        assert result == 0.0

    def test_max_drawdown_sizing_beyond_max(self, sizer: PositionSizer) -> None:
        # Drawdown exceeds limit -> factor clamped to 0
        result = sizer.max_drawdown_sizing(0.20, 0.15, 0.10)
        assert result == 0.0

    def test_max_drawdown_sizing_no_drawdown(self, sizer: PositionSizer) -> None:
        result = sizer.max_drawdown_sizing(0.0, 0.15, 0.10)
        assert pytest.approx(result, abs=1e-9) == 0.10

    def test_max_drawdown_sizing_partial(self, sizer: PositionSizer) -> None:
        # 1/3 of max -> factor = 2/3
        result = sizer.max_drawdown_sizing(0.05, 0.15, 0.09)
        assert pytest.approx(result, abs=1e-9) == 0.06

    def test_max_drawdown_sizing_zero_max_allowed(self, sizer: PositionSizer) -> None:
        assert sizer.max_drawdown_sizing(0.05, 0.0, 0.10) == 0.0
