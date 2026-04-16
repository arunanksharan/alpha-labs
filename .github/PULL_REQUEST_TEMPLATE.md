## What does this PR do?

<!-- Brief description of the change -->

## Why is this needed?

<!-- What problem does it solve? -->

## How to test

<!-- Steps to verify the change works -->

```bash
PYTHONPATH=. pytest tests/ -v
```

## Checklist

- [ ] Tests added/updated
- [ ] Tests pass locally (`PYTHONPATH=. pytest tests/`)
- [ ] Type hints added to all new functions
- [ ] Uses Polars (not Pandas) for new DataFrame operations
- [ ] No look-ahead bias in feature computations
- [ ] Follows existing patterns (BaseFeature, BaseStrategy, etc.)
