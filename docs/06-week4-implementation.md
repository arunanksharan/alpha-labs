# Week 4 Implementation Log — 2026-04-07

## What Was Built

### Momentum Feature (`features/technical/momentum.py`)
- **MomentumFeature**: Classic Jegadeesh-Titman 12-1 momentum
  - Configurable lookback (default 252) and skip_recent (default 21)
  - Formula: `(price[t-skip] / price[t-lookback]) - 1`
  - Auto-registered with FeatureRegistry

### Momentum Strategy (`strategies/momentum/strategy.py`)
- **MomentumStrategy**: Cross-sectional momentum with long/short legs
  - Ranks tickers by momentum per date
  - Long top_pct (20%), short bottom_pct (20%)
  - Confidence based on rank distance from median
  - Equal weight within long/short legs

### Fama-French Factor Model (`analytics/factors.py`)
- **FamaFrenchModel**: 3-factor and 5-factor attribution
  - OLS regression: R_i - R_f = α + β₁·MKT + β₂·SMB + β₃·HML + ε
  - Factor attribution: decomposes returns into factor contributions
  - Information Coefficient: rank correlation between signals and forward returns
  - Rolling factor exposure over configurable window
  - Synthetic factor data for testing (real Kenneth French data in future)

### Strategy Combiner (`strategies/combiner.py`)
- **StrategyCombiner**: Multi-strategy portfolio construction
  - Merge signals with configurable strategy weights
  - Same (date, ticker) signals averaged across strategies
  - Optimal weight methods: equal, inverse_vol, sharpe_weighted
  - Correlation analysis between strategy returns
  - Performance summary table

## Key Design Decisions
- Momentum skip_recent=21 avoids short-term reversal (well-documented effect)
- Factor model uses synthetic data for now — real data connector in Week 5
- Combiner's sharpe_weighted method only allocates to positive-Sharpe strategies
- All implementations reuse existing analytics.returns functions

## Test Results
461 tests passing (420 from Weeks 1-3 + 41 new)
