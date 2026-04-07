"""The Contrarian -- crowded-trade and volatility-anomaly specialist agent.

Looks for crowded trades, vol anomalies, and tail risks. Fades the crowd
when positioning is extreme and volatility signals are misaligned.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats as scipy_stats

from agents.specialists import AgentFinding
from core.adapters import fetch_and_prepare_prices
from analytics.returns import compute_returns, compute_sharpe, compute_volatility
from features.technical.momentum import MomentumFeature
from risk.var.monte_carlo import MonteCarloVaR


class TheContrarian:
    """Looks for crowded trades, vol anomalies, and tail risks."""

    AGENT_NAME: str = "the_contrarian"

    def analyze(self, ticker: str, start_date: str, end_date: str) -> AgentFinding:
        """Run contrarian analysis on *ticker* over the given date range.

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
        # Step 2: Compute returns
        # ----------------------------------------------------------
        returns_df: pl.DataFrame | None = None
        try:
            returns_df = compute_returns(prices.select("date", "close"))
            thoughts.append(f"Computed {len(returns_df)} daily returns.")
        except Exception as exc:
            thoughts.append(f"Returns computation failed: {exc}")

        # ----------------------------------------------------------
        # Step 3: Check if trade is "crowded" via momentum factor
        # ----------------------------------------------------------
        crowding: str = "neutral"
        momentum_value: float | None = None
        try:
            prices_with_mom = MomentumFeature().compute(prices)
            mom_series = prices_with_mom["momentum"].drop_nulls()
            if len(mom_series) > 0:
                momentum_value = float(mom_series.to_list()[-1])
                details["momentum"] = momentum_value

                # Use simple heuristic: if momentum is in top/bottom decile
                # of its own distribution, consider it crowded
                mom_arr = mom_series.to_numpy()
                pct_rank = float(np.mean(mom_arr <= momentum_value))
                details["momentum_percentile"] = pct_rank

                if pct_rank >= 0.90:
                    crowding = "crowded_long"
                    thoughts.append(
                        f"Momentum at {momentum_value:.4f} "
                        f"(top {(1 - pct_rank) * 100:.0f}% percentile) "
                        f"-- crowded long."
                    )
                elif pct_rank <= 0.10:
                    crowding = "crowded_short"
                    thoughts.append(
                        f"Momentum at {momentum_value:.4f} "
                        f"(bottom {pct_rank * 100:.0f}% percentile) "
                        f"-- crowded short."
                    )
                else:
                    thoughts.append(
                        f"Momentum at {momentum_value:.4f} "
                        f"(percentile: {pct_rank * 100:.0f}%) -- not crowded."
                    )
            else:
                thoughts.append("Momentum: insufficient data for lookback window.")
        except Exception as exc:
            thoughts.append(f"Crowding analysis failed: {exc}")

        details["crowding"] = crowding

        # ----------------------------------------------------------
        # Step 4: Realized vol vs GARCH forecast
        # ----------------------------------------------------------
        rv_annualized: float | None = None
        garch_vol: float | None = None
        vol_anomaly: bool = False

        if returns_df is not None and len(returns_df) >= 21:
            try:
                vol_df = compute_volatility(returns_df, window=21, annualize=True)
                vol_series = vol_df["volatility"].drop_nulls()
                if len(vol_series) > 0:
                    rv_annualized = float(vol_series.to_list()[-1]) * 100.0
                    details["realized_vol_pct"] = rv_annualized
            except Exception as exc:
                thoughts.append(f"Realized vol computation failed: {exc}")

            # GARCH forecast (optional -- requires arch package)
            try:
                from analytics.options import garch_forecast

                ret_series = returns_df["returns"].drop_nulls()
                garch_df = garch_forecast(ret_series, p=1, q=1, horizon=10)
                if len(garch_df) > 0:
                    # garch_forecast returns annualized percentage vol
                    garch_vol = float(garch_df["forecast_vol"].to_list()[0])
                    details["garch_forecast_vol_pct"] = garch_vol
            except Exception as exc:
                thoughts.append(f"GARCH forecast failed: {exc}")

            if rv_annualized is not None and garch_vol is not None:
                thoughts.append(
                    f"Realized vol: {rv_annualized:.1f}%, GARCH forecast: {garch_vol:.1f}%"
                )
                # Vol anomaly: realized and forecast diverge significantly
                if rv_annualized > 0:
                    vol_ratio = garch_vol / rv_annualized
                    details["vol_ratio"] = vol_ratio
                    if vol_ratio > 1.3 or vol_ratio < 0.7:
                        vol_anomaly = True
                        thoughts.append(
                            f"Vol anomaly detected: ratio = {vol_ratio:.2f}"
                        )
            elif rv_annualized is not None:
                thoughts.append(f"Realized vol: {rv_annualized:.1f}% (GARCH unavailable)")
        else:
            thoughts.append("Insufficient data for volatility analysis.")

        details["vol_anomaly"] = vol_anomaly

        # ----------------------------------------------------------
        # Step 5: Monte Carlo stress test
        # ----------------------------------------------------------
        stress_result: dict[str, float] | None = None
        if returns_df is not None:
            try:
                ret_series = returns_df["returns"].drop_nulls()
                mc = MonteCarloVaR(n_simulations=10_000, seed=42)
                stress_result = mc.stress_test(ret_series)
                details["stress_test"] = stress_result
                thoughts.append(
                    f"Stress test: normal VaR {stress_result['normal_var']:.4f}, "
                    f"stressed VaR {stress_result['stressed_var']:.4f}"
                )
            except Exception as exc:
                thoughts.append(f"Monte Carlo stress test failed: {exc}")

        # ----------------------------------------------------------
        # Step 6: Asymmetric payoff check
        # ----------------------------------------------------------
        if returns_df is not None:
            try:
                r_arr = returns_df["returns"].drop_nulls().to_numpy()
                skew_val = float(scipy_stats.skew(r_arr))
                details["return_skewness"] = skew_val

                upside = r_arr[r_arr > 0]
                downside = r_arr[r_arr < 0]
                if len(upside) > 0 and len(downside) > 0:
                    avg_up = float(np.mean(upside))
                    avg_down = float(np.mean(np.abs(downside)))
                    payoff_ratio = avg_up / avg_down if avg_down != 0 else float("inf")
                    details["payoff_ratio"] = payoff_ratio
                    if payoff_ratio > 1.2:
                        thoughts.append(
                            f"Asymmetric payoff: upside/downside ratio = {payoff_ratio:.2f} "
                            f"-- limited downside relative to upside."
                        )
                    elif payoff_ratio < 0.8:
                        thoughts.append(
                            f"Asymmetric payoff: upside/downside ratio = {payoff_ratio:.2f} "
                            f"-- limited upside relative to downside."
                        )
                    else:
                        thoughts.append(
                            f"Payoff ratio: {payoff_ratio:.2f} -- roughly symmetric."
                        )
            except Exception as exc:
                thoughts.append(f"Asymmetry check failed: {exc}")

        # ----------------------------------------------------------
        # Step 7: Determine signal (contrarian logic)
        # ----------------------------------------------------------
        #   - If crowded long AND overextended -> bearish (fade the crowd)
        #   - If crowded short AND fundamentals ok -> bullish (contrarian buy)
        #   - Otherwise neutral
        overextended = vol_anomaly or (
            momentum_value is not None and abs(momentum_value) > 0.5
        )

        if crowding == "crowded_long" and overextended:
            signal = "bearish"
            reasoning = (
                "Crowded long with overextended momentum/vol anomaly -- "
                "contrarian fade recommended."
            )
        elif crowding == "crowded_short" and overextended:
            signal = "bullish"
            reasoning = (
                "Crowded short with extreme pessimism -- "
                "contrarian buy opportunity."
            )
        else:
            signal = "neutral"
            reasoning = (
                f"Crowding: {crowding}, vol anomaly: {vol_anomaly} -- "
                f"no strong contrarian signal."
            )

        # ----------------------------------------------------------
        # Step 8: Confidence based on extremity
        # ----------------------------------------------------------
        confidence_factors: list[float] = []

        # Crowding strength
        if momentum_value is not None:
            mom_pct = details.get("momentum_percentile", 0.5)
            crowding_strength = abs(mom_pct - 0.5) * 2.0  # 0 to 1
            confidence_factors.append(crowding_strength)

        # Vol anomaly strength
        if "vol_ratio" in details:
            vol_divergence = abs(details["vol_ratio"] - 1.0)
            confidence_factors.append(min(vol_divergence, 1.0))

        # Stress ratio
        if stress_result is not None:
            stress_severity = min(abs(stress_result.get("stress_ratio", 1.0) - 1.0), 1.0)
            confidence_factors.append(stress_severity)

        if confidence_factors:
            confidence = float(np.mean(confidence_factors))
        else:
            confidence = 0.0

        confidence = max(0.0, min(confidence, 1.0))

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
