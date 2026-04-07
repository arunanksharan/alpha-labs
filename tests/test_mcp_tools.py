"""Tests for MCP tool definitions and handlers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api.mcp_server import TOOLS, get_tools, handle_tool_call


# ---------------------------------------------------------------------------
# Tool definition tests
# ---------------------------------------------------------------------------


def test_get_tools_returns_list() -> None:
    tools = get_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0


def test_all_tools_have_required_fields() -> None:
    """Every tool must have name, description, and inputSchema."""
    for tool in get_tools():
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
        assert "inputSchema" in tool, f"Tool {tool['name']} missing 'inputSchema'"

        schema = tool["inputSchema"]
        assert schema.get("type") == "object", (
            f"Tool {tool['name']} inputSchema type must be 'object'"
        )
        assert "properties" in schema, (
            f"Tool {tool['name']} inputSchema missing 'properties'"
        )
        assert "required" in schema, (
            f"Tool {tool['name']} inputSchema missing 'required'"
        )


def test_tool_names_are_unique() -> None:
    names = [t["name"] for t in get_tools()]
    assert len(names) == len(set(names)), "Duplicate tool names found"


def test_known_tool_names_present() -> None:
    names = {t["name"] for t in get_tools()}
    expected = {
        "research_strategy",
        "fetch_market_data",
        "run_backtest",
        "analyze_sentiment",
        "compute_risk_metrics",
        "analyze_signal_decay",
        "research_filing",
    }
    assert expected.issubset(names), f"Missing tools: {expected - names}"


# ---------------------------------------------------------------------------
# Handler tests (mocked to avoid heavy dependencies)
# ---------------------------------------------------------------------------


def test_handle_analyze_sentiment() -> None:
    """analyze_sentiment handler returns score, magnitude, label, key_phrases."""
    mock_result = MagicMock()
    mock_result.score = 0.75
    mock_result.magnitude = 0.9
    mock_result.label = "bullish"
    mock_result.key_phrases = ["strong growth", "record revenue"]

    mock_analyzer = MagicMock()
    mock_analyzer.analyze_text.return_value = mock_result

    with patch(
        "research.nlp.sentiment.FinancialSentimentAnalyzer",
        return_value=mock_analyzer,
    ):
        result = handle_tool_call(
            "analyze_sentiment",
            {"text": "The company reported strong growth and record revenue."},
        )

    assert result["score"] == 0.75
    assert result["magnitude"] == 0.9
    assert result["label"] == "bullish"
    assert "strong growth" in result["key_phrases"]


def test_handle_compute_risk_metrics() -> None:
    """compute_risk_metrics handler returns sharpe, sortino, etc."""
    with (
        patch("analytics.returns.compute_sharpe", return_value=1.5),
        patch("analytics.returns.compute_sortino", return_value=2.0),
        patch("analytics.returns.compute_max_drawdown", return_value=-0.10),
        patch("analytics.returns.compute_var", return_value=-0.02),
        patch("analytics.returns.compute_cvar", return_value=-0.03),
    ):
        result = handle_tool_call(
            "compute_risk_metrics",
            {
                "returns_json": [
                    {"date": "2024-01-02", "returns": 0.01},
                    {"date": "2024-01-03", "returns": -0.005},
                    {"date": "2024-01-04", "returns": 0.008},
                ],
                "confidence": 0.95,
            },
        )

    assert result["sharpe"] == 1.5
    assert result["sortino"] == 2.0
    assert result["max_drawdown"] == -0.10
    assert result["var"] == -0.02
    assert result["cvar"] == -0.03


def test_handle_unknown_tool_raises() -> None:
    """Calling an unknown tool must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown tool"):
        handle_tool_call("nonexistent_tool", {})


def test_handle_research_filing() -> None:
    """research_filing handler returns answer, sources, model."""
    mock_result = MagicMock()
    mock_result.answer = "Revenue increased 15% YoY."
    mock_result.sources = ["10-K page 42"]
    mock_result.model = "local-rag"

    mock_rag = MagicMock()
    mock_rag.query.return_value = mock_result

    with patch("research.nlp.rag_pipeline.FinancialRAG", return_value=mock_rag):
        result = handle_tool_call(
            "research_filing",
            {"query": "What was AAPL revenue growth?"},
        )

    assert result["answer"] == "Revenue increased 15% YoY."
    assert "10-K page 42" in result["sources"]
    assert result["model"] == "local-rag"
