"""Specialist quant research agents.

Each agent takes a ticker + date range, runs real computation using the
analytics engine, and returns structured findings with a thought stream.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentFinding:
    """Structured output from a specialist agent."""

    agent_name: str
    ticker: str
    signal: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0.0 to 1.0
    reasoning: str  # One-line summary
    details: dict  # All computed metrics
    thoughts: list[str]  # The "thought stream" -- reasoning steps visible to user

    def to_json(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "ticker": self.ticker,
            "signal": self.signal,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "details": self.details,
            "thoughts": self.thoughts,
        }
