"""Tests for core/llm.py — multi-model routing via LiteLLM."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.llm import (
    MODEL_ALIASES,
    LLMResponse,
    _detect_provider,
    _resolve_model,
    check_api_keys,
    get_available_models,
    llm_call,
    llm_call_safe,
)


class TestModelResolution:
    def test_alias_resolves(self) -> None:
        assert _resolve_model("claude-sonnet") == "anthropic/claude-sonnet-4-20250514"
        assert _resolve_model("gpt-4o") == "openai/gpt-4o"
        assert _resolve_model("gemini-flash") == "gemini/gemini-2.5-flash"

    def test_full_model_passthrough(self) -> None:
        assert _resolve_model("openai/gpt-4o-mini") == "openai/gpt-4o-mini"

    def test_unknown_alias_passthrough(self) -> None:
        assert _resolve_model("some-custom/model") == "some-custom/model"


class TestProviderDetection:
    def test_from_full_model(self) -> None:
        assert _detect_provider("openai/gpt-4o") == "openai"
        assert _detect_provider("anthropic/claude-sonnet-4-20250514") == "anthropic"
        assert _detect_provider("gemini/gemini-2.5-flash") == "gemini"

    def test_from_alias(self) -> None:
        assert _detect_provider("claude-sonnet") == "anthropic"
        assert _detect_provider("gpt-4o") == "openai"


class TestCheckApiKeys:
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test", "OPENAI_API_KEY": ""}, clear=False)
    def test_detects_configured_keys(self) -> None:
        keys = check_api_keys()
        assert keys["anthropic"] is True
        assert keys["openai"] is False


class TestGetAvailableModels:
    def test_returns_list(self) -> None:
        models = get_available_models()
        assert isinstance(models, list)
        assert len(models) == len(MODEL_ALIASES)

    def test_model_has_required_fields(self) -> None:
        models = get_available_models()
        for m in models:
            assert "alias" in m
            assert "model" in m
            assert "provider" in m
            assert "available" in m


class TestLLMResponse:
    def test_to_json(self) -> None:
        r = LLMResponse(content="test", model="gpt-4o", provider="openai", tokens_used=100)
        j = r.to_json()
        assert j["content"] == "test"
        assert j["model"] == "gpt-4o"
        assert j["tokens_used"] == 100


class TestLLMCall:
    @patch("litellm.completion_cost", return_value=0.001)
    @patch("litellm.completion")
    def test_call_with_alias(self, mock_completion: MagicMock, mock_cost: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Analysis complete"))]
        mock_response.usage = MagicMock(total_tokens=50)
        mock_response.model_dump.return_value = {}
        mock_completion.return_value = mock_response

        result = llm_call("Analyze AAPL", model="gpt-4o")

        assert result.content == "Analysis complete"
        assert result.provider == "openai"
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4o"

    @patch("litellm.completion_cost", return_value=0.0)
    @patch("litellm.completion")
    def test_call_with_system_prompt(self, mock_completion: MagicMock, mock_cost: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Yes"))]
        mock_response.usage = MagicMock(total_tokens=10)
        mock_response.model_dump.return_value = {}
        mock_completion.return_value = mock_response

        llm_call("Is NVDA bullish?", model="claude-sonnet", system_prompt="You are a quant analyst.")

        call_kwargs = mock_completion.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


class TestLLMCallSafe:
    @patch("litellm.completion")
    def test_returns_fallback_on_error(self, mock_completion: MagicMock) -> None:
        mock_completion.side_effect = Exception("API down")

        result = llm_call_safe("test", fallback="No LLM available")

        assert result.content == "No LLM available"
        assert result.provider == "fallback"
        assert result.tokens_used == 0
