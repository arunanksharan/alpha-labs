# Backend Reading Order

How to read the codebase — follow the data flow from raw market data to the dashboard.

## Layer 1: Configuration
```
config/settings.py          — All defaults: commission, slippage, risk limits, API keys
.env                        — Runtime overrides: API keys, model, database URL
```

## Layer 2: Data In
```
data/fetchers/yfinance_connector.py   — How OHLCV gets fetched (rate limiting, retry)
data/fetchers/fred_connector.py       — Macro data (FRED API, yield curves)
data/fetchers/edgar_connector.py      — SEC filings (10-K/10-Q text extraction)
data/storage/store.py                 — Parquet + DuckDB storage layer
```

## Layer 3: Feature Engineering
```
features/technical/indicators.py      — RSI, MACD, Bollinger (pure Polars, no ta-lib)
features/technical/zscore.py          — Z-score for mean reversion
features/technical/momentum.py        — Momentum ranking
features/store.py                     — Feature registry pattern
```

## Layer 4: Strategies
```
strategies/mean_reversion/strategy.py — Entry/exit rules, signal generation
strategies/momentum/strategy.py       — Momentum strategy
strategies/combiner.py                — Ensemble combiner
core/strategies.py                    — Strategy registry (ABC pattern)
```

## Layer 5: Backtest Engine
```
backtest/engine/vectorized.py         — THE core engine: weights -> daily returns -> equity curve
backtest/validation.py                — Deflated Sharpe ratio (anti-overfitting)
backtest/execution_model.py           — Transaction costs, slippage
core/backtest.py                      — BacktestResult dataclass + registry
```

## Layer 6: Risk
```
risk/manager.py                       — Signal filtering: position limits, sector limits
risk/position_sizing/engine.py        — Kelly criterion
risk/var/monte_carlo.py               — Monte Carlo VaR
risk/monitoring/circuit_breaker.py    — Drawdown circuit breakers
```

## Layer 7: Analytics
```
analytics/returns.py                  — Sharpe, Sortino, max drawdown, Calmar
analytics/statistics.py               — ADF test, Hurst exponent, cointegration
analytics/signal_decay.py             — IC curves, half-life (unique differentiator)
analytics/factors.py                  — Fama-French factor analysis
```

## Layer 8: Multi-Agent System
```
agents/specialists/the_quant.py           — Start here: cleanest agent example
agents/specialists/the_technician.py      — Technical analysis agent
agents/specialists/the_macro_strategist.py — Macro + VIX (uses YFinance)
agents/specialists/research_director.py   — Orchestrates all 6, synthesizes consensus
agents/chat.py                            — Chat wrapper over ResearchDirector
agents/graph.py                           — LangGraph DAG definition
agents/state.py                           — ResearchState dataclass
```

## Layer 9: Orchestrator (ties it all together)
```
core/orchestrator.py      — THE main pipeline: data -> features -> signals -> risk -> backtest
core/llm.py               — Multi-model LLM routing via LiteLLM
core/adapters.py           — DataFrame <-> Signal converters
core/serialization.py      — JSON serialization for API responses
```

## Layer 10: API + Database + Auth
```
api/server.py              — FastAPI app, all routes registered here
api/auth_routes.py         — Signup, login, JWT token management
api/agent_routes.py        — POST /api/agents/run, WebSocket streaming
api/chat_routes.py         — POST /api/chat
api/settings_routes.py     — API keys, model selection, prompts
api/universe_routes.py     — Ticker universe CRUD + cached results
db/models.py               — SQLAlchemy ORM models (9 tables)
db/session.py              — Database connection management
auth/service.py            — Password hashing, JWT creation/validation
auth/dependencies.py       — FastAPI auth dependencies
```

## The One File That Explains Everything

Read `core/orchestrator.py` — the `run()` method is a 10-step pipeline that calls every layer above in sequence. Once you understand that, the rest is implementation detail.
