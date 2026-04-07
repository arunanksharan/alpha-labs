# Week 5 Implementation Log — 2026-04-07

## What Was Built

### Technical Indicators (`features/technical/indicators.py`)
All implemented from scratch using polars expressions (no ta-lib):
- **RSIFeature**: Wilder's smoothing RSI, bounded 0-100
- **MACDFeature**: MACD line + signal line + histogram
- **BollingerBandsFeature**: upper/lower/middle bands + %B + bandwidth
- **ATRFeature**: True Range + Average True Range via EMA
- **OBVFeature**: On-Balance Volume (cumulative volume * price direction)

### Purged K-Fold CV (`models/training/cross_validation.py`)
- **PurgedKFoldCV**: Temporal cross-validation per López de Prado Ch. 7
  - Purging: removes training samples near test boundaries
  - Embargo: gap between test end and next training block
  - Contiguous time blocks (not random splits)
  - Score method supports accuracy, AUC, and Sharpe metrics

### Feature Importance (`models/training/feature_importance.py`)
- **FeatureImportance**: Three methods per López de Prado:
  - MDI: Mean Decrease Impurity (from tree models)
  - MDA: Mean Decrease Accuracy (permutation importance)
  - SFI: Single Feature Importance (individual feature models)
  - Clustered importance (group correlated features)

### Feature Store (`features/store.py`)
- **FeatureStore**: DuckDB-backed persistent storage for computed features
  - Avoids recomputation across backtest runs
  - Parquet per feature/ticker, DuckDB query layer
  - `compute_and_store()` convenience for pipeline integration
  - Multi-feature joins on date

## Test Results
521 tests passing (461 from Weeks 1-4 + 60 new)
