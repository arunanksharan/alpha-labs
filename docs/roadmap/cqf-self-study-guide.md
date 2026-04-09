# CQF Curriculum — Self-Study Guide

## Official CQF Structure

The CQF (Certificate in Quantitative Finance) is a 6-month part-time program. Below is their exact structure with self-study resources for each module. Whether you enroll or self-study, this is the roadmap.

**Source**: [cqf.com](https://www.cqf.com/about-cqf/program-structure/cqf-qualification), [Wall Street Mojo CQF Guide](https://www.wallstreetmojo.com/certificate-in-quantitative-finance-cqf-exam/)

---

## CQF Official Reading List

These are the books the CQF ships to enrolled students:

1. **"Paul Wilmott on Quantitative Finance"** — Paul Wilmott (3 volumes, the magnum opus)
2. **"Paul Wilmott Introduces Quantitative Finance"** — Paul Wilmott (lighter version of above)
3. **"Frequently Asked Questions in Quantitative Finance"** — Paul Wilmott
4. **"Asset Price Dynamics, Volatility and Prediction"** — Stephen Taylor
5. **"Monte Carlo Methods in Finance"** — Peter Jaeckel
6. **"The xVA Challenge"** — Jon Gregory
7. **"Machine Learning: An Applied Mathematics Introduction"** — Paul Wilmott
8. **"Python for Finance"** — Yves Hilpisch

---

## Pre-Course: Primers (Optional but Recommended)

### Mathematics Primer (~12 hours)
**What CQF covers**: Calculus, differential equations, linear algebra, probability, statistics

**Self-study resources:**
| Topic | Resource | Time |
|-------|----------|------|
| Calculus refresher | **3Blue1Brown — "Essence of Calculus"** (YouTube, 12 videos) | 4 hrs |
| Linear Algebra | **3Blue1Brown — "Essence of Linear Algebra"** (YouTube, 16 videos) | 3 hrs |
| Differential equations | **Khan Academy — Differential Equations** (free) | 3 hrs |
| Probability & Statistics | **Khan Academy — Statistics and Probability** (free) | 4 hrs |

**Book**: "Mathematics for Finance" — Marek Capinski & Tomasz Zastawniak (short, focused)

### Python Primer (~8 hours)
**What CQF covers**: Python syntax, mathematical libraries, financial applications

**Self-study:**
| Topic | Resource | Time |
|-------|----------|------|
| Python fundamentals | **You already know this** — skip | 0 |
| NumPy/Pandas for finance | **"Python for Finance" — Yves Hilpisch**, Ch. 1-6 | 4 hrs |
| Financial computations | Implement: compound returns, portfolio metrics, Monte Carlo in Python | 4 hrs |

### Finance Primer (~10 hours)
**What CQF covers**: Macroeconomics, capital markets, money markets, derivatives, commodities

**Self-study:**
| Topic | Resource | Time |
|-------|----------|------|
| Capital markets overview | **Khan Academy — Finance and Capital Markets** (free) | 3 hrs |
| Derivatives basics | **Hull — "Options, Futures, and Other Derivatives"**, Ch. 1-5 | 4 hrs |
| Money markets + fixed income | **Fabozzi — "Bond Markets, Analysis and Strategies"**, Ch. 1-3 | 3 hrs |

---

## Module 1: Building Blocks of Quantitative Finance

### What CQF Covers
- Random walks and Brownian motion
- Stochastic calculus and Ito's Lemma
- Stochastic differential equations (SDEs)
- Fokker-Planck and Kolmogorov equations
- Binomial models for option pricing
- Martingale theory
- Transition from discrete to continuous models

### Self-Study Resources

**Primary book:**
- **"Paul Wilmott Introduces Quantitative Finance"** — Ch. 1-10
  - Wilmott's writing is uniquely accessible for stochastic calculus
  - Time: 20 hours

**Alternative / supplementary:**
- **"Stochastic Calculus for Finance I" — Steven Shreve**
  - Vol I covers binomial models (discrete time). Start here if Wilmott is too fast.
  - Time: 15 hours

- **"Stochastic Calculus for Finance II" — Steven Shreve**
  - Vol II covers continuous time: Brownian motion, Ito's lemma, SDEs, martingales
  - Ch. 1-5 are essential
  - Time: 20 hours

**Video lectures:**
- **MIT 18.S096 — "Topics in Mathematics with Applications in Finance"**
  - MIT OCW (free). Lectures 1-8 cover stochastic calculus for finance.
  - Taught by practitioners from finance industry.
  - Time: 8 hours

- **QuantPy — "Stochastic Calculus for Quants"** (YouTube playlist)
  - Short, focused videos on each concept

**Practice:**
- Derive Ito's Lemma for f(S) = log(S) where dS = μSdt + σSdW
- Solve the geometric Brownian motion SDE
- Price a European call option using the binomial model (10 steps, then 100 steps)
- Implement a Monte Carlo simulation for option pricing in Python

**Time estimate: 30-35 hours**

---

## Module 2: Quantitative Risk & Return

### What CQF Covers
- Modern Portfolio Theory (Markowitz)
- Capital Asset Pricing Model (CAPM)
- Efficient frontier construction
- Sharpe ratio, information ratio, Sortino ratio
- Volatility modeling: EWMA, ARCH, GARCH
- Value at Risk (VaR): parametric, historical, Monte Carlo
- Expected Shortfall (CVaR)
- Factor models and risk decomposition

### Self-Study Resources

**Primary books:**
- **"Paul Wilmott Introduces Quantitative Finance"** — Ch. 21-26 (risk and portfolio)
- **"Active Portfolio Management" — Grinold & Kahn** — Ch. 1-8
  - THE institutional portfolio management book. Covers IR, IC, alpha, risk models.
  - Time: 25 hours

**For volatility modeling:**
- **"Analysis of Financial Time Series" — Ruey Tsay** — Ch. 3-4 (ARCH/GARCH)
  - Time: 8 hours

**For VaR:**
- **"Quantitative Risk Management" — McNeil, Frey & Embrechts** — Ch. 2-4
  - Rigorous treatment of VaR, CVaR, coherent risk measures
  - Time: 10 hours

**Video:**
- **MIT 15.401 — "Finance Theory I"** (MIT OCW)
  - Covers CAPM, efficient markets, portfolio theory
- **Ben Lambert — "GARCH Models"** (YouTube)
  - Clear explanation of volatility modeling

**Practice:**
- Build an efficient frontier for 10 stocks using real data
- Implement GARCH(1,1) from scratch in Python (don't use arch library first)
- Compute 1-day and 10-day VaR using all three methods (parametric, historical, Monte Carlo)
- Compare: does Ledoit-Wolf shrinkage improve your portfolio vs raw sample covariance?

**Assessment note**: CQF Exam 1 covers Modules 1-2

**Time estimate: 30-35 hours**

---

## Module 3: Equities & Currencies

### What CQF Covers
- Black-Scholes-Merton model (derivation and intuition)
- Risk-neutral pricing
- Delta hedging and the Greeks (Delta, Gamma, Vega, Theta, Rho)
- Implied volatility and the volatility smile/surface
- Exotic options pricing
- Numerical methods: finite differences, Monte Carlo, binomial trees
- FX options and currency models
- Python implementation of option pricing

### Self-Study Resources

**Primary books:**
- **"Paul Wilmott Introduces Quantitative Finance"** — Ch. 11-20 (Black-Scholes, Greeks, exotics)
- **"Options, Futures, and Other Derivatives" — John Hull** — Ch. 13-26
  - The industry standard. Every quant has read this.
  - Time: 30 hours

**For numerical methods:**
- **"Monte Carlo Methods in Finance" — Peter Jaeckel** — Ch. 1-8
  - How to actually implement pricing models computationally
  - Time: 15 hours

- **"Numerical Methods in Finance with C++" — Daniel Duffy** — selected chapters
  - Finite difference methods for PDE-based pricing
  - Time: 10 hours (reference only)

**For volatility:**
- **"The Volatility Surface" — Jim Gatheral**
  - THE book on implied volatility. Stochastic vol, local vol, SVI parameterization.
  - Time: 15 hours

**Video:**
- **Emanuel Derman — "The Volatility Smile"** (various lectures on YouTube)
  - Derman invented the local volatility model at Goldman. Hear it from the source.

**Practice:**
- Derive Black-Scholes from Ito's Lemma (pen and paper)
- Implement Black-Scholes pricer + all 5 Greeks in Python
- Build an implied volatility surface from market option prices (use yfinance options data)
- Price a barrier option using Monte Carlo simulation
- Implement a finite difference solver for the Black-Scholes PDE

**Assessment note**: CQF Exam 2 covers Module 3

**Time estimate: 35-40 hours**

---

## Module 4: Data Science & Machine Learning I

### What CQF Covers
- Supervised learning: regression, classification
- Linear regression, logistic regression, regularization (Lasso, Ridge, Elastic Net)
- k-Nearest Neighbors (k-NN)
- Support Vector Machines (SVM)
- Decision trees and ensemble methods (Random Forest, Gradient Boosting, XGBoost)
- Cross-validation and model selection
- Feature engineering for financial data
- Bias-variance tradeoff

### Self-Study Resources

**Primary books:**
- **"Machine Learning: An Applied Mathematics Introduction" — Paul Wilmott**
  - Written for the CQF. Mathematical treatment of ML algorithms.
  - Time: 15 hours

- **"An Introduction to Statistical Learning" (ISLR) — James, Witten, Hastie, Tibshirani**
  - Free PDF at statlearning.com. THE ML textbook.
  - Ch. 1-8
  - Time: 20 hours

**For financial applications:**
- **"Advances in Financial Machine Learning" — López de Prado** — Ch. 1-10
  - Why ML in finance is different. Triple barrier, purged CV, feature importance.
  - Time: 20 hours

- **"Machine Learning for Algorithmic Trading" — Stefan Jansen** — Ch. 1-12
  - Practical implementations with Python.
  - Time: 15 hours

**Video:**
- **Stanford CS229 — Machine Learning (Andrew Ng)** — YouTube (full course)
  - The classic. Focus on: regression, classification, regularization, trees, ensemble.
- **StatQuest — "Machine Learning"** (YouTube playlist by Josh Starmer)
  - Brilliant visual explanations. Watch the XGBoost, Random Forest, and cross-validation videos.

**Practice:**
- Build an XGBoost model to predict cross-sectional stock returns
- Implement purged K-fold cross-validation from scratch
- Compare: Lasso vs Ridge vs Elastic Net for feature selection on 50 financial features
- Compute feature importance using MDI, MDA, and SFI (López de Prado methods)

**Time estimate: 35-40 hours**

---

## Module 5: Data Science & Machine Learning II

### What CQF Covers
- Unsupervised learning: clustering (K-means, hierarchical, DBSCAN)
- Dimensionality reduction: PCA, t-SNE, autoencoders
- Deep learning fundamentals: neural networks, backpropagation
- Convolutional Neural Networks (CNNs)
- Recurrent Neural Networks (RNNs, LSTMs)
- Natural Language Processing (NLP)
- Transformer architectures and attention mechanisms
- Reinforcement learning fundamentals
- Applications in algorithmic trading and portfolio management

### Self-Study Resources

**Primary books:**
- **"Deep Learning" — Goodfellow, Bengio, Courville** — Ch. 1-12
  - The deep learning bible. Free at deeplearningbook.org
  - Focus on: Ch. 6 (feedforward), 9 (CNN), 10 (RNN), 11 (attention)
  - Time: 25 hours

- **"Natural Language Processing with Transformers" — Tunstall, von Werra, Wolf**
  - Hugging Face team. Practical transformer NLP.
  - Time: 15 hours

**For financial NLP:**
- **FinBERT paper — Araci (2019)**: BERT for financial sentiment
- **BloombergGPT paper — Wu et al. (2023)**: Finance-specific LLM
- **Ke, Kelly & Xiu (2019) — "Predicting Returns with Text Data"**: NLP signals for trading

**For RL in finance:**
- **"Reinforcement Learning" — Sutton & Barto** — Ch. 1-6
  - Free at incompleteideas.net. The standard textbook.
  - Time: 15 hours

**Video:**
- **Stanford CS224N — NLP with Deep Learning** (YouTube)
  - Transformer architecture, attention, BERT, fine-tuning
- **DeepMind — "Reinforcement Learning" lecture series** (YouTube)
  - David Silver's RL course. The best there is.
- **Andrej Karpathy — "Neural Networks: Zero to Hero"** (YouTube)
  - Build transformers from scratch. Incredibly clear.

**Practice:**
- Fine-tune FinBERT on earnings call transcripts, measure sentiment accuracy
- Build a simple LSTM for volatility prediction (it should work for vol, even if not for returns)
- Cluster stocks by return correlation using hierarchical clustering, compare with GICS sectors
- Implement a basic RL agent for simple portfolio allocation (2-3 assets)

**Assessment note**: CQF Exam 3 covers Modules 4-5

**Time estimate: 35-40 hours**

---

## Module 6: Fixed Income & Credit

### What CQF Covers
- Bond pricing and yield curve construction
- Duration, convexity, DV01
- Short-rate models: Vasicek, Cox-Ingersoll-Ross (CIR), Hull-White
- HJM framework (Heath-Jarrow-Morton)
- LIBOR/SOFR market models
- SABR stochastic volatility model
- Credit risk: structural models (Merton), reduced-form models
- Credit derivatives: CDS, CDOs
- CVA, DVA, xVA
- Copula models for default correlation

### Self-Study Resources

**Primary books:**
- **"Paul Wilmott on Quantitative Finance"** — Vol 2, Ch. 28-40 (fixed income) and Vol 3 (credit)
  - Time: 25 hours

- **"Options, Futures, and Other Derivatives" — Hull** — Ch. 31-35 (interest rate models, credit risk)
  - Time: 15 hours

- **"The xVA Challenge" — Jon Gregory**
  - THE book on CVA/DVA/xVA. Increasingly important post-2008.
  - Time: 15 hours (selective reading)

**For interest rate models:**
- **"Interest Rate Models: Theory and Practice" — Brigo & Mercurio**
  - The definitive reference. Dense but complete.
  - Time: 20 hours (selected chapters)

**For credit:**
- **"Credit Risk Modeling" — David Lando** — Ch. 1-6
  - Structural and reduced-form models explained clearly.
  - Time: 10 hours

**Video:**
- **QuantPy — "Fixed Income"** (YouTube playlist)
- **Patrick Boyle — "Credit Default Swaps Explained"** (YouTube)

**Practice:**
- Build a yield curve from swap rates using bootstrapping
- Implement Vasicek and CIR models, simulate interest rate paths
- Price a CDS using the reduced-form approach
- Compute CVA for a simple interest rate swap

**Time estimate: 30-35 hours**

---

## Advanced Electives (Choose 2)

CQF offers electives after Module 6. You select 2 based on your career focus.

### Elective Options (Typical)

| Elective | Best For | Self-Study Resource |
|----------|----------|-------------------|
| **Algorithmic Trading** | Systematic quant roles | "Algorithmic Trading" — Ernest Chan |
| **Advanced Volatility Modeling** | Derivatives/vol trading | "The Volatility Surface" — Jim Gatheral |
| **Advanced Risk Management** | Risk quant roles | "Quantitative Risk Management" — McNeil, Frey & Embrechts |
| **Portfolio Management** | Buy-side quant/PM roles | "Active Portfolio Management" — Grinold & Kahn |
| **Computational Finance** | Pricing/numerical methods | "Monte Carlo Methods in Finance" — Jaeckel |
| **Behavioral Finance** | Research roles | "Thinking, Fast and Slow" — Kahneman |
| **Python for Finance** | All roles | "Python for Finance" — Hilpisch |

**Recommended for your profile:**
1. **Algorithmic Trading** (directly relevant to your Alpha Lab)
2. **Portfolio Management** (the highest-value skill for senior roles)

---

## Final Project

The CQF capstone is a research project applying course concepts to a real financial problem.

**Your project**: The Alpha Lab is already a better capstone than most CQF students produce. If you enroll, use it.

---

## Total Self-Study Time Estimate

| Component | Hours |
|-----------|-------|
| Primers (math, Python, finance) | 20-25 |
| Module 1: Stochastic Calculus | 30-35 |
| Module 2: Risk & Return | 30-35 |
| Module 3: Equities & Currencies | 35-40 |
| Module 4: ML I | 35-40 |
| Module 5: ML II | 35-40 |
| Module 6: Fixed Income & Credit | 30-35 |
| Electives (2) | 30-40 |
| Practice problems & projects | 40-50 |
| **Total** | **285-340 hours** |

At 15-20 hours/week: **4-5 months** of dedicated self-study.

---

## CQF vs Self-Study: What Enrollment Gets You

| What You Get | Self-Study | CQF Enrolled |
|-------------|-----------|-------------|
| Knowledge | Same (books + videos are available to everyone) | Same |
| Credential on resume | No | Yes ("CQF" after your name) |
| Live lectures + Q&A | No | Yes (2x/week, 2.5 hrs each) |
| Faculty support | No | Yes (1-on-1 help) |
| Peer network | No | Yes (3,500+ alumni globally) |
| Lifelong Learning access | No | Yes (900+ hours of extra content) |
| Exam discipline | Self-motivated | 3 exams + final project |
| Cost | ~$500 (books) | ~$15,000 SGD |
| Time | 4-5 months | 6 months |

**The honest trade-off**: The knowledge is freely available. The credential, network, and structure cost $15K. Whether that's worth it depends on whether "CQF" on your resume opens doors that your project alone can't.

For Singapore specifically: CQF is recognized at GIC, Temasek, DBS, and all major funds with SG presence. It won't replace a PhD, but it signals "this person invested in quantitative finance education beyond their engineering background."
