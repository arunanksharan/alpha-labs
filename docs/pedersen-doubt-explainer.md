# Pedersen "Efficiently Inefficient" — Doubt Explainer

Questions asked while reading the book, answered with intuitive explanations. A living document — grows as you read.

---

## Q1: What is alpha and beta? (Pages 47-48)

### The Core Equation

```
R_t^e = α + β × R_t^(M,e) + ε_t
```

**Your strategy's return = free ride on the market + your actual skill + random noise.**

### Beta (β): How Much You're Just Riding the Market

Beta measures how much of your return is just because the market went up. You didn't earn it through skill — you got it for free by being exposed to the market.

**Example**: If β = 0.5, and the market goes up 10%, your strategy goes up 5% just from market exposure.

**Analogy**: You're surfing. Beta is the wave. If the ocean rises 10 feet, every surfer rises 10 feet. That's not skill — that's the wave carrying you. You can get beta for nearly free — buy an index fund for 0.03% fees. Nobody should pay hedge fund fees (2% + 20%) for beta.

### Alpha (α): Your Actual Skill

Alpha is what's left AFTER you subtract the market's contribution. It's the return you generated through genuine insight.

**Pedersen calls it "the Holy Grail"** — alpha is the ONLY thing hedge funds are paid to produce.

**Example**: A market-neutral fund (β = 0) with α = 6% makes 6% regardless of whether the market goes up or down.

**CAPM says alpha should be ZERO.** Every hedge fund's existence is a bet that CAPM is wrong — that skill exists, and they have it.

### Epsilon (ε): The Noise

Random stuff. Your biotech stocks went up because an FDA approval came through, not because of the market or your skill. Averages to zero over time.

### Market Neutrality

If your strategy has β = 0.7, you're 70% exposed to the market. To isolate pure alpha, you **short β dollars of the market** for every dollar of your strategy:

```
market-neutral return = R_strategy - β × R_market = α + ε
```

Market goes up 10%? Doesn't matter. Market crashes 20%? Also doesn't matter. Your return is purely your alpha plus noise.

---

## Q2: What does R_t^e = R_t - R^f mean? What is R^f? (Page 47)

### R^f (Risk-Free Rate)

R^f is the return you get for doing absolutely nothing risky. Park your money in a US Treasury bill, earn ~5% per year. Zero skill, zero risk, guaranteed.

### Why Subtract It?

If you earned 12% and the risk-free rate was 5%, you didn't really earn 12% through investing. You earned 7% above what a sleeping person would have earned.

**Excess return**: R_t^e = R_t - R^f = the interesting part.

### R_t^(M,e) (Market Excess Return)

Same logic applied to the stock market. If S&P returned 10% and risk-free is 5%, market excess return is 5%. That's what investors earned for taking the RISK of being in stocks.

### "Running a Regression"

You have 60 months of data. Plot your excess return (Y) vs market excess return (X). 60 dots. Draw the best-fit line.

- **β (slope)**: For every 1% the market goes up, how much do you go up?
- **α (y-intercept)**: When market excess return is zero, what do YOU earn? That's your skill.
- **ε (scatter)**: How far each dot is from the line. Noise.

---

## Q3: What is the t-statistic? Why is it important? How is it different from z-statistic? (Page 48)

### What It Is

You run a backtest. Alpha = 6%. The question: **"Is that skill or luck?"**

The t-statistic answers this:

```
t = estimate / standard error = α / SE(α)
```

### Intuition

Two fund managers both claim 6% alpha:

- **Manager A**: Returns are 6%, 5.5%, 6.2%, 5.8%, 6.1% (very consistent) → t-stat is HUGE
- **Manager B**: Returns are 20%, -15%, 30%, -8%, 6% (wildly inconsistent) → t-stat is SMALL

Both have α = 6%. But Manager A is probably skill, Manager B is probably luck.

### The Rule

- t > 2.0: probably real (95% confidence)
- t > 3.0: almost certainly real
- t < 2.0: could easily be luck

### Why It Matters in Finance

**Prevents self-deception**: Test 100 strategies, ~5 will have t > 2.0 by pure chance.

**The language of the industry**: When a PM asks "what's the t-stat?" they're asking "should I bet real money?"

**Connection to Sharpe**: t ≈ IR × √(years). SR of 1.0 needs 4 years for t = 2.0. SR of 0.5 needs 16 years.

### t-stat vs z-stat

| | Z-statistic | T-statistic |
|---|---|---|
| When to use | You KNOW the true σ | You ESTIMATE σ from sample |
| Distribution | Normal (same shape always) | T-distribution (fatter tails) |
| In finance | Almost never | Almost always |
| Large samples | Identical | Converges to z |

In practice: always use t-statistics. When someone says "z-stat" in finance, they mean t-stat.

---

## Q4: What is the t-distribution? How does standard error get calculated? Why √n?

### T-Distribution

The normal distribution assumes you know the true σ. The t-distribution says: **what if you estimated σ from a small sample?**

Your estimate of σ is itself uncertain. The t-distribution captures this double uncertainty with **fatter tails** — extreme values are more likely because your small sample could be misleading.

With 5 observations: very fat tails. With 30+: barely different from normal. With 1000: identical to normal.

### Standard Error: Why √n

```
SE = σ / √n
```

**The thought experiment:**

- 1 month of data: your estimate IS that one noisy month. Uncertainty = full σ.
- 4 months: highs and lows partially cancel. Uncertainty = σ/2.
- 100 months: lots of cancellation. Uncertainty = σ/10.

**The math:**

```
Var(sum of n independent things) = n × σ²
Var(average) = Var(sum/n) = nσ²/n² = σ²/n
SE = √(σ²/n) = σ/√n
```

**The brutal implication for hedge funds:**

| Sharpe Ratio | Years for t > 2.0 |
|---|---|
| 0.5 | 16 years |
| 1.0 | 4 years |
| 1.5 | ~2 years |
| 2.0 | 1 year |

A decent strategy (SR 0.5) needs 16 years of data to prove it's not luck.

---

## Q5: How does annualized variance work? Why var × n?

### Why Variance Scales Linearly

Each day's return is independent, with variance σ²_daily.

Over 2 days: R_2day = R_day1 + R_day2

```
Var(R_day1 + R_day2) = Var(R_day1) + Var(R_day2) = 2σ²
```

Because independent variances ADD.

Over n days: Var = n × σ²_daily. Over 252 trading days:

```
σ²_annual = 252 × σ²_daily
σ_annual = σ_daily × √252
```

### Why √n for Standard Deviation but n for Variance

Variance measures SQUARED dispersion. Adding n things → n × σ².
Standard deviation is the square root: √(nσ²) = σ√n.

**Random walk analogy**: After 100 random steps of length 1, you're ~10 steps from start (√100), not 100.

### Critical Assumption

This assumes returns are INDEPENDENT across time. When this breaks:
- **Autocorrelation (momentum)**: variance grows FASTER than n
- **Mean reversion**: variance grows SLOWER than n
- **Volatility clustering**: some periods are much riskier than the average

---

## Q6: "3% return at 2% risk, SR = 1.5 — is that good enough?" (Pages 50-51)

### The Investor's Complaint

"Only 3%? I wanted more." Pedersen says this investor is thinking wrong.

### Why Sharpe Matters More Than Raw Return

SR = 1.5 is exceptional. The return is low but the QUALITY is incredible. With leverage:

```
No leverage:   3% return,  2% risk,  SR = 1.5
2x leverage:   6% return,  4% risk,  SR = 1.5
5x leverage:  15% return, 10% risk,  SR = 1.5
```

Sharpe stays the same. You just turn up the volume. **You CAN eat risk-adjusted returns** — leverage converts quality into quantity.

### The Trap: Hidden Tail Risk

Some strategies LOOK low-risk because they collect small premiums most of the time. Then one day:

```
Months 1-23:  +0.5% each (selling options, collecting premium)
Month 24:     -25% (market crash, options exercised)
```

For 23 months this looks like SR = 3.0+. But the "risk" was hidden — it was tail risk that hadn't appeared yet. The Sharpe ratio was LYING.

**Pedersen's test**: Is the risk genuinely low (diversified stat-arb)? Or is it an illusion (option selling, carry trades)?

---

## Q7: What is the difference between the SR and IR denominators? Where does σ(ε) come from?

### The Confusion

```
SR = E(R - R^f) / σ(R - R^f)       ← total volatility in denominator
IR = α / σ(ε)                       ← residual volatility in denominator
```

Why different denominators?

### Where σ(ε) Comes From

Start with the regression: R_t^e = α + β R_t^(M,e) + ε_t

Hedge out the market (subtract β × market):

```
R_t^e - β R_t^(M,e) = α + ε_t
```

This is your **market-neutral return**. Its mean is α (because E(ε) = 0). Its std dev is σ(ε) (because α is constant, only ε varies).

So IR = α / σ(ε) is the "Sharpe ratio of your market-neutral return."

### Why They're Different

| | Sharpe | Information Ratio |
|---|---|---|
| **Numerator** | Total excess return | Alpha only |
| **Denominator** | Total volatility | Residual volatility only |
| **Market helps?** | Yes (market up → higher SR) | No (market stripped out) |

### Concrete Example

```
Fund A: β=1.0, α=3%, σ(total)=15%, σ(ε)=5%
Fund B: β=0.0, α=3%, σ(total)=5%,  σ(ε)=5%

Fund A SR = (3% + ~7% market) / 15% ≈ 0.67     ← looks good (market helps)
Fund B SR = 3% / 5% = 0.60                       ← looks slightly worse

Fund A IR = 3% / 5% = 0.60                       ← same skill
Fund B IR = 3% / 5% = 0.60                       ← same skill
```

Fund A has better Sharpe only because it rides the market. Both have identical IR because both have 3% alpha with 5% residual noise.

### Pedersen's Two Definitions of IR Are the Same

**Definition 1**: IR = α / σ(ε)
**Definition 2**: IR = E(R - R^b) / σ(R - R^b)

If benchmark = market and β = 1: R - R^b = α + ε, so E(R - R^b) = α and σ(R - R^b) = σ(ε). Same formula.

### When to Use Which

- **SR**: Is this fund worth investing in? (total performance)
- **IR**: Is this manager actually skilled? (strips out market)

A fund with high SR and zero IR is just the market with fees. SR flatters it, IR exposes it.

---

## Q8: Sortino Ratio — why only downside risk? What is the indicator function? (Page 32)

### The Problem Sortino Solves

Sharpe treats ALL volatility as bad. But if your fund returned +15% one month and +2% the next, Sharpe penalizes the +15% month. As an investor, you're not complaining about +15%. That's a good surprise.

**Sortino says: only penalize the bad surprises.**

### Built With Numbers

Two funds, 12 months:

```
Fund A: +2%, +3%, +1%, -4%, +2%, +5%, -1%, +3%, +2%, -3%, +4%, +1%
Fund B: +8%, +1%, -2%, +10%, -1%, +3%, +12%, +0%, -3%, +7%, +2%, +1%
```

Both average ~1.25% monthly excess return.

**Sharpe** (uses total volatility):
```
Fund A: σ = 2.7%  →  SR = 1.25/2.7 = 0.46
Fund B: σ = 4.8%  →  SR = 1.25/4.8 = 0.26
Sharpe says A is better.
```

But Fund B's extra volatility is mostly from big UP months (+8%, +10%, +12%). The down months are similar to Fund A.

**Sortino** (uses only downside volatility):

Step 1 — Set MAR = 0% (minimum acceptable return)

Step 2 — Filter with indicator function 1_{R < MAR}:
```
Fund A: kept -4%, -1%, -3%     → downside σ ≈ 2.5%
Fund B: kept -2%, -1%, -3%     → downside σ ≈ 1.6%
```

Step 3 — Compute:
```
Sortino A = 1.25% / 2.5% = 0.50
Sortino B = 1.25% / 1.6% = 0.78
Sortino says B is better.
```

Fund B's downside is actually SMALLER. The extra volatility was all upside.

### The Indicator Function 1_{R < MAR}

A gate that filters returns:

```
1_{R < MAR} = 1  if return is BELOW the minimum (keep it — it's a loss)
1_{R < MAR} = 0  if return is ABOVE the minimum (ignore it — it's fine)

R × 1_{R<MAR}:
  Month with R = -4%:  -4% × 1 = -4%  (kept)
  Month with R = +8%:  +8% × 0 =  0%  (ignored)
```

Take std dev of this filtered series → that's σ_downside.

### Pedersen's Key Point

**Sortino assumes**: You don't care whether you make 5% each year or 1% then 9%. Both average 5%, both have zero losses. Identical Sortino.

**Sharpe assumes**: You PREFER 5% each year. The 1%/9% path is "riskier" even though you never lost money.

### In Practice

Report both. A strategy where Sortino >> Sharpe has **positive skew** — surprises tend to be upside. That's a feature, not a bug.

---

## Q9: Why does checking P&L more frequently make risk feel worse? (Page 34, Table 2.1)

### The Setup

You have a strategy with annual Sharpe = 1.0. Genuinely excellent. Over a year, you expect to make money with high probability. But how does it FEEL day to day?

### How Sharpe Changes With Time Horizon

SR scales by √n. So if annual SR = 1.0:

```
SR over 4 years   = 1.0 × √4   = 2.0
SR over 1 year    = 1.0 × √1   = 1.0
SR over 1 quarter = 1.0 / √4   = 0.50
SR over 1 month   = 1.0 / √12  = 0.29
SR over 1 day     = 1.0 / √252 = 0.063
SR over 1 minute  = ≈ 0.003
```

Same strategy. Different horizons. Wildly different Sharpe ratios.

### Pedersen's Table 2.1 (Annual SR = 1.0)

```
Time Horizon    │  Sharpe Ratio  │  Pr(Loss)  │  How It Feels
────────────────┼────────────────┼────────────┼──────────────────
4 years         │     2.0        │    2.3%    │  "Almost never lose"
1 year          │     1.0        │   16.0%    │  "Lose 1 in 6 years"
1 quarter       │     0.5        │   31.0%    │  "Lose 1 in 3 quarters"
1 month         │     0.29       │   39.0%    │  "Lose 4-5 months per year"
1 day           │     0.063      │   47.5%    │  "Lose almost every other day"
1 minute        │     0.003      │   49.9%    │  "Basically a coin flip"
```

A strategy with SR = 1.0 loses money **47.5% of all trading days**. Almost every other day. At the minute level: 49.9% — essentially 50/50.

### The Psychological Impact

A PM with a live P&L screen glances at it 50 times a day. Each glance: ~50% chance of seeing red. Rational brain knows "annual SR = 1.0, I'll make money." Emotional brain sees "I'm losing RIGHT NOW."

This is why experienced PMs check P&L once or twice a day, not continuously. The STRATEGY didn't change — only how often you LOOKED.

---

## Q10: How does Sharpe ratio convert to loss probability? (Page 34)

### The Formula

```
Pr(loss) = Pr(N < -SR)
```

Where N is a standard normal random variable (mean 0, std dev 1).

### Step-by-Step Derivation

**Step 1**: Any return can be written as:

```
R^e = E(R^e) + σ × N
       ↑          ↑
   expected    random surprise
   (average)   (noise scaled by volatility)
```

Why σ × N? Because N has std dev = 1, but your actual returns have std dev = σ. Multiplying scales the noise to your real volatility.

**Concrete example**: E(R^e) = 0.5% monthly, σ = 2% monthly.

```
If N = +1.0 → R^e = 0.5% + 2% × 1.0  = +2.5%   (good month)
If N = -0.5 → R^e = 0.5% + 2% × (-0.5) = -0.5%  (bad month)
If N = -1.5 → R^e = 0.5% + 2% × (-1.5) = -2.5%  (terrible month)
```

**Step 2**: When do you lose money? When R^e < 0:

```
E(R^e) + σ × N < 0          (return is negative)
σ × N < -E(R^e)              (move E(R^e) to right side)
N < -E(R^e) / σ              (divide both sides by σ)
N < -SR                       (because SR = E(R^e)/σ by definition)
```

**In English**: You lose whenever random noise N is more negative than your Sharpe ratio. SR is how many standard deviations of noise your expected return can absorb before going negative.

**Step 3**: How often does N go below -SR? Look it up in the standard normal table:

```
Pr(N < x):

x = -3.0  →   0.13%     SR=3.0 → lose 0.13% of the time (almost never)
x = -2.0  →   2.3%      SR=2.0 → lose 2.3% of the time
x = -1.0  →  16.0%      SR=1.0 → lose 16% of the time
x = -0.5  →  31.0%      SR=0.5 → lose 31% of the time
x = -0.063→  47.5%      SR=0.063 → lose 47.5% (daily SR from annual 1.0)
x =  0.0  →  50.0%      SR=0.0 → coin flip (no edge at all)
```

### Why This Makes Sense Intuitively

**High Sharpe (SR = 2.0)**: Your expected return is 2 standard deviations above zero. Noise has to be EXTREMELY negative (below -2σ) to pull you into a loss. That's rare — only 2.3%.

**Low Sharpe (SR = 0.063, daily)**: Your expected return is only 0.063 standard deviations above zero. Even mild negative noise pushes you into a loss. That happens 47.5% of the time.

**Zero Sharpe (SR = 0)**: Your expected return IS zero. Any negative noise at all gives you a loss. That's exactly 50% — a coin flip. You have no edge.

### The Punchline

One number (annual Sharpe) tells you the probability of losing money at ANY time horizon:

```
1. Convert: SR_period = SR_annual / √(periods per year)
2. Look up: Pr(N < -SR_period)
3. That's your loss probability at that horizon
```

This is why SR is the universal language of hedge funds — it encodes everything about the strategy's risk-return in a single number.

---

## Q11: HWM, Drawdown, and MDD — what are they and why do they matter? (Pages 35-36)

### High Water Mark (HWM) — Your Personal Best

HWM = the highest value a fund has ever reached. It only moves UP, never down.

```
Month 1:  $100 → $110    HWM = $110 (new high)
Month 2:  $110 → $120    HWM = $120 (new high)
Month 3:  $120 → $105    HWM = $120 (stays — didn't beat it)
Month 4:  $105 → $115    HWM = $120 (still below peak)
Month 5:  $115 → $125    HWM = $125 (new high!)
```

**Why it matters for fees**: Hedge funds charge 20% of profits, but only on profits ABOVE the HWM. If a fund drops from $120 to $105, it earns zero performance fees until it gets back above $120. This prevents charging fees on "recovering losses."

### Drawdown (DD) — How Deep in the Hole

```
DD_t = (HWM_t - P_t) / HWM_t
```

How far you've fallen from your peak, as a percentage.

```
P=$120, HWM=$120  →  DD = 0%     (at peak)
P=$105, HWM=$120  →  DD = 12.5%  (down 12.5% from peak)
P=$115, HWM=$120  →  DD = 4.2%   (recovering but still below)
P=$125, HWM=$125  →  DD = 0%     (new peak, drawdown over)
```

### Maximum Drawdown (MDD) — The Worst Pain Ever

```
MDD = the largest DD that has ever occurred
```

MDD never resets. If you were once 25% below peak, MDD = 25% forever. It's the fund's worst moment on record.

**Why MDD matters more than volatility**: A 25% drawdown means investors see $1M become $750K. They panic, redeem, and the fund sells at the worst time. A PM who draws down 20%+ often gets fired.

### The Drawdown Control Rule (from Ch. 4)

```
VaR ≤ MADD - DD

"Risk budget = max acceptable drawdown minus current drawdown"

If MADD = 25% and you're already 15% down:
  Remaining budget = 10%. Reduce positions.
```

---

## Q12: The Stale Price Trick — how fake alpha appears from lagged reporting (Pages 36-37)

### The Setup

Late Capital Management (LCM) does the simplest thing possible — invests 100% in the S&P 500. Zero skill. But it reports returns **one month late**. January's return appears in February's numbers.

### Why This Breaks Beta

When you regress LCM's February return against the market's February return, you're actually comparing:

```
LCM's February number = January's market return
Market's February number = February's market return

cov(January market, February market) ≈ 0
(markets don't remember last month)
```

The regression sees no relationship. It concludes β ≈ 0.

### Where Fake Alpha Comes From

With β ≈ 0:

```
R_LCM = α + 0 × R_market + ε
```

The regression attributes ALL returns to alpha. The stock market earns ~7% above risk-free historically. So α ≈ 7%. LCM appears to have 7% alpha with zero market exposure.

**But it's completely fake.** LCM is just the market with a reporting lag.

### Why This Happens in Real Life

Funds that hold illiquid securities (private equity, distressed debt, real estate, OTC derivatives) have STALE prices — values from days or weeks ago. When the market crashes today, their positions still show yesterday's higher prices.

```
Day 1: Market -5%. Liquid fund shows -5%. Illiquid fund shows 0% (stale).
Day 2: Market +2%. Liquid fund shows +2%. Illiquid fund shows -5% (delayed).
```

The illiquid fund's lagged returns make beta look low and alpha look high. Same risk, hidden by pricing delays.

### Pedersen's Fix: Lagged Beta Regression

Add lagged market returns to the regression:

```
R_t = α_adj + β⁰R_mkt_t + β¹R_mkt_{t-1} + ... + β^L R_mkt_{t-L} + ε

True beta = β⁰ + β¹ + ... + β^L
```

For LCM: β⁰ ≈ 0 but β¹ ≈ 1.0. So true β = 1.0 and α_adjusted ≈ 0. Correct — no skill.

### The Lesson

When someone shows you β ≈ 0 and high alpha, ask: **"Are the prices real-time or stale?"** Low beta from illiquid assets is often fake hedging, not real hedging.

---

*Last updated: April 11, 2026. Add more questions as you read.*
