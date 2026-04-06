# The Agentic Alpha Lab

AI-powered quantitative research platform with statistically validated agentic signals.

## Project Context
- Building a full quant research stack: data → features → signals → portfolio → execution
- Python 3.12+, using 2026 best-in-class tooling
- Heavy use of LLMs for alpha research (earnings calls, filings, news sentiment)

## Stack (2026 Best-in-Class)
- **DataFrames**: Polars (primary), Pandas 3.0 (interop only)
- **Storage**: DuckDB + Parquet
- **Vector DB**: LanceDB (embedded, no server)
- **Backtesting**: VectorBT (research) + NautilusTrader (production execution sim)
- **ML**: LightGBM + XGBoost + scikit-learn
- **LLM**: Anthropic SDK v0.89+
- **Agents**: LangGraph for multi-agent orchestration
- **Viz**: Marimo (research notebooks), Plotly Dash (production dashboards), Streamlit (quick demos)
- **Package mgmt**: uv

## Code Style
- Use ruff for linting (target py312)
- Type hints everywhere
- Docstrings only for public APIs
- Prefer polars over pandas for new code
- DuckDB for local analytical queries

## Testing
- pytest, run with: `PYTHONPATH=. pytest tests/`
- Every strategy must have backtest validation tests

## Key Principles
- No look-ahead bias in any feature/signal computation
- All backtests must account for transaction costs and slippage
- Purged cross-validation for any ML model (no standard k-fold)
- Every external dependency behind an ABC — swap without touching strategies

## Branching
- `production` ← `staging` ← `development` ← `feature/*`
- Feature branches: `feature/week2-mean-reversion`, etc.
- All tests must pass before merge to development
