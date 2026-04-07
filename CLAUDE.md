# The Agentic Alpha Lab

AI-powered quantitative research platform with statistically validated agentic signals.

## Project Context
- Building a full quant research stack: data → features → signals → portfolio → execution
- Python 3.12+, using 2026 best-in-class tooling
- Heavy use of LLMs for alpha research (earnings calls, filings, news sentiment)
- Dashboard is a separate Next.js app under `dashboard/` using Avashi design system

## Stack (2026 Best-in-Class)

### Python Backend
- **Package mgmt**: Poetry
- **DataFrames**: Polars (primary), Pandas 3.0 (interop only)
- **Storage**: DuckDB + Parquet
- **Vector DB**: LanceDB (embedded, no server)
- **Backtesting**: VectorBT (research) + NautilusTrader (production execution sim)
- **ML**: LightGBM + XGBoost + scikit-learn
- **LLM**: Anthropic SDK v0.89+
- **Agents**: LangGraph for multi-agent orchestration
- **Research notebooks**: Marimo (reactive, .py files)

### Dashboard (Next.js)
- **Framework**: Next.js 15+ / React 19
- **Components**: shadcn/ui (Radix + CVA + Tailwind)
- **Styling**: Tailwind CSS, `clsx` + `tailwind-merge` + `class-variance-authority`
- **Charts**: Recharts (via shadcn charts) for financial data, Plotly for 3D surfaces
- **3D Visualizations**: Three.js + @react-three/fiber + @react-three/drei
- **Animation**: Framer Motion for DOM, requestAnimationFrame for 3D
- **State**: Zustand (client), @tanstack/react-query (server/API)
- **Icons**: lucide-react
- **Font**: Geist (Sans + Mono)
- **Theme**: Dark mode default, violet primary (#8b5cf6)
- **API**: FastAPI backend serving signals, backtests, analytics via REST

### Design Reference
- Follow Avashi design system: `/Users/paruljuniwal/kuzushi_labs/avashi/avashi-deploy/CLAUDE.md`
- Quality bar: Linear, Vercel, Raycast level UI

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

## Commit Rules
- **Small logical commits** — never batch an entire week into one commit
- Each production module + its test file = 1 commit
- Docs/init updates = separate commit
- Pattern: `feat(weekN): module description`, `docs(weekN): inits and log`
- Run tests before every commit

## Branching
- `production` ← `staging` ← `development` ← `feature/*`
- Feature branches: `feature/week2-mean-reversion`, etc.
- All tests must pass before merge to development
