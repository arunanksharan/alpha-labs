# The Agentic Alpha Lab

AI-powered quantitative research platform with statistically validated agentic signals.

Six specialist AI agents analyze any stock and produce a consensus signal with confidence score. Human-in-the-loop approval gate. Compute-first, LLM-second architecture -- every number is calculated from real data before an LLM touches it.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Tests](https://img.shields.io/badge/tests-1003_passing-brightgreen)
![Lines](https://img.shields.io/badge/lines-37K+-orange)
![Models](https://img.shields.io/badge/LLM-Claude%20|%20GPT%20|%20Gemini%20|%20Llama%20|%20DeepSeek-violet)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What Makes This Different

Most "AI trading" projects are thin wrappers around an LLM prompt. This project implements the **full quantitative research pipeline** from López de Prado's *Advances in Financial Machine Learning* — with AI agents as the orchestration layer, not the computation layer.

**Key principles:**
- **Compute first, LLM second** — every metric (z-scores, Sharpe ratios, factor loadings) is computed from real market data using vectorized operations. The LLM synthesizes findings; it doesn't generate numbers.
- **Statistically validated** — deflated Sharpe ratio, CPCV (combinatorial purged cross-validation), Monte Carlo permutation tests. No backtesting without overfit detection.
- **Modular and extensible** — every component (features, strategies, agents, risk models) is behind an abstract base class. Swap, extend, or replace without touching other modules.
- **Production patterns** — triple barrier labeling, meta-labeling, purged k-fold CV, fractional differentiation, CUSUM event-driven sampling. Not toy implementations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Dashboard (Next.js)                    │
│  Monitor | Chat | Signals | Performance | Backtest       │
└────────────────────────┬────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend                         │
├──────────────────────────────────────────────────────────┤
│  Agents Layer          │  Core Layer                      │
│  ├── Research Director │  ├── Features (technical, NLP)   │
│  ├── Quant Researcher  │  ├── Strategies (registry)       │
│  ├── Technician        │  ├── Backtesting (vectorized)    │
│  ├── Sentiment Analyst │  ├── Risk (position sizing)      │
│  ├── Fundamentalist    │  ├── Analytics (statistics)      │
│  ├── Macro Strategist  │  └── Data (YFinance, FRED)       │
│  └── Contrarian        │                                  │
├──────────────────────────────────────────────────────────┤
│  Storage: Polars + Parquet + DuckDB + LanceDB (embedded) │
└──────────────────────────────────────────────────────────┘
```

### Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, Polars, DuckDB, LanceDB |
| **Dashboard** | Next.js 16, React 19, Tailwind 4, Recharts, Three.js, Framer Motion |
| **LLM** | Multi-model via LiteLLM — Claude, GPT, Gemini, Llama, DeepSeek |
| **Data** | YFinance (market), FRED (macro), EDGAR (SEC filings) |
| **Testing** | pytest, 1003 tests across all modules |

---

## Quick Start

```bash
# Clone
git clone https://github.com/arunanksharan/alpha-labs.git
cd alpha-labs

# Backend
poetry install
cp .env.example .env  # Add your LLM API key(s)
PYTHONPATH=. uvicorn api.server:app --host 0.0.0.0 --port 8100 --reload

# Dashboard (new terminal)
cd dashboard
npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

**No database required.** Everything runs locally with Parquet files and embedded DuckDB.

### Configuration

The Settings page lets you:
- Add API keys for any LLM provider (OpenAI, Anthropic, Google, Groq, DeepSeek)
- Select the default model
- Customize each agent's system prompt

---

## The Six Agents

| Agent | Role | Key Metrics |
|-------|------|-------------|
| **Quant Researcher** | Statistical arbitrage, mean reversion | Z-scores, half-life, Hurst exponent, cointegration, IC decay |
| **Technician** | Technical analysis | RSI, MACD, Bollinger Bands, ATR, support/resistance |
| **Sentiment Analyst** | NLP on earnings calls and news | FinBERT sentiment, Loughran-McDonald, foundation model signals |
| **Fundamentalist** | Value analysis | DCF, Gordon model, P/E, P/B, EV/EBITDA, margin of safety |
| **Macro Strategist** | Macro regime detection | VIX, yield curve, FRED indicators, structural breaks (SADF) |
| **Contrarian** | Contrarian signals | Short interest, crowding, put/call ratios, consensus divergence |

The **Research Director** orchestrates all agents, resolves conflicts, and produces a consensus signal with confidence score. The human approves, rejects, or requests deeper analysis.

---

## AFML Implementation (López de Prado)

This project implements 17 of 20 chapters from *Advances in Financial Machine Learning*:

| Chapter | Concept | Implementation | File |
|---------|---------|---------------|------|
| 2 | CUSUM Event-Based Sampling | `CUSUMFilter` with dynamic thresholds | `analytics/filters.py` |
| 3 | Triple Barrier Labeling | Volatility-scaled barriers | `models/training/labeling.py` |
| 3 | Meta-Labeling | Direction/size separation | `models/training/labeling.py` |
| 4 | Sample Weights (Uniqueness) | Concurrency-based weighting | `models/training/labeling.py` |
| 5 | Fractional Differentiation | FFD with auto-d discovery | `features/technical/frac_diff.py` |
| 7 | Purged K-Fold CV | Embargo + purging | `models/training/cross_validation.py` |
| 8-9 | Feature Importance (MDI/MDA/SFI) | All three methods | `models/training/feature_importance.py` |
| 10 | Bet Sizing | Probability-to-position via CDF | `risk/position_sizing/bet_sizing.py` |
| 11 | Deflated Sharpe Ratio | Multiple testing correction | `backtest/validation.py` |
| 11 | Monte Carlo Permutation Test | Backtest validation | `backtest/validation.py` |
| 12 | CPCV | Probability of backtest overfitting | `backtest/validation.py` |
| 17 | Structural Breaks (SADF) | Bubble detection + regime classification | `analytics/structural_breaks.py` |
| — | LLM-as-Judge Validation | AI peer review of backtests | `backtest/validation.py` |

---

## Project Structure

```
quant-researcher/
├── agents/                    # AI agent definitions and orchestration
│   ├── specialists/           # 6 specialist agents + Research Director
│   ├── scheduler.py           # Agent scheduling and event-driven triggers
│   └── prompts/               # System prompts for each agent
├── analytics/                 # Statistical analysis
│   ├── statistics.py          # ADF, KPSS, Hurst, cointegration tests
│   ├── returns.py             # Sharpe, Sortino, drawdown, VaR, CVaR
│   ├── filters.py             # CUSUM event-based sampling
│   ├── structural_breaks.py   # Chow test, SADF, regime detection
│   ├── signal_decay.py        # IC/ICIR decay analysis
│   └── microstructure.py      # Amihud illiquidity, Kyle's lambda
├── backtest/                  # Backtesting framework
│   ├── engine/                # Vectorized backtest engine
│   ├── validation.py          # Deflated Sharpe, CPCV, Monte Carlo, LLM-as-Judge
│   └── reports/               # Tearsheet generation
├── core/                      # Abstract base classes and registries
│   ├── features.py            # BaseFeature + FeatureRegistry
│   ├── strategies.py          # BaseStrategy + StrategyRegistry
│   ├── backtest.py            # BacktestResult dataclass
│   └── risk.py                # Risk model interfaces
├── data/                      # Data ingestion and storage
├── features/                  # Feature computation
│   └── technical/             # RSI, MACD, momentum, z-score, frac_diff, spread
├── models/                    # ML models and training
│   ├── training/              # Labeling, CV, feature importance, sample weights
│   └── nlp_signals/           # FinBERT, Loughran-McDonald, model registry
├── risk/                      # Risk management
│   └── position_sizing/       # Kelly, inverse vol, risk parity, bet sizing
├── strategies/                # Trading strategies
├── portfolio/                 # Portfolio construction
├── execution/                 # Execution models
├── dashboard/                 # Next.js frontend
├── api/                       # FastAPI REST + WebSocket endpoints
├── config/                    # Configuration management
└── tests/                     # 1003 tests
```

---

## Extensibility — Building on Top

The codebase is designed for extensibility via **registries and abstract base classes**. You can add new components without modifying existing code.

### Adding a New Feature

```python
from core.features import BaseFeature, FeatureRegistry

@FeatureRegistry.register
class MyCustomFeature(BaseFeature):
    @property
    def name(self) -> str:
        return "my_custom_signal"

    @property
    def lookback_days(self) -> int:
        return 60

    @property
    def category(self) -> str:
        return "technical"

    def compute(self, data: pl.DataFrame) -> pl.DataFrame:
        # Your feature logic here — must use polars, no look-ahead bias
        signal = pl.col("close").rolling_mean(20) / pl.col("close").rolling_mean(60) - 1
        return data.with_columns(signal.alias("my_custom_signal"))
```

The feature is automatically available to all agents and strategies via the registry.

### Adding a New Strategy

```python
from core.strategies import BaseStrategy, StrategyRegistry, Signal

@StrategyRegistry.register
class MyStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "my_mean_reversion"

    @property
    def required_features(self) -> list[str]:
        return ["zscore_60", "my_custom_signal"]

    def generate_signals(self, features: pl.DataFrame) -> list[Signal]:
        # Your signal logic
        ...

    def get_positions(self, signals: list[Signal], capital: float) -> pl.DataFrame:
        # Your position sizing logic
        ...
```

### Adding a New Agent

```python
# agents/specialists/my_agent.py
class MySpecialist:
    """Custom specialist agent."""

    async def analyze(self, ticker: str, data: pl.DataFrame) -> dict:
        # Compute your metrics
        # Return structured analysis
        ...
```

Register in `agents/specialists/__init__.py` and wire into the Research Director.

### Adding a New NLP Model

```python
from models.nlp_signals.base import BaseNLPSignalModel, NLPModelRegistry

@NLPModelRegistry.register
class MyNLPModel(BaseNLPSignalModel):
    name = "my_sentiment_model"

    def analyze(self, text: str, context: dict | None = None) -> NLPSignalResult:
        # Your NLP logic
        ...
```

---

## Testing

```bash
# Run all tests
PYTHONPATH=. pytest tests/ -v

# Run specific module
PYTHONPATH=. pytest tests/test_frac_diff.py -v
PYTHONPATH=. pytest tests/test_structural_breaks.py -v
PYTHONPATH=. pytest tests/test_backtest_validation.py -v

# Run with coverage
PYTHONPATH=. pytest tests/ --cov=. --cov-report=html
```

1003 tests cover:
- All 6 agents + Research Director
- Triple barrier labeling + meta-labeling + sample weights
- Feature computation (RSI, MACD, momentum, z-score, frac diff)
- Backtesting engine + validation (deflated Sharpe, CPCV, permutation)
- Position sizing (Kelly, bet sizing, risk parity)
- Structural breaks (Chow, SADF, CUSUM)
- NLP pipeline (FinBERT, Loughran-McDonald)
- API endpoints

---

## Markets Supported

Any ticker that YFinance supports:

| Exchange | Example Tickers |
|----------|----------------|
| **SGX** | D05.SI (DBS), O39.SI (OCBC), U11.SI (UOB) |
| **NSE** | RELIANCE.NS, TCS.NS, INFY.NS |
| **NYSE/NASDAQ** | AAPL, NVDA, TSLA, META, GOOG |
| **LSE** | SHEL.L, HSBA.L |
| **HKEX** | 0005.HK, 9988.HK |
| **Others** | Any YFinance-supported ticker |

---

## Dashboard

| Page | What It Shows |
|------|---------------|
| **Monitor** | Morning brief, top signals, live agent reasoning stream |
| **Chat** | Conversational analysis — ask about any ticker or strategy |
| **Signals** | Active signals with confidence, direction, and decay tracking |
| **Performance** | Strategy breakdown, agent accuracy, P&L attribution |
| **Backtest** | Run backtests with equity curves, drawdown charts, monthly heatmaps |
| **Agents** | View and manage the 6 specialist agents |
| **Settings** | API keys, model selection, system prompt customization |

---

## Storage

| What | Where | Format |
|------|-------|--------|
| Market data | `data/` | Parquet (ZSTD compressed) |
| Analytical queries | In-memory | DuckDB |
| Vector store | `data/store/` | LanceDB (embedded) |
| Agent state | In-memory | WebSocket streaming |

No external database required. Everything runs locally.

---

## Contributing

Contributions welcome! Areas where help is most valuable:

1. **New features** — implement more technical indicators via `BaseFeature`
2. **New strategies** — add strategies via `BaseStrategy`
3. **More tests** — especially integration tests for the agent pipeline
4. **Dashboard improvements** — new visualizations, mobile responsiveness
5. **Data sources** — integrate additional data providers beyond YFinance
6. **Documentation** — tutorials, examples, API docs

Please ensure all new code:
- Has type hints
- Follows the existing abstract base class patterns
- Includes tests (`PYTHONPATH=. pytest tests/`)
- Uses Polars (not Pandas) for new features
- Prevents look-ahead bias in any feature computation

---

## Built With

[Claude Code](https://claude.com/claude-code) |
[Poetry](https://python-poetry.org/) |
[Next.js](https://nextjs.org/) |
[FastAPI](https://fastapi.tiangolo.com/) |
[Polars](https://pola.rs/) |
[DuckDB](https://duckdb.org/) |
[LiteLLM](https://litellm.ai/) |
[LanceDB](https://lancedb.com/)

---

## License

MIT
