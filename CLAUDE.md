# Quant Researcher

AI-powered quantitative research platform.

## Project Context
- Building a full quant research stack: data → features → signals → portfolio → execution
- Python 3.11+, using modern tooling (polars, duckdb, anthropic SDK)
- Heavy use of LLMs for alpha research (earnings calls, filings, news sentiment)

## Code Style
- Use ruff for linting
- Type hints everywhere
- Docstrings only for public APIs
- Prefer polars over pandas for new code (faster, more explicit)
- DuckDB for local analytical queries

## Testing
- pytest, run with: `pytest`
- Every strategy must have backtest validation tests

## Key Principles
- No look-ahead bias in any feature/signal computation
- All backtests must account for transaction costs and slippage
- Purged cross-validation for any ML model (no standard k-fold)
