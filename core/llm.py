"""Multi-model LLM routing via LiteLLM.

Supports OpenAI, Anthropic (Claude), Google (Gemini), and 100+ providers
through a single unified interface. Switch models via config or per-call.

Usage:
    from core.llm import llm_call, get_available_models

    # Uses default model from config
    response = llm_call("Analyze NVDA's latest earnings")

    # Override model per-call
    response = llm_call("Analyze NVDA", model="openai/gpt-4o")
    response = llm_call("Analyze NVDA", model="anthropic/claude-sonnet-4-20250514")
    response = llm_call("Analyze NVDA", model="gemini/gemini-2.5-flash")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Model aliases for convenience
MODEL_ALIASES: dict[str, str] = {
    # Anthropic
    "claude-opus": "anthropic/claude-opus-4-20250514",
    "claude-sonnet": "anthropic/claude-sonnet-4-20250514",
    "claude-haiku": "anthropic/claude-haiku-4-5-20251001",
    # OpenAI
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "o3": "openai/o3",
    "o4-mini": "openai/o4-mini",
    # Google Gemini
    "gemini-flash": "gemini/gemini-2.5-flash",
    "gemini-pro": "gemini/gemini-2.5-pro",
    # Open source (via Groq)
    "llama-70b": "groq/llama-3.3-70b-versatile",
    "llama-8b": "groq/llama-3.1-8b-instant",
    # DeepSeek
    "deepseek": "deepseek/deepseek-chat",
}

# Default model (can be overridden via env var)
DEFAULT_MODEL = os.environ.get("QR_DEFAULT_MODEL", "claude-sonnet")


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    model: str
    provider: str
    tokens_used: int
    cost_usd: float | None = None
    raw: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
        }


def _resolve_model(model: str) -> str:
    """Resolve model alias to full litellm model string."""
    return MODEL_ALIASES.get(model, model)


def _detect_provider(model: str) -> str:
    """Extract provider name from model string."""
    if "/" in model:
        return model.split("/")[0]
    for alias, full in MODEL_ALIASES.items():
        if alias == model:
            return full.split("/")[0]
    return "unknown"


def check_api_keys() -> dict[str, bool]:
    """Check which provider API keys are configured."""
    return {
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "gemini": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
        "groq": bool(os.environ.get("GROQ_API_KEY")),
        "deepseek": bool(os.environ.get("DEEPSEEK_API_KEY")),
    }


def get_available_models() -> list[dict[str, str]]:
    """Return models that have API keys configured."""
    keys = check_api_keys()
    available = []
    for alias, full_model in MODEL_ALIASES.items():
        provider = full_model.split("/")[0]
        has_key = keys.get(provider, False)
        available.append({
            "alias": alias,
            "model": full_model,
            "provider": provider,
            "available": has_key,
        })
    return available


def llm_call(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    json_mode: bool = False,
) -> LLMResponse:
    """Call any LLM through LiteLLM's unified interface.

    Args:
        prompt: The user message / question.
        model: Model alias or full litellm model string. Defaults to QR_DEFAULT_MODEL.
        system_prompt: Optional system message for context setting.
        temperature: Sampling temperature (0.0-1.0).
        max_tokens: Maximum response tokens.
        json_mode: Request JSON output (supported by some models).

    Returns:
        LLMResponse with content, model, provider, tokens, cost.

    Raises:
        ValueError: If no API key is configured for the requested provider.
    """
    try:
        import litellm
    except ImportError:
        raise ImportError("litellm not installed. Run: pip install litellm")

    # Suppress litellm's verbose logging
    litellm.suppress_debug_info = True

    resolved = _resolve_model(model or DEFAULT_MODEL)
    provider = _detect_provider(resolved)

    # Build messages
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Call kwargs
    kwargs: dict[str, Any] = {
        "model": resolved,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    logger.info("LLM call: model=%s provider=%s prompt_len=%d", resolved, provider, len(prompt))

    try:
        response = litellm.completion(**kwargs)
    except Exception as e:
        error_msg = str(e)
        if "AuthenticationError" in error_msg or "API key" in error_msg.lower():
            raise ValueError(
                f"No API key configured for {provider}. "
                f"Set the appropriate env var (e.g., {provider.upper()}_API_KEY)"
            ) from e
        raise

    # Extract response
    content = response.choices[0].message.content or ""
    usage = response.usage
    tokens = (usage.total_tokens if usage else 0)

    # Cost tracking (litellm provides this)
    cost = None
    try:
        cost = litellm.completion_cost(completion_response=response)
    except Exception:
        pass

    return LLMResponse(
        content=content,
        model=resolved,
        provider=provider,
        tokens_used=tokens,
        cost_usd=cost,
        raw=response.model_dump() if hasattr(response, "model_dump") else {},
    )


def llm_call_safe(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    fallback: str = "LLM unavailable — using computation-only analysis.",
    **kwargs,
) -> LLMResponse:
    """Like llm_call but returns fallback instead of raising on failure."""
    try:
        return llm_call(prompt, model=model, system_prompt=system_prompt, **kwargs)
    except Exception as e:
        logger.warning("LLM call failed (%s), using fallback: %s", e, fallback)
        return LLMResponse(
            content=fallback,
            model=model or DEFAULT_MODEL,
            provider="fallback",
            tokens_used=0,
        )
