"""Macro-environment and regime analysis agent.

Fetches macroeconomic indicators from FRED (Federal Reserve Economic Data)
and computes volatility regimes from price data.  When FRED is unavailable
the agent uses synthetic estimates so analysis always completes.
"""

from __future__ import annotations

import logging
import math
from datetime import date as Date

import numpy as np
import polars as pl

from agents.specialists import AgentFinding

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Synthetic macro estimates (used when FRED API key is missing)
# ---------------------------------------------------------------------------

_SYNTHETIC_MACRO: dict[str, float] = {
    "fed_funds_rate": 5.33,
    "yield_spread_10y2y": -0.30,
    "vix": 18.5,
}


def _generate_synthetic_prices(ticker: str, n_days: int = 252) -> pl.DataFrame:
    """Generate synthetic daily prices for volatility computation."""
    rng = np.random.default_rng(hash(ticker) % (2**31))
    base_price = 100.0 + rng.uniform(-20, 80)
    daily_returns = rng.normal(0.0005, 0.015, size=n_days)
    prices = base_price * np.cumprod(1 + daily_returns)
    dates = pl.date_range(
        Date(2024, 1, 1), Date(2024, 1, 1), eager=True
    )
    # Build a proper date series
    date_series = pl.Series(
        "date",
        [Date(2024, 1, 1).toordinal() + i for i in range(n_days)],
    ).cast(pl.Date)
    # Actually use from ordinal via a list comprehension
    date_list = [Date.fromordinal(Date(2024, 1, 1).toordinal() + i) for i in range(n_days)]

    return pl.DataFrame({
        "date": date_list,
        "close": prices.tolist(),
    })


class TheMacroStrategist:
    """Macro environment and regime analysis.

    Combines FRED macroeconomic indicators with price-based volatility
    regime detection to produce a macro-aware trading signal.
    """

    AGENT_NAME = "TheMacroStrategist"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, ticker: str, start_date: str, end_date: str) -> AgentFinding:
        """Analyse the macro environment and volatility regime for *ticker*.

        Parameters
        ----------
        ticker:
            Stock ticker symbol.
        start_date / end_date:
            ISO date strings defining the analysis window.

        Returns
        -------
        AgentFinding
        """
        thoughts: list[str] = []
        details: dict = {}
        data_quality = 1.0

        # -----------------------------------------------------------------
        # Step 1 -- fetch macro indicators from FRED
        # -----------------------------------------------------------------
        macro = self._fetch_macro_data(thoughts)
        if macro.get("_synthetic", False):
            data_quality *= 0.6
        details["macro"] = {k: v for k, v in macro.items() if k != "_synthetic"}

        fed_funds = macro["fed_funds_rate"]
        spread = macro["yield_spread_10y2y"]
        vix = macro["vix"]

        # -----------------------------------------------------------------
        # Step 2 -- yield curve analysis
        # -----------------------------------------------------------------
        if spread < 0:
            curve_status = "Inverted"
            thoughts.append(
                f"10Y-2Y spread: {spread:.2f}%. Inverted -- historically signals recession risk."
            )
        else:
            curve_status = "Normal"
            thoughts.append(
                f"10Y-2Y spread: {spread:.2f}%. Normal -- expansionary signal."
            )
        details["yield_curve"] = curve_status
        details["yield_spread"] = spread

        # -----------------------------------------------------------------
        # Step 3 -- volatility regime detection
        # -----------------------------------------------------------------
        prices = self._fetch_prices(ticker, start_date, end_date, thoughts)
        ann_vol, regime = self._compute_regime(prices, thoughts)
        details["annualized_vol"] = round(ann_vol, 2)
        details["regime"] = regime

        # -----------------------------------------------------------------
        # Step 4 -- macro environment assessment
        # -----------------------------------------------------------------
        recession_risk = spread < 0 or vix > 25
        assessment_parts: list[str] = []
        if spread < 0:
            assessment_parts.append("inverted yield curve")
        if vix > 25:
            assessment_parts.append(f"elevated VIX ({vix:.1f})")
        if fed_funds > 4.5:
            assessment_parts.append(f"tight monetary policy (FFR {fed_funds:.2f}%)")
        if not assessment_parts:
            assessment_parts.append("benign macro conditions")

        assessment = ", ".join(assessment_parts)
        thoughts.append(f"Macro environment: {assessment}")
        details["assessment"] = assessment
        details["recession_risk"] = recession_risk
        details["fed_funds_rate"] = fed_funds
        details["vix"] = vix

        # -----------------------------------------------------------------
        # Step 5 -- regime-aware signal
        # -----------------------------------------------------------------
        signal, signal_reasoning = self._determine_signal(
            regime, recession_risk, spread, vix, ann_vol, thoughts
        )

        # -----------------------------------------------------------------
        # Step 6 -- confidence
        # -----------------------------------------------------------------
        # Higher if multiple macro signals align
        alignment_count = 0
        if spread < 0 and vix > 25:
            alignment_count += 1  # both point to caution
        if spread > 0 and vix < 20:
            alignment_count += 1  # both point to calm
        if regime in ("low_vol", "high_vol"):
            alignment_count += 1  # clear regime

        confidence = data_quality * min(0.4 + alignment_count * 0.2, 1.0)
        confidence = max(0.0, min(1.0, confidence))
        thoughts.append(f"Signal: {signal} (confidence {confidence:.2f})")

        details["ticker"] = ticker
        details["start_date"] = start_date
        details["end_date"] = end_date

        reasoning = (
            f"Macro analysis: {signal_reasoning}. "
            f"Regime: {regime}, VIX: {vix:.1f}, spread: {spread:.2f}%."
        )

        return AgentFinding(
            agent_name=self.AGENT_NAME,
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            details=details,
            thoughts=thoughts,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fetch_macro_data(thoughts: list[str]) -> dict:
        """Fetch macro indicators via YFinance (works globally, no API key needed).

        Falls back to FRED if available, then to synthetic estimates.
        """
        # Primary: YFinance (no API key needed, works everywhere)
        try:
            import yfinance as yf

            vix_data = yf.download("^VIX", period="5d", progress=False)
            tnx_data = yf.download("^TNX", period="5d", progress=False)  # 10Y yield
            twoy_data = yf.download("2YY=F", period="5d", progress=False)  # 2Y yield

            vix_val = float(vix_data["Close"].iloc[-1].iloc[0]) if not vix_data.empty else 18.5

            if not tnx_data.empty and not twoy_data.empty:
                ten_y = float(tnx_data["Close"].iloc[-1].iloc[0])
                two_y = float(twoy_data["Close"].iloc[-1].iloc[0])
                spread_val = ten_y - two_y
                fed_funds = two_y  # Approximate: short-term rates track fed funds
            else:
                # Fallback: use ^FVX (5-year) as proxy
                fed_funds = _SYNTHETIC_MACRO["fed_funds_rate"]
                spread_val = _SYNTHETIC_MACRO["yield_spread_10y2y"]

            thoughts.append(
                f"Fetched market data: VIX={vix_val:.1f}, 10Y-2Y≈{spread_val:.2f}%"
            )
            return {
                "fed_funds_rate": fed_funds,
                "yield_spread_10y2y": spread_val,
                "vix": vix_val,
                "_synthetic": False,
            }
        except Exception:
            pass

        # Secondary: FRED (requires API key)
        try:
            from data.fetchers.fred_connector import FREDConnector, FREDSeries

            fred = FREDConnector()
            fred.connect()

            ff_df = fred.fetch_series(FREDSeries.FED_FUNDS)
            spread_df = fred.fetch_series(FREDSeries.YIELD_CURVE_SPREAD)
            vix_df = fred.fetch_series("VIXCLS")

            fed_funds = float(ff_df["value"][-1])
            spread_val = float(spread_df["value"][-1])
            vix_val = float(vix_df["value"][-1])

            thoughts.append(
                f"Fetched FRED data: FFR={fed_funds:.2f}%, 10Y-2Y={spread_val:.2f}%, VIX={vix_val:.1f}"
            )
            return {
                "fed_funds_rate": fed_funds,
                "yield_spread_10y2y": spread_val,
                "vix": vix_val,
                "_synthetic": False,
            }
        except Exception as exc:
            thoughts.append(
                f"Macro data sources unavailable ({type(exc).__name__}), using estimates."
            )
            return {**_SYNTHETIC_MACRO, "_synthetic": True}

    @staticmethod
    def _fetch_prices(
        ticker: str,
        start_date: str,
        end_date: str,
        thoughts: list[str],
    ) -> pl.DataFrame:
        """Try real price data; fall back to synthetic."""
        try:
            from core.adapters import fetch_and_prepare_prices

            prices = fetch_and_prepare_prices(ticker, start_date, end_date)
            thoughts.append(f"Fetched {len(prices)} price bars for {ticker}.")
            return prices
        except Exception as exc:
            thoughts.append(
                f"Price fetch failed ({type(exc).__name__}); using synthetic prices."
            )
            return _generate_synthetic_prices(ticker)

    @staticmethod
    def _compute_regime(
        prices: pl.DataFrame, thoughts: list[str]
    ) -> tuple[float, str]:
        """Compute annualised volatility and classify the regime."""
        close_col = "close" if "close" in prices.columns else "Close"
        if close_col not in prices.columns:
            thoughts.append("No close column found; defaulting to moderate-vol regime.")
            return 20.0, "moderate_vol"

        closes = prices[close_col].to_numpy().astype(float)
        if len(closes) < 10:
            thoughts.append("Insufficient price data; defaulting to moderate-vol regime.")
            return 20.0, "moderate_vol"

        # Rolling 60-day returns volatility (or all available if < 60)
        window = min(60, len(closes) - 1)
        log_returns = np.diff(np.log(closes))
        recent_returns = log_returns[-window:]
        daily_vol = float(np.std(recent_returns))
        ann_vol = daily_vol * math.sqrt(252) * 100  # percentage

        if ann_vol < 15:
            regime = "low_vol"
        elif ann_vol > 25:
            regime = "high_vol"
        else:
            regime = "moderate_vol"

        thoughts.append(
            f"Current regime: {regime}. Annualized vol: {ann_vol:.1f}%"
        )
        return ann_vol, regime

    @staticmethod
    def _determine_signal(
        regime: str,
        recession_risk: bool,
        spread: float,
        vix: float,
        ann_vol: float,
        thoughts: list[str],
    ) -> tuple[str, str]:
        """Produce a regime-aware signal and short reasoning string."""
        if recession_risk and regime == "high_vol":
            signal = "bearish"
            reason = "recession indicators + high-vol regime suggest caution"
        elif recession_risk and regime != "high_vol":
            signal = "neutral"
            reason = "mixed signals -- recession risk but vol contained"
        elif not recession_risk and regime == "low_vol":
            signal = "bullish"
            reason = "benign macro + low-vol regime favours momentum"
        elif not recession_risk and regime == "high_vol":
            signal = "neutral"
            reason = "no recession risk but elevated vol warrants caution"
        else:
            # moderate vol, no recession risk
            signal = "bullish" if spread > 0.5 and vix < 20 else "neutral"
            reason = (
                "moderate vol with positive spread"
                if signal == "bullish"
                else "moderate vol, macro signals mixed"
            )

        return signal, reason
