"""Signal decay analysis engine.

Measures how long a trading signal remains profitable by computing
rolling information coefficients, IC decay curves, and half-life
estimates.  This is a core differentiator for the quant-researcher
platform -- it answers the question *"how quickly does my alpha
disappear?"*
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats as scipy_stats


class SignalDecayAnalyzer:
    """Measure how long a trading signal remains profitable.

    Computes rolling IC, half-life of IC, and decay curves.

    Parameters
    ----------
    max_horizon : int
        Maximum forward days to analyse decay (default 60).
    """

    def __init__(self, max_horizon: int = 60) -> None:
        self.max_horizon = max_horizon

    # ------------------------------------------------------------------
    # IC decay curve
    # ------------------------------------------------------------------

    def compute_ic_curve(
        self, signals: pl.DataFrame, prices: pl.DataFrame
    ) -> pl.DataFrame:
        """Compute IC at each forward horizon from 1 to *max_horizon*.

        Parameters
        ----------
        signals
            DataFrame with columns ``[date, ticker, signal_value]``.
        prices
            DataFrame with columns ``[date, ticker, close]``, sorted by
            date within each ticker.

        Returns
        -------
        pl.DataFrame
            Columns: ``[horizon, ic, ic_std, ic_tstat, is_significant]``.
        """
        # Build a wide price matrix: date x ticker
        price_pivot = prices.pivot(on="ticker", index="date", values="close").sort("date")
        dates_arr = price_pivot["date"].to_list()
        ticker_cols = [c for c in price_pivot.columns if c != "date"]

        # Pre-compute forward returns for every horizon
        price_matrix = price_pivot.select(ticker_cols).to_numpy().astype(float)
        n_dates = len(dates_arr)

        # Map (date, ticker) -> row/col index for fast lookup
        date_to_idx = {d: i for i, d in enumerate(dates_arr)}
        ticker_to_col = {t: j for j, t in enumerate(ticker_cols)}

        horizons: list[int] = []
        ics: list[float] = []
        ic_stds: list[float] = []
        ic_tstats: list[float] = []
        is_significant: list[bool] = []

        for h in range(1, self.max_horizon + 1):
            # Forward return matrix: (close[t+h] / close[t]) - 1
            if h >= n_dates:
                break

            fwd_returns = np.full_like(price_matrix, np.nan)
            fwd_returns[: n_dates - h, :] = (
                price_matrix[h:, :] / price_matrix[: n_dates - h, :] - 1.0
            )

            # For each date in signals, gather cross-sectional IC
            daily_ics: list[float] = []
            for dt in signals["date"].unique().sort().to_list():
                if dt not in date_to_idx:
                    continue
                row_idx = date_to_idx[dt]
                if row_idx + h >= n_dates:
                    continue

                day_signals = signals.filter(pl.col("date") == dt)
                sig_vals: list[float] = []
                ret_vals: list[float] = []

                for ticker, sig_val in zip(
                    day_signals["ticker"].to_list(),
                    day_signals["signal_value"].to_list(),
                    strict=True,
                ):
                    if ticker not in ticker_to_col:
                        continue
                    col_idx = ticker_to_col[ticker]
                    fwd_ret = fwd_returns[row_idx, col_idx]
                    if np.isnan(fwd_ret):
                        continue
                    sig_vals.append(float(sig_val))
                    ret_vals.append(float(fwd_ret))

                if len(sig_vals) >= 3:
                    corr, _ = scipy_stats.spearmanr(sig_vals, ret_vals)
                    if not np.isnan(corr):
                        daily_ics.append(corr)

            if daily_ics:
                mean_ic = float(np.mean(daily_ics))
                std_ic = float(np.std(daily_ics, ddof=1)) if len(daily_ics) > 1 else 0.0
                t_stat = (
                    mean_ic / (std_ic / np.sqrt(len(daily_ics)))
                    if std_ic > 0
                    else 0.0
                )
            else:
                mean_ic = 0.0
                std_ic = 0.0
                t_stat = 0.0

            horizons.append(h)
            ics.append(mean_ic)
            ic_stds.append(std_ic)
            ic_tstats.append(float(t_stat))
            is_significant.append(abs(t_stat) > 1.96)

        return pl.DataFrame(
            {
                "horizon": horizons,
                "ic": ics,
                "ic_std": ic_stds,
                "ic_tstat": ic_tstats,
                "is_significant": is_significant,
            }
        )

    # ------------------------------------------------------------------
    # Half-life estimation
    # ------------------------------------------------------------------

    def compute_ic_half_life(self, ic_curve: pl.DataFrame) -> float:
        """Estimate the half-life of IC decay via exponential fit.

        Fits ``IC(h) = IC(0) * exp(-lambda * h)`` using OLS on
        ``ln(|IC|)`` vs ``h``.

        Returns
        -------
        float
            Half-life in trading days: ``ln(2) / lambda``.
        """
        horizons = ic_curve["horizon"].to_numpy().astype(float)
        ic_vals = ic_curve["ic"].to_numpy().astype(float)

        # Only use positive |IC| values for log fit
        abs_ic = np.abs(ic_vals)
        mask = abs_ic > 1e-10
        if mask.sum() < 2:
            return float("inf")

        h_valid = horizons[mask]
        log_ic = np.log(abs_ic[mask])

        # OLS: log(|IC|) = a - lambda * h
        slope, intercept, _, _, _ = scipy_stats.linregress(h_valid, log_ic)

        lam = -slope
        if lam <= 0:
            return float("inf")

        return float(np.log(2) / lam)

    # ------------------------------------------------------------------
    # Rolling IC
    # ------------------------------------------------------------------

    def rolling_ic(
        self,
        signals: pl.DataFrame,
        prices: pl.DataFrame,
        horizon: int = 5,
        window: int = 63,
    ) -> pl.DataFrame:
        """Compute IC over rolling windows of *window* trading days.

        Parameters
        ----------
        signals
            ``[date, ticker, signal_value]``
        prices
            ``[date, ticker, close]``
        horizon
            Forward return horizon for IC calculation.
        window
            Number of trading days per rolling window.

        Returns
        -------
        pl.DataFrame
            ``[date, ic, is_significant]``
        """
        # Compute forward returns for the given horizon
        fwd_returns = self._compute_forward_returns(prices, horizon)

        # Merge signals with forward returns
        merged = signals.join(fwd_returns, on=["date", "ticker"], how="inner")

        # Get unique sorted dates
        unique_dates = merged["date"].unique().sort().to_list()

        result_dates: list[object] = []
        result_ics: list[float] = []
        result_sig: list[bool] = []

        for i in range(window - 1, len(unique_dates)):
            window_dates = unique_dates[i - window + 1 : i + 1]
            window_data = merged.filter(pl.col("date").is_in(window_dates))

            if len(window_data) < 3:
                continue

            corr, pval = scipy_stats.spearmanr(
                window_data["signal_value"].to_numpy(),
                window_data["forward_return"].to_numpy(),
            )
            if np.isnan(corr):
                continue

            result_dates.append(unique_dates[i])
            result_ics.append(float(corr))
            result_sig.append(pval < 0.05)

        return pl.DataFrame(
            {
                "date": result_dates,
                "ic": result_ics,
                "is_significant": result_sig,
            }
        )

    # ------------------------------------------------------------------
    # Compare decay across signal sets
    # ------------------------------------------------------------------

    def compare_decay(
        self,
        signal_sets: dict[str, pl.DataFrame],
        prices: pl.DataFrame,
    ) -> pl.DataFrame:
        """Compare IC decay curves for multiple signal types.

        Parameters
        ----------
        signal_sets
            Mapping of signal name to signals DataFrame.
        prices
            Price DataFrame with ``[date, ticker, close]``.

        Returns
        -------
        pl.DataFrame
            ``[horizon, signal_name, ic]`` -- ready for plotting.
        """
        frames: list[pl.DataFrame] = []
        for name, sigs in signal_sets.items():
            curve = self.compute_ic_curve(sigs, prices)
            frames.append(
                curve.select("horizon", "ic").with_columns(
                    pl.lit(name).alias("signal_name")
                )
            )
        return pl.concat(frames)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def decay_summary(self, ic_curve: pl.DataFrame) -> dict[str, float]:
        """Return a concise summary of the IC decay curve.

        Keys: ``ic_at_1d``, ``ic_at_5d``, ``ic_at_20d``, ``half_life``,
        ``max_ic``, ``max_ic_horizon``.
        """
        def _ic_at(h: int) -> float:
            row = ic_curve.filter(pl.col("horizon") == h)
            if row.is_empty():
                return 0.0
            return float(row["ic"][0])

        max_ic_row = ic_curve.sort("ic", descending=True).head(1)
        max_ic = float(max_ic_row["ic"][0]) if not max_ic_row.is_empty() else 0.0
        max_ic_horizon = (
            float(max_ic_row["horizon"][0]) if not max_ic_row.is_empty() else 0.0
        )

        return {
            "ic_at_1d": _ic_at(1),
            "ic_at_5d": _ic_at(5),
            "ic_at_20d": _ic_at(20),
            "half_life": self.compute_ic_half_life(ic_curve),
            "max_ic": max_ic,
            "max_ic_horizon": max_ic_horizon,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_forward_returns(
        prices: pl.DataFrame, horizon: int
    ) -> pl.DataFrame:
        """Compute forward returns per ticker at a given horizon.

        Returns ``[date, ticker, forward_return]``.
        """
        result_frames: list[pl.DataFrame] = []
        for ticker in prices["ticker"].unique().to_list():
            tk = prices.filter(pl.col("ticker") == ticker).sort("date")
            closes = tk["close"].to_numpy().astype(float)
            dates = tk["date"].to_list()
            n = len(closes)
            fwd = np.full(n, np.nan)
            if n > horizon:
                fwd[:n - horizon] = closes[horizon:] / closes[:n - horizon] - 1.0
            result_frames.append(
                pl.DataFrame(
                    {
                        "date": dates,
                        "ticker": [ticker] * n,
                        "forward_return": fwd.tolist(),
                    }
                )
            )
        if not result_frames:
            return pl.DataFrame(
                {"date": [], "ticker": [], "forward_return": []},
            )
        return (
            pl.concat(result_frames)
            .filter(pl.col("forward_return").is_not_nan())
        )
