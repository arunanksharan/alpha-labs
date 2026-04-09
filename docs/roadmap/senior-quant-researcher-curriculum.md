# Senior Quant Researcher — Complete Curriculum from First Principles

## What Separates a $200K ML Engineer from a $1M Quant Researcher

A $1M quant researcher does ONE thing: **generates risk-adjusted returns that the fund cannot get elsewhere.** Everything they know — math, statistics, ML, finance — serves this single purpose.

The gap between an ML engineer and a quant researcher is NOT more ML knowledge. It's:

1. **Mathematical maturity** — not "I can use scikit-learn" but "I can derive why this estimator breaks under fat tails and propose a correction"
2. **Financial thinking** — not "I'll predict stock prices" but "I'll exploit a mispricing in the cross-section of expected returns caused by institutional constraints"
3. **Research discipline** — not "my backtest shows Sharpe 3" but "I've controlled for data snooping, transaction costs, crowding, and regime changes, and the signal still shows IC of 0.03 with t-stat > 3"
4. **Portfolio thinking** — not "this stock will go up" but "this 200-name portfolio has an expected IR of 1.2 with 8% annualized tracking error and drawdown budget of 15%"

This curriculum builds each layer in order. Skipping ahead will leave gaps that interviewers will find.

---

## Curriculum Overview

```
Part 1:  Linear Algebra & Optimization (math machinery)
Part 2:  Probability Theory (the language of uncertainty)
Part 3:  Statistics & Econometrics (measuring things in noisy markets)
Part 4:  Stochastic Calculus & Time Series (how prices move)
Part 5:  Financial Theory & Asset Pricing (why prices are what they are)
Part 6:  Factor Models & Cross-Sectional Research (the bread and butter of quant)
Part 7:  Market Microstructure (how trading actually works)
Part 8:  Machine Learning for Finance (what works and what doesn't)
Part 9:  NLP & Alternative Data (the new frontier)
Part 10: Portfolio Construction & Risk (from signals to money)
Part 11: Backtesting & Research Methodology (not lying to yourself)
Part 12: Execution & Implementation (the last mile)
Part 13: Interview Preparation (cracking the door)
```

Estimated total: **500-600 hours over 4-6 months** for a disciplined learner with your ML background.

---

## Part 1: Linear Algebra & Optimization

**Why this first**: Every model you'll build, every portfolio you'll construct, and every risk calculation you'll run is a matrix operation. PCA for factor models, eigendecomposition for covariance matrices, convex optimization for portfolio construction — it all starts here.

**What you need to know (not just use):**
- Vector spaces, linear transformations, eigenvalues/eigenvectors
- Positive definite matrices (covariance matrices must be PD — and in practice they often aren't)
- Singular Value Decomposition (dimensionality reduction for factor models)
- Principal Component Analysis (deriving statistical factors from returns)
- Convex optimization (portfolio optimization is a quadratic program)
- Gradient descent variants (for ML model training)

### Resources

**Primary textbook:**
- **"Introduction to Linear Algebra" — Gilbert Strang, 6th edition**
  - Chapters 1-7 (skip Ch 8-10 unless you have time)
  - Focus on: eigenvalues (Ch 6), SVD (Ch 7), positive definite matrices (Ch 6.5)
  - Time: 30 hours

**Video lectures:**
- **MIT 18.06 — Linear Algebra (Gilbert Strang)** — YouTube, full course
  - Watch lectures 1-24, skip proofs you already know, focus on the intuition
  - Time: 15 hours
- **3Blue1Brown — "Essence of Linear Algebra"** — YouTube, 16 videos
  - The single best visual intuition for linear algebra. Watch first.
  - Time: 3 hours

**For optimization:**
- **"Convex Optimization" — Boyd & Vandenberghe** (free at stanford.edu/~boyd/cvxbook)
  - Chapters 1-5 only. You need: convex sets, convex functions, quadratic programs, duality
  - Time: 15 hours
- **Stanford EE364a lectures** — YouTube
  - Boyd teaching his own book. Brilliant.

**Why this matters for interviews:**
- "Explain PCA" → "Eigendecomposition of the covariance matrix. The first k eigenvectors capture the directions of maximum variance. In finance, the first PC is usually 'the market,' the second is often a value/growth tilt."
- "How do you handle a non-positive-definite covariance matrix?" → "Nearest PD projection, shrinkage toward identity (Ledoit-Wolf), or factor model covariance."
- "How does portfolio optimization work?" → "Minimize w'Σw subject to w'μ = target return, w'1 = 1. It's a quadratic program solved with Lagrange multipliers or SOCP."

**Estimated time: 40-50 hours**

---

## Part 2: Probability Theory

**Why**: Financial markets are probability machines. Every price encodes a probability distribution of future outcomes. If you can't reason about probability precisely, you can't reason about markets.

**What you need to know:**
- Probability spaces, sigma-algebras, measurability (the rigorous foundation)
- Random variables, distributions, expectations, variance, covariance
- Conditional probability, Bayes' theorem (updating beliefs with new data)
- Common distributions and when they appear in finance:
  - Normal: returns (approximately, in the center)
  - Log-normal: prices
  - Student-t: fat-tailed returns (reality)
  - Chi-squared: variance estimators
  - F-distribution: regression testing
  - Poisson: event arrivals (trade counts, news)
- Moment generating functions, characteristic functions
- Convergence: in probability, in distribution, almost surely
- Law of large numbers and Central Limit Theorem (and when CLT fails — fat tails!)
- Multivariate distributions, copulas (dependency modeling beyond correlation)

### Resources

**Primary textbook:**
- **"All of Statistics" — Larry Wasserman**
  - Chapters 1-12
  - Perfect for someone with ML background who needs rigorous probability
  - Time: 25 hours

**Supplementary (critical for finance):**
- **"Statistical Consequences of Fat Tails" — Nassim Taleb**
  - Chapters 1-8
  - This changes how you think about risk. Financial returns are NOT normally distributed. Most quant disasters come from assuming they are.
  - Time: 15 hours

**Video:**
- **MIT 6.041 — Probabilistic Systems Analysis (John Tsitsiklis)** — MIT OCW
  - The gold standard. Watch lectures 1-14.
  - Time: 10 hours
- **Nassim Taleb — "Probability and Risk" talks** — YouTube
  - Search for his university lectures. He explains why Gaussian assumptions kill funds.

**Key interview concepts:**
- "What distribution do returns follow?" → "Approximately normal in the center with fat tails (excess kurtosis). Empirically, returns have kurtosis of 5-10 vs normal's 3. This means extreme events are 10-100x more likely than a normal distribution predicts."
- "What's a copula?" → "A function that models the dependency structure between random variables independent of their marginal distributions. In finance, correlations spike during crises (tail dependence) — copulas capture this while linear correlation doesn't."

**Estimated time: 30-40 hours**

---

## Part 3: Statistics & Econometrics for Finance

**Why**: This is where you learn to measure things in noisy, non-stationary, fat-tailed data. Standard ML metrics (accuracy, F1) are meaningless in finance. You need: t-statistics, information coefficients, Newey-West standard errors, and hypothesis testing under multiple comparisons.

**What you need to know:**

### 3A: Classical Statistics (refresh, go deep)
- Estimation: MLE, method of moments, Bayesian estimation
- Hypothesis testing: t-tests, F-tests, chi-squared tests, p-value pitfalls
- Confidence intervals and their interpretation
- Multiple testing: Bonferroni, Benjamini-Hochberg, False Discovery Rate
- Bootstrap and permutation tests (critical when distributions are unknown)

### 3B: Regression (the workhorse of quant finance)
- OLS: assumptions, derivation, properties (BLUE), interpretation
- Violations: heteroskedasticity (White standard errors), autocorrelation (Newey-West), multicollinearity (VIF)
- Fama-MacBeth regression (THE method for testing factor models in cross-section)
- Panel data: fixed effects, random effects, clustered standard errors
- Instrumental variables (2SLS) — used in causal inference for finance
- Quantile regression — beyond the mean

### 3C: Financial Econometrics
- Stationarity testing: ADF, KPSS, Phillips-Perron
- Cointegration: Engle-Granger, Johansen (for pairs trading)
- GARCH family: GARCH(1,1), EGARCH, GJR-GARCH (volatility modeling)
- Vector Autoregression (VAR) — multi-asset dynamics
- State-space models and Kalman filter (for adaptive estimation)

### Resources

**Primary textbooks:**
- **"Introductory Econometrics" — Jeffrey Wooldridge, Ch. 1-16**
  - The standard. Clear, rigorous, examples in economics/finance.
  - Time: 40 hours

- **"Analysis of Financial Time Series" — Ruey Tsay, Ch. 1-7**
  - ARMA, GARCH, volatility models, multivariate time series.
  - Time: 30 hours

**Supplementary:**
- **"Econometric Analysis" — William Greene, selected chapters**
  - For deeper dives: MLE (Ch 14), panel data (Ch 11), limited dependent variables (Ch 17)
  - Reference, not cover-to-cover

**Research papers:**
- **Fama & MacBeth (1973) — "Risk, Return, and Equilibrium"**
  - The methodology paper. Two-step cross-sectional regression. You WILL be asked about this.
- **Newey & West (1987) — "A Simple, Positive Semi-Definite Heteroskedasticity and Autocorrelation Consistent Covariance Matrix"**
  - HAC standard errors. Used in every quant research paper.
- **Harvey, Liu & Zhu (2016) — "... and the Cross-Section of Expected Returns"**
  - Multiple testing in factor research. Shows most published factors are false discoveries.

**Video:**
- **Ben Lambert — "Econometrics" playlist** — YouTube (100+ videos)
  - Clear, visual explanations of every econometrics concept
- **QuantEcon — "Quantitative Economics with Python"** (quantecon.org)
  - Thomas Sargent and John Stachurski. Computational econometrics.

**Key interview concepts:**
- "How do you test if a factor is significant?" → "Fama-MacBeth regression. For each month, regress cross-section of returns on factor exposures. Then take the time series of coefficient estimates and test if the mean is significantly different from zero using Newey-West standard errors to account for autocorrelation."
- "Your backtest shows Sharpe 2. Is it real?" → "Probably not. With 100 strategies tested, the expected max Sharpe under the null is ~3.0 (Bailey & López de Prado, 2014). I'd compute the deflated Sharpe ratio and check if p < 0.05 after adjusting for the number of trials."

**Estimated time: 50-60 hours**

---

## Part 4: Stochastic Calculus & Continuous-Time Finance

**Why**: Derivatives pricing, volatility modeling, and risk-neutral pricing all require stochastic calculus. Even if you don't price derivatives, understanding Ito's lemma, Brownian motion, and SDEs gives you a framework for thinking about how prices evolve continuously.

**What you need to know:**
- Brownian motion (Wiener process) — properties, construction
- Filtrations, adapted processes, martingales
- Ito's lemma (the chain rule for stochastic processes)
- Stochastic differential equations (geometric Brownian motion, Ornstein-Uhlenbeck)
- Black-Scholes derivation (from SDE to PDE to formula)
- Greeks (delta, gamma, vega, theta) — from the SDE perspective
- Risk-neutral pricing and the fundamental theorem of asset pricing
- Change of measure (Girsanov's theorem) — conceptual understanding

### Resources

**Primary textbook:**
- **"Stochastic Calculus for Finance I & II" — Steven Shreve**
  - Vol I: Binomial models (simpler, build intuition). 6 chapters.
  - Vol II: Continuous-time models. Chapters 1-6 are essential.
  - Time: 40 hours total

**Alternative (more accessible):**
- **"An Introduction to the Mathematics of Financial Derivatives" — Ali Hirsa & Salih Neftci**
  - Gentler than Shreve. Good if stochastic calculus is entirely new.
  - Time: 25 hours

**Video:**
- **MIT 18.S096 — "Topics in Mathematics with Applications in Finance"** — MIT OCW
  - Lectures on stochastic calculus, Black-Scholes, portfolio theory. Taught by quants.
  - Time: 12 hours (watch selected lectures)

**Key interview concepts:**
- "Derive Black-Scholes" → Stock follows dS = μSdt + σSdW. Apply Ito's lemma to log(S). Get log-normal distribution. Risk-neutral pricing: replace μ with r. Price = E^Q[e^{-rT} max(S_T - K, 0)].
- "What's Ito's lemma?" → "The chain rule for stochastic processes. If f(S,t) is a function of a stochastic process S, then df = (∂f/∂t + μS∂f/∂S + ½σ²S²∂²f/∂S²)dt + σS(∂f/∂S)dW. The extra term (½σ²S²∂²f/∂S²) is what makes stochastic calculus different from regular calculus."
- "What's a martingale?" → "A process where the best prediction of future value is the current value. Under risk-neutral measure, discounted asset prices are martingales."

**Note**: If you're targeting stat-arb / systematic equity roles (not derivatives), you can do a lighter pass on stochastic calculus. But every $1M+ role will test it at least conversationally.

**Estimated time: 30-40 hours**

---

## Part 5: Financial Theory & Asset Pricing

**Why**: This is the core intellectual framework of quant research. Factor models, anomalies, risk premia — everything you'll build as a quant researcher is grounded in asset pricing theory. Without it, you're a technician without a thesis.

**What you need to know:**

### 5A: Foundation
- Efficient Market Hypothesis (Fama, 1970) — what it actually says, where it fails
- CAPM (Sharpe, 1964) — single-factor model, beta, market risk premium
- Why CAPM fails empirically: size effect, value effect, momentum
- Arbitrage Pricing Theory (Ross, 1976) — multi-factor model

### 5B: Factor Models (THE topic for quant interviews)
- Fama-French 3-factor model (market, size, value)
- Carhart 4-factor model (+ momentum)
- Fama-French 5-factor model (+ profitability, investment)
- Quality factor (Novy-Marx, 2013; Asness, Frazzini & Pedersen, 2019)
- Low-volatility anomaly (Baker, Bradley & Wurgler, 2011)
- Factor timing — can you predict which factors will outperform?
- Factor crowding — what happens when everyone does the same thing

### 5C: Why Anomalies Exist (Required for interview discussions)
- Risk-based explanations: higher expected returns compensate for risk
- Behavioral explanations: cognitive biases create mispricings
- Institutional explanations: index effects, short-selling constraints, liquidity
- Limits to arbitrage: why mispricings persist even if detected

### Resources

**Primary textbooks:**
- **"Asset Pricing" — John Cochrane**
  - THE textbook for PhD-level asset pricing. Chapters 1-13.
  - Dense but foundational. Read slowly.
  - Time: 50 hours

- **"Efficiently Inefficient" — Lasse Heje Pedersen**
  - How hedge funds actually work. Covers every strategy type: equity, macro, fixed income, quant. Accessible and practical.
  - Time: 20 hours

**Research papers (required reading):**
- **Fama & French (1993) — "Common Risk Factors in the Returns on Stocks and Bonds"**
  - The 3-factor model paper. The most cited paper in finance.
- **Jegadeesh & Titman (1993) — "Returns to Buying Winners and Selling Losers"**
  - The momentum paper. Why past returns predict future returns.
- **Asness, Moskowitz & Pedersen (2013) — "Value and Momentum Everywhere"**
  - Value and momentum across asset classes. AQR's foundational research.
- **Novy-Marx (2013) — "The Other Side of Value: The Gross Profitability Premium"**
  - The quality/profitability factor.
- **McLean & Pontiff (2016) — "Does Academic Research Destroy Stock Return Predictability?"**
  - Meta-study: what happens to anomalies after publication? Answer: they decay by ~50%.
- **Harvey, Liu & Zhu (2016) — "... and the Cross-Section of Expected Returns"**
  - The multiple testing problem in factor research. 300+ published factors, most are false.

**Video:**
- **John Cochrane — "Asset Pricing" lectures** — YouTube
  - His entire PhD course. The best there is.
- **AQR — Research papers and white papers** (aqr.com)
  - Read their "Alternative Thinking" series. Practical factor research.

**Key interview concepts:**
- "What factors do you believe in?" → "Market, value, momentum, quality, and low volatility have the strongest out-of-sample evidence across geographies and time periods. I'm skeptical of most published factors after Harvey et al. (2016) showed the multiple testing problem."
- "Why does momentum work?" → "Behavioral: underreaction to new information (Hong & Stein, 1999) and herding (Bikhchandani et al., 1992). Institutional: funds rebalance slowly, creating short-term price persistence. Risk-based: momentum crashes during market reversals (Daniel & Moskowitz, 2016)."
- "What's your Sharpe ratio expectation for a single factor?" → "0.3-0.5 for a long-short factor portfolio, net of transaction costs. Anyone claiming higher for a well-known factor is either cherry-picking the time period or not accounting for costs."

**Estimated time: 50-60 hours**

---

## Part 6: Factor Models & Cross-Sectional Research

**Why**: This is the actual day-to-day work of a quant researcher at most systematic equity funds. You construct factors, test them, combine them, and trade them. If Part 5 is the theory, Part 6 is the practice.

**What you need to know:**
- Alpha construction: from raw data to tradeable signal
- Feature engineering for cross-sectional prediction
  - Fundamental: valuation ratios, quality metrics, growth rates
  - Technical: momentum, mean reversion, volatility
  - Alternative: sentiment, options-implied, insider trading, ESG
- Signal testing methodology:
  - Quintile sorts (the workhorse): sort stocks into 5 groups by signal, measure return spread
  - Fama-MacBeth regression (cross-sectional testing with time-series averaging)
  - Information Coefficient (IC): rank correlation between signal and forward returns
  - IC Information Ratio (ICIR): mean IC / std IC — the stability of the signal
- Signal combination: how to combine 50+ weak signals into a strong composite
- Universe selection: which stocks to trade and why
- Turnover analysis: signal changes → trading costs → net alpha

### Resources

**Primary textbook:**
- **"Quantitative Equity Portfolio Management" — Chincarini & Kim**
  - The most practical book on factor-based quant equity. Covers everything: factors, testing, portfolio construction, risk models.
  - Time: 30 hours

**Supplementary:**
- **"Expected Returns" — Antti Ilmanen**
  - Comprehensive survey of return predictability across all asset classes. Written by a quant practitioner at AQR.
  - Time: 20 hours (selective reading)

- **"Quantitative Trading" — Ernest Chan**
  - Practical. Gets you from idea to backtest fast. Good for mean reversion and momentum.
  - Time: 12 hours

**Research papers:**
- **Gu, Kelly & Xiu (2020) — "Empirical Asset Pricing via Machine Learning"**
  - THE paper on ML for cross-sectional returns. Uses neural nets, random forests, GBRT.
- **Green, Hand & Zhang (2017) — "The Characteristics that Provide Independent Information about Average U.S. Monthly Stock Returns"**
  - Which firm characteristics actually predict returns independently.
- **Frazzini, Israel & Moskowitz (2012) — "Trading Costs of Asset Pricing Anomalies"**
  - Are factors profitable after realistic trading costs? (Mostly yes, if you're careful.)

**Practical exercises (build these in the Alpha Lab):**
1. Construct a value factor (book-to-market) for the S&P 500. Sort into quintiles. Measure the spread.
2. Compute rolling IC for your factor over 20 years. Is it stable or decaying?
3. Combine value + momentum + quality into a composite signal. Does the composite outperform individual factors?

**Estimated time: 40-50 hours**

---

## Part 7: Market Microstructure

**Why**: Every alpha signal must be traded. Understanding HOW markets work — order books, bid-ask spreads, market impact, adverse selection — determines whether your signal is profitable after costs.

**What you need to know:**
- Order book mechanics: limit orders, market orders, bid-ask spread
- Market making and adverse selection (Glosten-Milgrom, Kyle)
- Price impact: temporary vs permanent, Almgren-Chriss model
- Transaction cost analysis (TCA): implementation shortfall, VWAP benchmarks
- Market fragmentation: dark pools, exchanges, alternative trading systems
- High-frequency effects: latency, order flow toxicity (VPIN)
- Why this matters for quant research: your backtest means nothing if you can't trade it

### Resources

**Primary textbook:**
- **"Trading and Exchanges" — Larry Harris**
  - The standard. Covers everything from how exchanges work to why prices move.
  - Chapters 1-20.
  - Time: 25 hours

**Supplementary:**
- **"Market Microstructure in Practice" — Lehalle & Laruelle**
  - Modern perspective: European markets, fragmentation, HFT impact.
  - Time: 12 hours

**Research papers:**
- **Kyle (1985) — "Continuous Auctions and Insider Trading"**
  - The fundamental model of price impact. Kyle's lambda.
- **Almgren & Chriss (2001) — "Optimal Execution of Portfolio Transactions"**
  - The optimal execution framework used by every quant fund.
- **Easley, López de Prado & O'Hara (2012) — "Flow Toxicity and Liquidity in a High-Frequency World"**
  - VPIN: measuring order flow toxicity.

**Key interview concepts:**
- "Your signal has IC of 0.03. Is it tradeable?" → "Depends on turnover and market impact. With 20% monthly turnover on large-cap stocks, transaction costs might be 5-10 bps per trade. If the signal generates 30 bps of monthly alpha but costs 10 bps to trade, net alpha is 20 bps. With enough breadth (200+ stocks), this can produce IR > 1."
- "How do you estimate market impact?" → "Almgren-Chriss: impact ∝ σ√(Q/V) where σ is volatility, Q is order size, V is daily volume. For a quant fund, impact is typically 5-20 bps depending on stock liquidity."

**Estimated time: 25-30 hours**

---

## Part 8: Machine Learning for Finance

**Why**: This is where your existing ML skills become your edge — IF you learn what's different about financial ML.

**What you need to know:**

### 8A: What's Different About Financial ML
- Low signal-to-noise ratio (IC of 0.02-0.05 is GOOD)
- Non-stationarity (the world changes; your model doesn't know)
- Adversarial environment (your alpha gets competed away)
- Regime changes (bull markets, bear markets, crises)
- Autocorrelation in features AND labels
- Survivorship bias, look-ahead bias, selection bias

### 8B: Methods That Work
- Gradient boosted trees (XGBoost, LightGBM) — the workhorse for tabular financial data
- Linear models with regularization (Lasso, Ridge, Elastic Net) — interpretable, hard to overfit
- Random forests — robust, good for feature importance
- Neural networks — mostly for alternative data (images, text), not structured data
- Ensemble methods — combining multiple models reduces overfitting risk

### 8C: Methods That Usually Don't Work (and why)
- Deep learning on price data (too noisy, too few samples, non-stationary)
- Reinforcement learning for portfolio allocation (works in paper, fails in practice)
- LSTM/RNN for return prediction (no evidence of consistent outperformance)
- Autoencoders for anomaly detection (interesting but unproven for alpha)

### 8D: Financial ML Methodology
- Feature engineering: lagged returns, accounting ratios, technical indicators, macro variables
- Label engineering: triple barrier labeling, forward returns at various horizons
- Cross-validation: purged K-fold, combinatorial purged CV, walk-forward
- Feature importance: MDI, MDA, SFI (López de Prado)
- Hyperparameter tuning: Bayesian optimization with purged CV
- Model stacking and blending

### Resources

**Primary textbook:**
- **"Advances in Financial Machine Learning" — Marcos López de Prado**
  - THE book. Every chapter matters. Read cover to cover.
  - Time: 30 hours

**Supplementary:**
- **"Machine Learning for Algorithmic Trading" — Stefan Jansen**
  - Practical. Code examples. Covers factor models, NLP, deep learning.
  - Time: 20 hours (selective chapters)

- **"Machine Learning for Asset Managers" — López de Prado**
  - Short, focused on clustering and portfolio construction with ML.
  - Time: 8 hours

**Research papers:**
- **Gu, Kelly & Xiu (2020)** — already listed, but re-read after Part 6
- **Feng, He & Polson (2018) — "Deep Learning for Predicting Asset Returns"**
  - How deep learning maps to factor models.
- **Bianchi, Büchner & Tamoni (2021) — "Bond Risk Premiums with Machine Learning"**
  - ML for fixed income — shows methodology for non-equity applications.
- **López de Prado (2018) — "The 10 Reasons Most Machine Learning Funds Fail"**
  - Read this. Then read it again.

**Video:**
- **Stanford CS229 — Machine Learning (Andrew Ng)** — YouTube
  - Refresher. Focus on: bias-variance tradeoff, regularization, model selection.
- **López de Prado lectures** — YouTube
  - Search for his talks at universities. He explains financial ML pitfalls better than anyone.

**Estimated time: 40-50 hours**

---

## Part 9: NLP & Alternative Data for Finance

**Why**: The JD mentions NLP explicitly. The frontier of quant research is alternative data — text from filings, earnings calls, news, social media, satellite imagery, credit card data. This is where new alpha comes from.

**What you need to know:**

### 9A: Financial NLP
- Text preprocessing for financial documents
- Sentiment analysis: dictionary-based (Loughran-McDonald), ML-based (FinBERT), LLM-based
- Named entity recognition for financial entities
- Topic modeling for thematic analysis
- Earnings call analysis: management tone, forward guidance extraction
- SEC filing analysis: 10-K/10-Q/8-K processing, change detection

### 9B: Transformer Architectures
- Attention mechanism (self-attention, multi-head attention)
- BERT: pre-training (MLM, NSP) and fine-tuning
- FinBERT, SEC-BERT: domain-adapted models
- Large Language Models: GPT-4, Claude for financial analysis
- RAG (Retrieval Augmented Generation): combining retrieval with generation
- Fine-tuning vs prompting vs RAG: when to use each

### 9C: Alternative Data
- What alternative data is: any non-traditional data source
- Types: satellite imagery, credit card data, web scraping, app usage, job postings
- Alpha lifecycle of alternative data: discovery → adoption → crowding → decay
- Vendor landscape: Quandl, RavenPack, Thinknum, Orbital Insight
- Legal and ethical considerations: insider trading laws, GDPR, web scraping legality

### Resources

**Primary textbook:**
- **"Natural Language Processing with Transformers" — Tunstall, von Werra, Wolf**
  - End-to-end NLP with Hugging Face. Fine-tuning, deployment, evaluation.
  - Time: 20 hours

**Research papers:**
- **Araci (2019) — "FinBERT: Financial Sentiment Analysis with Pre-Trained Language Models"**
- **Yang et al. (2020) — "FinBERT: A Pretrained Language Model for Financial Communications"**
- **Huang, Wang & Yang (2023) — "FinGPT: Democratizing Internet-Scale Data for Financial LLMs"**
- **Wu et al. (2023) — "BloombergGPT: A Large Language Model for Finance"**
- **Loughran & McDonald (2011) — "When Is a Liability Not a Liability?"**
  - The Loughran-McDonald financial sentiment word list. Still the standard.
- **Ke, Kelly & Xiu (2019) — "Predicting Returns with Text Data"**
  - ML + NLP for return prediction. Shows NLP signals have genuine predictive power.

**Practical courses:**
- **Hugging Face NLP Course** (free) — focus on Ch. 1-4 and 7
- **DeepLearning.ai — NLP Specialization** (Coursera)

**Your advantage**: You've already built RAG pipelines, sentiment analysis, and document processing in the Alpha Lab. Frame this experience directly.

**Estimated time: 30-40 hours**

---

## Part 10: Portfolio Construction & Risk Management

**Why**: Signals are worthless without portfolio construction. A quant researcher at a $1M salary doesn't just find signals — they build portfolios that optimally exploit those signals while managing risk. This is where money is actually made.

**What you need to know:**

### 10A: Portfolio Optimization
- Mean-variance optimization (Markowitz) and its problems (estimation error amplification)
- Shrinkage estimators: Ledoit-Wolf, James-Stein
- Black-Litterman model (combining market equilibrium with investor views)
- Hierarchical Risk Parity (López de Prado) — robust to estimation error
- Risk parity (Bridgewater-style: equal risk contribution)
- Robust optimization: worst-case approaches, uncertainty sets

### 10B: Risk Models
- Factor risk models: fundamental (Barra/Axioma), statistical (PCA), hybrid
- Specific risk: idiosyncratic risk estimation
- Stress testing: historical scenarios, hypothetical scenarios, reverse stress tests
- VaR: parametric, historical, Monte Carlo, expected shortfall (CVaR)
- Tail risk: extreme value theory, copulas for joint tail dependence

### 10C: Portfolio Constraints
- Turnover constraints (limiting trading costs)
- Sector/industry constraints
- Beta neutrality (removing market risk)
- Factor neutrality (isolating specific factor exposures)
- Liquidity constraints
- Tracking error constraints (for benchmark-relative strategies)

### Resources

**Primary textbook:**
- **"Active Portfolio Management" — Grinold & Kahn**
  - THE book for institutional portfolio management. Chapters 1-14.
  - Time: 35 hours

**Supplementary:**
- **"Robust Portfolio Optimization and Management" — Fabozzi, Kolm, Pachamanova & Focardi**
  - Advanced portfolio construction with realistic constraints.
  - Time: 15 hours (selective chapters)

- **"Quantitative Risk Management" — McNeil, Frey & Embrechts**
  - Rigorous treatment of risk measurement. EVT, copulas, credit risk.
  - Time: 15 hours (Ch. 1-7)

**Research papers:**
- **Ledoit & Wolf (2004) — "A Well-Conditioned Estimator for Large-Dimensional Covariance Matrices"**
  - Shrinkage estimation. Used everywhere.
- **López de Prado (2016) — "Building Diversified Portfolios that Outperform Out of Sample"**
  - Hierarchical Risk Parity. The alternative to Markowitz.
- **Black & Litterman (1992) — "Global Portfolio Optimization"**
  - The BL model. How to combine views with equilibrium.
- **Qian (2005) — "Risk Parity Portfolios"**
  - The original risk parity paper.

**Key interview concepts:**
- "Why doesn't mean-variance optimization work in practice?" → "Estimation error in expected returns is enormous. Small changes in input → wild changes in optimal weights. The optimizer is an 'error maximizer' — it overweights assets with overestimated returns and underweights those with underestimated returns."
- "How do you build a risk model?" → "Factor model: returns = factor_loadings × factor_returns + specific_returns. Estimate factor covariance matrix (low-dimensional) and specific variance (diagonal). Total covariance = BΣB' + D. This is well-conditioned even for 3000+ stocks."

**Estimated time: 40-50 hours**

---

## Part 11: Backtesting & Research Methodology

**Why**: The difference between a $200K ML engineer and a $1M quant researcher is RIGOR. Most backtests are wrong. Most published signals don't work out-of-sample. Knowing why — and how to avoid the pitfalls — is the core skill.

**What you need to know:**
- Types of backtest bias: survivorship, look-ahead, selection, data-snooping
- Walk-forward validation vs in-sample/out-of-sample split
- Deflated Sharpe ratio (Bailey & López de Prado)
- Combinatorial purged cross-validation (CPCV)
- White's reality check, stepwise SPA test (Hansen)
- The multiple testing nightmare: with 1000 tested strategies, expect Sharpe > 2.3 by chance
- Transaction cost modeling: commission, spread, market impact, delay
- Capacity estimation: at what AUM does the strategy break?
- Regime-conditional analysis: does it work in all environments?
- Paper trading: the final validation before real money

### Resources

**Primary:**
- **"Evidence-Based Technical Analysis" — David Aronson**
  - The scientific method applied to trading. Hypothesis testing, data snooping, multiple testing.
  - Time: 15 hours

- **López de Prado — "Advances in Financial ML", Ch. 11-18**
  - Backtesting, cross-validation, feature importance, bet sizing.
  - Time: 15 hours (re-read from Part 8)

**Research papers:**
- **Bailey & López de Prado (2014) — "The Deflated Sharpe Ratio"**
  - How to adjust Sharpe for the number of strategies tested.
- **Harvey & Liu (2015) — "Backtesting"**
  - A framework for evaluating backtests.
- **Bailey et al. (2014) — "Pseudo-Mathematics and Financial Charlatanism"**
  - Why most backtests are wrong. Required reading.

**Estimated time: 20-25 hours**

---

## Part 12: Execution & Implementation

**Why**: The "last mile" of quant research. Your beautiful signal means nothing if you can't execute it at scale.

**What you need to know:**
- Execution algorithms: VWAP, TWAP, IS (implementation shortfall), POV
- Optimal execution: Almgren-Chriss framework, urgency parameter
- Execution quality measurement: slippage analysis, IS decomposition
- Order management systems: how quant funds structure their trading infrastructure
- Latency considerations: you don't need microsecond latency for fundamental quant, but you need sub-minute
- Data infrastructure: tick data storage, feature computation at scale, real-time pipelines

### Resources

- **"Algorithmic Trading and DMA" — Barry Johnson**
  - Execution algorithms, market structure, DMA. Practical.
  - Time: 15 hours

- **"Optimal Trading Strategies" — Robert Kissell**
  - Transaction cost models, optimal execution.
  - Time: 10 hours (selected chapters)

**Estimated time: 15-20 hours**

---

## Part 13: Interview Preparation

**Why**: You need all the knowledge above, but you ALSO need to deliver it in a specific interview format.

### What Quant Interviews Look Like

**Round 1: Phone Screen (45-60 min)**
- Probability puzzles (brainteasers)
- Basic statistics questions
- "Tell me about your research"

**Round 2: Technical Interview (60-90 min)**
- Deeper statistics / econometrics
- ML methodology questions
- Finance knowledge (factors, asset pricing)
- Coding (live or take-home)

**Round 3: Research Presentation (45-60 min)**
- Present a piece of original research
- They'll challenge every assumption
- **Use the Alpha Lab as your presentation**

**Round 4: On-Site (4-6 hours)**
- Multiple interviewers
- System design
- Case study (here's a dataset, find a signal)
- Cultural fit / PM interaction simulation

### Resources

**Books:**
- **"Heard on the Street" — Timothy Crack**
  - Classic quant interview book. Probability, statistics, finance questions.
  - Time: 15 hours

- **"Quant Job Interview Questions and Answers" — Mark Joshi**
  - More advanced. Derivatives pricing, stochastic calculus questions.
  - Time: 10 hours

- **"A Practical Guide to Quantitative Finance Interviews" — Xinfeng Zhou**
  - Brainteasers, probability, statistics. 200+ problems.
  - Time: 15 hours

**Online:**
- **QuantNet forums** — real interview questions from Citadel, Two Sigma, DE Shaw
- **Glassdoor** — search "quant researcher" for company-specific questions
- **r/quant** — Reddit community with interview experiences

### Practice Problems (Do 5 per day in Week 7-8)

**Probability:**
1. You flip a fair coin until you get two heads in a row. What's the expected number of flips?
2. You have two envelopes, one with $X, one with $2X. You pick one and see $100. Should you switch?
3. Expected number of draws to complete a set of N distinct coupons?

**Statistics:**
4. You have a strategy with Sharpe 1.5 over 3 years. What's the probability this is due to luck?
5. How would you test if two time series are cointegrated? Walk through the steps.
6. Your regression has R² = 0.01 for stock returns. Is this useful?

**Finance:**
7. Explain the Fama-French 5-factor model. Which factors do you trust and why?
8. You find a signal with IC = 0.05. How much alpha does this translate to?
9. Why does momentum crash? How would you hedge this risk?

**ML:**
10. Why does standard K-fold CV overstate performance in financial data?
11. Your XGBoost model has train Sharpe 3.0 and test Sharpe 0.5. Diagnose.
12. How would you detect regime changes in real-time?

**Estimated time: 30-40 hours**

---

## Complete Study Plan: 22-Week Schedule

| Week | Part | Focus | Hours | Key Deliverable |
|------|------|-------|-------|----------------|
| 1 | 1 | Linear Algebra | 20 | PCA on stock returns matrix |
| 2 | 1-2 | Optimization + Probability basics | 20 | Quadratic optimization for 5-stock portfolio |
| 3 | 2 | Probability deep dive | 20 | Fat-tails analysis on real return data |
| 4 | 3A | Classical statistics | 20 | Multiple testing correction on 50 factors |
| 5 | 3B | Regression | 25 | Fama-MacBeth regression on momentum factor |
| 6 | 3C | Financial econometrics | 25 | GARCH model for volatility forecasting |
| 7 | 4 | Stochastic calculus | 25 | Black-Scholes implementation from SDE |
| 8 | 5A | Asset pricing foundations | 20 | CAPM test on 100 stocks |
| 9 | 5B | Factor models | 25 | 5-factor model implementation |
| 10 | 5C | Anomalies | 15 | Literature review: 10 key factor papers |
| 11 | 6 | Cross-sectional research | 25 | Full factor research pipeline |
| 12 | 7 | Market microstructure | 20 | Transaction cost model |
| 13 | 8A-B | Financial ML foundations | 25 | XGBoost cross-sectional predictor |
| 14 | 8C-D | ML methodology | 25 | Walk-forward with purged CV |
| 15 | 9A | Financial NLP | 20 | Fine-tune FinBERT on earnings calls |
| 16 | 9B-C | Transformers + alt data | 20 | NLP signal with IC measurement |
| 17 | 10A | Portfolio optimization | 25 | HRP vs Markowitz comparison |
| 18 | 10B-C | Risk models + constraints | 20 | Full risk model for 200-stock portfolio |
| 19 | 11 | Backtesting methodology | 20 | Deflated Sharpe on all your strategies |
| 20 | 12 | Execution | 15 | TCA analysis on paper trades |
| 21 | 13 | Interview prep — problems | 25 | 100 practice problems |
| 22 | 13 | Interview prep — mock interviews | 20 | 5 mock system design sessions |
| | | **Total** | **~500** | |

---

## The One Thing That Will Get You Hired

The Alpha Lab is not just a project — it is your **research presentation**. When they ask "present your research," you present:

1. "I built a multi-agent quant research platform with 9 specialist agents"
2. "Each agent does real computation — z-scores, backtests, factor models, NLP sentiment"
3. "I validate every signal with deflated Sharpe ratio to prevent overfitting"
4. "I measure signal decay to know when an edge is dying"
5. "I tested this on real data: mean reversion shows IC of 0.03 with 62% hit rate, surviving deflated Sharpe correction"
6. "The system runs autonomously and presents a morning brief with proposed trades"
7. "I built it because I believe the future of quant research is AI agents backed by statistical rigor — not LLM opinions"

That's the presentation that gets you to $1M.
