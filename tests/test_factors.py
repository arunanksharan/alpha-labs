"""Tests for analytics/factors.py — Fama-French factor model."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from analytics.factors import FamaFrenchModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _business_dates(start: date, n: int) -> list[date]:
    dates: list[date] = []
    current = start
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


@pytest.fixture()
def ff3() -> FamaFrenchModel:
    return FamaFrenchModel(n_factors=3)


@pytest.fixture()
def ff5() -> FamaFrenchModel:
    return FamaFrenchModel(n_factors=5)


@pytest.fixture()
def factors_3(ff3: FamaFrenchModel) -> pl.DataFrame:
    return ff3.load_factors("2022-01-03", "2023-01-03")


@pytest.fixture()
def factors_5(ff5: FamaFrenchModel) -> pl.DataFrame:
    return ff5.load_factors("2022-01-03", "2023-01-03")


# ---------------------------------------------------------------------------
# load_factors
# ---------------------------------------------------------------------------


class TestLoadFactors:
    def test_load_factors_schema_3(self, ff3: FamaFrenchModel) -> None:
        df = ff3.load_factors("2022-01-03", "2022-06-30")
        assert "date" in df.columns
        assert "mkt_rf" in df.columns
        assert "smb" in df.columns
        assert "hml" in df.columns
        assert "rf" in df.columns
        assert df["date"].dtype == pl.Date
        # Should NOT have 5-factor columns
        assert "rmw" not in df.columns
        assert "cma" not in df.columns

    def test_load_factors_schema_5(self, ff5: FamaFrenchModel) -> None:
        df = ff5.load_factors("2022-01-03", "2022-06-30")
        assert "rmw" in df.columns
        assert "cma" in df.columns
        assert "mkt_rf" in df.columns
        assert "rf" in df.columns

    def test_load_factors_business_days_only(self, ff3: FamaFrenchModel) -> None:
        df = ff3.load_factors("2022-01-03", "2022-01-09")  # Mon to Sun
        dates = df["date"].to_list()
        for d in dates:
            assert d.weekday() < 5

    def test_invalid_n_factors(self) -> None:
        with pytest.raises(ValueError, match="n_factors must be 3 or 5"):
            FamaFrenchModel(n_factors=4)


# ---------------------------------------------------------------------------
# regression
# ---------------------------------------------------------------------------


class TestRegression:
    def test_regression_returns_required_keys(
        self, ff3: FamaFrenchModel, factors_3: pl.DataFrame
    ) -> None:
        rng = np.random.default_rng(99)
        returns = pl.Series("returns", rng.normal(0.0003, 0.01, len(factors_3)))
        result = ff3.regression(returns, factors_3)

        assert "alpha" in result
        assert "alpha_tstat" in result
        assert "betas" in result
        assert "r_squared" in result
        assert "residual_vol" in result
        assert isinstance(result["betas"], dict)
        assert set(result["betas"].keys()) == {"mkt_rf", "smb", "hml"}  # type: ignore[union-attr]

    def test_regression_alpha_near_zero_for_market(
        self, ff3: FamaFrenchModel, factors_3: pl.DataFrame
    ) -> None:
        """Market returns regressed on market factor -> alpha ~0, beta ~1."""
        # Strategy returns = mkt_rf + rf (i.e. the market itself)
        mkt_returns = (factors_3["mkt_rf"] + factors_3["rf"]).alias("returns")
        result = ff3.regression(mkt_returns, factors_3)

        assert abs(result["alpha"]) < 1e-10  # type: ignore[arg-type]
        assert abs(result["betas"]["mkt_rf"] - 1.0) < 1e-10  # type: ignore[index]
        assert abs(result["betas"]["smb"]) < 1e-10  # type: ignore[index]
        assert abs(result["betas"]["hml"]) < 1e-10  # type: ignore[index]

    def test_regression_r_squared_bounds(
        self, ff3: FamaFrenchModel, factors_3: pl.DataFrame
    ) -> None:
        rng = np.random.default_rng(11)
        returns = pl.Series("returns", rng.normal(0.0003, 0.01, len(factors_3)))
        result = ff3.regression(returns, factors_3)
        assert 0.0 <= result["r_squared"] <= 1.0  # type: ignore[operator]

    def test_regression_5_factor(
        self, ff5: FamaFrenchModel, factors_5: pl.DataFrame
    ) -> None:
        rng = np.random.default_rng(22)
        returns = pl.Series("returns", rng.normal(0.0003, 0.01, len(factors_5)))
        result = ff5.regression(returns, factors_5)
        assert set(result["betas"].keys()) == {  # type: ignore[union-attr]
            "mkt_rf", "smb", "hml", "rmw", "cma"
        }


# ---------------------------------------------------------------------------
# factor_attribution
# ---------------------------------------------------------------------------


class TestFactorAttribution:
    def test_factor_attribution_sums_to_total(
        self, ff3: FamaFrenchModel, factors_3: pl.DataFrame
    ) -> None:
        rng = np.random.default_rng(33)
        returns = pl.Series("returns", rng.normal(0.0005, 0.01, len(factors_3)))
        attr = ff3.factor_attribution(returns, factors_3)

        assert "factor_name" in attr.columns
        assert "contribution" in attr.columns
        assert "pct_of_total" in attr.columns

        # Sum of pct_of_total (signed, weighted by abs) should be meaningful
        total_contrib = attr["contribution"].sum()
        # The sum of all contributions should equal mean excess return (approx)
        mean_excess = float(
            (returns - factors_3["rf"]).mean()  # type: ignore[arg-type]
        )
        assert abs(total_contrib - mean_excess) < 1e-8  # type: ignore[arg-type]

    def test_factor_attribution_has_alpha_row(
        self, ff3: FamaFrenchModel, factors_3: pl.DataFrame
    ) -> None:
        rng = np.random.default_rng(44)
        returns = pl.Series("returns", rng.normal(0.0003, 0.01, len(factors_3)))
        attr = ff3.factor_attribution(returns, factors_3)
        assert "alpha" in attr["factor_name"].to_list()


# ---------------------------------------------------------------------------
# information coefficient
# ---------------------------------------------------------------------------


class TestInformationCoefficient:
    def test_ic_perfect_signal(self, ff3: FamaFrenchModel) -> None:
        """Rank-preserving signal should yield IC = 1.0."""
        dates = _business_dates(date(2022, 1, 3), 5)
        tickers = ["A", "B", "C", "D", "E"]

        rows_sig: list[dict[str, object]] = []
        rows_ret: list[dict[str, object]] = []
        rng = np.random.default_rng(55)

        for dt in dates:
            values = rng.uniform(-1, 1, len(tickers))
            for i, t in enumerate(tickers):
                rows_sig.append(
                    {"date": dt, "ticker": t, "signal_value": float(values[i])}
                )
                # Forward return preserves rank perfectly
                rows_ret.append(
                    {"date": dt, "ticker": t, "forward_return": float(values[i])}
                )

        signals = pl.DataFrame(rows_sig).with_columns(pl.col("date").cast(pl.Date))
        fwd = pl.DataFrame(rows_ret).with_columns(pl.col("date").cast(pl.Date))

        ic = ff3.compute_information_coefficient(signals, fwd)
        assert abs(ic - 1.0) < 1e-10

    def test_ic_random_signal(self, ff3: FamaFrenchModel) -> None:
        """Random signal should yield IC near 0."""
        dates = _business_dates(date(2022, 1, 3), 200)
        tickers = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
        rng = np.random.default_rng(66)

        rows_sig: list[dict[str, object]] = []
        rows_ret: list[dict[str, object]] = []

        for dt in dates:
            sig_vals = rng.normal(0, 1, len(tickers))
            ret_vals = rng.normal(0, 1, len(tickers))
            for i, t in enumerate(tickers):
                rows_sig.append(
                    {"date": dt, "ticker": t, "signal_value": float(sig_vals[i])}
                )
                rows_ret.append(
                    {"date": dt, "ticker": t, "forward_return": float(ret_vals[i])}
                )

        signals = pl.DataFrame(rows_sig).with_columns(pl.col("date").cast(pl.Date))
        fwd = pl.DataFrame(rows_ret).with_columns(pl.col("date").cast(pl.Date))

        ic = ff3.compute_information_coefficient(signals, fwd)
        assert abs(ic) < 0.15  # should be close to 0


# ---------------------------------------------------------------------------
# rolling_factor_exposure
# ---------------------------------------------------------------------------


class TestRollingFactorExposure:
    def test_rolling_factor_exposure_shape(
        self, ff3: FamaFrenchModel, factors_3: pl.DataFrame
    ) -> None:
        rng = np.random.default_rng(77)
        returns = pl.Series("returns", rng.normal(0.0003, 0.01, len(factors_3)))
        window = 63
        result = ff3.rolling_factor_exposure(returns, factors_3, window=window)

        expected_rows = len(factors_3) - window + 1
        assert len(result) == expected_rows
        assert "date" in result.columns
        assert "mkt_rf_beta" in result.columns
        assert "smb_beta" in result.columns
        assert "hml_beta" in result.columns

    def test_rolling_too_few_observations(
        self, ff3: FamaFrenchModel
    ) -> None:
        factors = ff3.load_factors("2022-01-03", "2022-01-31")
        returns = pl.Series("returns", np.zeros(len(factors)))
        with pytest.raises(ValueError, match="Need at least"):
            ff3.rolling_factor_exposure(returns, factors, window=1000)

    def test_rolling_5_factor_columns(
        self, ff5: FamaFrenchModel, factors_5: pl.DataFrame
    ) -> None:
        rng = np.random.default_rng(88)
        returns = pl.Series("returns", rng.normal(0.0003, 0.01, len(factors_5)))
        result = ff5.rolling_factor_exposure(returns, factors_5, window=63)
        assert "rmw_beta" in result.columns
        assert "cma_beta" in result.columns
