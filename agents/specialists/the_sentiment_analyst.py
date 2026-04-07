"""NLP-based sentiment analysis agent for earnings calls and filings.

Uses :class:`FinancialSentimentAnalyzer` (rule-based, no API keys) to score
text and produce a bullish / bearish / neutral signal with a thought stream.
"""

from __future__ import annotations

import logging

from agents.specialists import AgentFinding
from research.nlp.sentiment import FinancialSentimentAnalyzer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sample text used when no earnings text is provided (demo mode)
# ---------------------------------------------------------------------------

_SAMPLE_EARNINGS_TEXT = (
    "We delivered strong revenue growth this quarter, exceeding expectations. "
    "Our innovative product lineup drove record profitability and robust "
    "momentum across all segments. Operating efficiency improved significantly, "
    "and we see continued opportunity for expansion. "
    "Question and Answer Session: "
    "Analysts asked about headwinds from regulatory challenges and potential "
    "risks in the macro environment. Management acknowledged uncertainty but "
    "reiterated optimistic guidance and strong resilience in core markets."
)


class TheSentimentAnalyst:
    """NLP analysis of earnings calls and filings.

    Runs the :class:`FinancialSentimentAnalyzer` pipeline and emits a
    structured :class:`AgentFinding` with a visible thought stream.
    """

    AGENT_NAME = "TheSentimentAnalyst"

    def __init__(self) -> None:
        self._analyzer = FinancialSentimentAnalyzer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        earnings_text: str | None = None,
    ) -> AgentFinding:
        """Analyse sentiment for *ticker* over the given date range.

        Parameters
        ----------
        ticker:
            Stock ticker symbol.
        start_date / end_date:
            ISO date strings defining the analysis window.
        earnings_text:
            Raw earnings-call or filing text.  If *None* a built-in demo
            excerpt is used.

        Returns
        -------
        AgentFinding
        """
        thoughts: list[str] = []
        details: dict = {}

        # Step 1 -- resolve input text
        if earnings_text is not None:
            text = earnings_text
            thoughts.append(f"Using provided earnings text ({len(text)} chars).")
        else:
            text = _SAMPLE_EARNINGS_TEXT
            thoughts.append(
                f"No earnings text supplied; using sample text ({len(text)} chars) for demo."
            )

        # Step 2 -- overall sentiment
        result = self._analyzer.analyze_text(text)
        thoughts.append(
            f"Analyzing text... sentiment score: {result.score:.4f}, label: {result.label}"
        )
        details["overall_score"] = result.score
        details["overall_magnitude"] = result.magnitude
        details["overall_label"] = result.label

        # Step 3 -- earnings-call section breakdown (if text is long enough)
        if len(text) >= 100:
            ec_result = self._analyzer.analyze_earnings_call(text)
            sections = ec_result["sections"]
            tone_shift = ec_result["tone_shift"]

            if "prepared_remarks" in sections:
                pr_score = sections["prepared_remarks"].score
                qa_score = sections["qa"].score
                thoughts.append(
                    f"Prepared remarks sentiment: {pr_score:.4f}, "
                    f"Q&A sentiment: {qa_score:.4f}, "
                    f"tone shift: {tone_shift:+.4f}"
                )
                details["prepared_remarks_score"] = pr_score
                details["qa_score"] = qa_score
            else:
                thoughts.append(
                    "Could not split into prepared remarks / Q&A; treated as single section."
                )

            details["tone_shift"] = tone_shift
        else:
            thoughts.append("Text too short for earnings-call section analysis.")

        # Step 4 -- key phrases
        key_phrases = result.key_phrases
        thoughts.append(f"Key phrases: {key_phrases}")
        details["key_phrases"] = key_phrases

        # Step 5 -- determine signal
        score = result.score
        if score > 0.02:
            signal = "bullish"
        elif score < -0.02:
            signal = "bearish"
        else:
            signal = "neutral"

        # Step 6 -- confidence
        confidence = result.magnitude * min(abs(score) * 10, 1.0)
        confidence = max(0.0, min(1.0, confidence))
        thoughts.append(f"Signal: {signal} (confidence {confidence:.2f})")

        details["ticker"] = ticker
        details["start_date"] = start_date
        details["end_date"] = end_date

        reasoning = (
            f"Sentiment analysis of text yields score {score:.4f} "
            f"({signal}, confidence {confidence:.2f})."
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
