# Agentic Alpha Lab — Architecture & Data Flow Tutorial

## How Data Flows Through the Platform

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION                             │
│  Browser → Login → Monitor / Chat / Backtest / Skills / Settings   │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js 16)                           │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Monitor  │  │   Chat   │  │ Backtest │  │  Skills  │           │
│  │          │  │          │  │          │  │          │           │
│  │ Fetches  │  │ Sends    │  │ Submits  │  │ Edits    │           │
│  │ universe │  │ messages │  │ async    │  │ agent    │           │
│  │ signals  │  │ to chat  │  │ jobs     │  │ markdown │           │
│  │ + runs   │  │ API      │  │ with     │  │ skill    │           │
│  │ Start    │  │          │  │ per-req  │  │ files    │           │
│  │ Research │  │ Voice    │  │ config   │  │          │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │              │              │              │                │
└───────┼──────────────┼──────────────┼──────────────┼────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    API ROUTES                                │   │
│  │                                                              │   │
│  │  /api/health          → Health check                        │   │
│  │  /api/auth/*          → JWT signup/login/refresh            │   │
│  │  /api/chat            → 6-agent analysis via ResearchChat   │   │
│  │  /api/jobs/submit     → Async backtest job submission       │   │
│  │  /api/jobs/{id}       → Job status + results polling        │   │
│  │  /api/universe/*      → Ticker universe CRUD + cache        │   │
│  │  /api/skills/*        → Agent skill markdown CRUD           │   │
│  │  /api/settings/*      → API keys, model, config             │   │
│  │  /api/config-agent    → NLP config changes via LLM          │   │
│  │  /api/cron/*          → Scheduled research cycles           │   │
│  │  /api/voice/key       → Deepgram API key proxy              │   │
│  │  /ws                  → WebSocket event stream              │   │
│  │  /ws/voice            → Voice pipeline (STT → LLM → tools) │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Auth Layer │  │  Rate Limiter│  │  CORS (configurable)     │  │
│  │  JWT tokens │  │  120/min API │  │  Via CORS_ORIGINS env    │  │
│  │  bcrypt     │  │  10/min auth │  │                          │  │
│  └─────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
```

## Flow 1: "Start Research" on Monitor Page

```
User clicks "Start Research" with D05.SI selected
        │
        ▼
Frontend: POST /api/chat  {"message": "Analyze D05.SI"}
        │
        ▼
Backend: ResearchChat.send("Analyze D05.SI")
        │
        ▼
ResearchDirector.answer_question()
        │
        ├──→ _parse_intent() → detects "D05.SI" as ticker_research
        │
        ▼
ResearchDirector.research_ticker("D05.SI")
        │
        ├──→ fetch_and_prepare_prices("D05.SI") → YFinance or Parquet cache
        │         │
        │         ▼
        │    490 daily OHLCV bars (from data/store/ohlcv/D05.SI/1d.parquet)
        │
        ├──→ TheQuant.analyze()
        │         Z-score = 0.47, win rate = 50%, momentum rank
        │
        ├──→ TheTechnician.analyze()
        │         RSI = 53.9, MACD hist = 0.055, %B = 0.62
        │
        ├──→ TheSentimentAnalyst.analyze()
        │         FinBERT score = 0.19 (bullish)
        │
        ├──→ TheFundamentalist.analyze()
        │         DCF value = $65.58, PE ratio, Gordon model
        │
        ├──→ TheMacroStrategist.analyze()
        │         VIX = 19.2, yield spread = 0.51% (from YFinance)
        │
        ├──→ TheContrarian.analyze()
        │         Crowded long, contrarian fade signal
        │
        ▼
_synthesize() → vote count: 2 bullish, 3 neutral, 1 bearish
        │         consensus = "bullish", confidence = 43%
        │
        ▼
Response JSON:
{
  "answer": "On D05.SI: My view is **bullish** with 43% confidence...",
  "citations": ["the_quant: Z-score at 0.47...", ...],
  "actions": ["Run backtest on D05.SI", "Compare D05.SI with peers"],
  "agent_traces": [
    {"agent": "quant", "signal": "neutral", "confidence": 0.12, "thoughts": [...]},
    {"agent": "technician", "signal": "neutral", "confidence": 0.0, "thoughts": [...]},
    ...
  ]
}
        │
        ▼
Frontend: parses agent_traces, shows each agent in Thought Stream
          with 400ms stagger animation
```

## Flow 2: Backtest Job Submission

```
User on /backtest: sets NVDA, mean_reversion, 2023-06-01, threshold=1.5, window=30
        │
        ▼
Frontend: POST /api/jobs/submit
{
  "ticker": "NVDA",
  "strategy": "mean_reversion",
  "start_date": "2023-06-01",
  "end_date": "2025-12-31",
  "config": {
    "commission": 0.0005,
    "slippage": 0.0002,
    "strategy_params": {"entry_threshold": 1.5, "window": 30}
  }
}
        │
        ▼
Backend: ThreadPoolJobRunner.submit()
        │
        ├──→ Returns job_id immediately (e.g., "a7c4fc2210fe")
        │
        ▼ (in background thread)
run_research_job() — the pipeline wrapper:

  Step 1 (0%): fetch_and_prepare_prices("NVDA")
        │       → YFinance or Parquet cache → 648 daily bars
        │
  Step 2 (14%): StrategyRegistry.get("mean_reversion", entry_threshold=1.5, window=30)
        │
  Step 3 (25%): ZScoreFeature(window=30).compute(prices)
        │        → adds "zscore" column to DataFrame
        │
  Step 4 (40%): strategy.generate_signals(features)
        │        → 186 signals (z < -1.5 = long, z > 1.5 = short)
        │
  Step 5 (50%): RiskManager.evaluate(signals)
        │        → filters by position limits, Kelly sizing
        │        → 10 signals approved, 176 rejected
        │
  Step 6 (60%): VectorizedBacktestEngine.run()
        │        → forward-fill weights across ALL 648 trading days
        │        → daily portfolio returns with transaction costs
        │        → equity curve: $100k → $119k (+19.0%)
        │        → Sharpe = +0.39, Win Rate = 53%
        │
  Step 7 (78%): BacktestValidator.deflated_sharpe_ratio()
        │
  Step 8 (88%): SignalDecayAnalyzer.compute_ic_curve()
        │
  Step 9 (100%): Complete → persist to research_history DB table
        │
        ▼
Frontend: polls GET /api/jobs/{id} every 2 seconds
          shows progress bar → renders equity curve, metrics, trades
```

## Flow 3: Voice Pipeline

```
User clicks mic button on Chat page
        │
        ▼
Browser: getUserMedia() → MediaRecorder (WebM/Opus, 250ms chunks)
        │
        ▼
WebSocket: connects to /ws/voice
        │
        ├──→ Browser sends binary audio chunks
        │
        ▼
Backend: handle_voice_session()
        │
        ├──→ Forwards audio to Deepgram Nova-3 via WebSocket
        │         wss://api.deepgram.com/v1/listen?model=nova-3
        │
        ├──→ Deepgram returns interim transcriptions in real-time
        │         → sent to browser as JSON {"type": "transcript", "text": "analyze DBS"}
        │
        ├──→ On speech_final: sends transcript to GPT-5-mini with tools
        │         System prompt includes agent skills from /api/skills
        │
        ├──→ GPT decides to call research_ticker("D05.SI")
        │         → executes handle_research_ticker()
        │         → runs full 6-agent analysis
        │         → returns tool result to GPT
        │
        ├──→ GPT generates response: "DBS is bullish with 43% confidence..."
        │         → streamed token-by-token to browser
        │
        ▼
Browser: shows transcript in input box, response in chat bubble
```

## Flow 4: Skills System

```
User navigates to /skills
        │
        ▼
Frontend: GET /api/skills → 6 agent cards with default skills
        │
User clicks "The Quant" card
        │
        ▼
Editor: shows markdown skill file (1335 chars)
  # The Quant
  ## Role: quantitative analyst
  ## Expertise: z-scores, momentum, statistics
  ## Analysis Framework: 5-step methodology
  ## Output Format: signal, confidence, metrics
  ## Personality: data-driven, skeptical
        │
User edits and clicks Save
        │
        ▼
Frontend: PUT /api/skills/the_quant {"skill": "modified markdown"}
        │
        ▼
Backend: saves to agent_prompts DB table (user-scoped)
        │
        ▼
Next time agents run:
  - settings_routes.py reads skill from DB (falls back to default)
  - Voice pipeline uses skill as system context for GPT
  - Chat API includes skill context in agent synthesis
```

## Database Schema

```
SQLite (dev) / PostgreSQL (prod)
├── users              (id, email, hashed_password, is_verified)
├── sessions           (id, user_id, refresh_token, expires_at)
├── user_settings      (user_id, key, value)         — per-user config overrides
├── platform_config    (key, value, category)         — 38 configurable params
├── agent_prompts      (user_id, agent_name, prompt)  — custom skills
├── research_universe  (user_id, ticker, strategies)  — per-user universe
├── api_keys           (user_id, provider, encrypted_key)
├── research_history   (id, user_id, ticker, strategy, result_json)
├── chat_history       (id, user_id, role, content, metadata)
```

## Data Storage (Non-DB)

```
data/
├── store/ohlcv/         — Parquet files (ZSTD compressed)
│   ├── D05.SI/1d.parquet
│   ├── NVDA/1d.parquet
│   └── ... (17 tickers)
├── cache/research/      — JSON cached research results (34 files)
│   ├── D05.SI__mean_reversion.json
│   └── ...
├── universe.json        — ticker universe config
└── quant_researcher.db  — SQLite database (dev)
```

## Key Design Principles

1. **Compute-first, LLM-second**: All 6 agents compute with Python (z-scores, RSI, DCF). The LLM only synthesizes and explains.

2. **No look-ahead bias**: Features use only past data. Purged cross-validation for ML models.

3. **Per-request config**: Every backtest can have different commission, slippage, strategy params. Global defaults are just defaults.

4. **Pluggable everything**: Strategy registry, feature registry, backtest engine, job runner — all behind ABCs.

5. **Skills as markdown**: Agent personality and methodology defined in editable markdown files, not hardcoded Python.
