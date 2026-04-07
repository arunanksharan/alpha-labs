# The Living Lab — Detailed Build Roadmap

## What We're Building

A quant research partner that continuously discovers alpha, reasons out loud, and asks for human approval before acting. Three surfaces: Morning Brief, Thought Stream, Research Chat. Nine specialist agents backed by real computation.

## What Already Exists (Reuse, Don't Rewrite)

| Module | Lines | Reused By |
|--------|-------|-----------|
| `analytics/returns.py` (Sharpe, Sortino, VaR, etc.) | 314 | The Quant agent |
| `analytics/statistics.py` (ADF, cointegration, Hurst) | 290 | The Quant agent |
| `analytics/signal_decay.py` (IC curves, half-life) | 348 | The Quant agent |
| `analytics/factors.py` (Fama-French, IC, factor attribution) | 282 | The Quant agent |
| `analytics/options.py` (Black-Scholes, Greeks, IV, GARCH) | 292 | The Contrarian agent |
| `analytics/microstructure.py` (VWAP, Amihud, Kyle's λ) | 252 | Execution Strategist |
| `features/technical/indicators.py` (RSI, MACD, Bollinger, ATR, OBV) | 273 | The Technician agent |
| `features/technical/zscore.py`, `momentum.py`, `spread.py` | 160 | The Quant, Technician |
| `strategies/mean_reversion/`, `momentum/`, `combiner.py` | 688 | Research Director |
| `risk/manager.py`, `position_sizing/`, `var/`, `monitoring/` | 891 | Risk Manager agent |
| `portfolio/optimization/optimizer.py` (HRP, BL, MV) | 671 | Portfolio Architect |
| `backtest/engine/vectorized.py`, `validation.py` | 860 | The Quant agent |
| `research/nlp/sentiment.py` | 331 | Sentiment Analyst |
| `research/nlp/document_processor.py`, `rag_pipeline.py` | 510 | The Fundamentalist |
| `research/reports/generator.py` | 300 | Research Director |
| `models/training/labeling.py`, `cross_validation.py` | 520 | The Quant agent |
| `models/inference/signal_generator.py` | 282 | The Quant agent |
| `execution/algorithms/vwap_twap.py`, `paper_trader.py` | 543 | Execution Strategist |
| `core/serialization.py`, `adapters.py`, `orchestrator.py` | 696 | API layer |
| `api/server.py`, `mcp_server.py`, `events.py` | 481 | Backend |

**Total reusable: ~8,984 lines of tested, production code.**

---

## Build Phases

### Phase A: Specialist Agents (Backend — Python)

Rewrite the 5 generic agent nodes (`agents/nodes.py`) into 9 specialist agents, each backed by real computation from our analytics engine.

#### A1: `agents/specialists/the_quant.py`
The statistical edge-finder. Computes z-scores, factor exposures, signal decay, historical win rates.

**What it does on each call:**
1. Compute rolling z-scores for the ticker (calls `ZScoreFeature`)
2. Compute momentum rank across universe (calls `MomentumFeature`)
3. Compute factor exposures (calls `FamaFrenchModel.regression()`)
4. If z-score passes threshold: run historical backtest of similar signals
5. Compute signal decay (calls `SignalDecayAnalyzer.compute_ic_curve()`)
6. Compute deflated Sharpe across historical instances (calls `BacktestValidator`)

**Output:** Structured finding with signal, confidence, historical stats, and reasoning text.

**Emits thoughts:**
- "Computing z-score for NVDA... z = -2.1 (past -2.0 entry threshold)"
- "Historical: 47 similar instances, 62% win rate, +2.1% avg return"
- "Deflated Sharpe significant at p=0.03 — this is a real edge"

#### A2: `agents/specialists/the_fundamentalist.py`
Reads SEC filings, computes intrinsic value, checks margin of safety.

**What it does:**
1. Fetch latest 10-K/10-Q via `EdgarConnector.fetch_company_facts()`
2. Extract key financials: revenue, earnings, FCF, margins
3. Run simplified DCF (3-stage: growth → transition → terminal)
4. Compute margin of safety = (intrinsic_value - market_price) / intrinsic_value
5. RAG query: "What changed in the latest filing vs prior year?"
6. Check earnings consistency (trend over 4+ quarters)

**Emits thoughts:**
- "Reading NVDA 10-K filed 2024-10-31..."
- "Revenue: $60.9B (+94% YoY), Gross margin: 72.7%"
- "DCF intrinsic value: $187. Current price: $173. Margin of safety: 8%"

#### A3: `agents/specialists/the_technician.py`
Chart pattern recognition and technical indicator analysis.

**What it does:**
1. Compute RSI, MACD, Bollinger Bands, ATR, OBV (calls `indicators.py`)
2. Identify oversold/overbought (RSI < 30 or > 70)
3. Detect MACD crossovers (bullish/bearish)
4. Check Bollinger Band position (%B)
5. Volume confirmation (OBV trend)

**Emits thoughts:**
- "RSI(14) = 28 — oversold territory"
- "MACD crossover imminent (MACD approaching signal line from below)"
- "Price at lower Bollinger Band, %B = 0.05 — extreme"

#### A4: `agents/specialists/the_sentiment_analyst.py`
NLP analysis of earnings calls, news, and filings.

**What it does:**
1. Analyze recent earnings call transcript (calls `FinancialSentimentAnalyzer`)
2. Detect management tone shift (prepared remarks vs Q&A)
3. Track sentiment drift across quarterly calls
4. Extract forward guidance keywords
5. Generate sentiment signal with key phrases

**Emits thoughts:**
- "Analyzing Q3 2024 earnings call..."
- "Management tone: +0.31 (bullish). 'AI infrastructure' mentioned 14x vs 3x last year"
- "CEO more confident in Q&A than prepared remarks (tone shift: +0.19)"

#### A5: `agents/specialists/the_macro_strategist.py`
Macro environment and regime analysis.

**What it does:**
1. Fetch macro data via `FREDConnector` (yield curve, VIX, unemployment)
2. Compute yield curve spread (10Y-2Y) — inversion check
3. Detect market regime (low/high vol, trending/mean-reverting)
4. Check sector rotation signals
5. Assess how macro environment affects the current strategy

**Emits thoughts:**
- "Yield curve spread: +0.45% (not inverted, no recession signal)"
- "VIX at 14.2 — low volatility regime"
- "Regime: bullish momentum. Mean reversion underperforms in this environment by -1.2%"

#### A6: `agents/specialists/the_contrarian.py`
Looks for crowded trades, tail risks, and vol anomalies.

**What it does:**
1. Check implied vs realized vol (calls `analytics/options.py`)
2. Assess if trade is crowded (momentum factor — if everyone is long, be cautious)
3. Compute tail risk metrics (Monte Carlo VaR stress test)
4. Look for asymmetric payoff opportunities

**Emits thoughts:**
- "NVDA implied vol: 42% vs realized vol: 28%. Premium of 14% — market pricing in uncertainty"
- "Short interest: 1.2% — not crowded"
- "Stress test: 2x vol shock would cause -8.2% loss. Asymmetric? No — risk/reward is balanced"

#### A7: `agents/specialists/risk_manager.py`
Portfolio-level risk evaluation. Can VETO signals.

**What it does:**
1. Compute portfolio VaR with proposed new position
2. Check position size limits (max 10% per position)
3. Check sector exposure limits (max 40% per sector)
4. Check correlation with existing positions
5. Apply circuit breakers if drawdown exceeds threshold
6. Size position using Kelly criterion

**Emits thoughts:**
- "Adding NVDA long: portfolio VaR changes from -1.8% to -2.1% (within 3% limit)"
- "Sector tech exposure would be 36% (within 40% limit)"
- "Kelly sizing: 4.2% = $4,200 on $100K portfolio"

#### A8: `agents/specialists/portfolio_architect.py`
Constructs optimal portfolio from approved signals.

**What it does:**
1. Collect all approved signals
2. Run HRP optimization (calls `PortfolioOptimizer.hierarchical_risk_parity()`)
3. Compare with risk parity allocation
4. Compute rebalancing trades needed
5. Estimate turnover and transaction costs

#### A9: `agents/specialists/research_director.py`
The orchestrator — the "confident analyst" voice.

**What it does:**
1. Decide which tickers to research (based on scans from Technician + Quant)
2. For each candidate: call relevant specialists
3. Synthesize findings: "5/6 agents bullish on NVDA"
4. Resolve disagreements: if Contrarian objects, weigh the evidence
5. Write the morning brief
6. Handle chat responses (grounded in specialist outputs)
7. Track which past calls were right/wrong

**This is the agent the human interacts with.**

---

### Phase B: Research Cycle Scheduler (Backend)

#### B1: `agents/scheduler.py`
Cron-like scheduler for daily and weekly research cycles.

- `DailyCycle`: pre-market scan → signal generation → risk evaluation → morning brief
- `WeeklyCycle`: performance review → signal decay → strategy weight adjustment
- Configurable: which tickers, which strategies, what time
- Runs as a background asyncio task in the FastAPI server
- Emits events to WebSocket at each step

#### B2: `api/cycle_routes.py`
API endpoints for cycle management:
- `POST /api/cycles/run-daily` — trigger daily cycle manually
- `POST /api/cycles/run-weekly` — trigger weekly cycle manually
- `GET /api/cycles/status` — current cycle state
- `GET /api/cycles/schedule` — configured schedule
- `POST /api/cycles/configure` — update schedule/tickers

---

### Phase C: Research Chat API (Backend)

#### C1: `agents/chat.py`
Research chat handler — natural language research backed by computation.

- Receives user message + conversation history
- Research Director interprets intent:
  - "Why NVDA not AMD?" → calls Quant + Technician for both, compares
  - "Build me a vol strategy" → calls Contrarian + Options analytics
  - "What happened last week?" → calls performance tracker + factor decomposition
- Each response includes:
  - Natural language answer (confident analyst voice)
  - Data citations (which computation backed each claim)
  - Action suggestions ("Want me to run a backtest?" / "Approve this trade?")

#### C2: `api/chat_routes.py`
- `POST /api/chat` — send message, get response
- `GET /api/chat/history` — conversation history
- Response includes: `answer`, `citations`, `suggested_actions`, `agent_traces` (which agents were consulted)

---

### Phase D: Dashboard Rebuild (Frontend — Next.js)

Complete rewrite of the dashboard around the three surfaces.

#### D1: Layout & Navigation
- Sidebar: Monitor, Chat, Signals, Portfolio, Performance, Settings
- Top bar: Agent Pulse ("3 agents active · 47 tasks today · Next cycle: 2h")
- Connection status (Demo/Live toggle)

#### D2: Morning Brief Page (`/` — default landing)
- Personalized greeting with time-aware message
- Top Conviction section: highest-confidence signals with multi-agent reasoning
- Watchlist: tickers approaching entry thresholds
- Portfolio Health: P&L, Sharpe, VaR, decay status
- "What I Learned": meta-learning from recent signals
- Action buttons: Approve/Reject/Dig Deeper per signal

#### D3: Thought Stream (sidebar or dedicated page)
- Real-time feed of agent reasoning
- Each entry: timestamp, agent icon, agent name, thought text
- Expandable: click to see full computation details
- Filterable by agent (show only Quant, only Sentiment, etc.)
- Auto-scrolling with pause on hover

#### D4: Research Chat Page (`/chat`)
- Chat interface (message input + response area)
- Responses rendered as rich cards:
  - Text with bold claims
  - Inline data tables (metrics)
  - Mini charts (sparklines for trends)
  - Citation badges ("Source: backtest, 47 instances")
  - Action buttons ("Run Backtest", "Approve Trade", "Compare with...")
- Agent trace: which specialists were consulted (collapsible)

#### D5: Signal Board Page (`/signals`)
- Grid of signal cards
- Each card: ticker, direction (long/short/flat), confidence bar, age
- Visual aging: signals turn yellow → orange → red as they approach half-life
- Click signal → expand to see full reasoning chain
- Filter: by strategy, by agent, by conviction level
- Sort: by confidence, by age, by potential return

#### D6: Portfolio Page (`/portfolio`)
- Treemap visualization (size = position, color = P&L)
- Proposed trades overlay (highlighted borders)
- Risk metrics: VaR, exposure by sector, correlation matrix
- Rebalancing suggestions from Portfolio Architect

#### D7: Performance Page (`/performance`)
- Equity curve (actual paper trading P&L)
- Signal scorecard: "This week: 7/12 profitable, +2.3% net"
- Strategy breakdown: which strategy types are working
- Agent accuracy: "The Quant was right 64% of the time, The Sentiment Analyst 58%"
- Signal decay monitor: are our edges still alive?

#### D8: 3D Visualizations
- Vol surface (already built)
- Correlation heatmap (already built)
- Factor exposure 3D scatter (new)

---

### Phase E: Integration & Polish

#### E1: End-to-end testing
- Start backend → run daily cycle → morning brief populates → approve trade → paper execute
- Chat: ask question → get grounded response with citations
- Demo mode: pre-loaded data, all surfaces work offline

#### E2: Demo preparation
- Prefetch data for 10 tickers
- Pre-run a daily cycle so morning brief is ready
- Prepare 3-4 scripted demo paths:
  1. "Open dashboard, read morning brief, approve NVDA trade"
  2. "Ask the agent: Why NVDA not AMD?"
  3. "Watch the thought stream as agents analyze TSLA"
  4. "Check performance: how did last week's signals do?"

---

## Build Order (Implementation Sequence)

### Sprint 1: Agent Specialists + Chat (Backend)
**Files:** `agents/specialists/*.py`, `agents/chat.py`, `agents/scheduler.py`
**Why first:** The dashboard is nothing without real agent reasoning behind it.

| # | File | Est. Lines | Depends On |
|---|------|-----------|-----------|
| 1 | `agents/specialists/__init__.py` | 10 | — |
| 2 | `agents/specialists/the_quant.py` | 200 | analytics/* |
| 3 | `agents/specialists/the_technician.py` | 120 | features/technical/* |
| 4 | `agents/specialists/the_sentiment_analyst.py` | 120 | research/nlp/* |
| 5 | `agents/specialists/the_fundamentalist.py` | 180 | research/nlp/rag*, data/fetchers/edgar* |
| 6 | `agents/specialists/the_macro_strategist.py` | 120 | data/fetchers/fred* |
| 7 | `agents/specialists/the_contrarian.py` | 120 | analytics/options*, risk/var/* |
| 8 | `agents/specialists/risk_manager_agent.py` | 120 | risk/* |
| 9 | `agents/specialists/portfolio_architect_agent.py` | 100 | portfolio/* |
| 10 | `agents/specialists/research_director.py` | 300 | all specialists |
| 11 | `agents/chat.py` | 200 | research_director |
| 12 | `agents/scheduler.py` | 150 | all specialists |
| 13 | `api/chat_routes.py` | 80 | agents/chat |
| 14 | `api/cycle_routes.py` | 80 | agents/scheduler |
| 15 | Tests for all above | 600 | — |
| | **Sprint 1 Total** | **~2,500** | |

### Sprint 2: Dashboard Rebuild (Frontend)
**Files:** Complete rewrite of `dashboard/src/`

| # | Component | Est. Lines |
|---|-----------|-----------|
| 1 | Layout + Sidebar + Agent Pulse | 200 |
| 2 | Morning Brief page | 400 |
| 3 | Thought Stream component | 250 |
| 4 | Research Chat page | 400 |
| 5 | Signal Board page | 300 |
| 6 | Portfolio page | 300 |
| 7 | Performance page | 300 |
| 8 | Zustand store rewrite | 150 |
| 9 | API hooks (chat, cycles, signals) | 200 |
| 10 | 3D visualizations (reuse + new) | 150 |
| | **Sprint 2 Total** | **~2,650** |

### Sprint 3: Integration + Demo Polish
| # | Task |
|---|------|
| 1 | End-to-end: daily cycle → morning brief → approve → execute |
| 2 | Chat: grounded responses with citations |
| 3 | Demo mode: pre-loaded data |
| 4 | Prefetch + precompute for meetup |
| 5 | Scripted demo paths |

---

## Success Criteria

When done, opening the dashboard should feel like this:

> You open the app at 8am. The morning brief greets you by name. It tells you the overnight scan found 3 opportunities. NVDA is the highest conviction — 5 of 6 agents agree, with a 62% historical win rate. You click "Dig Deeper" and see the full reasoning chain: z-score at -2.1, management tone +0.19, no crowded trade risk, Kelly says 4.2%. You type "Why not AMD?" and the agent explains: AMD is oversold but fundamentals don't support it — 2% revenue growth vs NVDA's 94%. You approve the NVDA trade. The agent sizes it, routes it to paper trading, and starts monitoring. Tomorrow's brief will tell you how it went.

That's the platform. That's the demo. That's what gets you Head of AI.
