"""Fundamental analysis agent -- SEC filings and intrinsic-value estimation.

Attempts to pull real XBRL data from SEC EDGAR.  When the network call
fails (no connectivity, rate-limited, etc.) the agent falls back to
synthetic / price-based estimates so analysis always completes.
"""

from __future__ import annotations

import logging
import math

from agents.specialists import AgentFinding

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic fallback data keyed by ticker (top US large-caps)
# ---------------------------------------------------------------------------

_SYNTHETIC_FUNDAMENTALS: dict[str, dict] = {
    "AAPL": {
        "revenue": 383_3e6,
        "net_income": 97_0e6,
        "total_assets": 352_6e6,
        "total_equity": 62_1e6,
        "total_liabilities": 290_4e6,
        "shares_outstanding": 15_4e9 / 1000,
        "current_price": 170.0,
        "revenue_growth": 0.02,
    },
    "MSFT": {
        "revenue": 227_6e6,
        "net_income": 82_5e6,
        "total_assets": 411_9e6,
        "total_equity": 206_2e6,
        "total_liabilities": 205_7e6,
        "shares_outstanding": 7_43e9 / 1000,
        "current_price": 420.0,
        "revenue_growth": 0.13,
    },
}

_DEFAULT_FUNDAMENTALS: dict = {
    "revenue": 50_0e6,
    "net_income": 5_0e6,
    "total_assets": 100_0e6,
    "total_equity": 40_0e6,
    "total_liabilities": 60_0e6,
    "shares_outstanding": 1_0e9 / 1000,
    "current_price": 100.0,
    "revenue_growth": 0.05,
}


def _extract_latest_value(facts: dict, concept: str) -> float | None:
    """Pull the most recent annual USD value for *concept* from EDGAR facts."""
    try:
        gaap = facts.get("facts", {}).get("us-gaap", {})
        entry = gaap.get(concept, {})
        units = entry.get("units", {})
        usd_vals = units.get("USD") or units.get("USD/shares") or []
        # Keep only 10-K (annual) filings and pick the latest
        annuals = [v for v in usd_vals if v.get("form") == "10-K"]
        if not annuals:
            annuals = usd_vals
        if not annuals:
            return None
        annuals.sort(key=lambda v: v.get("end", ""), reverse=True)
        return float(annuals[0]["val"])
    except Exception:
        return None


class TheFundamentalist:
    """Reads SEC filings, computes intrinsic value.

    Falls back to synthetic data when EDGAR is unavailable so the agent
    always returns a valid :class:`AgentFinding`.
    """

    AGENT_NAME = "TheFundamentalist"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, ticker: str, start_date: str, end_date: str) -> AgentFinding:
        """Run fundamental analysis for *ticker*.

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
        data_quality = 1.0  # 1.0 = real EDGAR data, 0.5 = synthetic

        # Step 1 -- try to fetch from EDGAR
        fundamentals: dict | None = None
        try:
            from data.fetchers.edgar_connector import EdgarConnector

            connector = EdgarConnector()
            connector.connect()
            facts = connector.fetch_company_facts(ticker)
            fundamentals = self._extract_fundamentals(facts, thoughts)
            thoughts.append("Successfully retrieved EDGAR XBRL data.")
        except Exception as exc:
            thoughts.append(
                f"EDGAR fetch failed ({type(exc).__name__}); falling back to estimates."
            )
            data_quality = 0.5

        if fundamentals is None:
            fundamentals = _SYNTHETIC_FUNDAMENTALS.get(
                ticker.upper(), _DEFAULT_FUNDAMENTALS
            ).copy()
            thoughts.append("Using synthetic / estimated fundamental data.")

        # Step 2 -- key metrics
        revenue = fundamentals["revenue"]
        net_income = fundamentals["net_income"]
        total_assets = fundamentals["total_assets"]
        total_equity = fundamentals["total_equity"]
        total_liabilities = fundamentals["total_liabilities"]

        thoughts.append(
            f"Revenue: ${revenue / 1e9:.2f}B, Net Income: ${net_income / 1e9:.2f}B"
        )
        details["revenue"] = revenue
        details["net_income"] = net_income
        details["total_assets"] = total_assets
        details["total_equity"] = total_equity

        # Step 3 -- ratios
        roe = (net_income / total_equity * 100) if total_equity != 0 else 0.0
        debt_equity = (
            total_liabilities / total_equity if total_equity != 0 else float("inf")
        )
        net_margin = (net_income / revenue * 100) if revenue != 0 else 0.0

        thoughts.append(
            f"ROE: {roe:.1f}%, Debt/Equity: {debt_equity:.2f}, Net Margin: {net_margin:.1f}%"
        )
        details["roe"] = round(roe, 2)
        details["debt_equity"] = round(debt_equity, 2)
        details["net_margin"] = round(net_margin, 2)

        # Step 4 -- simplified DCF
        revenue_growth = fundamentals.get("revenue_growth", 0.05)
        growth_rate = min(revenue_growth, 0.15)
        terminal_growth = 0.025
        discount_rate = 0.10
        current_price = fundamentals.get("current_price", 100.0)
        shares = fundamentals.get("shares_outstanding", 1e6)

        # Project free cash flow (approximate as net_income * 0.8)
        fcf = net_income * 0.8
        dcf_value = 0.0
        for year in range(1, 11):
            projected_fcf = fcf * ((1 + growth_rate) ** year)
            dcf_value += projected_fcf / ((1 + discount_rate) ** year)

        # Terminal value
        terminal_fcf = fcf * ((1 + growth_rate) ** 10) * (1 + terminal_growth)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        dcf_value += terminal_value / ((1 + discount_rate) ** 10)

        intrinsic_per_share = dcf_value / shares if shares > 0 else 0.0
        margin_of_safety = (
            (intrinsic_per_share - current_price) / current_price * 100
            if current_price > 0
            else 0.0
        )

        thoughts.append(
            f"DCF intrinsic value: ${intrinsic_per_share:.2f}. "
            f"Current price: ${current_price:.2f}. "
            f"Margin of safety: {margin_of_safety:.1f}%"
        )
        details["intrinsic_value"] = round(intrinsic_per_share, 2)
        details["current_price"] = current_price
        details["margin_of_safety"] = round(margin_of_safety, 2)
        details["growth_rate"] = round(growth_rate * 100, 2)
        details["discount_rate"] = discount_rate
        details["dcf_total"] = round(dcf_value, 2)

        # Step 5 -- signal
        if margin_of_safety > 10:
            signal = "bullish"
        elif margin_of_safety < -10:
            signal = "bearish"
        else:
            signal = "neutral"

        # Step 6 -- confidence
        mos_factor = min(abs(margin_of_safety) / 50.0, 1.0)
        confidence = data_quality * mos_factor
        confidence = max(0.0, min(1.0, confidence))
        thoughts.append(f"Signal: {signal} (confidence {confidence:.2f})")

        details["data_quality"] = data_quality
        details["ticker"] = ticker
        details["start_date"] = start_date
        details["end_date"] = end_date

        reasoning = (
            f"Fundamental DCF analysis yields intrinsic value ${intrinsic_per_share:.2f} "
            f"vs price ${current_price:.2f} ({signal}, margin of safety {margin_of_safety:.1f}%)."
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
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_fundamentals(facts: dict, thoughts: list[str]) -> dict | None:
        """Try to build a fundamentals dict from EDGAR company facts."""
        revenue = _extract_latest_value(facts, "Revenues") or _extract_latest_value(
            facts, "RevenueFromContractWithCustomerExcludingAssessedTax"
        )
        net_income = _extract_latest_value(facts, "NetIncomeLoss")
        total_assets = _extract_latest_value(facts, "Assets")
        total_equity = _extract_latest_value(facts, "StockholdersEquity")
        total_liabilities = _extract_latest_value(facts, "Liabilities")

        if any(v is None for v in [revenue, net_income, total_assets, total_equity]):
            thoughts.append("EDGAR data incomplete; some XBRL concepts missing.")
            return None

        # Estimate revenue growth from the two most recent annual revenues
        revenue_growth = 0.05  # default
        try:
            gaap = facts.get("facts", {}).get("us-gaap", {})
            rev_entry = gaap.get("Revenues", gaap.get(
                "RevenueFromContractWithCustomerExcludingAssessedTax", {}
            ))
            usd_vals = rev_entry.get("units", {}).get("USD", [])
            annuals = sorted(
                [v for v in usd_vals if v.get("form") == "10-K"],
                key=lambda v: v.get("end", ""),
                reverse=True,
            )
            if len(annuals) >= 2:
                recent = float(annuals[0]["val"])
                prior = float(annuals[1]["val"])
                if prior > 0:
                    revenue_growth = (recent - prior) / prior
        except Exception:
            pass

        return {
            "revenue": revenue,
            "net_income": net_income,
            "total_assets": total_assets,
            "total_equity": total_equity,
            "total_liabilities": total_liabilities or 0.0,
            "shares_outstanding": 1e6,  # placeholder
            "current_price": 100.0,  # placeholder
            "revenue_growth": revenue_growth,
        }
