# Branching Strategy

## Branch Structure

```
production  ← stable releases, tagged versions
  ↑ merge
staging     ← integration testing, pre-release validation
  ↑ merge
development ← active development, feature integration
  ↑ merge
feature/*   ← individual features (short-lived)
```

## Branch Policies

### `production`
- Only receives merges from `staging`
- Tagged with semantic versions (v0.1.0, v0.2.0, etc.)
- Always deployable / demo-ready
- Protected: no direct commits

### `staging`
- Receives merges from `development`
- Integration testing happens here
- Pre-release validation before production

### `development`
- Main working branch
- Receives merges from `feature/*` branches
- All tests must pass before merge

### `feature/*`
- Named: `feature/week1-data-pipeline`, `feature/week2-mean-reversion`, etc.
- Branch from `development`
- Merge back to `development` via PR or direct merge
- Delete after merge

## Workflow

1. Create feature branch: `git checkout -b feature/week2-mean-reversion development`
2. Develop and commit on feature branch
3. Run tests: `PYTHONPATH=. pytest tests/`
4. Merge to development: `git checkout development && git merge feature/week2-mean-reversion`
5. Delete feature branch: `git branch -d feature/week2-mean-reversion`
6. When milestone complete: merge development → staging → production
