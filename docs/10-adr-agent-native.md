# ADR-008: Agent-Native Architecture

**Date**: 2026-04-07
**Status**: Accepted

## Context

After building Weeks 1-11 (20,850 lines, 653 tests), we evaluated whether our platform reflects the realities of 2026 AI/agent development. The answer was no — we'd built a strong traditional quant stack but designed it for a human operator.

## The Problem

The quant industry is in the middle of a transition:

```
2020: Human-driven         "I run the analysis and decide"
2024: Human-in-the-loop    "Agent proposes, I approve"
2026: Human-on-the-loop    "Agents act, I monitor + override"  ← target
2028: Autonomous            "Agents run, I set constraints"
```

Our Weeks 1-11 platform was stuck at "human-driven." Every interaction required a human to run CLI commands, read tear sheets, and make decisions manually.

## Decision

Redesign the platform to be **agent-native**:

1. **MCP Server**: Expose all capabilities as Model Context Protocol tools. Any AI agent (Claude, GPT, custom) can call `fetch_market_data`, `run_backtest`, `research_filing` as tools.

2. **Multi-Agent Orchestration**: LangGraph-based agent system where specialized agents (Research, Risk, Validation, Report) collaborate autonomously with human approval gates.

3. **Structured JSON First**: All API responses return structured JSON. Human-readable formats (HTML, plots) are secondary views.

4. **Event-Driven**: WebSocket/SSE stream for real-time signal notifications. Agents and dashboards subscribe to the same event stream.

5. **Human-on-the-Loop**: Agents propose actions, human approves/overrides via dashboard. Circuit breakers can pause the system.

## Why This Matters

- **For Head of AI positioning**: The mandate at funds like Point72, Citadel, GIC is "build autonomous research agents." Demonstrating this architecture is the proof.
- **For the Singapore meetup**: The live demo of agents autonomously researching and humans approving on a dashboard is far more compelling than "I run a CLI command."
- **For the platform**: MCP exposure means any AI agent can use our tools — this is the new API economy.

## Architecture Change

```
BEFORE (Human-Driven):
Human → CLI → Platform → HTML Report → Human reads

AFTER (Agent-Native):
AI Agent → MCP/API → Platform → Structured JSON → Agent processes
Human → Dashboard → Monitors → Approves/Overrides
```

## What Stays the Same

All Weeks 1-11 code remains valid. The core modules (analytics, strategies, backtest, risk, features, models, research) are the **implementation layer**. Weeks 12-13 add the **agent layer** on top:

- MCP Server wraps existing functions as tools
- LangGraph agents call existing modules
- FastAPI serves existing data as JSON
- Dashboard visualizes existing outputs

No rewrite needed. Just a new interface layer.

## Implications

- Weeks 12-13 roadmap completely redesigned
- MCP server becomes the primary integration point
- Dashboard serves humans monitoring agents, not humans driving analysis
- Meetup demo shifts from "look what I built" to "look what my agents do"
