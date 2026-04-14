"""Voice research pipeline — Deepgram STT → LLM with tools → text response.

Uses Pipecat's pipeline architecture for composable, extensible voice processing.
No TTS — text responses only (cost-effective for quant research).

Architecture:
    Browser mic (PCM 16kHz) → WebSocket → Deepgram STT → LLM (GPT-5-mini)
    → Tool calls (research_ticker, run_backtest, fetch_signals)
    → Text response streamed back to browser
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool definitions for the LLM
# ---------------------------------------------------------------------------

RESEARCH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "research_ticker",
            "description": "Analyze a stock ticker using 6 specialist AI agents (quant, technician, sentiment, fundamentalist, macro strategist, contrarian). Returns consensus signal, confidence, and reasoning from each agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., D05.SI for DBS Singapore, RELIANCE.NS for Reliance India, AAPL for Apple US)",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_backtest",
            "description": "Run a backtest for a trading strategy on a specific ticker. Returns total return, Sharpe ratio, win rate, and equity curve.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "strategy": {"type": "string", "enum": ["mean_reversion", "momentum"], "description": "Trading strategy to test"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format (default: 2023-01-01)"},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_signals",
            "description": "Get the latest trading signals for all tickers in the research universe. Shows which stocks are signaling long, short, or neutral.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

SYSTEM_PROMPT = """You are the voice-driven Research Director for a quantitative hedge fund platform called Agentic Alpha Lab.

You help quant researchers analyze stocks using voice commands. You have access to:
1. research_ticker — runs 6 specialist AI agents (Quant, Technician, Sentiment, Fundamentalist, Macro, Contrarian) on any ticker
2. run_backtest — backtests strategies (mean reversion, momentum) on historical data
3. fetch_signals — shows current signals for all tracked tickers

When a user asks about a stock, ALWAYS use research_ticker first.
When they ask to "run a backtest" or "test a strategy", use run_backtest.
When they ask "what's interesting" or "any signals", use fetch_signals.

Be concise and confident. Lead with the signal (BULLISH/BEARISH/NEUTRAL), then the key numbers.
Speak like a senior analyst briefing a portfolio manager — no filler, just insights.

Supported tickers: D05.SI (DBS), O39.SI (OCBC), U11.SI (UOB), C6L.SI (SIA),
RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, AAPL, NVDA, MSFT, GOOG, META, AMZN, TSLA, SBIN.NS, ITC.NS"""


# ---------------------------------------------------------------------------
# Tool execution handlers
# ---------------------------------------------------------------------------


async def handle_research_ticker(arguments: dict) -> dict:
    """Execute the research_ticker tool using the existing ResearchDirector."""
    ticker = arguments.get("ticker", "").strip().upper()
    if not ticker:
        return {"error": "No ticker provided"}

    try:
        from agents.specialists.research_director import ResearchDirector
        director = ResearchDirector()

        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = "2023-01-01"

        # Run in thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: director.answer_question(f"Analyze {ticker}", context={}),
        )

        return {
            "answer": result.get("answer", ""),
            "citations": result.get("citations", [])[:3],
            "actions": result.get("actions", []),
        }
    except Exception as e:
        logger.error("research_ticker failed: %s", e)
        return {"error": str(e)}


async def handle_run_backtest(arguments: dict) -> dict:
    """Execute run_backtest using the existing orchestrator."""
    ticker = arguments.get("ticker", "").strip().upper()
    strategy = arguments.get("strategy", "mean_reversion")
    start_date = arguments.get("start_date", "2023-06-01")

    if not ticker:
        return {"error": "No ticker provided"}

    try:
        from core.orchestrator import ResearchOrchestrator

        loop = asyncio.get_event_loop()
        orchestrator = ResearchOrchestrator()
        result = await loop.run_in_executor(
            None,
            lambda: orchestrator.run(ticker, strategy, start_date, datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        )
        j = result.to_json()
        bt = j.get("backtest", {})

        return {
            "ticker": ticker,
            "strategy": strategy,
            "total_return": f"{bt.get('total_return', 0) * 100:.1f}%",
            "sharpe_ratio": f"{bt.get('sharpe_ratio', 0):.2f}",
            "win_rate": f"{bt.get('win_rate', 0) * 100:.0f}%",
            "max_drawdown": f"{bt.get('max_drawdown', 0) * 100:.1f}%",
            "signals_count": j.get("signals_count", 0),
        }
    except Exception as e:
        logger.error("run_backtest failed: %s", e)
        return {"error": str(e)}


async def handle_fetch_signals(arguments: dict) -> dict:
    """Fetch current signals from the universe cache."""
    try:
        import json as json_mod
        from pathlib import Path

        cache_dir = Path("data/cache/research")
        signals = []

        if cache_dir.exists():
            for f in cache_dir.glob("*__mean_reversion.json"):
                try:
                    data = json_mod.loads(f.read_text())
                    bt = data.get("backtest", {})
                    ticker = data.get("ticker", f.stem.split("__")[0])
                    ret = bt.get("total_return", 0)
                    direction = "LONG" if ret > 0.01 else "SHORT" if ret < -0.01 else "NEUTRAL"
                    signals.append({
                        "ticker": ticker,
                        "direction": direction,
                        "return": f"{ret * 100:.1f}%",
                        "sharpe": f"{bt.get('sharpe_ratio', 0):.2f}",
                    })
                except Exception:
                    pass

        signals.sort(key=lambda s: abs(float(s["return"].replace("%", ""))), reverse=True)
        return {"signals": signals[:10], "count": len(signals)}
    except Exception as e:
        return {"error": str(e)}


TOOL_HANDLERS = {
    "research_ticker": handle_research_ticker,
    "run_backtest": handle_run_backtest,
    "fetch_signals": handle_fetch_signals,
}


# ---------------------------------------------------------------------------
# Voice WebSocket handler (Deepgram STT → LLM with tools → text stream)
# ---------------------------------------------------------------------------


async def handle_voice_session(websocket, send_json):
    """Run a complete voice research session.

    This is the core pipeline:
    1. Receive audio chunks from browser via WebSocket
    2. Stream to Deepgram for real-time transcription
    3. When user finishes speaking, send transcript to LLM with tools
    4. Execute tool calls (research, backtest, signals)
    5. Stream the final text response back to browser

    Args:
        websocket: FastAPI WebSocket connection
        send_json: Async callable to send JSON to the client
    """
    import httpx

    deepgram_key = os.environ.get("DEEPGRAM_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if not deepgram_key:
        await send_json({"type": "error", "message": "DEEPGRAM_API_KEY not configured"})
        return

    if not openai_key:
        await send_json({"type": "error", "message": "OPENAI_API_KEY not configured"})
        return

    await send_json({"type": "ready", "message": "Voice pipeline ready (Deepgram Nova-3 + GPT-5-mini)"})

    # Track conversation context
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    transcript_buffer = ""

    # ── Deepgram WebSocket connection ──
    import websockets

    dg_url = (
        "wss://api.deepgram.com/v1/listen"
        "?model=nova-3"
        "&language=en"
        "&smart_format=true"
        "&interim_results=true"
        "&endpointing=300"
        "&utterance_end_ms=1500"
        "&punctuate=true"
    )

    dg_headers = {"Authorization": f"Token {deepgram_key}"}

    try:
        async with websockets.connect(dg_url, additional_headers=dg_headers) as dg_ws:
            # ── Task 1: Forward browser audio to Deepgram ──
            async def forward_audio():
                nonlocal transcript_buffer
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            await dg_ws.send(data["bytes"])
                        elif "text" in data:
                            msg = json.loads(data["text"])
                            if msg.get("type") == "stop":
                                # User stopped speaking — close Deepgram connection
                                await dg_ws.send(json.dumps({"type": "CloseStream"}))
                                break
                except Exception:
                    pass

            # ── Task 2: Receive transcriptions from Deepgram ──
            async def receive_transcriptions():
                nonlocal transcript_buffer
                try:
                    async for msg in dg_ws:
                        data = json.loads(msg)

                        if data.get("type") == "Results":
                            alt = data.get("channel", {}).get("alternatives", [{}])[0]
                            transcript = alt.get("transcript", "")
                            is_final = data.get("is_final", False)
                            speech_final = data.get("speech_final", False)

                            if transcript:
                                if is_final:
                                    transcript_buffer = transcript
                                    await send_json({
                                        "type": "transcript",
                                        "text": transcript,
                                        "is_final": True,
                                    })
                                else:
                                    await send_json({
                                        "type": "transcript",
                                        "text": transcript,
                                        "is_final": False,
                                    })

                                if speech_final and transcript_buffer:
                                    # User finished speaking — process with LLM
                                    await process_with_llm(
                                        transcript_buffer,
                                        messages,
                                        openai_key,
                                        send_json,
                                    )
                                    transcript_buffer = ""

                        elif data.get("type") == "UtteranceEnd":
                            if transcript_buffer:
                                await process_with_llm(
                                    transcript_buffer,
                                    messages,
                                    openai_key,
                                    send_json,
                                )
                                transcript_buffer = ""

                except websockets.exceptions.ConnectionClosed:
                    pass
                except Exception as e:
                    logger.error("Deepgram receive error: %s", e)

            # Run both tasks concurrently
            await asyncio.gather(
                forward_audio(),
                receive_transcriptions(),
                return_exceptions=True,
            )

    except Exception as e:
        logger.error("Voice session error: %s", e)
        await send_json({"type": "error", "message": str(e)})


async def process_with_llm(
    user_text: str,
    messages: list[dict],
    openai_key: str,
    send_json,
) -> None:
    """Process transcribed text through LLM with tool calling.

    Handles the full loop: LLM → tool call → tool result → LLM → response.
    Streams the final text response token by token.
    """
    import httpx

    messages.append({"role": "user", "content": user_text})
    await send_json({"type": "processing", "message": f"Analyzing: {user_text}"})

    # ── Call LLM with tools ──
    max_iterations = 3  # Prevent infinite tool call loops

    for iteration in range(max_iterations):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Determine model
                model = os.environ.get("QR_DEFAULT_MODEL", "gpt-5-mini")
                # Map alias to full model name
                model_map = {
                    "gpt-5-mini": "gpt-5-mini",
                    "gpt-4o": "gpt-4o",
                    "gpt-4o-mini": "gpt-4o-mini",
                }
                api_model = model_map.get(model, model)

                body = {
                    "model": api_model,
                    "messages": messages,
                    "tools": RESEARCH_TOOLS,
                    "stream": True,
                }

                # GPT-5 doesn't support temperature
                if "gpt-5" not in api_model:
                    body["temperature"] = 0.3

                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=60.0,
                )

                if response.status_code != 200:
                    error_text = response.text
                    await send_json({"type": "error", "message": f"LLM error: {error_text[:200]}"})
                    return

                # ── Parse streaming response ──
                full_content = ""
                tool_calls = []  # Accumulate tool calls
                current_tool_call = None

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        finish_reason = chunk["choices"][0].get("finish_reason")

                        # Text content
                        if "content" in delta and delta["content"]:
                            full_content += delta["content"]
                            await send_json({
                                "type": "response_chunk",
                                "text": delta["content"],
                            })

                        # Tool calls
                        if "tool_calls" in delta:
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                if tc.get("id"):
                                    current_tool_call = {
                                        "id": tc["id"],
                                        "function": {"name": "", "arguments": ""},
                                    }
                                    while len(tool_calls) <= idx:
                                        tool_calls.append(None)
                                    tool_calls[idx] = current_tool_call

                                if current_tool_call and tc.get("function"):
                                    if "name" in tc["function"]:
                                        current_tool_call["function"]["name"] += tc["function"]["name"]
                                    if "arguments" in tc["function"]:
                                        current_tool_call["function"]["arguments"] += tc["function"]["arguments"]

                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

                # ── Handle tool calls ──
                active_tool_calls = [tc for tc in tool_calls if tc is not None]

                if active_tool_calls:
                    # Add assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": full_content or None,
                        "tool_calls": [
                            {"id": tc["id"], "type": "function", "function": tc["function"]}
                            for tc in active_tool_calls
                        ],
                    })

                    # Execute each tool
                    for tc in active_tool_calls:
                        func_name = tc["function"]["name"]
                        try:
                            func_args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            func_args = {}

                        await send_json({
                            "type": "tool_call",
                            "tool": func_name,
                            "args": func_args,
                        })

                        handler = TOOL_HANDLERS.get(func_name)
                        if handler:
                            result = await handler(func_args)
                        else:
                            result = {"error": f"Unknown tool: {func_name}"}

                        await send_json({
                            "type": "tool_result",
                            "tool": func_name,
                            "result": result,
                        })

                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result),
                        })

                    # Continue loop — LLM will process tool results
                    continue

                else:
                    # No tool calls — we have the final response
                    if full_content:
                        messages.append({"role": "assistant", "content": full_content})
                        await send_json({
                            "type": "response_complete",
                            "text": full_content,
                        })
                    return

        except Exception as e:
            logger.error("LLM call failed: %s", e)
            await send_json({"type": "error", "message": f"LLM error: {str(e)}"})
            return

    await send_json({"type": "error", "message": "Too many tool call iterations"})
