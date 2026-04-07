"""Triple barrier labeling and meta-labeling for financial ML.

Implements the labeling methodology from Lopez de Prado,
"Advances in Financial Machine Learning", Chapters 3-4.

Triple barrier labeling defines three exit conditions for each trade:
    1. Upper barrier  -- take-profit (price rises by profit_taking * daily_vol)
    2. Lower barrier  -- stop-loss   (price falls by stop_loss * daily_vol)
    3. Vertical barrier -- time expiry (max_holding_period days elapsed)

Meta-labeling separates the *direction* decision (primary model) from the
*size* decision (secondary/meta model).  The meta-label is binary: 1 if the
primary model's predicted direction agrees with the realized outcome, 0
otherwise.

Sample weights based on label uniqueness prevent overlapping labels from
dominating the training set.
"""

from __future__ import annotations

import numpy as np
import polars as pl


class TripleBarrierLabeler:
    """Triple barrier labeling method for financial ML.

    Three barriers define the outcome:
    1. Upper barrier: take-profit (positive return threshold)
    2. Lower barrier: stop-loss (negative return threshold)
    3. Vertical barrier: time expiry (max holding period)

    Reference: Lopez de Prado, "Advances in Financial ML", Ch. 3
    """

    def __init__(
        self,
        profit_taking: float = 2.0,
        stop_loss: float = 2.0,
        max_holding_period: int = 10,
        vol_window: int = 20,
    ) -> None:
        if profit_taking <= 0:
            raise ValueError(f"profit_taking must be positive, got {profit_taking}")
        if stop_loss <= 0:
            raise ValueError(f"stop_loss must be positive, got {stop_loss}")
        if max_holding_period < 1:
            raise ValueError(
                f"max_holding_period must be >= 1, got {max_holding_period}"
            )
        if vol_window < 2:
            raise ValueError(f"vol_window must be >= 2, got {vol_window}")

        self.profit_taking = profit_taking
        self.stop_loss = stop_loss
        self.max_holding_period = max_holding_period
        self.vol_window = vol_window

    # ------------------------------------------------------------------
    # Label
    # ------------------------------------------------------------------

    def label(self, prices: pl.DataFrame) -> pl.DataFrame:
        """Apply triple barrier labeling to a price series.

        Parameters
        ----------
        prices : pl.DataFrame
            Must contain ``date`` (Date) and ``close`` (numeric) columns.

        Returns
        -------
        pl.DataFrame
            Columns: ``[date, label, barrier_hit, return_at_barrier,
            holding_period]``.

            * **label** -- 1 (upper barrier hit first / profitable),
              -1 (lower barrier hit first / loss), 0 (vertical barrier /
              timeout).
            * **barrier_hit** -- ``"upper"``, ``"lower"``, or ``"vertical"``.
            * **return_at_barrier** -- simple return from entry to the bar
              where the first barrier was touched.
            * **holding_period** -- number of bars held.

        Notes
        -----
        This produces **forward-looking** labels.  They are used *only*
        as training targets; they must **never** appear as features.
        """
        self._validate_prices(prices)

        dates = prices["date"].to_list()
        close = prices["close"].to_numpy().astype(np.float64)
        n = len(close)

        # Daily log returns -> rolling std (daily volatility)
        log_returns = np.diff(np.log(close), prepend=np.nan)
        daily_vol = self._rolling_std(log_returns, self.vol_window)

        labels: list[int] = []
        barriers: list[str] = []
        returns_at_barrier: list[float] = []
        holding_periods: list[int] = []
        valid_dates: list[object] = []

        for t in range(n):
            vol_t = daily_vol[t]
            if np.isnan(vol_t) or vol_t == 0.0:
                continue

            upper = close[t] * (1.0 + self.profit_taking * vol_t)
            lower = close[t] * (1.0 - self.stop_loss * vol_t)
            end = min(t + self.max_holding_period, n - 1)

            hit_label = 0
            hit_barrier = "vertical"
            hit_idx = end

            for j in range(t + 1, end + 1):
                if close[j] >= upper:
                    hit_label = 1
                    hit_barrier = "upper"
                    hit_idx = j
                    break
                if close[j] <= lower:
                    hit_label = -1
                    hit_barrier = "lower"
                    hit_idx = j
                    break

            ret = (close[hit_idx] - close[t]) / close[t]
            hp = hit_idx - t

            valid_dates.append(dates[t])
            labels.append(hit_label)
            barriers.append(hit_barrier)
            returns_at_barrier.append(ret)
            holding_periods.append(hp)

        return pl.DataFrame(
            {
                "date": valid_dates,
                "label": labels,
                "barrier_hit": barriers,
                "return_at_barrier": returns_at_barrier,
                "holding_period": holding_periods,
            }
        ).with_columns(pl.col("date").cast(pl.Date))

    # ------------------------------------------------------------------
    # Meta-label
    # ------------------------------------------------------------------

    def meta_label(
        self,
        primary_signals: pl.DataFrame,
        labels: pl.DataFrame,
    ) -> pl.DataFrame:
        """Produce meta-labels for a secondary (sizing) model.

        The primary model decides *direction*; the meta-model learns
        whether that direction call was *correct*, enabling it to
        abstain or scale position size.

        Parameters
        ----------
        primary_signals : pl.DataFrame
            Columns ``[date, direction]`` where direction is in {-1, 0, 1}.
        labels : pl.DataFrame
            Output of :meth:`label` (must contain ``date`` and ``label``).

        Returns
        -------
        pl.DataFrame
            Columns ``[date, direction, meta_label]``.
            ``meta_label`` is 1 when the primary direction matches the
            realized label direction, 0 otherwise.
        """
        joined = primary_signals.join(labels.select("date", "label"), on="date")

        meta = joined.with_columns(
            pl.when(
                # Direction matches: both positive or both negative
                ((pl.col("direction") > 0) & (pl.col("label") > 0))
                | ((pl.col("direction") < 0) & (pl.col("label") < 0))
            )
            .then(pl.lit(1))
            .otherwise(pl.lit(0))
            .alias("meta_label")
        )

        return meta.select("date", "direction", "meta_label")

    # ------------------------------------------------------------------
    # Sample weights (uniqueness-based, Ch. 4)
    # ------------------------------------------------------------------

    def compute_sample_weights(
        self,
        labels: pl.DataFrame,
        prices: pl.DataFrame,
    ) -> pl.DataFrame:
        """Compute uniqueness-based sample weights.

        Overlapping labels share information; a label whose holding
        period overlaps with many others should receive a lower weight
        so it does not dominate training.

        Parameters
        ----------
        labels : pl.DataFrame
            Output of :meth:`label`.  Must contain ``date`` and
            ``holding_period``.
        prices : pl.DataFrame
            Price DataFrame used to map dates to integer indices.

        Returns
        -------
        pl.DataFrame
            Columns ``[date, weight]``.  Weights are normalized so they
            sum to ``len(labels)``.
        """
        price_dates = prices["date"].to_list()
        date_to_idx: dict[object, int] = {d: i for i, d in enumerate(price_dates)}

        label_dates = labels["date"].to_list()
        holding_periods = labels["holding_period"].to_numpy()
        n_labels = len(label_dates)
        n_bars = len(price_dates)

        # Build concurrency matrix: for each bar, how many labels span it
        concurrency = np.zeros(n_bars, dtype=np.float64)
        start_end: list[tuple[int, int]] = []

        for i in range(n_labels):
            d = label_dates[i]
            idx = date_to_idx.get(d)
            if idx is None:
                start_end.append((-1, -1))
                continue
            end_idx = min(idx + int(holding_periods[i]), n_bars - 1)
            start_end.append((idx, end_idx))
            concurrency[idx : end_idx + 1] += 1.0

        # Average uniqueness per label = mean(1 / concurrency) over its span
        weights = np.ones(n_labels, dtype=np.float64)
        for i in range(n_labels):
            s, e = start_end[i]
            if s < 0:
                continue
            conc_slice = concurrency[s : e + 1]
            # Avoid division by zero (should not happen, but be safe)
            safe = np.where(conc_slice > 0, conc_slice, 1.0)
            weights[i] = np.mean(1.0 / safe)

        # Normalize so weights sum to n_labels (like uniform weighting)
        total = weights.sum()
        if total > 0:
            weights = weights * (n_labels / total)

        return pl.DataFrame(
            {
                "date": label_dates,
                "weight": weights.tolist(),
            }
        ).with_columns(pl.col("date").cast(pl.Date))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rolling_std(arr: np.ndarray, window: int) -> np.ndarray:
        """Compute rolling standard deviation, returning NaN for
        positions with insufficient data."""
        out = np.full_like(arr, np.nan)
        for i in range(window - 1, len(arr)):
            out[i] = np.nanstd(arr[i - window + 1 : i + 1], ddof=1)
        return out

    @staticmethod
    def _validate_prices(prices: pl.DataFrame) -> None:
        if "date" not in prices.columns:
            raise ValueError("prices DataFrame must contain a 'date' column")
        if "close" not in prices.columns:
            raise ValueError("prices DataFrame must contain a 'close' column")
