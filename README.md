# The Agentic Alpha Lab

AI-powered quantitative research platform with statistically validated agentic signals.

Six specialist AI agents analyze any stock and produce a consensus signal with confidence score. Human-in-the-loop approval gate. Compute-first, LLM-second architecture -- every number is calculated from real data before an LLM touches it.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Tests](https://img.shields.io/badge/tests-824_passing-brightgreen)
![Models](https://img.shields.io/badge/LLM-GPT--5_mini%20|%20Claude%20|%20Gemini%20|%20Llama%20|%20DeepSeek-violet)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

Six specialist agents work together like a real trading desk:

| Agent | Role |
|-------|------|
| **Quant Researcher** | Z-scores, mean reversion half-life, statistical arbitrage |
| **Technician** | RSI, MACD, Bollinger Bands, support/resistance |
| **Sentiment Analyst** | Earnings call NLP, news sentiment, FinBERT scoring |
| **Fundamentalist** | DCF, Gordon model, value ratios, margin of safety |
| **Macro Strategist** | VIX, yield curve, FRED macro indicators, regime detection |
| **Contrarian** | Short interest, crowding metrics, consensus divergence |

Each agent computes its own metrics from real market data. The LLM synthesizes their findings into a consensus signal with a confidence score. You approve, reject, or dig deeper.

---

## Architecture

**Backend**: Python 3.11+, FastAPI, Polars, DuckDB + Parquet storage, LanceDB for vector search

**Dashboard**: Next.js 16, React 19, Tailwind 4, Three.js (3D visualizations), Recharts, Zustand, Framer Motion

**LLM**: Multi-model via LiteLLM -- GPT-5-mini, GPT-4o, Claude, Gemini, Llama, DeepSeek

**Data**: YFinance for market data (SGX, NSE, NYSE -- no API key needed), FRED for macro indicators (optional)

---

## Quick Start

```bash
# Terminal 1 -- Backend
cd quant-researcher
conda activate zucol  # or any Python 3.11+ env
poetry install
PYTHONPATH=. uvicorn api.server:app --host 0.0.0.0 --port 8100 --reload

# Terminal 2 -- Dashboard
cd dashboard
npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Configuration

The Settings page ([http://localhost:3000/settings](http://localhost:3000/settings)) lets you:

- **Add API keys** -- OpenAI, Anthropic, Gemini, Groq, DeepSeek
- **Select default LLM model** -- choose from any supported provider
- **Customize agent system prompts** -- edit each agent's personality and focus

No `.env` file needed. Configure everything from the UI.

---

## Storage

| What | Where |
|------|-------|
| Market data | Parquet files (ZSTD compressed) + DuckDB analytical queries |
| Vector store | LanceDB (embedded, for RAG over SEC filings) |
| Agent state | In-memory (server lifetime), WebSocket streaming to dashboard |
| Settings/prompts | In-memory (restart resets to defaults) |

No external database required. Everything runs locally.

---

## Testing

```bash
PYTHONPATH=. pytest tests/
```

824 tests covering every module -- agents, strategies, backtesting, features, portfolio construction, and API endpoints.

---

## Dashboard Pages

| Page | What It Shows |
|------|---------------|
| **Monitor** | Morning brief, top signals, thought stream with live agent reasoning |
| **Chat** | Conversational deep-dive into any ticker or strategy |
| **Signals** | Active signals table with confidence, direction, and decay tracking |
| **Performance** | Strategy breakdown, agent accuracy, P&L attribution |
| **Backtest** | Run backtests with equity curves, drawdown charts, monthly heatmaps |
| **Agents** | View and manage the 6 specialist agents |
| **Settings** | API keys, model selection, system prompt customization |
| **Research** | Research notes and paper references |

---

## Markets Supported

Any ticker that YFinance supports:

- **SGX**: D05.SI (DBS), O39.SI (OCBC), U11.SI (UOB)
- **NSE**: RELIANCE.NS, TCS.NS, INFY.NS
- **NYSE/NASDAQ**: Any US ticker (AAPL, NVDA, TSLA, etc.)
- **Others**: LSE, HKEX, TSE -- anything YFinance covers

---

## Built With

[Claude Code](https://claude.com/claude-code) |
[Poetry](https://python-poetry.org/) |
[Next.js 16](https://nextjs.org/) |
[FastAPI](https://fastapi.tiangolo.com/) |
[Polars](https://pola.rs/) |
[DuckDB](https://duckdb.org/) |
[LiteLLM](https://litellm.ai/)

---

## License

MIT
