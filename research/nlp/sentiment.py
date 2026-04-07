"""Financial sentiment analysis for earnings calls and filings.

Rule-based sentiment scoring using Loughran-McDonald inspired word lists.
No ML model required -- works offline without API keys.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

import numpy as np
import polars as pl

from core.strategies import Signal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Loughran-McDonald inspired financial word lists
# ---------------------------------------------------------------------------

POSITIVE_WORDS: frozenset[str] = frozenset({
    "profit", "growth", "exceeded", "outperformed", "improved", "strong",
    "robust", "gain", "gains", "surpassed", "favorable", "optimistic",
    "upgrade", "upgraded", "upside", "positive", "strength", "record",
    "innovation", "efficient", "efficiency", "achievement", "benefit",
    "beneficial", "opportunity", "opportunities", "momentum", "recovery",
    "recovered", "resilient", "resilience", "expansion", "expanded",
    "accelerated", "acceleration", "breakthrough", "dividend", "dividends",
    "rewarding", "profitability", "profitable", "superior", "outpaced",
    "exceeded", "surpass", "enhance", "enhanced", "advancement", "progress",
    "progressed", "thriving", "successful", "success", "leadership",
    "innovative",
})

NEGATIVE_WORDS: frozenset[str] = frozenset({
    "loss", "losses", "decline", "declined", "risk", "risks", "impairment",
    "weakness", "default", "defaults", "litigation", "adverse", "adversely",
    "deteriorated", "deterioration", "downturn", "downgrade", "downgraded",
    "negative", "deficit", "deficits", "restructuring", "closure", "closures",
    "layoff", "layoffs", "writedown", "writeoff", "penalty", "penalties",
    "fraud", "violation", "violations", "bankruptcy", "insolvent", "insolvency",
    "foreclosure", "delinquent", "delinquency", "underperformed", "shortfall",
    "disappointing", "disappointed", "recession", "contraction", "impaired",
    "terminated", "termination", "severance", "volatile", "volatility",
    "exposure", "threat", "threats", "challenge", "challenged", "challenging",
    "headwind", "headwinds",
})

UNCERTAINTY_WORDS: frozenset[str] = frozenset({
    "may", "could", "uncertain", "uncertainty", "approximate", "approximately",
    "contingent", "contingency", "possible", "possibly", "probable", "probably",
    "unpredictable", "unforeseeable", "unclear", "unknown", "tentative",
    "preliminary", "estimated", "assumes", "assumption", "assumptions",
    "speculative", "depends", "dependent", "conditional", "indefinite",
    "variable", "fluctuate", "fluctuation",
})

LITIGIOUS_WORDS: frozenset[str] = frozenset({
    "lawsuit", "lawsuits", "arbitration", "plaintiff", "plaintiffs",
    "defendant", "defendants", "liability", "liabilities", "litigation",
    "settlement", "settlements", "indemnify", "indemnification", "allegation",
    "allegations", "injunction", "tribunal", "regulatory", "subpoena",
    "claimant",
})

# ---------------------------------------------------------------------------
# Tokenisation helper
# ---------------------------------------------------------------------------

_TOKEN_PATTERN = re.compile(r"[a-z]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase tokenisation splitting on non-alpha characters."""
    return _TOKEN_PATTERN.findall(text.lower())


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class SentimentResult:
    """Result of a financial sentiment analysis."""

    score: float  # -1.0 (bearish) to 1.0 (bullish)
    magnitude: float  # 0.0 to 1.0 (strength of sentiment)
    label: str  # "bullish", "bearish", "neutral"
    key_phrases: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class FinancialSentimentAnalyzer:
    """Rule-based financial sentiment analysis.

    Uses financial-domain word lists (Loughran-McDonald style).
    No ML model required -- works offline without API keys.
    """

    def __init__(self) -> None:
        self.positive_words = POSITIVE_WORDS
        self.negative_words = NEGATIVE_WORDS
        self.uncertainty_words = UNCERTAINTY_WORDS
        self.litigious_words = LITIGIOUS_WORDS

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyze_text(self, text: str) -> SentimentResult:
        """Compute sentiment for a block of financial text.

        Parameters
        ----------
        text:
            Raw text (earnings call transcript, filing excerpt, etc.).

        Returns
        -------
        SentimentResult with score, magnitude, label, and key phrases.
        """
        tokens = _tokenize(text)
        total = len(tokens)
        if total == 0:
            return SentimentResult(score=0.0, magnitude=0.0, label="neutral", key_phrases=[])

        pos_count = sum(1 for t in tokens if t in self.positive_words)
        neg_count = sum(1 for t in tokens if t in self.negative_words)

        score = (pos_count - neg_count) / total
        magnitude = (pos_count + neg_count) / total

        # Clamp score to [-1, 1] range
        score = max(-1.0, min(1.0, score))
        magnitude = max(0.0, min(1.0, magnitude))

        if score > 0.01:
            label = "bullish"
        elif score < -0.01:
            label = "bearish"
        else:
            label = "neutral"

        key_phrases = self._extract_key_phrases(text)

        return SentimentResult(
            score=score,
            magnitude=magnitude,
            label=label,
            key_phrases=key_phrases,
        )

    # ------------------------------------------------------------------
    # Earnings call analysis
    # ------------------------------------------------------------------

    def analyze_earnings_call(self, transcript: str) -> dict:
        """Analyse an earnings-call transcript with section breakdown.

        Attempts to split the transcript into *prepared remarks* and *Q&A*.
        If the split markers are not found the whole text is treated as a
        single section.

        Returns
        -------
        dict with keys:
            overall   - SentimentResult for the full transcript
            sections  - dict[str, SentimentResult] per detected section
            tone_shift - float difference (Q&A score - prepared remarks score)
        """
        overall = self.analyze_text(transcript)

        # Try to split on common section markers
        sections: dict[str, SentimentResult] = {}
        qa_pattern = re.compile(
            r"(question[- ]?and[- ]?answer|q\s*&\s*a|q&a\s+session)",
            re.IGNORECASE,
        )
        match = qa_pattern.search(transcript)

        tone_shift = 0.0

        if match:
            prepared_text = transcript[: match.start()]
            qa_text = transcript[match.start() :]

            prepared_result = self.analyze_text(prepared_text)
            qa_result = self.analyze_text(qa_text)

            sections["prepared_remarks"] = prepared_result
            sections["qa"] = qa_result
            tone_shift = qa_result.score - prepared_result.score
        else:
            sections["full_transcript"] = overall

        return {
            "overall": overall,
            "sections": sections,
            "tone_shift": tone_shift,
        }

    # ------------------------------------------------------------------
    # Time-series drift
    # ------------------------------------------------------------------

    def sentiment_drift(self, texts: list[tuple[str, str]]) -> pl.DataFrame:
        """Compute sentiment over a time series of documents.

        Parameters
        ----------
        texts:
            List of ``(date_string, text)`` tuples ordered chronologically.

        Returns
        -------
        Polars DataFrame with columns:
            date, score, magnitude, label, drift, significant_shift
        """
        rows: list[dict] = []
        prev_score: float | None = None

        for date_str, text in texts:
            result = self.analyze_text(text)
            drift = 0.0 if prev_score is None else result.score - prev_score
            rows.append({
                "date": date_str,
                "score": result.score,
                "magnitude": result.magnitude,
                "label": result.label,
                "drift": drift,
            })
            prev_score = result.score

        if not rows:
            return pl.DataFrame(
                schema={"date": pl.Utf8, "score": pl.Float64, "magnitude": pl.Float64,
                         "label": pl.Utf8, "drift": pl.Float64, "significant_shift": pl.Boolean},
            )

        df = pl.DataFrame(rows)

        # Mark significant shifts (drift > 2 standard deviations)
        drift_values = df["drift"].to_numpy()
        std = float(np.std(drift_values)) if len(drift_values) > 1 else 0.0
        threshold = 2.0 * std if std > 0 else float("inf")

        df = df.with_columns(
            (pl.col("drift").abs() > threshold).alias("significant_shift"),
        )

        return df

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signals(
        self,
        sentiments: pl.DataFrame,
        threshold: float = 0.02,
        ticker: str = "UNKNOWN",
    ) -> list[Signal]:
        """Convert a sentiment DataFrame into trading signals.

        Parameters
        ----------
        sentiments:
            DataFrame produced by :meth:`sentiment_drift` (must have
            ``date``, ``score``, ``magnitude`` columns).
        threshold:
            Minimum absolute score to emit a signal.
        ticker:
            Ticker symbol to attach to each signal.

        Returns
        -------
        List of :class:`Signal` objects.
        """
        signals: list[Signal] = []

        for row in sentiments.iter_rows(named=True):
            score = row["score"]
            magnitude = row["magnitude"]

            if abs(score) < threshold:
                continue

            direction = 1.0 if score > 0 else -1.0
            confidence = min(1.0, magnitude * abs(score) * 100)

            signals.append(
                Signal(
                    ticker=ticker,
                    date=row["date"],
                    direction=direction,
                    confidence=confidence,
                    metadata={"sentiment_score": score, "label": row["label"]},
                )
            )

        return signals

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_key_phrases(self, text: str, top_n: int = 3) -> list[str]:
        """Return the *top_n* most sentiment-bearing sentences."""
        sentences = re.split(r"[.!?]+", text)
        scored: list[tuple[float, str]] = []

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            tokens = _tokenize(sent)
            if not tokens:
                continue
            pos = sum(1 for t in tokens if t in self.positive_words)
            neg = sum(1 for t in tokens if t in self.negative_words)
            density = (pos + neg) / len(tokens)
            scored.append((density, sent))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_n]]
