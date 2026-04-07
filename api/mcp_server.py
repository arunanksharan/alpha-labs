"""MCP Server for the Agentic Alpha Lab.

Exposes quant research tools via Model Context Protocol.
Any MCP-compatible AI agent (Claude, etc.) can call these tools.

Run with: python -m api.mcp_server
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "research_strategy",
        "description": (
            "Run complete quant research pipeline: fetch data -> compute features "
            "-> generate signals -> backtest -> validate -> analyze decay. "
            "Returns comprehensive JSON results."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, MSFT)",
                },
                "strategy": {
                    "type": "string",
                    "description": "Strategy name: mean_reversion, momentum",
                    "default": "mean_reversion",
                },
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
                "initial_capital": {"type": "number", "default": 100000},
            },
            "required": ["ticker", "start_date", "end_date"],
        },
    },
    {
        "name": "fetch_market_data",
        "description": (
            "Fetch OHLCV market data for a ticker. "
            "Returns date, open, high, low, close, volume."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
            "required": ["ticker", "start_date", "end_date"],
        },
    },
    {
        "name": "run_backtest",
        "description": (
            "Backtest trading signals against historical prices. "
            "Returns Sharpe, Sortino, max drawdown, equity curve."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "signals_json": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of {date, ticker, direction, confidence}",
                },
                "prices_json": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of {date, ticker, close}",
                },
                "initial_capital": {"type": "number", "default": 100000},
            },
            "required": ["signals_json", "prices_json"],
        },
    },
    {
        "name": "analyze_sentiment",
        "description": (
            "Analyze financial sentiment of text (earnings calls, SEC filings). "
            "Returns bullish/bearish/neutral with score."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Financial text to analyze",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "compute_risk_metrics",
        "description": (
            "Compute VaR, CVaR, max drawdown, and other risk metrics "
            "for a return series."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "returns_json": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of {date, returns}",
                },
                "confidence": {"type": "number", "default": 0.95},
            },
            "required": ["returns_json"],
        },
    },
    {
        "name": "analyze_signal_decay",
        "description": (
            "Measure how long a trading signal remains profitable. "
            "Returns IC curve, half-life, and decay summary."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "signals_json": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of {date, ticker, signal_value}",
                },
                "prices_json": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of {date, ticker, close}",
                },
                "max_horizon": {"type": "integer", "default": 60},
            },
            "required": ["signals_json", "prices_json"],
        },
    },
    {
        "name": "research_filing",
        "description": (
            "Query SEC filings using RAG. Searches stored financial documents "
            "and returns relevant excerpts with an AI-generated answer."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Research question about a company's filings",
                },
                "ticker": {
                    "type": "string",
                    "description": "Company ticker (optional, for filtering)",
                },
            },
            "required": ["query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool handler dispatch
# ---------------------------------------------------------------------------


def handle_tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Route MCP tool call to the appropriate platform handler."""

    if name == "research_strategy":
        from core.orchestrator import ResearchOrchestrator

        orch = ResearchOrchestrator()
        result = orch.run(
            ticker=arguments["ticker"],
            strategy_name=arguments.get("strategy", "mean_reversion"),
            start_date=arguments["start_date"],
            end_date=arguments["end_date"],
            initial_capital=arguments.get("initial_capital", 100_000.0),
        )
        return result.to_json()

    if name == "fetch_market_data":
        from core.adapters import fetch_and_prepare_prices

        prices = fetch_and_prepare_prices(
            arguments["ticker"], arguments["start_date"], arguments["end_date"]
        )
        return {"rows": len(prices), "data": prices.head(20).to_dicts()}

    if name == "run_backtest":
        from core.backtest import BacktestEngineRegistry
        from core.serialization import df_from_json

        signals = df_from_json(arguments["signals_json"])
        prices = df_from_json(arguments["prices_json"])
        engine = BacktestEngineRegistry.get("vectorized")
        result = engine.run(signals, prices, arguments.get("initial_capital", 100_000.0))
        return result.to_json()

    if name == "analyze_sentiment":
        from research.nlp.sentiment import FinancialSentimentAnalyzer

        analyzer = FinancialSentimentAnalyzer()
        result = analyzer.analyze_text(arguments["text"])
        return {
            "score": result.score,
            "magnitude": result.magnitude,
            "label": result.label,
            "key_phrases": result.key_phrases,
        }

    if name == "compute_risk_metrics":
        from core.serialization import df_from_json
        from analytics.returns import (
            compute_cvar,
            compute_max_drawdown,
            compute_sharpe,
            compute_sortino,
            compute_var,
        )

        returns_df = df_from_json(arguments["returns_json"])
        confidence = arguments.get("confidence", 0.95)
        return {
            "sharpe": compute_sharpe(returns_df),
            "sortino": compute_sortino(returns_df),
            "max_drawdown": compute_max_drawdown(returns_df),
            "var": compute_var(returns_df, confidence=confidence),
            "cvar": compute_cvar(returns_df, confidence=confidence),
        }

    if name == "analyze_signal_decay":
        from analytics.signal_decay import SignalDecayAnalyzer
        from core.serialization import df_from_json

        signals = df_from_json(arguments["signals_json"])
        prices = df_from_json(arguments["prices_json"])
        analyzer = SignalDecayAnalyzer(max_horizon=arguments.get("max_horizon", 60))
        ic_curve = analyzer.compute_ic_curve(signals, prices)
        return {
            "ic_curve": ic_curve.to_dicts(),
            "half_life": analyzer.compute_ic_half_life(ic_curve),
            "summary": analyzer.decay_summary(ic_curve),
        }

    if name == "research_filing":
        from research.nlp.rag_pipeline import FinancialRAG

        rag = FinancialRAG()
        result = rag.query(arguments["query"])
        return {
            "answer": result.answer,
            "sources": result.sources,
            "model": result.model,
        }

    raise ValueError(f"Unknown tool: {name}")


def get_tools() -> list[dict[str, Any]]:
    """Return MCP tool definitions."""
    return TOOLS
