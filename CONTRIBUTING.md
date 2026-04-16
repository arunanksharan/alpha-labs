# Contributing to The Agentic Alpha Lab

Thank you for your interest in contributing! This project welcomes contributions of all kinds — features, bug fixes, tests, documentation, and ideas.

## How to Contribute

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/alpha-labs.git
cd alpha-labs
poetry install
```

### 2. Create a Branch

```bash
git checkout -b feat/your-feature-name
```

### 3. Make Your Changes

Follow the existing patterns:
- **New features**: Implement `BaseFeature` and register with `@FeatureRegistry.register`
- **New strategies**: Implement `BaseStrategy` and register with `@StrategyRegistry.register`
- **New NLP models**: Implement `BaseNLPSignalModel` and register with `@NLPModelRegistry.register`
- **New agents**: Add to `agents/specialists/` following existing agent patterns

### 4. Write Tests

Every new module needs tests:

```bash
PYTHONPATH=. pytest tests/ -v
```

Tests must pass before submitting a PR.

### 5. Submit a Pull Request

Push your branch and open a PR against `main`. Include:
- What the change does
- Why it's needed
- How to test it

---

## Code Style

- **Python 3.11+** with type hints everywhere
- **Polars** (not Pandas) for new DataFrame operations
- **ruff** for linting: `ruff check .`
- Docstrings only for public APIs
- No look-ahead bias in any feature computation
- Every external dependency behind an ABC — swap without touching strategies

## What We're Looking For

High-impact contributions:

| Area | Examples |
|------|---------|
| **Features** | New technical indicators, alternative data signals |
| **Strategies** | Mean reversion, momentum, statistical arbitrage variants |
| **Data sources** | Polygon.io, Alpaca, crypto exchanges |
| **ML models** | New NLP models, time series models, ensemble methods |
| **Tests** | Integration tests, edge cases, agent pipeline tests |
| **Docs** | Tutorials, API documentation, architecture guides |
| **Dashboard** | New visualizations, mobile improvements |

## Reporting Issues

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version, OS, and relevant package versions

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful and constructive.
