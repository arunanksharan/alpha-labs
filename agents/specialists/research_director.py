"""Research Director -- orchestrates specialist agents and synthesizes findings.

The Research Director is the "confident analyst" voice the user interacts with.
It coordinates all specialist agents, collects their findings, synthesizes a
consensus view, and produces actionable research briefs.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from agents.specialists import AgentFinding

logger = logging.getLogger(__name__)


@dataclass
class ResearchBrief:
    """The morning brief output."""

    greeting: str
    top_convictions: list[dict]  # [{ticker, signal, confidence, agent_summary, reasoning}]
    watchlist: list[dict]  # [{ticker, status, note}]
    portfolio_health: dict  # {pnl, sharpe, var, decay_status}
    what_i_learned: str  # Meta-learning from recent signals
    pending_approvals: list[dict]  # [{ticker, action, size, rationale}]

    def to_json(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Specialist protocol -- any object with an analyze(ticker, start, end) method
# ---------------------------------------------------------------------------

class _SpecialistProtocol:
    """Minimal interface that specialist agents must implement."""

    def analyze(self, ticker: str, start_date: str, end_date: str) -> AgentFinding:
        ...


# ---------------------------------------------------------------------------
# Director
# ---------------------------------------------------------------------------

class ResearchDirector:
    """Orchestrates specialist agents, synthesizes findings, writes briefs."""

    def __init__(self) -> None:
        self._specialists: dict[str, Any] | None = None

    # -- Lazy loading -------------------------------------------------------

    def _load_specialists(self) -> dict[str, Any]:
        """Import and instantiate specialist agents lazily to avoid circular imports."""
        if self._specialists is not None:
            return self._specialists

        specialists: dict[str, Any] = {}
        agent_classes = {
            "quant": ("agents.specialists.the_quant", "TheQuant"),
            "technician": ("agents.specialists.the_technician", "TheTechnician"),
            "sentiment": ("agents.specialists.the_sentiment_analyst", "TheSentimentAnalyst"),
            "fundamentalist": ("agents.specialists.the_fundamentalist", "TheFundamentalist"),
            "macro": ("agents.specialists.the_macro_strategist", "TheMacroStrategist"),
            "contrarian": ("agents.specialists.the_contrarian", "TheContrarian"),
        }

        for name, (module_path, class_name) in agent_classes.items():
            try:
                import importlib
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                specialists[name] = cls()
            except (ImportError, AttributeError) as exc:
                logger.warning("Could not load specialist %s: %s", name, exc)

        self._specialists = specialists
        return specialists

    # -- Core research ------------------------------------------------------

    def research_ticker(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        event_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        """Run full multi-agent analysis on a single ticker.

        Parameters
        ----------
        ticker:
            Ticker symbol (e.g. "AAPL").
        start_date / end_date:
            ISO date strings for the analysis window.
        event_callback:
            Optional callback invoked with each agent's event dict as they complete.

        Returns
        -------
        dict
            All findings + synthesis with consensus signal and confidence.
        """
        specialists = self._load_specialists()
        findings: list[dict] = []
        agent_traces: list[dict] = []

        for agent_name, agent in specialists.items():
            try:
                if event_callback:
                    event_callback({
                        "agent": agent_name,
                        "status": "running",
                        "ticker": ticker,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                finding: AgentFinding = agent.analyze(ticker, start_date, end_date)
                finding_dict = finding.to_json()
                findings.append(finding_dict)

                agent_traces.append({
                    "agent": agent_name,
                    "thoughts": finding.thoughts,
                    "signal": finding.signal,
                    "confidence": finding.confidence,
                })

                if event_callback:
                    event_callback({
                        "agent": agent_name,
                        "status": "completed",
                        "ticker": ticker,
                        "signal": finding.signal,
                        "confidence": finding.confidence,
                        "reasoning": finding.reasoning,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            except Exception as exc:
                logger.error("Agent %s failed on %s: %s", agent_name, ticker, exc)
                agent_traces.append({
                    "agent": agent_name,
                    "error": str(exc),
                })
                if event_callback:
                    event_callback({
                        "agent": agent_name,
                        "status": "failed",
                        "ticker": ticker,
                        "error": str(exc),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

        # -- Synthesize consensus -------------------------------------------
        synthesis = self._synthesize(ticker, findings)

        return {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "findings": findings,
            "synthesis": synthesis,
            "agent_traces": agent_traces,
        }

    # -- Synthesis logic ----------------------------------------------------

    @staticmethod
    def _synthesize(ticker: str, findings: list[dict]) -> dict:
        """Aggregate specialist findings into a consensus view."""
        if not findings:
            return {
                "consensus_signal": "neutral",
                "consensus_confidence": 0.0,
                "high_conviction": False,
                "vote_counts": {"bullish": 0, "bearish": 0, "neutral": 0},
                "reasoning": f"No agent findings available for {ticker}.",
            }

        votes: dict[str, int] = {"bullish": 0, "bearish": 0, "neutral": 0}
        confidence_sum = 0.0
        key_points: list[str] = []

        for f in findings:
            signal = f.get("signal", "neutral")
            votes[signal] = votes.get(signal, 0) + 1
            confidence_sum += f.get("confidence", 0.0)
            if f.get("reasoning"):
                key_points.append(f"{f['agent_name']}: {f['reasoning']}")

        total = len(findings)
        consensus_signal = max(votes, key=votes.get)  # type: ignore[arg-type]
        consensus_confidence = confidence_sum / total if total else 0.0
        high_conviction = votes[consensus_signal] > 4

        # Build one-line reasoning
        vote_str = f"{votes[consensus_signal]}/{total} agents {consensus_signal}"
        key_summary = ". ".join(key_points[:3]) if key_points else "Limited data"
        reasoning = f"{vote_str}. Key: {key_summary}."

        return {
            "consensus_signal": consensus_signal,
            "consensus_confidence": round(consensus_confidence, 4),
            "high_conviction": high_conviction,
            "vote_counts": votes,
            "reasoning": reasoning,
        }

    # -- Morning brief ------------------------------------------------------

    def generate_morning_brief(
        self,
        tickers: list[str],
        start_date: str,
        end_date: str,
        event_callback: Callable[[dict], None] | None = None,
    ) -> ResearchBrief:
        """Generate the full morning research brief across multiple tickers.

        Parameters
        ----------
        tickers:
            List of ticker symbols to research.
        start_date / end_date:
            ISO date strings for the analysis window.
        event_callback:
            Optional callback for real-time event streaming.

        Returns
        -------
        ResearchBrief
            Complete brief with convictions, watchlist, health, and pending approvals.
        """
        results: list[dict] = []
        for ticker in tickers:
            try:
                result = self.research_ticker(ticker, start_date, end_date, event_callback)
                results.append(result)
            except Exception as exc:
                logger.error("Failed to research %s: %s", ticker, exc)
                results.append({
                    "ticker": ticker,
                    "synthesis": {
                        "consensus_signal": "neutral",
                        "consensus_confidence": 0.0,
                        "high_conviction": False,
                        "vote_counts": {"bullish": 0, "bearish": 0, "neutral": 0},
                        "reasoning": f"Research failed: {exc}",
                    },
                    "findings": [],
                    "agent_traces": [],
                })

        # Sort by consensus confidence descending
        results.sort(
            key=lambda r: r.get("synthesis", {}).get("consensus_confidence", 0.0),
            reverse=True,
        )

        # Top 3 -> convictions
        top_convictions: list[dict] = []
        for r in results[:3]:
            syn = r.get("synthesis", {})
            top_convictions.append({
                "ticker": r["ticker"],
                "signal": syn.get("consensus_signal", "neutral"),
                "confidence": syn.get("consensus_confidence", 0.0),
                "agent_summary": syn.get("vote_counts", {}),
                "reasoning": syn.get("reasoning", ""),
            })

        # Next up to 5 -> watchlist
        watchlist: list[dict] = []
        for r in results[3:8]:
            syn = r.get("synthesis", {})
            watchlist.append({
                "ticker": r["ticker"],
                "status": "approaching" if syn.get("consensus_confidence", 0) > 0.4 else "monitoring",
                "note": syn.get("reasoning", ""),
            })

        # Portfolio health placeholder
        portfolio_health = {
            "pnl": 0.0,
            "sharpe": 0.0,
            "var": 0.0,
            "decay_status": "not_computed",
        }

        # Pending approvals: high conviction signals that need human sign-off
        pending_approvals: list[dict] = []
        for conv in top_convictions:
            if conv["confidence"] > 0.7 and conv["signal"] != "neutral":
                pending_approvals.append({
                    "ticker": conv["ticker"],
                    "action": "buy" if conv["signal"] == "bullish" else "sell",
                    "size": "standard",
                    "rationale": conv["reasoning"],
                })

        # Greeting
        now = datetime.now(timezone.utc)
        period = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
        greeting = (
            f"Good {period}. I've analyzed {len(tickers)} tickers and have "
            f"{len(top_convictions)} conviction ideas ready for review."
        )

        return ResearchBrief(
            greeting=greeting,
            top_convictions=top_convictions,
            watchlist=watchlist,
            portfolio_health=portfolio_health,
            what_i_learned="Meta-learning not yet implemented. Will track signal accuracy over time.",
            pending_approvals=pending_approvals,
        )

    # -- Research chat question answering -----------------------------------

    def answer_question(
        self,
        question: str,
        context: dict | None = None,
    ) -> dict:
        """Handle a research chat question with grounded computation.

        Parses intent from the question, calls relevant specialists, and
        returns a confident, opinionated analyst response.

        Parameters
        ----------
        question:
            Natural language research question.
        context:
            Optional context dict (e.g. chat history).

        Returns
        -------
        dict
            {answer, citations, actions, agent_traces}
        """
        question_lower = question.lower().strip()

        # -- Parse intent ---------------------------------------------------
        intent = self._parse_intent(question_lower)

        answer = ""
        citations: list[str] = []
        actions: list[str] = []
        agent_traces: list[dict] = []

        # Default date range for analysis
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = datetime(
            datetime.now(timezone.utc).year - 1, 1, 1
        ).strftime("%Y-%m-%d")

        if intent["type"] == "ticker_research":
            ticker = intent["ticker"]
            result = self.research_ticker(ticker, start_date, end_date)
            syn = result.get("synthesis", {})
            agent_traces = result.get("agent_traces", [])

            answer = (
                f"On {ticker}: My view is **{syn.get('consensus_signal', 'neutral')}** "
                f"with {syn.get('consensus_confidence', 0):.0%} confidence. "
                f"{syn.get('reasoning', '')}"
            )
            citations = [
                f"{f['agent_name']}: {f['reasoning']}"
                for f in result.get("findings", [])
                if f.get("reasoning")
            ]
            actions = [
                f"Run backtest on {ticker}",
                f"Compare {ticker} with peers",
                f"Approve trade on {ticker}" if syn.get("high_conviction") else f"Add {ticker} to watchlist",
            ]

        elif intent["type"] == "comparison":
            tickers = intent["tickers"]
            results_map: dict[str, dict] = {}
            for t in tickers:
                results_map[t] = self.research_ticker(t, start_date, end_date)
                agent_traces.extend(results_map[t].get("agent_traces", []))

            comparison_lines: list[str] = []
            for t, r in results_map.items():
                syn = r.get("synthesis", {})
                comparison_lines.append(
                    f"{t}: {syn.get('consensus_signal', 'neutral')} "
                    f"({syn.get('consensus_confidence', 0):.0%} confidence)"
                )

            answer = "Here's my comparison:\n" + "\n".join(comparison_lines)
            citations = [
                f"{t} synthesis: {r.get('synthesis', {}).get('reasoning', '')}"
                for t, r in results_map.items()
            ]
            best = max(results_map.items(), key=lambda x: x[1].get("synthesis", {}).get("consensus_confidence", 0))
            actions = [
                f"Deep dive into {best[0]}",
                "Run portfolio optimization with these tickers",
            ]

        elif intent["type"] == "performance":
            answer = (
                "Performance review is not yet connected to live portfolio data. "
                "Run a daily cycle to generate performance metrics."
            )
            actions = ["Run daily cycle", "Check backtest results"]

        elif intent["type"] == "strategy":
            answer = (
                "I can help build a strategy. Tell me the ticker and I'll research it "
                "with all six specialist agents, then suggest entry/exit rules based on "
                "the strongest signals."
            )
            actions = ["Research a specific ticker", "Run morning brief"]

        else:
            # General / fallback: try to extract any ticker mention
            tickers_found = self._extract_tickers(question)
            if tickers_found:
                ticker = tickers_found[0]
                result = self.research_ticker(ticker, start_date, end_date)
                syn = result.get("synthesis", {})
                agent_traces = result.get("agent_traces", [])
                answer = (
                    f"I interpreted your question as being about {ticker}. "
                    f"My current view: **{syn.get('consensus_signal', 'neutral')}** "
                    f"({syn.get('consensus_confidence', 0):.0%} confidence). "
                    f"{syn.get('reasoning', '')}"
                )
                citations = [
                    f"{f['agent_name']}: {f['reasoning']}"
                    for f in result.get("findings", [])
                    if f.get("reasoning")
                ]
                actions = [f"Run backtest on {ticker}", "Ask a more specific question"]
            else:
                answer = (
                    "I'm your research analyst. Ask me about a specific ticker, "
                    "compare stocks, review performance, or ask me to build a strategy. "
                    "Example: 'What's your view on AAPL?' or 'Compare NVDA vs MSFT'."
                )
                actions = ["Research AAPL", "Run morning brief", "Compare NVDA vs MSFT"]

        return {
            "answer": answer,
            "citations": citations,
            "actions": actions,
            "agent_traces": agent_traces,
        }

    # -- Intent parsing helpers ---------------------------------------------

    @staticmethod
    def _parse_intent(question: str) -> dict:
        """Simple keyword-based intent parser."""
        # Comparison: "why X vs Y", "compare X and Y", "AAPL vs MSFT"
        question_upper = question.upper()
        compare_pattern = r"(?:COMPARE)\s+([A-Z]{1,5})\s+(?:AND|VS|VERSUS|WITH)\s+([A-Z]{1,5})"
        match = re.search(compare_pattern, question_upper)
        if match:
            return {"type": "comparison", "tickers": [match.group(1), match.group(2)]}

        # "X vs Y" without explicit compare keyword
        vs_pattern = r"([A-Z]{2,5})\s+(?:VS|VERSUS)\s+([A-Z]{2,5})"
        match = re.search(vs_pattern, question_upper)
        if match:
            return {"type": "comparison", "tickers": [match.group(1), match.group(2)]}

        # Also catch "why X over Y"
        why_pattern = r"WHY\s+(?:IS\s+)?([A-Z]{2,5})\s+(?:OVER|VS|VERSUS|BETTER\s+THAN|NOT|INSTEAD\s+OF)\s+([A-Z]{2,5})"
        match = re.search(why_pattern, question_upper)
        if match:
            return {"type": "comparison", "tickers": [match.group(1), match.group(2)]}

        # Performance
        perf_keywords = ["performance", "last week", "last month", "returns", "how did", "pnl"]
        if any(kw in question for kw in perf_keywords):
            return {"type": "performance"}

        # Strategy building
        strategy_keywords = ["build", "strategy", "create", "design", "construct"]
        if any(kw in question for kw in strategy_keywords):
            return {"type": "strategy"}

        # Single ticker research -- iterate all uppercase words and pick the first non-noise one
        noise = {
            "I", "A", "THE", "IS", "IT", "MY", "ME", "DO", "ON", "IN",
            "AT", "TO", "OR", "AN", "IF", "SO", "NO", "AM", "AS", "BE",
            "BY", "GO", "HE", "OF", "UP", "US", "WE", "WHAT", "WHY",
            "HOW", "CAN", "WILL", "YOUR", "VIEW", "FOR", "NOT", "BUT",
            "ALL", "ARE", "WAS", "HAS", "HAD", "HIS", "HER", "ITS",
            "OUR", "OUT", "WHO", "DID", "GET", "HIM", "LET", "SAY",
            "SHE", "TOO", "USE", "DAD", "MOM", "OLD", "SEE", "NOW",
            "WAY", "MAY", "DAY", "NEW", "ONE", "TWO", "TOP", "RUN",
            "SET", "TRY", "ASK", "OWN", "PUT", "BIG", "END", "OFF",
            "MAN", "GOT", "GAS", "THAT", "THIS", "WITH", "HAVE",
            "FROM", "BEEN", "SOME", "WHEN", "THEM", "THAN", "EACH",
            "MAKE", "LIKE", "LONG", "LOOK", "MANY", "MOST", "OVER",
            "SUCH", "TAKE", "JUST", "INTO", "VERY", "ALSO", "BACK",
            "GOOD", "GIVE", "MUCH", "THEN", "WELL", "ONLY", "COME",
            "MADE", "FIND", "HERE", "TELL", "THINK", "ABOUT", "HELLO",
            "THERE", "WOULD", "COULD", "SHOULD", "THESE", "THOSE",
            "OTHER", "WHICH", "THEIR", "AFTER", "FIRST", "NEVER",
            "WHERE", "EVERY", "TIME", "NEED", "WANT", "YOU", "BUY",
            "SELL", "HOLD", "CALL", "KNOW", "SHOW", "HELP", "MEAN",
            "MORE", "LAST", "BEST", "SAME", "REAL", "HIGH", "LOW",
            "DOWN", "BEEN", "DOES", "DONE", "KEEP", "NEXT", "WORK",
            "PART", "YEAR", "SURE", "STILL", "BEING", "SINCE", "WHILE",
            "UNTIL", "BELOW", "ABOVE", "UNDER", "DOING", "GOING",
            "MARKET", "STOCK", "STOCKS", "TODAY", "RIGHT",
        }
        for candidate_match in re.finditer(r"\b([A-Z]{2,5})\b", question.upper()):
            candidate = candidate_match.group(1)
            if candidate not in noise:
                return {"type": "ticker_research", "ticker": candidate}

        return {"type": "general"}

    @staticmethod
    def _extract_tickers(text: str) -> list[str]:
        """Extract potential ticker symbols from text."""
        noise = {
            "I", "A", "THE", "IS", "IT", "MY", "ME", "DO", "ON", "IN",
            "AT", "TO", "OR", "AN", "IF", "SO", "NO", "AM", "AS", "BE",
            "BY", "GO", "HE", "OF", "UP", "US", "WE", "WHAT", "WHY",
            "HOW", "CAN", "WILL", "YOUR", "VIEW", "FOR", "NOT", "BUT",
            "ALL", "ARE", "WAS", "HAS", "HAD", "HIS", "HER", "ITS",
            "OUR", "OUT", "WHO", "DID", "GET", "HIM", "LET", "SAY",
            "SHE", "TOO", "USE", "NOW", "WAY", "MAY", "DAY", "NEW",
            "ONE", "TWO", "TOP", "RUN", "SET", "TRY", "ASK", "OWN",
            "PUT", "BIG", "END", "OFF", "MAN", "GOT", "GAS", "THAT",
            "THIS", "WITH", "HAVE", "FROM", "BEEN", "SOME", "WHEN",
            "THEM", "THAN", "EACH", "MAKE", "LIKE", "LONG", "LOOK",
            "MANY", "MOST", "OVER", "SUCH", "TAKE", "JUST", "INTO",
            "VERY", "ALSO", "BACK", "GOOD", "GIVE", "MUCH", "THEN",
            "WELL", "ONLY", "COME", "MADE", "FIND", "HERE", "TELL",
            "THINK", "ABOUT", "HELLO", "THERE", "WOULD", "COULD",
            "SHOULD", "THESE", "THOSE", "OTHER", "WHICH", "THEIR",
            "AFTER", "FIRST", "NEVER", "WHERE", "EVERY",
        }
        candidates = re.findall(r"\b([A-Z]{2,5})\b", text.upper())
        return [c for c in candidates if c not in noise]
