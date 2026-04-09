# Integrated Curriculum — CQF + Senior Quant Researcher

## Why This File Exists

The original `senior-quant-researcher-curriculum.md` is a **equity-quant-heavy** curriculum. The CQF is a **derivatives/pricing-heavy** curriculum. They're complementary, not redundant.

Here's where they overlap and where they don't:

```
                    Original Curriculum          CQF
                    ───────────────────          ───

Linear Algebra      ██████████  (Part 1)         ░░ (primer only)
Probability         ██████████  (Part 2)         ░░ (primer only)
Econometrics        ██████████  (Part 3)         ████ (Module 2 partial)
Stochastic Calc     ██████████  (Part 4)         ██████████ (Module 1) ← OVERLAP
Asset Pricing       ██████████  (Part 5)         ░░ (not covered)
Factor Models       ██████████  (Part 6)         ░░ (not covered)
Microstructure      ██████████  (Part 7)         ░░ (not covered)
ML for Finance      ██████████  (Part 8)         ██████████ (Modules 4-5) ← OVERLAP
NLP / Alt Data      ██████████  (Part 9)         ████ (Module 5 partial)
Portfolio / Risk    ██████████  (Part 10)        ████████ (Module 2) ← PARTIAL OVERLAP
Backtesting         ██████████  (Part 11)        ░░ (not covered)
Execution           ██████████  (Part 12)        ░░ (not covered)
Interview Prep      ██████████  (Part 13)        ░░ (not covered)
Black-Scholes/Greeks ████ (Part 4 briefly)       ██████████ (Module 3) ← CQF ADDS
Fixed Income        ░░ (not covered)             ██████████ (Module 6) ← CQF ADDS
Credit Risk / xVA   ░░ (not covered)             ██████████ (Module 6) ← CQF ADDS
Exotic Options      ░░ (not covered)             ████████ (Module 3)   ← CQF ADDS
Numerical Methods   ░░ (briefly)                 ████████ (Module 3)   ← CQF ADDS
```

## What Changes

### The CQF adds 3 areas the original curriculum missed:

1. **Fixed Income & Credit** (CQF Module 6) — bond pricing, yield curves, credit risk, CDS, CVA/xVA. The original curriculum is 100% equity-focused. For a $1M role at a multi-asset fund, you need fixed income knowledge.

2. **Derivatives Pricing Depth** (CQF Module 3) — exotic options, numerical methods (finite differences, Monte Carlo), volatility surfaces. The original curriculum covers Black-Scholes but not at implementation depth.

3. **Numerical Methods** — finite difference solvers for PDEs, Monte Carlo with variance reduction, binomial/trinomial trees. These are practical skills the original curriculum skimped on.

### The original curriculum covers 6 areas the CQF doesn't:

1. **Asset Pricing Theory** (Part 5) — Cochrane-level factor theory, anomalies, why factors work
2. **Cross-Sectional Research** (Part 6) — quintile sorts, IC/ICIR, Fama-MacBeth, signal construction
3. **Market Microstructure** (Part 7) — order books, Kyle's lambda, Almgren-Chriss
4. **Backtesting Methodology** (Part 11) — deflated Sharpe, CPCV, multiple testing
5. **Execution** (Part 12) — VWAP/TWAP, implementation shortfall
6. **Interview Preparation** (Part 13) — practice problems, mock interviews

---

## The Integrated Roadmap: 26 Weeks

Merges both curricula. Eliminates redundancy. Fills all gaps.

### Phase 1: Mathematical Foundations (Weeks 1-4)
*Source: Original Parts 1-2 + CQF Primers*

| Week | Topic | Hours | Source |
|------|-------|-------|--------|
| 1 | Linear Algebra: eigenvectors, PCA, SVD, positive definite matrices | 20 | Original Part 1 |
| 2 | Convex Optimization: quadratic programs, Lagrange, duality | 15 | Original Part 1 |
| 2 | Probability: distributions, convergence, fat tails | 15 | Original Part 2 |
| 3 | Probability deep dive: copulas, extreme value theory, multivariate | 20 | Original Part 2 + Taleb |
| 4 | Calculus refresher: ODEs, PDEs, Taylor series (CQF primer level) | 10 | CQF Math Primer |

**Resources**: Strang (linear algebra), Boyd (optimization), Wasserman (probability), Taleb (fat tails)

### Phase 2: Statistics & Econometrics (Weeks 5-7)
*Source: Original Part 3 + CQF Module 2 (partial)*

| Week | Topic | Hours | Source |
|------|-------|-------|--------|
| 5 | Classical stats: MLE, hypothesis testing, bootstrap, multiple testing | 20 | Original Part 3A |
| 6 | Regression: OLS, Fama-MacBeth, panel data, Newey-West | 25 | Original Part 3B |
| 7 | Financial econometrics: ADF, GARCH, cointegration, Kalman filter | 25 | Original Part 3C + CQF Module 2 |

**Resources**: Wooldridge (econometrics), Tsay (financial time series)

### Phase 3: Stochastic Calculus & Derivatives (Weeks 8-11)
*Source: Original Part 4 + CQF Modules 1 & 3 (this is where CQF adds the most)*

| Week | Topic | Hours | Source |
|------|-------|-------|--------|
| 8 | Brownian motion, Ito's Lemma, SDEs, martingales | 25 | CQF Module 1 + Original Part 4 |
| 9 | Black-Scholes derivation, risk-neutral pricing, Greeks | 25 | CQF Module 3 |
| 10 | Implied volatility, vol surface, stochastic vol (Heston, SABR) | 20 | CQF Module 3 + Gatheral |
| 11 | Numerical methods: finite differences, Monte Carlo, variance reduction | 20 | CQF Module 3 + Jaeckel |

**Resources**: Shreve (stochastic calculus), Hull (derivatives), Wilmott (intro QF), Gatheral (vol surface), Jaeckel (Monte Carlo)

### Phase 4: Financial Theory & Factor Research (Weeks 12-15)
*Source: Original Parts 5-6 (NOT in CQF — this is your equity quant edge)*

| Week | Topic | Hours | Source |
|------|-------|-------|--------|
| 12 | Asset pricing: CAPM, APT, Fama-French, factor models | 25 | Original Part 5A-B |
| 13 | Anomalies: why they exist, risk vs behavioral vs institutional | 20 | Original Part 5C |
| 14 | Cross-sectional research: quintile sorts, IC, ICIR, signal construction | 25 | Original Part 6 |
| 15 | Signal combination, factor timing, factor crowding | 20 | Original Part 6 |

**Resources**: Cochrane (asset pricing), Pedersen (efficiently inefficient), Chincarini & Kim (quant equity), Ilmanen (expected returns)

**Key papers**: Fama-French 1993, Jegadeesh-Titman 1993, Harvey-Liu-Zhu 2016, Gu-Kelly-Xiu 2020

### Phase 5: Machine Learning for Finance (Weeks 16-19)
*Source: Original Parts 8-9 + CQF Modules 4-5*

| Week | Topic | Hours | Source |
|------|-------|-------|--------|
| 16 | Financial ML fundamentals: what's different, purged CV, triple barrier | 25 | Original Part 8 + CQF Module 4 |
| 17 | Tree models: XGBoost/LightGBM for cross-section, feature importance | 25 | CQF Module 4 + López de Prado |
| 18 | Deep learning: neural nets for finance, when DL works vs doesn't | 20 | CQF Module 5 |
| 19 | NLP: FinBERT, transformers, earnings call analysis, RAG | 25 | Original Part 9 + CQF Module 5 |

**Resources**: López de Prado (Advances in Financial ML), ISLR, Jansen (ML for algo trading), Goodfellow (deep learning), Tunstall (NLP with transformers)

### Phase 6: Fixed Income & Credit (Weeks 20-21)
*Source: CQF Module 6 (NOT in original curriculum — CQF fills this gap)*

| Week | Topic | Hours | Source |
|------|-------|-------|--------|
| 20 | Bond pricing, yield curves, duration/convexity, short-rate models | 20 | CQF Module 6 |
| 21 | Credit risk: structural/reduced-form models, CDS, CVA/xVA, copulas | 20 | CQF Module 6 |

**Resources**: Hull Ch. 31-35, Gregory (xVA Challenge), Brigo & Mercurio (interest rate models)

**Note**: If you're targeting pure equity quant roles, you can do a lighter pass on Weeks 20-21. If targeting multi-asset or Head of AI roles at global funds, these weeks are essential.

### Phase 7: Portfolio, Risk & Microstructure (Weeks 22-23)
*Source: Original Parts 7 & 10 + CQF Module 2 (partial)*

| Week | Topic | Hours | Source |
|------|-------|-------|--------|
| 22 | Portfolio construction: Markowitz, HRP, Black-Litterman, risk models | 25 | Original Part 10 + CQF Module 2 |
| 23 | Market microstructure: order books, Kyle's lambda, market impact, execution | 25 | Original Parts 7 & 12 |

**Resources**: Grinold & Kahn (APM), Harris (Trading and Exchanges), Almgren-Chriss (optimal execution)

### Phase 8: Research Methodology & Backtesting (Week 24)
*Source: Original Part 11 (NOT in CQF)*

| Week | Topic | Hours | Source |
|------|-------|-------|--------|
| 24 | Backtesting pitfalls, deflated Sharpe, CPCV, multiple testing, TCA | 25 | Original Part 11 |

**Resources**: López de Prado Ch. 11-18, Aronson (evidence-based TA), Bailey & López de Prado papers

### Phase 9: Interview Preparation (Weeks 25-26)
*Source: Original Part 13 (NOT in CQF)*

| Week | Topic | Hours | Source |
|------|-------|-------|--------|
| 25 | Practice problems: probability, statistics, finance, ML (100+ problems) | 25 | Original Part 13 |
| 26 | Mock interviews: system design, research presentation, behavioral | 25 | Original Part 13 |

**Resources**: Crack (Heard on the Street), Joshi (Quant Interview Q&A), Zhou (Practical Guide)

---

## Summary: What Changed

| Area | Original Curriculum | Integrated Curriculum | Change |
|------|--------------------|-----------------------|--------|
| Fixed Income & Credit | Not covered | 40 hours (Weeks 20-21) | **ADDED from CQF** |
| Derivatives depth | Light (30 hrs) | Deep (90 hrs, Weeks 8-11) | **EXPANDED with CQF** |
| Numerical methods | Not covered | 20 hours (Week 11) | **ADDED from CQF** |
| Vol surface / SABR | Not covered | 20 hours (Week 10) | **ADDED from CQF** |
| xVA / credit derivatives | Not covered | 20 hours (Week 21) | **ADDED from CQF** |
| Factor research | 50 hours | 65 hours (Weeks 12-15) | **Kept, slightly expanded** |
| Microstructure | 25 hours | 25 hours (Week 23) | **Unchanged** |
| Backtesting | 20 hours | 25 hours (Week 24) | **Unchanged** |
| Interview prep | 35 hours | 50 hours (Weeks 25-26) | **Unchanged** |
| Total | ~500 hours / 22 weeks | **~620 hours / 26 weeks** | **+120 hours** |

## The Bottom Line

The original curriculum gets you hired as an **equity quant researcher**.

The integrated curriculum gets you hired as a **quant researcher at a multi-asset fund** — which is what the $500K-$1M Head of AI JD describes ("global investment fund," not "equity-only fund").

The extra 120 hours (fixed income, credit, derivatives depth, numerical methods) is the difference between "I know equities" and "I can build an AI system across the entire fund's investment universe."

---

## Which Curriculum Should You Follow?

| If your target is... | Follow |
|---------------------|--------|
| Pure equity quant (Citadel Securities, systematic equity pod) | Original (22 weeks) |
| Multi-asset quant / Head of AI at a global fund | **Integrated (26 weeks)** |
| Derivatives quant / vol trader | CQF + Original Parts 5-7, 11-13 |
| Quant developer → quant researcher transition | Original Parts 5-8, 10-13 (skip math you know) |
