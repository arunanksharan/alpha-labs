# ⚡ The Agentic Alpha Lab

**AI-native quant research platform where agents discover alpha, reason out loud, and ask for your approval before acting.**

> 9 specialist agents backed by real computation. Morning briefs. Signal decay tracking. Human-on-the-loop approval. Built with Claude Code.

![Python](https://img.shields.io/badge/Python-28%2C230_lines-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-6%2C787_lines-blue)
![Tests](https://img.shields.io/badge/tests-808_passing-green)
![Models](https://img.shields.io/badge/LLM-OpenAI%20|%20Anthropic%20|%20Gemini%20|%20Groq-violet)

---

## What Is This?

Most AI-in-finance projects give you **LLM opinions**. This platform gives you **statistically validated signals backed by real computation**.

Inspired by [Virat Singh's ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) (50K+ stars), which shows 13 famous investors debating stocks. But Virat's project has no backtesting, no validation, no signal decay measurement, and no continuous operation.

**We start where Virat ends:**

| | Virat's ai-hedge-fund | Agentic Alpha Lab |
|---|---|---|
| Agents | 13 investor personas (LLM opinions) | 9 specialists (real computation + LLM synthesis) |
| Backtesting | None | Vectorized engine + deflated Sharpe validation |
| Signal decay | None | IC curves, half-life measurement |
| Risk management | Basic position limits | Kelly, VaR, Monte Carlo, circuit breakers |
| Continuous operation | Run once, read output | Daily/weekly autonomous cycles |
| Human interaction | Read terminal output | Morning brief + research chat + approval queue |
| Data sources | Paid API (Financial Datasets) | Free (YFinance, FRED, SEC EDGAR) |

---

## The Three Surfaces

When you open the dashboard, you see three interconnected experiences:

### 1. Morning Brief
*"Good morning, Parul. I ran the overnight scan across 50 tickers. Here's what matters."*

A personalized research brief with top conviction trades, watchlist items, portfolio health, and what the agent learned from recent performance. Each conviction comes with multi-agent reasoning — you can see exactly which agents agree and why.

### 2. Thought Stream
Watch agents reason in real-time:
```
16:42:33 │ 🔬 The Quant    │ Computing z-score for NVDA... z = -2.1 (entry zone)
16:42:35 │ 📊 Technician    │ RSI(14) = 28 — oversold. MACD crossover imminent.
16:42:37 │ 💬 Sentiment     │ Management tone shift +0.19 in Q&A vs prepared remarks
16:42:39 │ 😈 Contrarian    │ Short interest 1.2% — not crowded. No objection.
16:42:41 │ 🛡️ Risk Manager  │ Kelly sizing: $4,200 (4.2% of portfolio). VaR within limits.
16:42:43 │ 👤 Director      │ ⚡ NVDA LONG — 5/6 agents bullish, confidence 84%
```

### 3. Research Chat
Ask the agent anything — every response is backed by computation:
```
You: Why NVDA not AMD?

Director: Good question. Three key differences:
1. Signal strength: NVDA z=-2.1 (past entry) vs AMD z=-1.4 (not yet)
2. Fundamentals: NVDA revenue +94% YoY vs AMD +2%
3. Historical: NVDA at z=-2.0 wins 62% (47 instances). AMD: 41% (23 instances).
Bottom line: NVDA is oversold AND fundamentally strong. AMD is just oversold.

📊 Sources: Quant Engine, Technician   🔬 62% win | +2.1% avg | 12d hold
[Run Backtest] [Approve Trade] [Compare with peers]
```

---

## The 9 Specialist Agents

Each agent runs **real computation** from our 28K-line analytics engine, then (optionally) uses an LLM to synthesize the findings into natural language.

| Agent | What It Computes | Key Metric |
|-------|-----------------|------------|
| **🔬 The Quant** | Z-scores, factor models, backtests, signal decay, deflated Sharpe | "47 instances, 62% win rate, p=0.03" |
| **📊 The Technician** | RSI, MACD crossover, Bollinger %B, ATR | "RSI=28 oversold, MACD crossover imminent" |
| **😈 The Contrarian** | Crowding detection, GARCH vs realized vol, Monte Carlo stress test | "Top 10% momentum = crowded. Stress VaR 2.3x" |
| **💬 The Sentiment Analyst** | Loughran-McDonald sentiment, earnings call tone shift, key phrases | "Tone shift +0.19, 'AI infrastructure' mentioned 14x" |
| **📋 The Fundamentalist** | SEC EDGAR XBRL data, DCF valuation, margin of safety | "DCF $187, price $173, margin of safety 8%" |
| **🌐 The Macro Strategist** | FRED data, yield curve, VIX, regime detection | "Low vol regime — momentum favored" |
| **🛡️ Risk Manager** | Portfolio VaR, Kelly criterion, position limits, circuit breakers | "VaR +0.3%, Kelly $4,200" |
| **🏗️ Portfolio Architect** | HRP, Black-Litterman, risk parity, efficient frontier | "Optimal allocation via risk parity" |
| **👤 Research Director** | Orchestrates all agents, writes briefs, handles chat | "5/6 bullish. Three signals converge." |

Full prompt specifications for each agent: [`docs/prompts/`](docs/prompts/)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONSUMER LAYER                               │
│  Dashboard (Next.js)  │  Research Chat  │  CLI  │  MCP Server   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                  API LAYER (FastAPI)                              │
│  /research  /chat  /agents/run  /cycles  /models  /signals      │
│  WebSocket event streaming for real-time dashboard updates       │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│               AGENT ORCHESTRATION (LangGraph)                    │
│  Research → Risk → [Human Approval] → Validation → Decay → Report│
│  9 specialist agents · Daily/weekly autonomous cycles             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    ANALYTICS ENGINE                               │
│  Returns · Statistics · Signal Decay · Factor Models · Options   │
│  Microstructure · Backtesting · Validation · Risk · Portfolio    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      DATA LAYER                                  │
│  YFinance │ FRED │ SEC EDGAR │ DuckDB + Parquet │ LanceDB (RAG) │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Poetry (Python) or pip

### 1. Clone and install

```bash
git clone <repo-url> && cd quant-researcher

# Python backend
pip install -e ".[dev]"
# or: poetry install

# Dashboard
cd dashboard && npm install && cd ..
```

### 2. Configure API keys (optional)

```bash
cp .env.example .env
# Edit .env — add whichever keys you have:
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=AI...
```

**No API keys are required.** The platform works with computation-only agents. LLM keys enhance the synthesis layer.

### 3. Pre-fetch demo data (optional, for offline demo)

```bash
PYTHONPATH=. python scripts/prefetch_demo_data.py
```

### 4. Start the servers

```bash
# Terminal 1: Backend (port 8100)
PYTHONPATH=. uvicorn api.server:app --port 8100

# Terminal 2: Dashboard (port 3100)
cd dashboard && PORT=3100 npm run dev
```

### 5. Open the dashboard

Navigate to **http://localhost:3100**

---

## Dashboard Pages

| Page | URL | What You See |
|------|-----|-------------|
| **Monitor** | `/` | Morning brief + thought stream + equity curve + signal cards |
| **Chat** | `/chat` | Research conversation with citations and action buttons |
| **Signals** | `/signals` | Signal board with visual aging (green → yellow → red) |
| **Performance** | `/performance` | Win rate, strategy breakdown, agent accuracy, decay health |
| **Agents** | `/agents` | Agent timeline + 3D vol surface + 3D correlation heatmap |
| **Settings** | `/settings` | API config, demo/live toggle, model selector, prefetch |

---

## Multi-Model Support

Switch between LLM providers with a single dropdown in the sidebar:

| Provider | Models | Env Var |
|----------|--------|---------|
| **Anthropic** | Claude Sonnet 4, Claude Haiku 4.5, Claude Opus 4 | `ANTHROPIC_API_KEY` |
| **OpenAI** | GPT-4o, GPT-4o Mini, o3, o4 Mini | `OPENAI_API_KEY` |
| **Google** | Gemini 2.5 Flash, Gemini 2.5 Pro | `GEMINI_API_KEY` |
| **Groq** | Llama 3.3 70B, Llama 3.1 8B | `GROQ_API_KEY` |
| **DeepSeek** | DeepSeek V3 | `DEEPSEEK_API_KEY` |

Powered by [LiteLLM](https://github.com/BerriAI/litellm) — 100+ providers, unified interface.

```python
from core.llm import llm_call

response = llm_call("Analyze NVDA", model="claude-sonnet")  # Anthropic
response = llm_call("Analyze NVDA", model="gpt-4o")         # OpenAI
response = llm_call("Analyze NVDA", model="gemini-flash")   # Google
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/strategies` | List available strategies |
| `GET` | `/api/models` | List LLM models + API key status |
| `POST` | `/api/research` | Full research pipeline (sync) |
| `POST` | `/api/chat` | Research chat (grounded responses) |
| `POST` | `/api/agents/run` | Start multi-agent pipeline (async) |
| `POST` | `/api/agents/approve` | Approve/reject pending signals |
| `GET` | `/api/agents/status` | Agent system status |
| `POST` | `/api/cycles/run-daily` | Trigger daily research cycle |
| `POST` | `/api/cycles/run-weekly` | Trigger weekly review cycle |
| `POST` | `/api/backtest` | Quick backtest from CSV |
| `POST` | `/api/signal-decay` | IC curve analysis |
| `POST` | `/api/models/test` | Test a specific LLM model |
| `WS` | `/ws` | Real-time event stream |

### MCP Server (for AI agents)

7 tools exposed via Model Context Protocol:
- `research_strategy` — full pipeline
- `fetch_market_data` — OHLCV data
- `run_backtest` — backtest signals
- `analyze_sentiment` — financial text sentiment
- `compute_risk_metrics` — VaR, CVaR, Sharpe
- `analyze_signal_decay` — IC curve + half-life
- `research_filing` — RAG over SEC filings

---

## What's Inside (Module Guide)

### Analytics Engine
| Module | What It Does |
|--------|-------------|
| `analytics/returns.py` | Sharpe, Sortino, VaR, CVaR, drawdown, correlation, beta, alpha |
| `analytics/statistics.py` | ADF, KPSS, Hurst exponent, cointegration, half-life |
| `analytics/signal_decay.py` | IC curves, half-life, rolling IC, decay comparison |
| `analytics/factors.py` | Fama-French 3/5 factor, factor attribution, rolling exposure |
| `analytics/options.py` | Black-Scholes, Greeks, implied vol, GARCH forecasting |
| `analytics/microstructure.py` | VWAP, TWAP, Amihud illiquidity, Kyle's lambda |

### Strategies
| Module | What It Does |
|--------|-------------|
| `strategies/mean_reversion/` | Z-score + pairs trading (single-asset and cointegrated pairs) |
| `strategies/momentum/` | Cross-sectional 12-1 momentum (long top 20%, short bottom 20%) |
| `strategies/combiner.py` | Multi-strategy portfolio with optimal weighting |

### ML Pipeline
| Module | What It Does |
|--------|-------------|
| `models/training/labeling.py` | Triple barrier labeling + meta-labeling (López de Prado) |
| `models/training/cross_validation.py` | Purged K-fold CV (prevents financial data leakage) |
| `models/training/feature_importance.py` | MDI, MDA, SFI feature importance |
| `models/inference/signal_generator.py` | Walk-forward ML signal generation |
| `features/technical/indicators.py` | RSI, MACD, Bollinger, ATR, OBV (from scratch) |
| `features/store.py` | DuckDB-backed feature store |

### Risk & Portfolio
| Module | What It Does |
|--------|-------------|
| `risk/manager.py` | Position limits, exposure caps, VaR constraints |
| `risk/position_sizing/engine.py` | Kelly, risk parity, inverse vol, vol targeting |
| `risk/var/monte_carlo.py` | Monte Carlo VaR/CVaR, Cholesky-correlated portfolios |
| `risk/monitoring/circuit_breaker.py` | Drawdown monitor, configurable triggers |
| `portfolio/optimization/optimizer.py` | Markowitz, HRP, Black-Litterman, efficient frontier |

### Research (NLP/LLM)
| Module | What It Does |
|--------|-------------|
| `research/nlp/sentiment.py` | Loughran-McDonald sentiment, tone shift, drift tracking |
| `research/nlp/document_processor.py` | SEC filing chunking with section extraction |
| `research/nlp/rag_pipeline.py` | LanceDB vector store + Claude/GPT RAG |
| `research/reports/generator.py` | Automated HTML research reports |

### Backtesting & Validation
| Module | What It Does |
|--------|-------------|
| `backtest/engine/vectorized.py` | Polars-native vectorized backtester |
| `backtest/validation.py` | Deflated Sharpe, Bonferroni/BH, CPCV, permutation tests |
| `backtest/execution_model.py` | Almgren-Chriss market impact, realistic costs |
| `backtest/reports/tearsheet.py` | Equity curve, drawdown, monthly heatmap |

### Execution
| Module | What It Does |
|--------|-------------|
| `execution/algorithms/vwap_twap.py` | VWAP/TWAP order scheduling |
| `execution/algorithms/paper_trader.py` | Simulated paper trading |

---

## Project Stats

| Metric | Value |
|--------|-------|
| Python | 28,230 lines |
| TypeScript | 6,787 lines |
| **Total** | **35,017 lines** |
| Files | 188 |
| Tests | 808 passing |
| Agent prompts | 9 documented |
| API endpoints | 14 |
| MCP tools | 7 |

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/prompts/`](docs/prompts/) | All 9 agent prompt specifications |
| [`docs/00-genesis-conversation.md`](docs/00-genesis-conversation.md) | Project founding decisions |
| [`docs/02-architecture-decisions.md`](docs/02-architecture-decisions.md) | ADRs (8 decisions documented) |
| [`docs/10-adr-agent-native.md`](docs/10-adr-agent-native.md) | Agent-native architecture rationale |
| [`docs/12-refined-vision.md`](docs/12-refined-vision.md) | The Living Lab vision |
| [`docs/13-living-lab-roadmap.md`](docs/13-living-lab-roadmap.md) | Detailed build roadmap |

---

## Tech Stack

### Backend
- **Python 3.12+** — core language
- **Polars** — DataFrames (5-10x faster than Pandas)
- **DuckDB + Parquet** — analytical storage
- **LanceDB** — vector database for RAG
- **FastAPI** — API server with WebSocket streaming
- **LiteLLM** — multi-model LLM routing (100+ providers)
- **LangGraph** — multi-agent orchestration

### Frontend
- **Next.js 15** — React framework
- **Tailwind CSS** — utility-first styling
- **shadcn/ui patterns** — Radix + CVA
- **Recharts** — 2D financial charts
- **Three.js + React Three Fiber** — 3D visualizations
- **Framer Motion** — animations
- **Zustand** — client state management

### Design
- **Dark theme** — zinc-950 background
- **Violet primary** — #8b5cf6
- **Geist font** — Sans + Mono
- Follows the [Avashi Design System](https://github.com/kuzushi-labs/avashi)

---

## Running Tests

```bash
# All tests
PYTHONPATH=. pytest tests/

# Specific module
PYTHONPATH=. pytest tests/test_specialist_agents.py -v

# With coverage
PYTHONPATH=. pytest tests/ --cov=. --cov-report=html
```

---

## Built With Claude Code

This entire platform — 35,000+ lines of production code — was built in a single extended session using [Claude Code](https://claude.ai/claude-code), Anthropic's CLI for Claude.

The development followed a 13-week roadmap accelerated through AI-assisted development:
- Week 1-4: Data pipeline, strategies, risk management, factor models
- Week 5-8: ML pipeline, signal decay, NLP/RAG, backtest validation
- Week 9-11: Options pricing, microstructure, portfolio optimization
- Week 12-13: Agent-native architecture, multi-agent system, dashboard

---

## License

MIT

---

## Disclaimer

This project is for **educational and research purposes only**. It is not intended for real trading or investment decisions. The authors are not responsible for any financial losses incurred from using this software. Past performance of any strategy or signal does not guarantee future results.
