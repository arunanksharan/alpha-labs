"""The Quant -- statistical edge-finder specialist agent.

Computes z-scores, backtests mean-reversion signals, measures signal decay,
and validates results with the deflated Sharpe ratio.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats as scipy_stats

from agents.specialists import AgentFinding
from core.adapters import fetch_and_prepare_prices
from features.technical.zscore import ZScoreFeature
from features.technical.momentum import MomentumFeature
from analytics.returns import compute_returns, compute_sharpe
from analytics.signal_decay import SignalDecayAnalyzer
from backtest.engine.vectorized import VectorizedBacktestEngine
from backtest.validation import BacktestValidator


class TheQuant:
    """The statistical edge-finder. Computes z-scores, backtests signals, measures decay."""

    AGENT_NAME: str = "the_quant"

    def analyze(self, ticker: str, start_date: str, end_date: str) -> AgentFinding:
        """Run full quantitative analysis on *ticker* over the given date range.

        Parameters
        ----------
        ticker:
            Ticker symbol (e.g. "AAPL").
        start_date:
            ISO date string (YYYY-MM-DD).
        end_date:
            ISO date string (YYYY-MM-DD).

        Returns
        -------
        AgentFinding
            Structured result with signal, confidence, details, and thought stream.
        """
        thoughts: list[str] = []
        details: dict = {}

        # ----------------------------------------------------------
        # Step 1: Fetch prices
        # ----------------------------------------------------------
        try:
            prices = fetch_and_prepare_prices(ticker, start_date, end_date)
            thoughts.append(f"Fetched {len(prices)} price bars for {ticker}.")
        except Exception as exc:
            thoughts.append(f"Failed to fetch prices for {ticker}: {exc}")
            return AgentFinding(
                agent_name=self.AGENT_NAME,
                ticker=ticker,
                signal="neutral",
                confidence=0.0,
                reasoning=f"Could not fetch price data: {exc}",
                details={},
                thoughts=thoughts,
            )

        # ----------------------------------------------------------
        # Step 2: Compute z-score
        # ----------------------------------------------------------
        z_value: float = 0.0
        try:
            prices_with_z = ZScoreFeature(window=20).compute(prices)
            z_value = float(prices_with_z["zscore"].drop_nulls().to_list()[-1])
            details["zscore"] = z_value
            thoughts.append(f"Computing z-score for {ticker}... z = {z_value:.2f}")
        except Exception as exc:
            thoughts.append(f"Z-score computation failed: {exc}")

        # ----------------------------------------------------------
        # Step 3: Compute momentum
        # ----------------------------------------------------------
        momentum_value: float | None = None
        try:
            prices_with_mom = MomentumFeature().compute(prices)
            mom_series = prices_with_mom["momentum"].drop_nulls()
            if len(mom_series) > 0:
                momentum_value = float(mom_series.to_list()[-1])
                details["momentum"] = momentum_value
                thoughts.append(f"Momentum rank: {momentum_value:.4f}")
            else:
                thoughts.append("Momentum: insufficient data for lookback window.")
        except Exception as exc:
            thoughts.append(f"Momentum computation failed: {exc}")

        # ----------------------------------------------------------
        # Step 4: Z-score threshold check
        # ----------------------------------------------------------
        if abs(z_value) >= 2.0:
            thoughts.append(f"Z-score at {z_value:.2f} -- past entry threshold")
        else:
            thoughts.append(f"Z-score at {z_value:.2f} -- within normal range")

        # ----------------------------------------------------------
        # Step 5: Historical backtest with mean reversion signals
        # ----------------------------------------------------------
        win_rate: float = 50.0
        avg_return: float = 0.0
        n_instances: int = 0
        try:
            # Build mean-reversion signals from z-score
            prices_with_z = ZScoreFeature(window=20).compute(prices)
            signal_df = (
                prices_with_z.filter(pl.col("zscore").is_not_null())
                .with_columns([
                    pl.when(pl.col("zscore") < -2.0)
                    .then(pl.lit(1.0))
                    .when(pl.col("zscore") > 2.0)
                    .then(pl.lit(-1.0))
                    .otherwise(pl.lit(0.0))
                    .alias("direction"),
                    pl.lit(1.0).alias("confidence"),
                    pl.lit(ticker).alias("ticker"),
                ])
                .filter(pl.col("direction") != 0.0)
                .select("date", "ticker", "direction", "confidence")
            )

            if len(signal_df) > 0:
                # Prepare prices with ticker column for the engine
                bt_prices = prices.with_columns(pl.lit(ticker).alias("ticker"))
                engine = VectorizedBacktestEngine()
                result = engine.run(signal_df, bt_prices)
                win_rate = result.win_rate * 100.0
                avg_return = result.total_return * 100.0
                n_instances = len(signal_df)
                details["backtest_win_rate"] = win_rate
                details["backtest_avg_return"] = avg_return
                details["backtest_n_signals"] = n_instances
                details["backtest_sharpe"] = result.sharpe_ratio
                thoughts.append(
                    f"Historical: {n_instances} similar instances, "
                    f"{win_rate:.1f}% win rate, {avg_return:.2f}% avg return"
                )
            else:
                thoughts.append("Historical: no mean-reversion signals triggered in sample.")
        except Exception as exc:
            thoughts.append(f"Backtest failed: {exc}")

        # ----------------------------------------------------------
        # Step 6: Signal decay analysis
        # ----------------------------------------------------------
        try:
            # Build signal and price DataFrames in the format SignalDecayAnalyzer expects
            prices_with_z = ZScoreFeature(window=20).compute(prices)
            signal_for_decay = (
                prices_with_z.filter(pl.col("zscore").is_not_null())
                .select(
                    pl.col("date"),
                    pl.lit(ticker).alias("ticker"),
                    pl.col("zscore").alias("signal_value"),
                )
            )
            price_for_decay = prices.select(
                pl.col("date"),
                pl.lit(ticker).alias("ticker"),
                pl.col("close"),
            )

            analyzer = SignalDecayAnalyzer(max_horizon=30)
            ic_curve = analyzer.compute_ic_curve(signal_for_decay, price_for_decay)
            half_life = analyzer.compute_ic_half_life(ic_curve)
            details["signal_half_life"] = half_life
            details["ic_curve_summary"] = analyzer.decay_summary(ic_curve)
            thoughts.append(f"Signal half-life: {half_life:.1f} days")
        except Exception as exc:
            thoughts.append(f"Signal decay analysis failed: {exc}")

        # ----------------------------------------------------------
        # Step 7: Deflated Sharpe ratio
        # ----------------------------------------------------------
        try:
            returns_df = compute_returns(prices.select("date", "close"))
            sharpe = compute_sharpe(returns_df)
            r_arr = returns_df["returns"].drop_nulls().to_numpy()
            skew_val = float(scipy_stats.skew(r_arr))
            kurt_val = float(scipy_stats.kurtosis(r_arr)) + 3.0  # scipy returns excess

            validation = BacktestValidator.deflated_sharpe_ratio(
                sharpe=sharpe,
                n_trials=10,  # assume we tested ~10 parameter combos
                n_observations=len(r_arr),
                skewness=skew_val,
                kurtosis=kurt_val,
            )
            details["deflated_sharpe"] = validation.deflated_sharpe
            details["deflated_sharpe_pvalue"] = validation.p_value
            details["original_sharpe"] = validation.original_sharpe
            significant = "significant" if validation.is_valid else "not significant"
            thoughts.append(
                f"Deflated Sharpe p={validation.p_value:.4f} -- {significant}"
            )
        except Exception as exc:
            thoughts.append(f"Deflated Sharpe computation failed: {exc}")

        # ----------------------------------------------------------
        # Step 8: Determine signal
        # ----------------------------------------------------------
        if z_value < -2.0 and win_rate > 55.0:
            signal = "bullish"
            reasoning = (
                f"Z-score deeply negative ({z_value:.2f}) with "
                f"favorable historical win rate ({win_rate:.1f}%) -- mean reversion buy."
            )
        elif z_value > 2.0 and win_rate > 55.0:
            signal = "bearish"
            reasoning = (
                f"Z-score extended positive ({z_value:.2f}) with "
                f"favorable historical win rate ({win_rate:.1f}%) -- mean reversion sell."
            )
        else:
            signal = "neutral"
            reasoning = (
                f"Z-score at {z_value:.2f}, win rate at {win_rate:.1f}% -- "
                f"no strong statistical edge detected."
            )

        # ----------------------------------------------------------
        # Step 9: Compute confidence
        # ----------------------------------------------------------
        confidence = min(win_rate / 100.0, abs(z_value) / 4.0, 1.0)
        confidence = max(confidence, 0.0)

        thoughts.append(f"Final signal: {signal} (confidence: {confidence:.2f})")

        return AgentFinding(
            agent_name=self.AGENT_NAME,
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            details=details,
            thoughts=thoughts,
        )
