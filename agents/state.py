"""Shared agent state for the LangGraph multi-agent research pipeline.

Defines the state dataclass passed between agent nodes and the event model
used for dashboard observability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AgentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class AgentEvent:
    """An event emitted by an agent during execution."""

    agent_name: str
    status: AgentStatus
    message: str
    data: dict = field(default_factory=dict)
    timestamp: str = ""  # ISO format, set on creation

    def to_json(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        }


@dataclass
class ResearchState:
    """Shared state passed between agents in the LangGraph."""

    ticker: str
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float = 100_000.0

    # Populated by agents
    prices: dict = field(default_factory=dict)  # serialized DataFrame
    features: dict = field(default_factory=dict)
    signals: list = field(default_factory=list)  # serialized Signal list
    risk_assessment: dict = field(default_factory=dict)
    backtest_result: dict = field(default_factory=dict)
    validation_result: dict = field(default_factory=dict)
    signal_decay: dict = field(default_factory=dict)
    research_report: str = ""

    # Control flow
    events: list = field(default_factory=list)  # list of AgentEvent.to_json()
    errors: list = field(default_factory=list)
    human_approval_required: bool = False
    human_approved: bool | None = None  # None = pending, True = approved, False = rejected

    def add_event(
        self,
        agent_name: str,
        status: AgentStatus,
        message: str,
        data: dict | None = None,
    ) -> None:
        from datetime import datetime, timezone

        event = AgentEvent(
            agent_name=agent_name,
            status=status,
            message=message,
            data=data or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.events.append(event.to_json())
