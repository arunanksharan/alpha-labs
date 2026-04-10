# Pedersen "Efficiently Inefficient" — Math & Statistics Companion

Read this alongside the book. Every notation, concept, and equation explained intuitively.

---

## Part A: Core Math Operations (Used Throughout)

### Summation — Σ (Sigma)

**Notation**: Σᵢ xᵢ or Σᵢ₌₁ⁿ xᵢ

**What it means**: Add them all up.

```
Σᵢ₌₁³ xᵢ = x₁ + x₂ + x₃

If x₁ = 2, x₂ = 5, x₃ = 3:
Σ = 2 + 5 + 3 = 10
```

When Pedersen writes Σᵢ(Fᵢ - F̄)Rᵢ, it means: for every stock i, compute (Fᵢ - F̄) × Rᵢ, then add them all up.

### Product — Π (Pi)

**Notation**: Πᵢ₌₁ⁿ (1 + Rᵢ)

**What it means**: Multiply them all together. Used for compounding returns.

```
Π₌₁³ (1 + Rᵢ) = (1 + R₁) × (1 + R₂) × (1 + R₃)

If R₁ = 10%, R₂ = -5%, R₃ = 8%:
= 1.10 × 0.95 × 1.08 = 1.1286
Total return = 12.86%
```

This is how geometric average works: [(1+R₁)(1+R₂)...(1+Rₙ)]^(1/n) - 1

### Subscripts and Superscripts

Pedersen uses these heavily. Here's the pattern:

```
Rₜ     — return at time t (subscript = time)
Rⁱ     — return of security i (superscript = which security)
Rₜⁱ    — return of security i at time t (both)
Rᵉ     — excess return (e = excess, above risk-free)
R^f     — risk-free return (f = free)
R^M     — market return (M = market)
R^(M,e) — market EXCESS return (both M and e)
R^HML   — return of the HML factor (high minus low)
R^SMB   — return of the SMB factor (small minus big)
```

### max and min

**Notation**: max_{s≤t} Pₛ

**What it means**: The largest value of P across all times s up to time t.

Pedersen uses this for High Water Mark:
```
HWM_t = max_{s≤t} Pₛ

Translation: look at every price from the beginning up to now.
Pick the highest one. That's the high water mark.
```

Similarly: MDD_t = max_{j≤t} DD_j means "the worst drawdown we've seen so far."

### Absolute Value — |x|

**Notation**: |x|

**What it means**: The magnitude, ignoring sign.

```
|5| = 5
|-3| = 3
|0| = 0
```

Used when Pedersen talks about position sizes or t-statistics: "a t-statistic above 2 in absolute value" means t > 2 OR t < -2.

---

## Part B: Probability & Statistics Concepts

### Expected Value — E(X)

**Notation**: E(X), E(R), E(R - R^f)

**What it means**: The average outcome over many repetitions. The "long-run average."

```
E(X) = Σ probability(xᵢ) × xᵢ

Coin flip: E(payoff) = 0.5 × $10 + 0.5 × (-$5) = $2.50
```

**In Pedersen**: E(R - R^f) is the expected excess return — what you'd earn on average above the risk-free rate.

**Key property**: E(aX + bY) = aE(X) + bE(Y). Expectation of a sum is the sum of expectations. Always. Even if X and Y are correlated.

### Variance — var(X) or σ²

**Notation**: var(X), σ², σ²(R)

**What it means**: How spread out the values are. The average squared distance from the mean.

```
var(X) = E[(X - E(X))²]

In practice with data:
var = [(R₁ - R̄)² + (R₂ - R̄)² + ... + (Rₜ - R̄)²] / (T - 1)
```

**Why squared?** Positive and negative deviations would cancel if you just averaged them. Squaring makes everything positive.

**Why T-1?** Called "Bessel's correction." You estimated R̄ from the same data, using up one "degree of freedom." For large T, it barely matters.

**Key properties**:
- var(aX) = a² × var(X) — scaling by a multiplies variance by a²
- var(X + Y) = var(X) + var(Y) + 2cov(X,Y)
- If X and Y are independent: var(X + Y) = var(X) + var(Y)

### Standard Deviation — σ

**Notation**: σ, σ(R), σ(ε), σ^downside

**What it means**: Square root of variance. In the same units as the original data (percentage for returns), making it interpretable.

```
σ = √(variance)

If monthly returns bounce between -3% and +5% around a mean of 1%:
σ ≈ 2-3% per month
```

**Pedersen uses several specific σ's:**
- σ(R - R^f): volatility of excess returns (used in Sharpe ratio)
- σ(ε): idiosyncratic volatility (used in Information ratio)
- σ^downside: only counts negative returns (used in Sortino ratio)
- σ^annual = σ × √n: annualized volatility

### Covariance — cov(X, Y)

**Notation**: cov(X, Y), cov(Rⁱ, R^M)

**What it means**: How two things move together.

```
cov(X, Y) = E[(X - E(X)) × (Y - E(Y))]

Positive: when X is above average, Y tends to be above average too
Negative: when X is above average, Y tends to be below average
Zero: no relationship
```

**Pedersen uses this for beta**:
```
β = cov(Rⁱ, R^M) / var(R^M)

Translation: how much does security i co-move with the market,
scaled by how much the market moves on its own.
```

### Correlation — ρ (rho) or corr(X, Y)

**Notation**: ρ, corr(X, Y)

**What it means**: Covariance normalized to be between -1 and +1.

```
ρ = cov(X, Y) / (σ(X) × σ(Y))

ρ = +1: perfect positive relationship (move together exactly)
ρ = 0: no linear relationship
ρ = -1: perfect negative relationship (move exactly opposite)
```

**In Pedersen**: "correlations matter" for portfolio construction — a long position with high correlation to other longs is bad (concentrated risk), but high correlation with shorts is good (natural hedge).

### Regression — OLS (Ordinary Least Squares)

**Notation**: Y = a + bX + ε

**What it means**: Draw the best-fit line through data. "Best" = minimizes the sum of squared errors (distances from points to line).

**Pedersen's key regressions:**

1. **Single factor**: Rₜᵉ = α + β R_t^(M,e) + εₜ
2. **Three factor**: Rₜᵉ = α + β^M R_t^(M,e) + β^HML R_t^HML + β^SMB R_t^SMB + εₜ
3. **Predictive**: Rₜ₊₁ᵉ = a + bFₜ + εₜ₊₁ (note: signal at time t, return at t+1)
4. **Cross-sectional**: Rᵢₜ₊₁ = a + bFᵢₜ + εᵢₜ₊₁ (across stocks i at each time t)
5. **Stale prices**: Rₜᵉ = α + β⁰Rₜ^(M,e) + β¹R_{t-1}^(M,e) + ... + εₜ

**How OLS finds b** (the slope):
```
b̂ = Σ(Fₜ - F̄)(Rₜ₊₁) / Σ(Fₜ - F̄)²

Numerator: how much signal and return move together
Denominator: how spread out the signal is
```

**Pedersen's deep insight (Section 3.4)**: A regression coefficient IS a trading strategy's profit. If b > 0, buying when signal is high and selling when low makes money. The t-statistic of b IS the strategy's Sharpe ratio (approximately).

### The Hat — b̂ (b-hat)

**Notation**: b̂, α̂, σ̂

**What the hat means**: An ESTIMATE from data, not the true value.

```
b̂ = estimated slope from regression (from your sample of data)
b  = true slope (unknown, what you're trying to estimate)

b̂ might be 0.5, but the true b could be 0.3 or 0.7.
The standard error tells you how uncertain the estimate is.
```

### Standard Error — SE

**Notation**: SE(b̂), σ̂/√T

**What it means**: How uncertain your estimate is. How much b̂ would change if you had different data.

```
SE = σ̂ / √T

σ̂ = how noisy individual observations are
T = how many observations you have
√T = the "averaging effect" — more data → more precise estimate
```

### t-statistic

**Notation**: t = b̂ / SE(b̂), or t = √T × b̂/σ̂

**What it means**: How many standard errors your estimate is from zero. Measures "is this real or luck?"

```
t > 2.0: probably real (95% confidence)
t > 3.0: almost certainly real
t < 2.0: might be luck

t = √T × SR  (t-stat equals √years × Sharpe ratio)
```

### Probability — Pr(...)

**Notation**: Pr(R^e < 0), Pr(loss ≤ $10M)

**What it means**: The probability that something happens. A number between 0 and 1 (or 0% and 100%).

```
Pr(R^e < 0) = probability of losing money in a given period
Pr(loss ≤ $10M) = 95%  means "95% of the time, losses are ≤ $10M"
```

**In Pedersen's Table 2.1**: With annual Sharpe of 1.0:
- Pr(loss in a year) = 16%
- Pr(loss in a month) = 39%
- Pr(loss on a day) = 47.5%
Same strategy, different time horizons, wildly different loss probabilities.

### Normal Distribution — N(μ, σ²)

**Notation**: N, Pr(N < -SR)

**What it means**: The bell curve. Most returns cluster around the mean, with tails dying off symmetrically.

**Pedersen's key usage**: Loss probability = Pr(N < -SR) where N is standard normal. This converts Sharpe ratio directly to probability of loss.

**The critical caveat** (Pedersen acknowledges): Real returns are NOT normal. They have fat tails — extreme events happen much more often than the bell curve predicts. This is why VaR and stress tests matter.

---

## Part C: Finance-Specific Measures

### Return (R_t) and Excess Return (R_t^e)

```
R_t = (P_t - P_{t-1}) / P_{t-1}     simple return
R_t = ln(P_t / P_{t-1})              log return

R_t^e = R_t - R^f                    excess return (above risk-free)
```

### Alpha (α) and Beta (β)

From regression: R_t^e = α + β R_t^(M,e) + ε_t

- **α**: your skill (return not explained by market)
- **β**: your market exposure (how much you ride the wave)
- **ε**: noise (luck, idiosyncratic risk)

### Sharpe Ratio (SR)

```
SR = E(R - R^f) / σ(R - R^f)

Annualization: SR_annual = SR_period × √n
where n = periods per year (252 for daily, 12 for monthly)
```

### Information Ratio (IR)

```
IR = α / σ(ε)

Measures skill per unit of skill-risk.
Strips out market exposure entirely.
```

### Alpha-to-Margin Ratio (AM)

```
AM = α / margin

How much alpha per dollar of capital tied up.
AM = IR × σ(ε) / margin
```

### Sortino Ratio (S)

```
S = E(R - R^f) / σ^downside

σ^downside = σ(R × 1_{R < MAR})

Only penalizes DOWNSIDE volatility.
1_{R < MAR} is the indicator function: 1 if return is below minimum acceptable, 0 otherwise.
```

### Value at Risk (VaR)

```
Pr(loss ≤ VaR) = confidence level (e.g., 95%)

95% VaR of $10M means:
"95% of the time, we lose less than $10M"
"5% of the time, we could lose MORE than $10M"
```

### Expected Shortfall (ES) / CVaR

```
ES = E(loss | loss > VaR)

The AVERAGE loss on days when you exceed VaR.
VaR tells you the threshold; ES tells you how bad it gets beyond that.
```

### High Water Mark (HWM) and Drawdown (DD)

```
HWM_t = max_{s≤t} P_s        highest value ever reached

DD_t = (HWM_t - P_t) / HWM_t   how far below peak (as percentage)

MDD_t = max_{j≤t} DD_j         worst drawdown ever
```

### Drawdown Control Rule

```
VaR_t ≤ MADD - DD_t

"Your risk budget (VaR) must be less than the gap between
your maximum acceptable drawdown and your current drawdown."

If MADD = 25% and you're already 15% down:
VaR must be ≤ 10%. Reduce positions.
```

---

## Part D: Portfolio Math (Chapter 4)

### Portfolio — x = (x¹, ..., xˢ)

**Notation**: x is a vector. Each x^s is dollars invested in security s.

```
x = ($30K in AAPL, $20K in MSFT, $50K in bonds)

The remainder (W - x¹ - x² - ... - xˢ) goes to risk-free.
```

### Portfolio Return

```
Future wealth = x¹(1+R¹) + ... + xˢ(1+Rˢ) + (W - Σxˢ)(1+R^f)

Simplified in excess returns:
Portfolio excess return = x¹R^(e,1) + x²R^(e,2) + ... + xˢR^(e,s)
```

### Mean-Variance Optimization

```
Maximize: x'E(R^e) - (γ/2) x'Ω x

Where:
x'E(R^e) = expected portfolio excess return
x'Ω x    = portfolio variance (risk)
γ         = risk aversion (higher = more conservative)
Ω         = covariance matrix (how all securities co-move)
```

**Solution**: x* = γ⁻¹ Ω⁻¹ E(R^e)

Translation: invest more in securities with high expected return, low variance, and low correlation with others.

### Covariance Matrix — Ω

```
Ω is an S×S matrix where entry (i,j) = cov(Rⁱ, Rʲ)

For 3 securities:
Ω = | var(R¹)     cov(R¹,R²)  cov(R¹,R³) |
    | cov(R²,R¹)  var(R²)     cov(R²,R³) |
    | cov(R³,R¹)  cov(R³,R²)  var(R³)    |

Diagonal = each security's variance
Off-diagonal = how pairs co-move
```

### Portfolio Variance

```
var(portfolio) = x' Ω x = Σᵢ Σⱼ xⁱ xʲ cov(Rⁱ, Rʲ)

For 2 securities:
var = (x¹)²σ₁² + (x²)²σ₂² + 2x¹x²cov(R¹,R²)
```

This is why correlations matter — the cross-term 2x¹x²cov can be large.

---

## Part E: Trading & Implementation (Chapter 5)

### Transaction Costs

```
TC^$ = P^execution - P^before          effective cost ($ per share)
TC   = TC^$ / P^before                  as percentage

TC^realized = P^execution - P^later     realized cost (price reversal)

TC^VWAP = P^execution - P^VWAP         cost vs volume-weighted average
```

### Expected Transaction Cost

```
Ê(TC) = (1/I) Σᵢ TCᵢ

Average cost across I observed trades.
```

### Implementation Shortfall (IS)

```
IS = TC + OC

IS = performance of paper portfolio - performance of live portfolio

TC = transaction costs (what you paid to trade)
OC = opportunity cost (profits you missed by not trading)
```

### Capacity

As assets grow, market impact increases. There's an optimal size where total dollar profit is maximized — beyond that, impact eats the alpha.

---

## Part F: Notation Quick Reference

| Symbol | Name | Meaning |
|--------|------|---------|
| Σ | Sigma (sum) | Add everything up |
| Π | Pi (product) | Multiply everything together |
| E(X) | Expected value | Long-run average |
| var(X), σ² | Variance | Squared spread |
| σ | Std deviation | Spread in original units |
| cov(X,Y) | Covariance | How X and Y co-move |
| ρ | Correlation | Normalized covariance, -1 to +1 |
| R_t | Return | Period return |
| R^f | Risk-free rate | Treasury bill rate |
| R^e | Excess return | R - R^f |
| α | Alpha | Skill (regression intercept) |
| β | Beta | Market exposure (regression slope) |
| ε | Epsilon | Noise (regression residual) |
| 1_{condition} | Indicator | 1 if true, 0 if false |
| b̂ | b-hat | Estimated value from data |
| SR | Sharpe ratio | Excess return / volatility |
| IR | Information ratio | Alpha / tracking error |
| AM | Alpha-to-margin | Alpha / margin requirement |
| S | Sortino ratio | Excess return / downside vol |
| VaR | Value at Risk | Maximum loss at confidence level |
| ES | Expected Shortfall | Average loss beyond VaR |
| HWM | High water mark | Highest value ever |
| DD | Drawdown | How far below peak |
| MDD | Max drawdown | Worst DD ever |
| MADD | Max acceptable DD | Your drawdown budget |
| TC | Transaction cost | Cost of trading |
| IS | Implementation shortfall | TC + opportunity cost |
| OC | Opportunity cost | Cost of NOT trading |
| x | Portfolio | Vector of positions |
| Ω | Covariance matrix | All pairwise covariances |
| γ | Risk aversion | How much you hate risk |
| λ | Risk premium | Compensation per unit of risk |
| ψ | Margin premium | Compensation for capital |
| F | Forecasting variable | Signal used to predict returns |
| F̄ | Average of F | Mean signal across stocks or time |
| T | Number of time periods | Length of data |
| n | Periods per year | 252 (daily), 12 (monthly) |
| W | Wealth | Total capital |
| P | Price | Security price |
| m | Margin | Capital required per dollar invested |

---

Keep this file open as you read. When you hit a symbol you don't recognize, search this page. By the time you finish Pedersen, every symbol will be second nature.
