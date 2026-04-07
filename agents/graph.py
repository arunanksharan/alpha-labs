"""LangGraph DAG definition for the multi-agent research pipeline.

Flow:
    research_agent -> risk_agent -> [approval_gate] -> validation_agent
                                                    -> decay_agent -> report_agent

If approval_gate returns "wait", the graph pauses for human approval.
If "abort", it skips directly to report_agent with partial results.

When langgraph is not installed, AgentRunner falls back to simple sequential
execution so the system remains functional without the dependency.
"""

from __future__ import annotations

import logging

from agents.nodes import (
    approval_gate,
    decay_agent,
    report_agent,
    research_agent,
    risk_agent,
    validation_agent,
)
from agents.state import AgentStatus, ResearchState

logger = logging.getLogger(__name__)


def build_research_graph():
    """Build the LangGraph research pipeline.

    Returns a compiled StateGraph, or ``None`` if langgraph is not installed.
    """
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(ResearchState)
        graph.add_node("research", research_agent)
        graph.add_node("risk", risk_agent)
        graph.add_node("validation", validation_agent)
        graph.add_node("decay", decay_agent)
        graph.add_node("report", report_agent)

        graph.set_entry_point("research")
        graph.add_edge("research", "risk")
        graph.add_conditional_edges(
            "risk",
            approval_gate,
            {
                "continue": "validation",
                "abort": "report",
                "wait": END,  # Pause for human approval
            },
        )
        graph.add_edge("validation", "decay")
        graph.add_edge("decay", "report")
        graph.add_edge("report", END)

        return graph.compile()
    except ImportError:
        logger.warning("langgraph not installed, using simple sequential fallback")
        return None


class AgentRunner:
    """Run the multi-agent research system."""

    def __init__(self) -> None:
        self._graph = build_research_graph()

    def run(
        self,
        ticker: str,
        strategy: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100_000.0,
    ) -> ResearchState:
        """Execute the full agent pipeline."""
        state = ResearchState(
            ticker=ticker,
            strategy_name=strategy,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
        )

        if self._graph is not None:
            result = self._graph.invoke(state)
            return result

        # Fallback: run sequentially without LangGraph
        state = research_agent(state)
        state = risk_agent(state)
        gate = approval_gate(state)
        if gate == "continue":
            state = validation_agent(state)
            state = decay_agent(state)
        state = report_agent(state)
        return state

    def approve(self, state: ResearchState) -> ResearchState:
        """Human approves the pending signals -- resume the pipeline."""
        state.human_approved = True
        state.add_event("human", AgentStatus.APPROVED, "Human approved signals")

        if self._graph is not None:
            return self._graph.invoke(state)

        # Fallback sequential continuation
        state = validation_agent(state)
        state = decay_agent(state)
        state = report_agent(state)
        return state

    def reject(self, state: ResearchState) -> ResearchState:
        """Human rejects the pending signals -- skip to report."""
        state.human_approved = False
        state.add_event("human", AgentStatus.REJECTED, "Human rejected signals")
        state = report_agent(state)
        return state
