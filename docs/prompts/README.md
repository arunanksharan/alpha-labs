# Agent Prompts — The Agentic Alpha Lab

This folder documents every prompt used by the 9 specialist agents. Each agent combines a **system prompt** (defining its persona and analytical framework) with **computed data** (real metrics from our analytics engine) to produce grounded, citation-backed research.

## How Prompts Work in Our System

Unlike Virat's ai-hedge-fund where agents are mostly LLM-based, our agents compute first and optionally use LLMs to synthesize. The flow is:

```
1. Agent computes metrics (z-score, RSI, DCF, etc.) — pure Python, no LLM
2. Agent formats computed data into a structured context
3. (Optional) LLM receives: system prompt + computed data → synthesizes insight
4. Agent returns: AgentFinding with signal, confidence, reasoning, thoughts
```

The prompts below are used in step 3 when LLM synthesis is enabled. Without an LLM, agents still produce signals based on pure computation (step 1-2).

## Agent Prompts

| Agent | Prompt File | LLM Required? |
|-------|------------|---------------|
| The Quant | [the_quant.md](the_quant.md) | No — pure statistical computation |
| The Technician | [the_technician.md](the_technician.md) | No — rule-based indicator scoring |
| The Contrarian | [the_contrarian.md](the_contrarian.md) | No — crowding + vol computation |
| The Sentiment Analyst | [the_sentiment_analyst.md](the_sentiment_analyst.md) | Optional — enhances with LLM interpretation |
| The Fundamentalist | [the_fundamentalist.md](the_fundamentalist.md) | Optional — enhances DCF interpretation |
| The Macro Strategist | [the_macro_strategist.md](the_macro_strategist.md) | Optional — enhances regime interpretation |
| Risk Manager | [risk_manager.md](risk_manager.md) | No — pure VaR/Kelly computation |
| Portfolio Architect | [portfolio_architect.md](portfolio_architect.md) | No — optimization computation |
| Research Director | [research_director.md](research_director.md) | Optional — enhances synthesis and chat |

## Multi-Model Support

All LLM-enhanced prompts work with any provider via LiteLLM:
- `claude-sonnet` (Anthropic) — best for nuanced financial reasoning
- `gpt-4o` (OpenAI) — strong general analysis
- `gemini-flash` (Google) — fastest, good for real-time synthesis
- `llama-70b` (Groq) — open source, fast inference
- `deepseek` — cost-effective alternative

Set `QR_DEFAULT_MODEL` in `.env` or pass `model=` per-call.
