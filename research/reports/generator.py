"""Automated research report generator.

Produces self-contained HTML research reports from analysis results
(sentiment, factor exposures, backtest metrics, risk data, signals).
"""

from __future__ import annotations

import html as html_mod
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class ResearchReport:
    """A completed research report ready for display or persistence."""

    title: str
    ticker: str
    date: str
    summary: str
    sections: list[dict] = field(default_factory=list)  # [{title, content}]
    signals: list[dict] = field(default_factory=list)  # [{date, direction, confidence, rationale}]
    html: str = ""


# ---------------------------------------------------------------------------
# Theme colours (Avashi dark design system)
# ---------------------------------------------------------------------------

_COLORS = {
    "bg": "#111827",
    "card_bg": "#1f2937",
    "text": "#f9fafb",
    "muted": "#9ca3af",
    "violet": "#8b5cf6",
    "green": "#22c55e",
    "red": "#ef4444",
    "border": "#374151",
}

# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class ResearchReportGenerator:
    """Generate HTML research reports from analysis results."""

    def __init__(self, template_style: str = "dark") -> None:
        self.template_style = template_style

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, ticker: str, analysis: dict) -> ResearchReport:
        """Build a :class:`ResearchReport` from heterogeneous analysis data.

        Parameters
        ----------
        ticker:
            Stock ticker symbol.
        analysis:
            Dictionary that may contain any of the following keys:
            ``sentiment``, ``factors``, ``backtest``, ``risk``, ``signals``,
            ``fundamentals``.
        """
        report_date = str(date.today())
        sections: list[dict] = []
        signal_dicts: list[dict] = []

        # -- Executive Summary (always present) --
        summary_parts: list[str] = []
        summary_parts.append(f"Research report for {ticker} generated on {report_date}.")

        # -- Sentiment Analysis --
        sentiment = analysis.get("sentiment")
        if sentiment is not None:
            sect_content = self._build_sentiment_section(sentiment)
            sections.append({"title": "Sentiment Analysis", "content": sect_content})
            label = sentiment.get("label", "N/A") if isinstance(sentiment, dict) else getattr(sentiment, "label", "N/A")
            summary_parts.append(f"Sentiment: {label}.")

        # -- Factor Exposure --
        factors = analysis.get("factors")
        if factors is not None:
            sect_content = self._build_factors_section(factors)
            sections.append({"title": "Factor Exposure", "content": sect_content})
            summary_parts.append("Factor exposure analysis included.")

        # -- Backtest Results --
        backtest = analysis.get("backtest")
        if backtest is not None:
            sect_content = self._build_backtest_section(backtest)
            sections.append({"title": "Backtest Results", "content": sect_content})
            summary_parts.append("Backtest results included.")

        # -- Risk Assessment --
        risk = analysis.get("risk")
        if risk is not None:
            sect_content = self._build_risk_section(risk)
            sections.append({"title": "Risk Assessment", "content": sect_content})
            summary_parts.append("Risk assessment included.")

        # -- Trading Signals --
        signals = analysis.get("signals")
        if signals is not None:
            sect_content, signal_dicts = self._build_signals_section(signals)
            sections.append({"title": "Trading Signals", "content": sect_content})
            summary_parts.append(f"{len(signal_dicts)} trading signal(s) generated.")

        summary = " ".join(summary_parts)

        report = ResearchReport(
            title=f"{ticker} Research Report",
            ticker=ticker,
            date=report_date,
            summary=summary,
            sections=sections,
            signals=signal_dicts,
        )

        report.html = self._build_html(report)
        return report

    def save(self, report: ResearchReport, path: Path | str) -> None:
        """Persist the report HTML to *path*."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.html, encoding="utf-8")
        logger.info("Report saved to %s", path)

    # ------------------------------------------------------------------
    # HTML builder
    # ------------------------------------------------------------------

    def _build_html(self, report: ResearchReport) -> str:
        """Return a self-contained HTML document with embedded styles."""
        section_cards = "\n".join(
            self._card_html(s["title"], s["content"]) for s in report.sections
        )

        return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{_esc(report.title)}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: {_COLORS['bg']};
    color: {_COLORS['text']};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 2rem;
    line-height: 1.6;
  }}
  h1 {{
    color: {_COLORS['violet']};
    font-size: 1.75rem;
    margin-bottom: 0.25rem;
  }}
  .meta {{
    color: {_COLORS['muted']};
    font-size: 0.85rem;
    margin-bottom: 1.5rem;
  }}
  .summary {{
    background: {_COLORS['card_bg']};
    border-left: 4px solid {_COLORS['violet']};
    padding: 1rem 1.25rem;
    border-radius: 0.5rem;
    margin-bottom: 1.5rem;
  }}
  .card {{
    background: {_COLORS['card_bg']};
    border: 1px solid {_COLORS['border']};
    border-radius: 0.5rem;
    margin-bottom: 1.25rem;
    overflow: hidden;
  }}
  .card-header {{
    background: {_COLORS['border']};
    padding: 0.75rem 1.25rem;
    font-weight: 600;
    color: {_COLORS['violet']};
  }}
  .card-body {{
    padding: 1rem 1.25rem;
    white-space: pre-wrap;
  }}
  .bullish {{ color: {_COLORS['green']}; }}
  .bearish {{ color: {_COLORS['red']}; }}
  .neutral {{ color: {_COLORS['muted']}; }}
</style>
</head>
<body>
<h1>{_esc(report.title)}</h1>
<div class="meta">{_esc(report.ticker)} &mdash; {_esc(report.date)}</div>
<div class="summary">{_esc(report.summary)}</div>
{section_cards}
</body>
</html>"""

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_sentiment_section(self, sentiment: object) -> str:
        """Format sentiment data (dict or SentimentResult)."""
        if isinstance(sentiment, dict):
            score = sentiment.get("score", "N/A")
            magnitude = sentiment.get("magnitude", "N/A")
            label = sentiment.get("label", "N/A")
            phrases = sentiment.get("key_phrases", [])
        else:
            score = getattr(sentiment, "score", "N/A")
            magnitude = getattr(sentiment, "magnitude", "N/A")
            label = getattr(sentiment, "label", "N/A")
            phrases = getattr(sentiment, "key_phrases", [])

        lines = [
            f"Score: {score}",
            f"Magnitude: {magnitude}",
            f"Label: {label}",
        ]
        if phrases:
            lines.append("")
            lines.append("Key Phrases:")
            for p in phrases:
                lines.append(f"  - {p}")
        return "\n".join(lines)

    def _build_factors_section(self, factors: object) -> str:
        if isinstance(factors, dict):
            return "\n".join(f"{k}: {v}" for k, v in factors.items())
        if isinstance(factors, pl.DataFrame):
            return str(factors)
        return str(factors)

    def _build_backtest_section(self, backtest: object) -> str:
        if isinstance(backtest, dict):
            return "\n".join(f"{k}: {v}" for k, v in backtest.items())
        return str(backtest)

    def _build_risk_section(self, risk: object) -> str:
        if isinstance(risk, dict):
            return "\n".join(f"{k}: {v}" for k, v in risk.items())
        return str(risk)

    def _build_signals_section(self, signals: list) -> tuple[str, list[dict]]:
        signal_dicts: list[dict] = []
        lines: list[str] = []
        for sig in signals:
            if isinstance(sig, dict):
                d = sig
            else:
                d = {
                    "date": getattr(sig, "date", ""),
                    "direction": getattr(sig, "direction", 0),
                    "confidence": getattr(sig, "confidence", 0),
                    "rationale": (getattr(sig, "metadata", {}) or {}).get("label", ""),
                }
            signal_dicts.append(d)
            direction_str = "LONG" if d.get("direction", 0) > 0 else "SHORT"
            lines.append(
                f"{d.get('date', 'N/A')}  {direction_str}  "
                f"confidence={d.get('confidence', 'N/A')}"
            )
        return "\n".join(lines) if lines else "No signals.", signal_dicts

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _card_html(title: str, content: str) -> str:
        return (
            f'<div class="card">'
            f'<div class="card-header">{_esc(title)}</div>'
            f'<div class="card-body">{_esc(content)}</div>'
            f"</div>"
        )


def _esc(text: str) -> str:
    """HTML-escape arbitrary text."""
    return html_mod.escape(str(text))
