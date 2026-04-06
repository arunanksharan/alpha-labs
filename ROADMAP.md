# The Agentic Alpha Lab — 13-Week Roadmap

**Subtitle**: Quant Researcher → Head of AI
**Goal**: Head of AI in Quant Research by end of Q2 2026
**Philosophy**: Build first, learn theory to explain why it broke. Every week ships code.
**Constraint**: Free and open-source data sources and tools only.
**Differentiator**: Statistically Validated Agentic Signals — moving beyond LLM opinions to backtested, risk-managed investment signals.
**Reference**: Virat Singh's [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) (50K+ stars) — our version adds real backtesting, statistical validation, and RAG over unstructured financial documents.

---

## Free & Open-Source Data Sources

### Market Data (Price / OHLCV)

| Source | What | Access |
|--------|------|--------|
| **yfinance** | Historical + real-time equity data via Yahoo Finance | `pip install yfinance` — free, no API key |
| **FRED (Federal Reserve)** | Macro data: interest rates, GDP, unemployment, inflation | `fredapi` — free API key from fred.stlouisfed.org |
| **OpenBB** | Aggregates 100+ free data sources into one SDK | `pip install openbb` — free tier |
| **Tiingo** | EOD + IEX real-time, fundamentals | Free tier: 500 req/hr |
| **Alpha Vantage** | OHLCV, fundamentals, economic indicators | Free tier: 25 req/day |
| **Polygon.io** | Stocks, options, crypto, forex | Free tier: 5 API calls/min, delayed data |
| **Binance API** | Crypto OHLCV, order book, trades | Free, no key for public endpoints |

### Fundamental Data

| Source | What | Access |
|--------|------|--------|
| **SEC EDGAR** | 10-K, 10-Q, 8-K, proxy statements | Free — `sec-edgar-downloader` or `edgartools` |
| **Financial Modeling Prep** | Financial statements, ratios, estimates | Free tier: 250 req/day |
| **SimFin** | Quarterly/annual financials for US companies | Free tier via `simfin` package |

### Alternative / NLP Data

| Source | What | Access |
|--------|------|--------|
| **SEC EDGAR full-text** | Earnings call transcripts (via 8-K filings) | Free |
| **Reddit API** | r/wallstreetbets, r/stocks sentiment | Free tier |
| **News API** | 80,000+ sources, headlines | Free tier: 100 req/day |
| **GDELT** | Global news events, sentiment | Free, massive scale |
| **Wikipedia pageviews** | Attention proxy for stocks | Free API |

### Backtesting Frameworks (All Free/OSS)

| Framework | Language | Stars | Best For |
|-----------|----------|-------|----------|
| **Qlib** (Microsoft) | Python | 16K+ | ML-oriented quant research, factor mining |
| **Backtrader** | Python | 14K+ | Event-driven backtesting, flexible |
| **VectorBT** | Python | 4K+ | Vectorized backtesting, fast |
| **QuantConnect LEAN** | C#/Python | 9K+ | Production algo trading, 300+ fund users |
| **Zipline (reloaded)** | Python | — | Quantopian's engine, maintained fork |

### Portfolio / Risk Tools (All Free/OSS)

| Tool | What |
|------|------|
| **PyPortfolioOpt** | Mean-variance, Black-Litterman, HRP |
| **skfolio** | Portfolio optimization on scikit-learn |
| **Riskfolio-Lib** | Portfolio optimization + risk measures |
| **QuantStats** | Performance analytics + tear sheets |
| **empyrical** | Common financial risk metrics |

---

## Reference: Virat Singh's AI Hedge Fund

### What He Built (Our Baseline)
- 18 multi-agent system: 12 investor personas + 4 analysts + 2 ops agents
- LangGraph orchestration, multi-LLM (OpenAI/Groq/Anthropic/DeepSeek)
- React/TS frontend, Docker deployment
- 50,200+ stars — most viral AI finance project ever

### What It Lacks (Our Opportunity)

| Gap | Our Solution |
|-----|-------------|
| No backtesting | Walk-forward validation, out-of-sample testing via Qlib/VectorBT |
| No statistical validation | Signal significance testing, information coefficient analysis |
| No RAG over unstructured docs | SEC EDGAR full-text RAG (10-K, earnings calls) |
| No signal decay analysis | Rolling IC, half-life measurement |
| Structured API data only | NLP-derived signals from unstructured documents |
| No risk management | VaR, position sizing, drawdown circuit breakers |
| No real factor model | Fama-French integration, factor attribution |

### Integration Plan
- Week 1-2: Study his agent architecture, adapt the multi-agent pattern
- Week 5-7: Build our differentiators (RAG, ML signals, backtesting)
- Week 8: Side-by-side comparison (his agents vs our validated signals)

---

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│  Streamlit Dashboard │ Jupyter Notebooks │ CLI │ API (FastAPI)  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    ORCHESTRATION LAYER                           │
│  Research Pipeline │ Backtest Runner │ Signal Combiner           │
│  Multi-Agent Framework (LangGraph) │ Workflow Scheduler          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      STRATEGY LAYER                             │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  Mean     │  │ Momentum  │  │ ML-Based │  │ LLM Persona  │   │
│  │ Reversion │  │ Factor    │  │ Signals  │  │ Agents       │   │
│  └──────────┘  └───────────┘  └──────────┘  └──────────────┘   │
│  All implement: BaseStrategy(ABC)                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      ANALYTICS LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Risk Engine  │  │ Portfolio    │  │ Performance           │  │
│  │ VaR, CVaR    │  │ Optimizer    │  │ Attribution           │  │
│  │ Kelly, Sizing│  │ HRP, BL, MV │  │ Factor decomposition  │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      FEATURE LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Technical    │  │ Fundamental  │  │ Alternative / NLP     │  │
│  │ RSI, MACD,   │  │ P/E, EV/    │  │ Sentiment, earnings   │  │
│  │ Bollinger    │  │ EBITDA, FCF  │  │ call NLP, news        │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
│  All implement: BaseFeature(ABC)                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    BACKTEST LAYER                                │
│  Event-Driven Engine │ Walk-Forward │ Monte Carlo Simulation    │
│  Transaction Cost Models │ Slippage │ Tear Sheet Generator      │
│  Pluggable: Qlib │ VectorBT │ Backtrader (via BacktestConnector)│
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    CONNECTOR LAYER                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │ Market Data│  │ Fundamental│  │ Alt Data   │  │ Execution│  │
│  │ Connector  │  │ Connector  │  │ Connector  │  │ Connector│  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬────┘  │
│        │               │               │               │        │
│  yfinance         SEC EDGAR       News API        Alpaca       │
│  Tiingo           SimFin          Reddit API      IBKR         │
│  Alpha Vantage    FMP             GDELT           Paper Trade  │
│  Polygon          OpenBB          Wikipedia                    │
│  Binance                                                        │
│  All implement: BaseConnector(ABC)                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      STORAGE LAYER                              │
│  DuckDB (analytical queries) │ Parquet (columnar files)         │
│  SQLite (metadata/config)    │ ChromaDB (vector embeddings)     │
└─────────────────────────────────────────────────────────────────┘
```

### Connector Pattern (How extensibility works)

Every external dependency is behind an abstract connector. To add a new data source:

1. Implement `BaseConnector` (or `BaseMarketDataConnector`, `BaseFundamentalConnector`, etc.)
2. Register it in the connector registry
3. Config drives which connector is active — zero code changes to strategies

Same pattern for strategies (`BaseStrategy`), features (`BaseFeature`), and backtest engines (`BaseBacktestEngine`).

---

## Phase 1: Foundations + First Strategy (Weeks 1-4)

### Week 1: Data Pipeline + Connector Layer
**Build**: Market data ingestion with pluggable connectors
- [ ] `BaseConnector` ABC + connector registry
- [ ] `YFinanceConnector` — historical OHLCV (free, no API key)
- [ ] `FREDConnector` — macro data (interest rates, GDP, CPI)
- [ ] `SECEdgarConnector` — filing metadata + full-text download
- [ ] Storage layer: DuckDB for queries, Parquet for raw data
- [ ] Returns calculator, volatility, correlation matrix
- [ ] Hypothesis testing: t-test, KS test on returns distributions
- [ ] CLI: `qr fetch --source yfinance --ticker AAPL --start 2020-01-01`

**Learn**:
- Ernie Chan "Quantitative Trading" Ch. 1-3
- Fat tails: why returns aren't normal (Taleb Ch. 1-4)
- YouTube: Patrick Boyle "What do Quants Actually Do?"

**Key concept**: Stationarity — test for it, understand why most price series aren't stationary

---

### Week 2: Mean Reversion Strategy + Backtest Engine v1
**Build**: First strategy + backtesting foundation
- [ ] `BaseStrategy` ABC with `generate_signals()`, `get_positions()`
- [ ] `MeanReversionStrategy` — pairs trading, z-score entry/exit
- [ ] Cointegration testing (Engle-Granger, Johansen) — implement + statsmodels
- [ ] `BaseBacktestEngine` ABC
- [ ] `VectorBTBacktester` connector (fast, good for iteration)
- [ ] Basic metrics: Sharpe, Sortino, max drawdown, Calmar, win rate
- [ ] Tear sheet generator using QuantStats

**Learn**:
- Ernie Chan Ch. 4-5 (mean reversion)
- ADF test, Hurst exponent — implement from scratch
- MIT 18.650 Lectures 1-4 (hypothesis testing)

**Key concept**: Look-ahead bias — the #1 reason backtests lie

---

### Week 3: Risk Management Framework
**Build**: Risk engine with position sizing
- [ ] Kelly criterion calculator
- [ ] VaR: parametric, historical, Monte Carlo
- [ ] Expected Shortfall / CVaR
- [ ] Position sizing engine (risk parity, equal weight, Kelly)
- [ ] Drawdown monitor + circuit breakers
- [ ] Risk dashboard (Streamlit — first visual output, good for meetup demo)

**Learn**:
- Hull Ch. 22 (Value at Risk)
- "Active Portfolio Management" Ch. 1-3 (IR = IC × √BR)
- AQR paper: "Understanding Risk Parity"

**Key concept**: Risk-adjusted returns > raw returns. 20% return / 5% vol beats 50% return / 40% vol.

---

### Week 4: Momentum + Factor Models
**Build**: Cross-sectional momentum + factor framework
- [ ] `MomentumStrategy` — 12-1 month momentum, variations
- [ ] `BaseFeature` ABC for feature engineering
- [ ] Fama-French factor model (implement from scratch using FRED data)
- [ ] Factor exposure analysis for each strategy
- [ ] Strategy combiner: mean reversion + momentum portfolio
- [ ] Correlation analysis between strategies

**Learn**:
- AQR: "Value and Momentum Everywhere" (Asness et al.)
- Fama-French 3-factor, 5-factor model theory
- Ernie Chan Ch. 6-7

**Key concept**: Uncorrelated strategies combine superlinearly

---

## Phase 2: ML + Alpha Research (Weeks 5-8)

### Week 5: Feature Engineering Platform
**Build**: Alpha factor research tools
- [ ] Technical indicators library (RSI, MACD, Bollinger, ATR, OBV — build from scratch)
- [ ] `FMPConnector` or `SimFinConnector` for fundamental data
- [ ] Feature importance framework (MDI, MDA, SFI per López de Prado)
- [ ] Purged K-fold cross-validation (CRITICAL for financial ML)
- [ ] Feature store in DuckDB

**Learn**:
- López de Prado "Advances in Financial ML" Ch. 1-6
- Why standard CV fails in finance (autocorrelation, leakage)
- Stanford CS229 Lectures 1-5

**Key concept**: Purged cross-validation — financial data has temporal structure. Ignoring this = overfitting.

---

### Week 6: ML Signal Generation
**Build**: ML-based alpha signals
- [ ] Tree-based models (XGBoost/LightGBM for cross-sectional prediction)
- [ ] Walk-forward optimization framework
- [ ] Triple barrier labeling (López de Prado)
- [ ] Meta-labeling — ML to size bets, not just direction
- [ ] Ensemble + model stacking
- [ ] Signal decay analysis (rolling IC, half-life, decay curve visualization)
- [ ] Signal Decay Engine: measure how long an AI-derived signal remains profitable
  - Rolling Information Coefficient (IC) over time windows
  - Half-life of IC (when does the signal lose statistical significance?)
  - Decay curve visualization (key demo artifact for meetup)
  - Compare decay rates: technical vs fundamental vs NLP-derived signals

**Learn**:
- López de Prado Ch. 7-10 (meta-labeling, bet sizing)
- Implement triple barrier labeling from scratch
- Bias-variance tradeoff in financial context
- Information Coefficient analysis: Grinold & Kahn Ch. 6

**Key concept**: Meta-labeling — separate "what to trade" from "how much to bet". Signal decay tells you "how long to hold the bet."

---

### Week 7: LLM-Powered Alpha Research (Your Differentiator)
**Build**: AI-native research tools — this is where we surpass Virat's ai-hedge-fund
- [ ] `SECEdgarConnector` enhancement: full-text 10-K, 10-Q, 8-K download + chunking
- [ ] Earnings call transcript analyzer (sentiment drift, management tone shift)
- [ ] Forward guidance extraction + tracking over time
- [ ] ChromaDB vector store for document embeddings
- [ ] RAG pipeline: query financial documents with Claude API
- [ ] Multi-agent investor personas (à la Virat) BUT with RAG-grounded reasoning
- [ ] Cross-document contradiction signals (e.g., CEO says X in earnings call, 10-K says Y)
- [ ] Research report generator (automated analysis → HTML/PDF)

**Learn**:
- "Machine Learning for Asset Managers" — López de Prado
- NLP for finance: FinBERT, sentiment as alpha
- Man AHL, Two Sigma blog posts on LLM usage

**Key concept**: LLMs are your unfair advantage. Most quant researchers can't build production LLM pipelines.

---

### Week 8: Production Backtesting + Validation
**Build**: Institutional-quality backtesting
- [ ] `QlibBacktester` connector (Microsoft Qlib integration)
- [ ] Realistic execution modeling (slippage, market impact)
- [ ] Monte Carlo simulation for robustness
- [ ] Walk-forward analysis automation
- [ ] Multiple testing correction (Bonferroni, BH) — combat p-hacking
- [ ] Combinatorial purged cross-validation (CPCV)
- [ ] Side-by-side: Virat's agent signals vs our ML + NLP signals (backtested)

**Learn**:
- "Evidence-Based Technical Analysis" — Aronson
- Multiple hypothesis testing, deflated Sharpe ratio
- López de Prado: "The 7 Reasons Most ML Funds Fail"

**Key concept**: Backtest overfitting — most published strategies are noise. Learn to detect this.

---

## Phase 3: Derivatives + Advanced Topics (Weeks 9-11)

### Week 9: Options + Volatility
**Build**: Volatility analysis toolkit
- [ ] Black-Scholes pricer (implement from scratch)
- [ ] Greeks calculator (Delta, Gamma, Vega, Theta, Rho)
- [ ] Implied volatility surface construction
- [ ] GARCH model for volatility forecasting (using `arch` library)
- [ ] Vol trading strategies (straddles, strangles, calendar spreads)
- [ ] Options data via free sources (CBOE delayed, yfinance options chains)

**Learn**:
- Hull Ch. 13-19 (Black-Scholes, Greeks, vol smiles)
- "Volatility Trading" — Euan Sinclair
- CME Group options education (YouTube)

**Key concept**: Volatility is a tradeable asset class

---

### Week 10: Market Microstructure + Execution
**Build**: Order book analysis + execution optimizer
- [ ] Binance L2 order book data (free WebSocket)
- [ ] VWAP / TWAP execution algorithms
- [ ] Market impact model (Almgren-Chriss)
- [ ] Bid-ask spread analysis
- [ ] `AlpacaConnector` for paper trading (free)

**Learn**:
- "Trading and Exchanges" — Larry Harris (Ch. 1-10)
- Kyle's Lambda, Amihud illiquidity ratio
- Microstructure: why execution quality is alpha

**Key concept**: Gap between backtest and live returns is almost entirely execution

---

### Week 11: Portfolio Construction + Optimization
**Build**: Portfolio optimization engine
- [ ] Mean-variance optimization (Markowitz + limitations)
- [ ] Black-Litterman model
- [ ] Hierarchical Risk Parity (López de Prado)
- [ ] Risk parity implementation
- [ ] Regime-aware allocation (HMM-based)
- [ ] Integration with PyPortfolioOpt and skfolio

**Learn**:
- "Active Portfolio Management" Ch. 4-8 (Grinold & Kahn)
- López de Prado: "Building Diversified Portfolios that Outperform OOS"
- Why mean-variance is unstable (estimation error amplification)

**Key concept**: Diversification is the only free lunch. Naive diversification is a trap.

---

## Phase 4: Integration + Leadership Positioning (Weeks 12-13)

### Week 12: Full Pipeline + Demo Polish
**Build**: End-to-end platform
- [ ] Data → Features → Signals → Portfolio → Execution → Monitoring pipeline
- [ ] Streamlit dashboard: strategy performance, risk metrics, research outputs
- [ ] Alert system (drawdown, signal notifications)
- [ ] Paper trading via Alpaca (free)
- [ ] FastAPI layer for programmatic access
- [ ] Docker Compose for one-command deployment
- [ ] Demo mode: pre-loaded with compelling backtest results

**Learn**:
- System design for trading systems
- How quant funds structure research → production pipeline

---

### Week 13: Documentation + Thought Leadership
**Build**: Credibility artifacts
- [ ] Architecture documentation with C4 diagrams
- [ ] Strategy research reports (publishable quality)
- [ ] Blog posts / LinkedIn articles:
  - "How I Built an LLM-Powered Quant Research Platform with Claude Code"
  - "Meta-Labeling: Why Most ML Trading Strategies Fail"
  - "From Engineer to Quant: What I Built in 13 Weeks"
- [ ] Open-source the platform
- [ ] Prepare Singapore meetup presentation

---

## Singapore Claude Code + Fintech Meetup

### This IS Fintech

Fintech = technology that improves or automates financial services. Specifically:
- **Quantitative Asset Management** — AI-powered systematic investment research
- **WealthTech** — institutional-grade investment infrastructure
- **RegTech adjacent** — automated SEC filing analysis and compliance data extraction

### Positioning: "The Agentic Alpha Lab"

**Core differentiator**: Statistically Validated Agentic Signals.
- Virat's ai-hedge-fund: viral PoC, LLM *opinions* over structured API data
- Our platform: production-grade *validated signals* with backtesting, risk management, and RAG over unstructured filings
- Relevant to Singapore's institutional landscape: Point72, Citadel, GIC, Temasek

### Presentation Angle

**Title**: "The Agentic Alpha Lab: Building Statistically Validated Investment Signals with Claude Code"

**Structure** (30-40 min):
1. **The Problem** (5 min): Most AI-in-finance projects produce opinions, not signals. What makes a signal tradeable?
2. **The Reference** (5 min): Virat's ai-hedge-fund (50K stars) — impressive but no validation. What's missing?
3. **Live Demo** (15 min): Walk through the platform:
   - Fetch data → generate features → run backtest → show tear sheet
   - LLM-powered earnings call analysis → signal generation
   - Signal decay visualization — "how long does a CEO sentiment signal last?"
   - Risk dashboard with position sizing
4. **Claude Code as Force Multiplier** (5 min): How AI-assisted development accelerates fintech prototyping
   - Show git log — thousands of lines built in weeks
   - Live: ask Claude Code to add a new connector or strategy on stage
5. **Architecture Deep-Dive** (5 min): The layered, modular design with plug-in connectors

**Key demo artifacts** (prioritize these):
- Signal decay curves (unique, impressive, quantitative)
- Backtest tear sheets (visual, professional)
- LLM research output (earnings call → investment thesis with citations)
- Side-by-side: Virat's agent output vs our validated signal
- Live Claude Code interaction (build something on stage)

---

## Daily Routine

| Time | Activity |
|------|----------|
| Morning (1 hr) | Theory: book chapter or paper |
| Midday (2-3 hrs) | Build: write code, ship features |
| Evening (30 min) | Review: what broke, what concept do I need? |
| Weekend (4 hrs) | Deep dive: implement a concept from scratch |

---

## Reading List (Priority Order)

### Tier 1 — Read First
1. "Quantitative Trading" — Ernie Chan
2. "Advances in Financial ML" — Marcos López de Prado
3. "Active Portfolio Management" — Grinold & Kahn

### Tier 2 — Reference as Needed
4. "Options, Futures, and Other Derivatives" — John C. Hull
5. "Trading and Exchanges" — Larry Harris
6. "Volatility Trading" — Euan Sinclair

### Tier 3 — Deep Expertise
7. "Stochastic Calculus for Finance" — Shreve (if derivatives-focused)
8. "Statistical Consequences of Fat Tails" — Taleb
9. "Machine Learning for Asset Managers" — López de Prado
10. "Evidence-Based Technical Analysis" — Aronson

### Free Resources
- **YouTube**: Patrick Boyle, 3Blue1Brown, MIT OCW, Stanford CS229
- **Papers**: AQR.com research, SSRN.com
- **Platforms**: QuantConnect, Numerai, WorldQuant BRAIN
- **Communities**: r/quant, r/algotrading, QuantConnect Discord

---

## Success Metrics (End of 13 Weeks)

- [ ] 3+ backtested strategies with realistic assumptions
- [ ] 1 ML-based alpha signal with out-of-sample validation
- [ ] Production-grade backtesting + data infrastructure
- [ ] LLM-powered research tools (the differentiator)
- [ ] Published content demonstrating expertise
- [ ] Paper trading with real signals
- [ ] Singapore meetup presentation delivered
- [ ] Can speak fluently about: factor models, risk management, ML pitfalls in finance, market microstructure
