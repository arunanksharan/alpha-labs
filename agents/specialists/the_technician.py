"""The Technician -- chart pattern and technical indicator specialist agent.

Computes RSI, MACD, Bollinger Bands, and ATR, then aggregates a directional
score to produce a bullish/bearish/neutral signal.
"""

from __future__ import annotations

import polars as pl

from agents.specialists import AgentFinding
from core.adapters import fetch_and_prepare_prices
from features.technical.indicators import (
    ATRFeature,
    BollingerBandsFeature,
    MACDFeature,
    RSIFeature,
)


class TheTechnician:
    """Chart pattern and technical indicator analysis."""

    AGENT_NAME: str = "the_technician"

    def analyze(self, ticker: str, start_date: str, end_date: str) -> AgentFinding:
        """Run full technical analysis on *ticker* over the given date range.

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
        score: int = 0
        n_indicators: int = 0

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

        # Verify required columns are present
        required_cols = {"date", "open", "high", "low", "close", "volume"}
        missing = required_cols - set(prices.columns)
        if missing:
            thoughts.append(f"Warning: price DataFrame missing columns: {missing}")

        # ----------------------------------------------------------
        # Step 2: RSI
        # ----------------------------------------------------------
        rsi_value: float | None = None
        try:
            prices_with_rsi = RSIFeature(period=14).compute(prices)
            rsi_series = prices_with_rsi["rsi"].drop_nulls()
            if len(rsi_series) > 0:
                rsi_value = float(rsi_series.to_list()[-1])
                details["rsi"] = rsi_value
                thoughts.append(f"RSI(14) = {rsi_value:.2f}")

                n_indicators += 1
                if rsi_value < 30:
                    score += 1
                    thoughts.append("RSI < 30 -- oversold (+1 bullish)")
                elif rsi_value > 70:
                    score -= 1
                    thoughts.append("RSI > 70 -- overbought (-1 bearish)")
                else:
                    thoughts.append("RSI in neutral zone.")
        except Exception as exc:
            thoughts.append(f"RSI computation failed: {exc}")

        # ----------------------------------------------------------
        # Step 3: MACD
        # ----------------------------------------------------------
        try:
            prices_with_macd = MACDFeature().compute(prices)
            macd_series = prices_with_macd["macd"].drop_nulls()
            signal_series = prices_with_macd["macd_signal"].drop_nulls()
            hist_series = prices_with_macd["macd_histogram"].drop_nulls()

            if len(macd_series) > 0 and len(signal_series) > 0 and len(hist_series) > 0:
                macd_val = float(macd_series.to_list()[-1])
                signal_val = float(signal_series.to_list()[-1])
                hist_val = float(hist_series.to_list()[-1])
                details["macd"] = macd_val
                details["macd_signal"] = signal_val
                details["macd_histogram"] = hist_val
                thoughts.append(
                    f"MACD: {macd_val:.4f}, Signal: {signal_val:.4f}, "
                    f"Histogram: {hist_val:.4f}"
                )

                n_indicators += 1
                # Check for crossover: histogram just turned positive = bullish
                hist_list = hist_series.to_list()
                if len(hist_list) >= 2:
                    prev_hist = float(hist_list[-2])
                    if prev_hist <= 0 and hist_val > 0:
                        score += 1
                        thoughts.append("MACD bullish crossover (+1 bullish)")
                    elif prev_hist >= 0 and hist_val < 0:
                        score -= 1
                        thoughts.append("MACD bearish crossover (-1 bearish)")
                    elif hist_val > 0:
                        thoughts.append("MACD histogram positive -- momentum up.")
                    else:
                        thoughts.append("MACD histogram negative -- momentum down.")
        except Exception as exc:
            thoughts.append(f"MACD computation failed: {exc}")

        # ----------------------------------------------------------
        # Step 4: Bollinger Bands
        # ----------------------------------------------------------
        try:
            prices_with_bb = BollingerBandsFeature().compute(prices)
            pct_b_series = prices_with_bb["bb_pct_b"].drop_nulls()

            if len(pct_b_series) > 0:
                pct_b = float(pct_b_series.to_list()[-1])
                details["bb_pct_b"] = pct_b
                thoughts.append(f"Price at {pct_b * 100:.1f}% of Bollinger Band")

                n_indicators += 1
                if pct_b < 0.0:
                    score += 1
                    thoughts.append("Below lower Bollinger Band -- oversold (+1 bullish)")
                elif pct_b > 1.0:
                    score -= 1
                    thoughts.append("Above upper Bollinger Band -- overbought (-1 bearish)")
                else:
                    thoughts.append("Within Bollinger Bands -- no extreme reading.")

                # Also capture bandwidth
                bw_series = prices_with_bb["bb_bandwidth"].drop_nulls()
                if len(bw_series) > 0:
                    details["bb_bandwidth"] = float(bw_series.to_list()[-1])
        except Exception as exc:
            thoughts.append(f"Bollinger Bands computation failed: {exc}")

        # ----------------------------------------------------------
        # Step 5: ATR
        # ----------------------------------------------------------
        try:
            prices_with_atr = ATRFeature().compute(prices)
            atr_series = prices_with_atr["atr"].drop_nulls()

            if len(atr_series) > 0:
                atr_val = float(atr_series.to_list()[-1])
                last_close = float(prices["close"].to_list()[-1])
                atr_pct = (atr_val / last_close) * 100.0 if last_close != 0 else 0.0
                details["atr"] = atr_val
                details["atr_pct"] = atr_pct
                thoughts.append(f"ATR = {atr_val:.2f} ({atr_pct:.2f}% of price)")
        except Exception as exc:
            thoughts.append(f"ATR computation failed: {exc}")

        # ----------------------------------------------------------
        # Step 6 & 7: Aggregate score and determine signal
        # ----------------------------------------------------------
        details["technical_score"] = score
        details["n_indicators"] = n_indicators

        if score > 0:
            signal = "bullish"
        elif score < 0:
            signal = "bearish"
        else:
            signal = "neutral"

        # ----------------------------------------------------------
        # Step 8: Confidence based on indicator agreement
        # ----------------------------------------------------------
        if n_indicators > 0:
            # confidence = fraction of indicators that agree with the signal
            confidence = min(abs(score) / n_indicators, 1.0)
        else:
            confidence = 0.0

        thoughts.append(
            f"Technical score: {score} across {n_indicators} indicators "
            f"-> {signal} (confidence: {confidence:.2f})"
        )

        # Build reasoning summary
        parts: list[str] = []
        if rsi_value is not None:
            parts.append(f"RSI={rsi_value:.1f}")
        if "macd_histogram" in details:
            parts.append(f"MACD hist={details['macd_histogram']:.4f}")
        if "bb_pct_b" in details:
            parts.append(f"%B={details['bb_pct_b']:.2f}")
        reasoning = f"Technical consensus {signal}: {', '.join(parts)}."

        return AgentFinding(
            agent_name=self.AGENT_NAME,
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            details=details,
            thoughts=thoughts,
        )
