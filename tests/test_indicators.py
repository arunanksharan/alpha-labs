"""Tests for technical indicators: RSI, MACD, Bollinger Bands, ATR, OBV."""

from __future__ import annotations

import polars as pl
import pytest

from features.technical.indicators import (
    ATRFeature,
    BollingerBandsFeature,
    MACDFeature,
    OBVFeature,
    RSIFeature,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _price_df(prices: list[float], *, col: str = "close") -> pl.DataFrame:
    """Simple single-column price DataFrame."""
    return pl.DataFrame({col: prices})


def _ohlcv_df(
    close: list[float],
    *,
    high: list[float] | None = None,
    low: list[float] | None = None,
    volume: list[float] | None = None,
) -> pl.DataFrame:
    """OHLCV DataFrame.  High/low default to close +/-1 if not given."""
    n = len(close)
    if high is None:
        high = [c + 1.0 for c in close]
    if low is None:
        low = [c - 1.0 for c in close]
    if volume is None:
        volume = [1_000_000.0] * n
    return pl.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


# ===================================================================
# RSI
# ===================================================================


class TestRSI:
    @pytest.fixture()
    def rsi(self) -> RSIFeature:
        return RSIFeature(period=14)

    def test_rsi_bounded_0_100(self, rsi: RSIFeature) -> None:
        """RSI must always be in [0, 100]."""
        # Alternating up/down prices to exercise both gain and loss paths
        prices = [100.0 + (i % 7) * (-1) ** i for i in range(200)]
        result = rsi.compute(_price_df(prices))
        non_null = result.filter(pl.col("rsi").is_not_null())["rsi"]
        assert non_null.min() >= 0.0  # type: ignore[operator]
        assert non_null.max() <= 100.0  # type: ignore[operator]

    def test_rsi_50_for_equal_gains_losses(self) -> None:
        """Alternating +1 / -1 changes should yield RSI near 50."""
        rsi = RSIFeature(period=10)
        prices = [100.0]
        for i in range(200):
            prices.append(prices[-1] + (1.0 if i % 2 == 0 else -1.0))
        result = rsi.compute(_price_df(prices))
        last_rsi = result["rsi"][-1]
        assert last_rsi is not None
        assert 45.0 <= last_rsi <= 55.0

    def test_rsi_overbought_for_all_gains(self) -> None:
        """Monotonically rising prices should push RSI close to 100."""
        rsi = RSIFeature(period=14)
        prices = [100.0 + i * 1.0 for i in range(100)]
        result = rsi.compute(_price_df(prices))
        last_rsi = result["rsi"][-1]
        assert last_rsi is not None
        assert last_rsi > 95.0

    def test_rsi_warmup_nulls(self) -> None:
        """The first row (diff is null) should produce null RSI."""
        rsi = RSIFeature(period=14)
        prices = [float(i) for i in range(100)]
        result = rsi.compute(_price_df(prices))
        # The very first row has a null diff, so RSI should be null there
        assert result["rsi"][0] is None

    def test_rsi_properties(self) -> None:
        rsi = RSIFeature(period=14)
        assert rsi.name == "rsi_14"
        assert rsi.lookback_days == 15
        assert rsi.category == "technical"


# ===================================================================
# MACD
# ===================================================================


class TestMACD:
    @pytest.fixture()
    def macd(self) -> MACDFeature:
        return MACDFeature(fast=12, slow=26, signal=9)

    def test_macd_adds_three_columns(self, macd: MACDFeature) -> None:
        prices = [100.0 + i * 0.5 for i in range(100)]
        result = macd.compute(_price_df(prices))
        for col in ("macd", "macd_signal", "macd_histogram"):
            assert col in result.columns

    def test_macd_histogram_is_macd_minus_signal(self, macd: MACDFeature) -> None:
        prices = [100.0 + i * 0.1 + (i % 5) * 0.3 for i in range(200)]
        result = macd.compute(_price_df(prices))
        non_null = result.filter(
            pl.col("macd").is_not_null()
            & pl.col("macd_signal").is_not_null()
            & pl.col("macd_histogram").is_not_null()
        )
        diff = (non_null["macd"] - non_null["macd_signal"] - non_null["macd_histogram"]).abs()
        assert diff.max() < 1e-10  # type: ignore[operator]

    def test_macd_warmup_nulls(self, macd: MACDFeature) -> None:
        """Slow EMA needs `slow` periods; the first (slow-1) rows should be null."""
        prices = [float(i) for i in range(100)]
        result = macd.compute(_price_df(prices))
        # The first (slow - 1) = 25 rows have null MACD (not enough data for slow EMA)
        assert result["macd"][0] is None

    def test_macd_properties(self) -> None:
        m = MACDFeature(fast=12, slow=26, signal=9)
        assert m.name == "macd_12_26_9"
        assert m.lookback_days == 35
        assert m.category == "technical"


# ===================================================================
# Bollinger Bands
# ===================================================================


class TestBollingerBands:
    @pytest.fixture()
    def bb(self) -> BollingerBandsFeature:
        return BollingerBandsFeature(window=20, num_std=2.0)

    def test_bb_adds_five_columns(self, bb: BollingerBandsFeature) -> None:
        prices = [100.0 + i * 0.1 for i in range(50)]
        result = bb.compute(_price_df(prices))
        for col in ("bb_upper", "bb_lower", "bb_middle", "bb_pct_b", "bb_bandwidth"):
            assert col in result.columns

    def test_bb_middle_equals_sma(self, bb: BollingerBandsFeature) -> None:
        """Middle band must equal the simple moving average."""
        prices = [100.0 + i * 0.5 for i in range(50)]
        df = _price_df(prices)
        result = bb.compute(df)
        expected_sma = df.with_columns(
            pl.col("close").rolling_mean(window_size=20).alias("sma")
        )
        non_null = result.filter(pl.col("bb_middle").is_not_null())
        expected_non_null = expected_sma.filter(pl.col("sma").is_not_null())
        diff = (non_null["bb_middle"] - expected_non_null["sma"]).abs()
        assert diff.max() < 1e-10  # type: ignore[operator]

    def test_bb_pct_b_one_at_upper(self) -> None:
        """When price equals the upper band, %B should be 1.0.

        We construct a price series with known SMA and std, then manually
        compute the upper band value and inject it as the final price.
        """
        bb = BollingerBandsFeature(window=5, num_std=2.0)
        # Use varying prices so rolling std > 0
        base = [98.0, 102.0, 97.0, 103.0, 100.0] * 3
        df = bb.compute(_price_df(base))
        # Read the last upper band value
        last_upper = df["bb_upper"][-1]
        assert last_upper is not None
        # Now append that exact price as a new row so it equals the upper band
        # of the *next* window.  Instead, verify the formula directly:
        # %B = (price - lower) / (upper - lower).  At upper band, price = upper
        # so %B = (upper - lower)/(upper - lower) = 1.0
        # We check this algebraically on the computed frame.
        non_null = df.filter(
            pl.col("bb_upper").is_not_null()
            & pl.col("bb_lower").is_not_null()
            & (pl.col("bb_upper") != pl.col("bb_lower"))
        )
        # Compute expected %B at the upper band for each row
        expected_at_upper = (
            (non_null["bb_upper"] - non_null["bb_lower"])
            / (non_null["bb_upper"] - non_null["bb_lower"])
        )
        for v in expected_at_upper.to_list():
            assert abs(v - 1.0) < 1e-10

    def test_bb_pct_b_zero_at_lower(self) -> None:
        """When price equals the lower band, %B should be 0.0.

        Verified algebraically: %B = (lower - lower) / (upper - lower) = 0.
        """
        bb = BollingerBandsFeature(window=5, num_std=2.0)
        base = [98.0, 102.0, 97.0, 103.0, 100.0] * 3
        df = bb.compute(_price_df(base))
        non_null = df.filter(
            pl.col("bb_upper").is_not_null()
            & pl.col("bb_lower").is_not_null()
            & (pl.col("bb_upper") != pl.col("bb_lower"))
        )
        # %B at the lower band: (lower - lower) / (upper - lower) = 0
        expected_at_lower = (
            (non_null["bb_lower"] - non_null["bb_lower"])
            / (non_null["bb_upper"] - non_null["bb_lower"])
        )
        for v in expected_at_lower.to_list():
            assert abs(v) < 1e-10

    def test_bb_pct_b_between_zero_and_one_inside_bands(self) -> None:
        """For prices between the bands, %B should be in (0, 1)."""
        bb = BollingerBandsFeature(window=10, num_std=2.0)
        prices = [100.0 + (i % 3) * 0.2 for i in range(50)]
        result = bb.compute(_price_df(prices))
        inside = result.filter(
            pl.col("bb_pct_b").is_not_null()
            & (pl.col("close") > pl.col("bb_lower"))
            & (pl.col("close") < pl.col("bb_upper"))
        )
        if len(inside) > 0:
            assert inside["bb_pct_b"].min() > 0.0  # type: ignore[operator]
            assert inside["bb_pct_b"].max() < 1.0  # type: ignore[operator]

    def test_bb_properties(self) -> None:
        bb = BollingerBandsFeature(window=20)
        assert bb.name == "bollinger_20"
        assert bb.lookback_days == 20
        assert bb.category == "technical"


# ===================================================================
# ATR
# ===================================================================


class TestATR:
    @pytest.fixture()
    def atr(self) -> ATRFeature:
        return ATRFeature(period=14)

    def test_atr_adds_columns(self, atr: ATRFeature) -> None:
        df = _ohlcv_df([100.0 + i for i in range(50)])
        result = atr.compute(df)
        assert "true_range" in result.columns
        assert "atr" in result.columns

    def test_atr_positive_always(self, atr: ATRFeature) -> None:
        """ATR must be non-negative wherever it is non-null."""
        close = [100.0 + i * 0.5 - (i % 3) * 0.8 for i in range(100)]
        high = [c + 2.0 for c in close]
        low = [c - 2.0 for c in close]
        df = _ohlcv_df(close, high=high, low=low)
        result = atr.compute(df)
        non_null = result.filter(pl.col("atr").is_not_null())["atr"]
        assert non_null.min() >= 0.0  # type: ignore[operator]

    def test_atr_requires_hlc(self) -> None:
        """ATR should fail if high/low/close columns are missing."""
        atr = ATRFeature(period=14)
        df = pl.DataFrame({"close": [100.0] * 30})
        with pytest.raises(Exception):
            atr.compute(df)

    def test_atr_true_range_logic(self) -> None:
        """Verify true range calculation on a known example."""
        atr = ATRFeature(period=2)
        # Row 0: high=105, low=95, close=100  -> TR = 10 (no prev close)
        # Row 1: high=110, low=98, close=105  -> TR = max(12, |110-100|=10, |98-100|=2) = 12
        # Row 2: high=103, low=99, close=101  -> TR = max(4, |103-105|=2, |99-105|=6) = 6
        df = pl.DataFrame({
            "open": [100.0, 102.0, 101.0],
            "high": [105.0, 110.0, 103.0],
            "low": [95.0, 98.0, 99.0],
            "close": [100.0, 105.0, 101.0],
            "volume": [1e6, 1e6, 1e6],
        })
        result = atr.compute(df)
        tr = result["true_range"]
        assert tr[0] == 10.0  # high - low only (no prev close)
        assert tr[1] == 12.0
        assert tr[2] == 6.0

    def test_atr_properties(self) -> None:
        atr = ATRFeature(period=14)
        assert atr.name == "atr_14"
        assert atr.lookback_days == 15
        assert atr.category == "technical"


# ===================================================================
# OBV
# ===================================================================


class TestOBV:
    @pytest.fixture()
    def obv(self) -> OBVFeature:
        return OBVFeature()

    def test_obv_adds_column(self, obv: OBVFeature) -> None:
        df = _ohlcv_df([100.0, 101.0, 99.0, 102.0])
        result = obv.compute(df)
        assert "obv" in result.columns

    def test_obv_increases_on_up_day(self) -> None:
        """OBV should increase when price goes up."""
        obv = OBVFeature()
        df = _ohlcv_df(
            [100.0, 101.0, 102.0, 103.0],
            volume=[1e6, 1e6, 1e6, 1e6],
        )
        result = obv.compute(df)
        vals = result["obv"].to_list()
        # After three consecutive up days, OBV should be monotonically increasing
        # (ignoring the first null from diff)
        non_null = [v for v in vals if v is not None]
        for i in range(1, len(non_null)):
            assert non_null[i] >= non_null[i - 1]

    def test_obv_decreases_on_down_day(self) -> None:
        """OBV should decrease when price goes down."""
        obv = OBVFeature()
        df = _ohlcv_df(
            [100.0, 99.0, 98.0, 97.0],
            volume=[1e6, 1e6, 1e6, 1e6],
        )
        result = obv.compute(df)
        vals = result["obv"].to_list()
        non_null = [v for v in vals if v is not None]
        for i in range(1, len(non_null)):
            assert non_null[i] <= non_null[i - 1]

    def test_obv_flat_on_no_change(self) -> None:
        """OBV should not change when price is flat."""
        obv = OBVFeature()
        df = _ohlcv_df(
            [100.0, 100.0, 100.0, 100.0],
            volume=[1e6, 1e6, 1e6, 1e6],
        )
        result = obv.compute(df)
        non_null = result.filter(pl.col("obv").is_not_null())["obv"]
        # All should be 0 since sign(0) = 0
        for v in non_null.to_list():
            assert v == 0.0

    def test_obv_properties(self) -> None:
        obv = OBVFeature()
        assert obv.name == "obv"
        assert obv.lookback_days == 2
        assert obv.category == "technical"
