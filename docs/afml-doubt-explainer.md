# López de Prado "Advances in Financial Machine Learning" — Doubt Explainer

Questions asked while reading the book, answered with intuitive explanations. A living document — grows as you read.

---

## Q1: Where does the expression E_0[θ_T] = E_0[T] × (P[b_t=1] - P[b_t=-1]) come from? (Page 29-30, Ch 2)

### The Setup

We have T ticks in a bar. Each tick is labeled b_t ∈ {+1, -1} by the tick rule.

The tick imbalance is:

```
θ_T = Σ b_t   (sum from t=1 to T)
```

We want to know: **what imbalance should we *expect* in a bar of T ticks?** If the actual imbalance exceeds the expected imbalance, something unusual is happening → create a new bar.

### The Derivation — Step by Step

**Step 1: Expected value of a single b_t**

Each b_t is either +1 or -1. The expected value of any single tick label is:

```
E[b_t] = (+1) × P[b_t = 1] + (-1) × P[b_t = -1]
       = P[b_t = 1] - P[b_t = -1]
```

This is just the definition of expected value: sum of (each outcome × its probability).

**Concrete example**: If 55% of ticks are buys and 45% are sells:

```
E[b_t] = (+1)(0.55) + (-1)(0.45) = 0.55 - 0.45 = +0.10
```

On average, each tick contributes +0.10 to the imbalance. There's a slight buy bias.

**Step 2: Expected value of the sum θ_T**

θ_T is a sum of T terms. The expected value of a sum equals the sum of the expected values (linearity of expectation — always works, even if terms are correlated):

```
E[θ_T] = E[Σ b_t] = Σ E[b_t] = T × E[b_t]
```

There are T ticks, each contributing E[b_t] in expectation, so:

```
E[θ_T] = T × (P[b_t = 1] - P[b_t = -1])
```

**Step 3: But T itself is random**

Here's the subtle part. We don't know how many ticks will be in the bar (that's what we're trying to determine!). So T is also a random variable.

LdP writes E_0[T] — the expected bar length estimated at the *beginning* of the bar (that's what the subscript 0 means). He's using the approximation:

```
E_0[θ_T] ≈ E_0[T] × (P[b_t = 1] - P[b_t = -1])
```

This treats T and b_t as approximately independent — the number of ticks in a bar doesn't systematically affect whether each tick is a buy or sell. This is a reasonable assumption.

**Step 4: Simplify using P[buy] + P[sell] = 1**

Since P[b_t = 1] + P[b_t = -1] = 1, we can write P[b_t = -1] = 1 - P[b_t = 1]:

```
P[b_t = 1] - P[b_t = -1] = P[b_t = 1] - (1 - P[b_t = 1])
                           = 2P[b_t = 1] - 1
```

So:

```
E_0[θ_T] = E_0[T] × (2P[b_t = 1] - 1)
```

This is the form LdP uses on page 29.

### Why This Formula Makes Intuitive Sense

Think of it as: **expected imbalance = (how many ticks) × (bias per tick)**

| Scenario | E_0[T] | P[buy] | 2P-1 | E_0[θ_T] | Interpretation |
|---|---|---|---|---|---|
| Balanced, short bar | 500 | 0.50 | 0.00 | 0 | No expected imbalance |
| Balanced, long bar | 2000 | 0.50 | 0.00 | 0 | Still no bias, just more ticks |
| Buy-biased, short bar | 500 | 0.55 | 0.10 | 50 | Expect 50 more buys than sells |
| Buy-biased, long bar | 2000 | 0.55 | 0.10 | 200 | Expect 200 more buys than sells |
| Strong sell bias | 1000 | 0.40 | -0.20 | -200 | Expect 200 more sells than buys |

### The Threshold Condition

Now the bar creation rule becomes clear:

```
T* = arg min { |θ_T| ≥ E_0[T] × |2P[b_t = 1] - 1| }
```

In words: **close the bar at the earliest tick T where the actual imbalance |θ_T| exceeds the expected imbalance.**

If the expected imbalance is 50 (slight buy bias in a typical bar), but the actual imbalance has already hit 50 after only 300 ticks (instead of the usual 1000), that's a signal: "buying pressure is arriving much faster than normal → informed traders are likely present → create a bar NOW."

### The Key Math Concept: Linearity of Expectation

The entire derivation rests on one fact from probability:

```
E[X₁ + X₂ + ... + X_T] = E[X₁] + E[X₂] + ... + E[X_T]
```

This works **regardless of whether the X's are independent or correlated.** It's one of the most powerful and simple results in probability. You don't need to know the joint distribution, you don't need independence — it just works.

This is why the formula is so clean: the expected sum = (number of terms) × (expected value per term).

### What E_0 Means (The Subscript 0)

The subscript 0 in E_0 means "the expectation computed using information available at time 0" — the start of the bar. In practice:

- E_0[T] is estimated as an **EWMA of previous bar lengths**: `E_0[T] = α × T_prev + (1-α) × E_prev[T]`
- P[b_t = 1] is estimated as an **EWMA of buy fractions in previous bars**

Both are backward-looking estimates that update after each bar closes. They're not fixed constants — they adapt to changing market conditions.

---

## Q2: What is Section 2.4 "Dealing with Multi-Product Series" about? (Pages 59-62, Ch 2)

### The Problem: You Can't Just Glue Prices Together

This section addresses a fundamental data engineering problem. There are two scenarios where naively concatenating price series breaks everything:

**Scenario A: Futures contracts expire (same product, different months)**

Futures contracts have expiry dates. You trade the March contract, then switch ("roll") to June:

```
March 19 (ESH26, last day):  price = $5,250
March 20 (ESM26, first day): price = $5,265
```

The $15 gap is NOT a market move. It's the **cost of carry** — the June contract is more expensive because it includes 3 extra months of interest rates minus dividends. If you naively chain these prices, your backtest sees a fake +$15 jump. Over years of quarterly rolls, these phantom jumps compound into massive distortions.

**Scenario B: Different products entirely (comparing apples to oil)**

If you're building signals across ES (S&P futures), CL (crude oil), and GC (gold):

```
ES moves 10 points  → $500 per contract   (point value = $50)
CL moves 10 points  → $10,000 per contract (point value = $1,000)
GC moves 10 points  → $1,000 per contract  (point value = $100)
```

"10 points" means completely different things. You cannot compare raw price moves across instruments.

### LdP's Solutions (Ranked from Simple to Sophisticated)

#### Solution 1: Use Returns Instead of Prices

```
r_t = (p_t - p_{t-1}) / p_{t-1}
```

A 1% move is a 1% move regardless of which contract you're in. This eliminates the roll gap problem because the gap happens *between* contracts, not *within* a return calculation.

**Limitation**: You lose the price level. A stock at $5 behaves differently from a stock at $500 (different tick dynamics, different option chains). Returns discard this information.

#### Solution 2: Roll-Adjusted Series (Backward Adjustment)

Take today's price as truth. Walk backward through history and subtract each roll gap:

```
Actual prices:
  March contract:  $5,200 → $5,230 → $5,250  |roll gap = $15|
  June contract:   $5,265 → $5,280 → $5,300

Backward-adjusted (subtract $15 from all March prices):
  $5,185 → $5,215 → $5,235 → $5,265 → $5,280 → $5,300
                              ↑ seamless transition, no gap
```

Now the series is continuous. Returns computed from this adjusted series are correct.

**But there's a catch**: The old prices ($5,185, $5,215...) are *not* the prices you actually traded at. This is fine for signal generation and pattern detection, but **wrong for P&L calculation**. If your backtest says "bought at $5,185," you actually bought at $5,200. Your P&L is off by $15 per contract.

**Forward adjustment** does the opposite — keeps old prices real, adjusts new ones. Same trade-off, just reversed.

#### Solution 3: Dollar-Risk Normalization (LdP's Preferred Approach)

Instead of adjusting prices, express everything in **dollar risk per unit of volatility**.

Every futures contract has a **point value** — the dollar amount one point of price movement is worth:

| Contract | Point Value | Price | Notional per Contract | Daily Vol (~) | Dollar Vol |
|---|---|---|---|---|---|
| ES (S&P 500) | $50 | 5,250 | $262,500 | 1.0% | $2,625 |
| NQ (Nasdaq) | $20 | 18,500 | $370,000 | 1.3% | $4,810 |
| CL (Crude Oil) | $1,000 | 75 | $75,000 | 2.0% | $1,500 |
| GC (Gold) | $100 | 2,350 | $235,000 | 0.8% | $1,880 |

**Dollar volatility** = price × point_value × percentage_volatility

This is the key normalization. Now you can compare:
- "ES moved 1 dollar-vol" = "CL moved 1 dollar-vol" = same risk
- Position sizing becomes: "I want $X of dollar-vol exposure" — applies uniformly across all products

#### Solution 4: The ETF Trick (For Equities)

For stock portfolios, use ETFs as proxies instead of tracking hundreds of individual stocks:

- SPY instead of 500 individual S&P stocks
- QQQ instead of 100 Nasdaq stocks
- XLF instead of individual bank stocks

The ETF automatically handles:
- Stock splits (AAPL splits 4:1 → ETF adjusts seamlessly)
- Dividends (reinvested or accounted for)
- Index reconstitution (stocks added/removed)
- Mergers and delistings

**LdP's warning about ETFs**:
- **Creation/redemption arbitrage** can distort intraday prices
- **Tracking error** — ETF returns ≠ index returns exactly
- **Survivorship bias** — backtest only contains current members, not past failures

#### Solution 5: Risk-Weighted Multi-Product Bars

The most sophisticated approach — building information bars *across* multiple products simultaneously:

```
Multi-product imbalance = Σ_i (w_i × b_{i,t} × v_{i,t} × pointvalue_i)
```

Where for each product i:
- `w_i` = weight (typically inverse of dollar volatility — so volatile products get less weight)
- `b_{i,t}` = tick direction (+1/-1) from the tick rule
- `v_{i,t}` = volume of the tick
- `pointvalue_i` = dollar value per point

This creates a single imbalance measure across your entire universe. A big buy in oil and a big sell in gold might cancel out (θ ≈ 0, no bar). But a big buy in BOTH oil and gold = strong imbalance (θ >> 0, create a bar). The latter suggests a macro event (inflation trade) that affects multiple assets simultaneously.

### Why This Matters Practically

| If you're trading... | You need... | Why |
|---|---|---|
| Single stock (AAPL) | Nothing from this section | No roll, no cross-product issues |
| Stock portfolio | Solution 4 (ETF trick) or returns | Handle splits, dividends |
| Single futures contract | Solution 2 (roll adjustment) | Handle contract expiry |
| Multi-asset futures | Solution 3 (dollar-risk normalization) | Compare across products |
| Cross-asset alpha signals | Solution 5 (risk-weighted bars) | Detect macro information flow |

### Connection to Alpha Lab

Alpha Lab currently uses daily equity OHLCV from YFinance — so we don't face the futures roll problem yet. But this section becomes critical when:

1. **Adding commodity/futures data** — must handle rolls correctly
2. **Comparing z-scores across stocks** — a z-score of -2 on AAPL vs TSLA means different things in dollar terms if TSLA is 3× more volatile
3. **Multi-asset portfolio construction** — position sizing must normalize by dollar volatility, not by share count or notional value
4. **Building cross-asset signals** — "risk-on" signals that fire when buying pressure appears simultaneously across equities, credit, and commodities

The key principle from this section: **always think in risk-adjusted units, never in raw prices, when comparing across instruments.**

---

## Q3: What is the Fixed Time Horizon Method and why does LdP say it's broken? (Pages 43-44, Ch 3)

### The Problem Being Solved

You have a features matrix X (rows are observations, columns are features). You want to train a supervised ML model. For supervised learning, you need **labels** — for each observation, you need to tell the model: "this was a BUY (+1), SELL (-1), or DO NOTHING (0)."

The question is: **how do you assign those labels?**

### The Fixed Time Horizon Method

This is what virtually every academic ML-in-finance paper does. It's the "naive" approach.

**The rule**: Look at the return `h` bars into the future. If it's big enough positive, label +1. If big enough negative, label -1. Otherwise, label 0.

### The Math — Unpacked

**Setup notation**:
- You have bars indexed `t = 1, ..., T` (think of these as days for now)
- You sampled `I` observations from these bars: `{X_i}` for `i = 1, ..., I`
- Each observation `X_i` happened at bar `t_{i,0}` (the bar index where you observed it)

**The return over the horizon**:

```
r_{t_{i,0}, t_{i,0}+h} = p_{t_{i,0}+h} / p_{t_{i,0}} - 1
```

In plain English: **the price `h` bars later, divided by the price now, minus 1.**

Example: AAPL is at $180 today (bar `t_{i,0}`). You set `h = 5` (look 5 days ahead). In 5 days AAPL is at $189.

```
r = 189/180 - 1 = 0.05 = +5%
```

**The labeling rule**:

```
y_i = { -1   if r < -τ         (big drop → SELL)
       {  0   if |r| ≤ τ        (small move → DO NOTHING)
       { +1   if r > τ          (big rise → BUY)
```

Where `τ` (tau) is a **threshold** you pick. Think of it as "how big does the move need to be before I care?"

### Concrete Example — Visualizing It

Let's say `τ = 2%` and `h = 10 days`:

```
Day 0: AAPL = $180    (this is our observation X_i, at bar t_{i,0})
Day 10: AAPL = ?      (this is bar t_{i,0} + h)

Scenario A: Day 10 price = $190
  r = 190/180 - 1 = +5.6%
  5.6% > 2% → y_i = +1 (BUY)    ✓ price went up enough

Scenario B: Day 10 price = $173
  r = 173/180 - 1 = -3.9%
  -3.9% < -2% → y_i = -1 (SELL)  ✓ price dropped enough

Scenario C: Day 10 price = $182
  r = 182/180 - 1 = +1.1%
  |1.1%| ≤ 2% → y_i = 0 (NOTHING)  move too small to care
```

Visually, imagine a horizontal band around the current price:

```
Price
  |
  |  - - - - - - - - - - - $183.60  (+2% = τ upper)
  |  ════════════════════   $180.00  (entry price)
  |  - - - - - - - - - - - $176.40  (-2% = τ lower)
  |
  |←————— h = 10 days ————→|
  Day 0                    Day 10

  If price on Day 10 is ABOVE upper line → label +1
  If price on Day 10 is BELOW lower line → label -1
  If price on Day 10 is BETWEEN the lines → label 0
```

### Why LdP Says This Method Is Broken

LdP gives three specific criticisms (page 44):

**Problem 1: Time bars have bad statistics**

Time bars (daily OHLCV) don't produce uniform information content. Monday at market open has 100x more activity than Wednesday at 2pm. You're feeding your ML model bars with wildly different information quality, but treating them identically.

**Problem 2: The threshold τ is fixed, but volatility changes**

This is the killer problem. Suppose you set `τ = 2%` (like in our example). But:

```
Period A: AAPL's daily vol = 4% (σ_{t_{i,0}} = 1E-4 per tick ≈ 4% daily)
  → A 2% move is LESS than one standard deviation
  → Happens all the time, basically noise
  → You're labeling noise as signal → many false +1 and -1 labels

Period B: AAPL's daily vol = 0.5% (quiet market)
  → A 2% move is FOUR standard deviations
  → This is a massive, rare event
  → You're missing lots of meaningful 1% moves that get labeled 0
```

Same `τ`, completely different meaning. In high-vol periods, you generate tons of garbage labels. In low-vol periods, almost everything is labeled 0. Your ML model gets confused because the labels aren't consistent.

**Problem 3: No stop-losses or take-profits (the path is ignored)**

This is what LdP considers the deepest flaw. Fixed-time horizon only looks at **where the price is at exactly bar h**. It ignores the entire path between now and then.

```
Scenario: You buy AAPL at $180, h = 10 days, τ = 2%

Day 0:  $180  (entry)
Day 1:  $175  (-2.8% → you'd be stopped out in real trading!)
Day 2:  $170  (-5.6% → massive pain)
Day 3:  $168  (-6.7% → margin call territory)
...
Day 9:  $178
Day 10: $185  (+2.8% → label = +1 ???)
```

The fixed-time method says "label = +1, this was a buy!" But in reality:
- Any sane trader would have been stopped out at Day 1
- The drawdown hit -6.7% — no risk manager allows that for a 2.8% gain
- The strategy would have been closed at a LOSS, not held to day 10

**The label is lying about what actually would have happened.**

### Why This Matters for ML

When you train an ML model on these labels, you're training it to predict something that **doesn't match how trading actually works**. The model learns:

> "When features look like X, the price goes up in 10 days"

But what it should learn is:

> "When features look like X, a trade with a stop-loss and take-profit will be profitable"

This is exactly why LdP invented the **Triple Barrier Method** (Section 3.4), which fixes all three problems by:
1. Using dynamic thresholds based on volatility (not fixed τ)
2. Including stop-losses (lower horizontal barrier)
3. Including take-profits (upper horizontal barrier)
4. Including a maximum holding period (vertical barrier)
5. Labeling based on **which barrier is hit first**, not where the price is at a fixed future time

### Connection to Alpha Lab

Alpha Lab already implements the Triple Barrier Method in `models/training/labeling.py` — we skipped the fixed-time approach entirely because of these flaws. The implementation uses dynamic volatility-based thresholds (Snippet 3.1 from the book: `getDailyVol`) to set barrier widths that adapt to market conditions.

---

## Q4: How does variance connect to risk? Why is risk always described as variance? (Foundation concept, referenced throughout AFML and Pedersen)

### Start With Intuition: What IS Risk?

Risk means **uncertainty about the outcome**. If you invest $100:

- If you'll get back exactly $103 → **zero risk** (you know the outcome)
- If you'll get back somewhere between $80 and $120 → **high risk** (wide range of possible outcomes)

Risk is about **how spread out** the possible outcomes are. And "how spread out" is literally the definition of variance.

### The Math Connection

**Variance** measures the average squared deviation from the mean:

```
Var(r) = E[(r - E[r])²]
```

In English: "On average, how far are actual returns from the expected return?"

**Standard deviation** (σ) is just the square root of variance — same concept, in the same units as returns (percentages):

```
σ = √Var(r)
```

### Concrete Example

Two stocks, both with **expected return = +10% per year**:

```
Stock A (low variance):
  Year 1: +8%    Year 2: +12%    Year 3: +9%    Year 4: +11%
  Mean = 10%
  Deviations: -2%, +2%, -1%, +1%
  Variance = (4 + 4 + 1 + 1) / 4 = 2.5
  σ = √2.5 = 1.58%

Stock B (high variance):
  Year 1: -20%   Year 2: +40%   Year 3: +25%   Year 4: -5%
  Mean = 10%
  Deviations: -30%, +30%, +15%, -15%
  Variance = (900 + 900 + 225 + 225) / 4 = 562.5
  σ = √562.5 = 23.7%
```

Both stocks average +10%. But Stock B swings wildly — you could lose 20% in a year. **That's risk.** The variance captures it: 562.5 vs 2.5.

### Why Variance Specifically? (Markowitz 1952)

This choice goes back to **Harry Markowitz (1952)** — the founder of Modern Portfolio Theory. He chose variance for three practical reasons:

**Reason 1: It's mathematically tractable**

```
Var(portfolio) = Σᵢ Σⱼ wᵢ wⱼ σᵢⱼ

where wᵢ = weight of asset i, σᵢⱼ = covariance of i and j
```

You can compute portfolio risk from individual asset risks + their correlations.

**Reason 2: If returns are normally distributed, variance tells you EVERYTHING**

A normal distribution is fully described by mean (μ) and variance (σ²):

```
Normal(μ=10%, σ=15%):
  68% of the time: returns between -5% and +25%    (μ ± 1σ)
  95% of the time: returns between -20% and +40%   (μ ± 2σ)
  99.7% of the time: returns between -35% and +55% (μ ± 3σ)
```

**Reason 3: It connects directly to the Sharpe Ratio**

```
Sharpe = (E[r] - r_f) / σ = reward / risk
```

If risk = σ (from variance), Sharpe is literally "return per unit of risk."

### The Honest Criticism: Variance Is a Flawed Risk Measure

**Flaw 1: Variance penalizes upside equally**

```
Stock C: returns = +2%, +15%, +3%, +20%     (big upside surprises)
Stock D: returns = +2%, -15%, +3%, -20%     (big downside surprises)

Both have the SAME variance! But C's "risk" is good news, D's is actual danger.
```

This is why the **Sortino Ratio** exists (from Pedersen Q8) — it only counts *downside* variance.

**Flaw 2: It assumes symmetric, normal distributions**

Real financial returns have fat tails and negative skew:

```
Normal says: a -20% daily move has probability ≈ 1 in a billion years
Reality:     Black Monday 1987 was -22.6% in ONE DAY
```

**Flaw 3: It's backward-looking**

Variance is estimated from historical data. But risk is about the future.

### Why We Still Use It

| Alternative | Problem |
|---|---|
| VaR (Value at Risk) | Doesn't tell you *how bad* beyond the threshold |
| CVaR (Expected Shortfall) | Harder to optimize portfolios with |
| Downside deviation | Only half the information, sometimes unstable |
| Max Drawdown | A single number from a single path — not statistical |

Variance is the **least bad** option that's also mathematically convenient.

### The Chain You'll See Everywhere

```
Variance (σ²)
  ↓ square root
Standard Deviation (σ) = "volatility"
  ↓ used in
Sharpe Ratio = return / σ
  ↓ used in
Portfolio Optimization = maximize Sharpe
  ↓ used in
Position Sizing = scale by 1/σ (risk parity)
  ↓ used in
Triple Barrier Labels = barrier width = f(σ)  ← LdP Ch 3!
```

That last line is the direct link to what you just read: LdP's fix for the Fixed Time Horizon method is to make `τ` a function of volatility (`σ`), not a fixed constant. **Variance literally connects the theory of risk to the practical implementation of labeling.**

---

## Q5: What does PCA Weights (Section 2.4.2) actually mean? What is spectral decomposition VW = WΛ, "projection on orthogonal basis," and how does it connect to 3Blue1Brown's linear algebra? (Pages 35-36, Ch 2)

### The Goal

You have a portfolio of N instruments (stocks, futures, bonds). You want to find portfolio weights `ω` (how much of each instrument to hold) such that the portfolio's **risk is distributed in a specific way** across independent risk sources.

That's it. The rest is machinery to achieve this.

### Layer 1: The Covariance Matrix V — "Who Moves With Whom"

You have N instruments. Their returns are correlated — when banks go down, they all go down together. The **covariance matrix** `V` captures all of these relationships:

```
         AAPL    GOOG    JPM     XOM
AAPL  [ 0.04    0.025   0.01    0.005 ]
GOOG  [ 0.025   0.05    0.008   0.003 ]
JPM   [ 0.01    0.008   0.03    0.012 ]
XOM   [ 0.005   0.003   0.012   0.06  ]
```

- **Diagonal** = variance of each asset (AAPL's variance = 0.04, so σ = 20%)
- **Off-diagonal** = covariance between pairs (AAPL-GOOG = 0.025, they move together — both tech)
- The matrix is **symmetric** (cov(AAPL,GOOG) = cov(GOOG,AAPL))

**The problem**: these 4 instruments are entangled. AAPL and GOOG move together. JPM and XOM partially move together. You can't think about risk clearly because everything is correlated with everything.

### Layer 2: Spectral Decomposition VW = WΛ — "Untangle the Mess"

#### The 3Blue1Brown Connection: What Is a Matrix, Really?

In 3B1B's *Essence of Linear Algebra*, Grant teaches: **a matrix is a linear transformation**. It takes a vector and moves it somewhere — stretching, rotating, shearing.

The covariance matrix V is exactly this. It's a transformation that takes any portfolio `ω` and outputs a vector `Vω` that tells you the portfolio's risk profile. When you compute `ω'Vω`, you're measuring how much V "stretches" ω — that stretch is the portfolio variance.

But some directions get stretched more than others. **Eigenvectors are the special directions that don't rotate — they only stretch.** And eigenvalues are how much they stretch.

#### The Equation VW = WΛ — In 3B1B Language

Remember 3B1B's key insight: for most vectors v, the transformation Av changes both direction and magnitude. But for eigenvectors, Av = λv — **only the magnitude changes, the direction stays the same.**

`VW = WΛ` is just this, written for ALL eigenvectors at once:

```
V × [w₁ | w₂ | w₃ | w₄] = [w₁ | w₂ | w₃ | w₄] × [λ₁  0   0   0 ]
                                                     [0   λ₂  0   0 ]
                                                     [0   0   λ₃  0 ]
                                                     [0   0   0   λ₄]
```

Column by column, this says:

```
V × w₁ = λ₁ × w₁     ← "applying V to w₁ just scales it by λ₁"
V × w₂ = λ₂ × w₂     ← "applying V to w₂ just scales it by λ₂"
V × w₃ = λ₃ × w₃
V × w₄ = λ₄ × w₄
```

**In 3B1B terms**: eigenvectors are the directions where the covariance matrix does nothing but stretch. The eigenvalue is the stretch factor. And the stretch factor IS the variance along that direction.

**W** = matrix whose columns are all the eigenvectors (the "special directions")
**Λ** = diagonal matrix of eigenvalues (the "stretch factors" = variances along each direction)

#### What the Eigenvectors Mean Financially

Each eigenvector is a **theme** or **factor** that drives multiple assets simultaneously:

```
w₁ = [ 0.5,  0.5,  0.5,  0.5 ]  → "market" (everything moves together)
w₂ = [ 0.6,  0.6, -0.4, -0.4 ]  → "tech vs finance/energy"
w₃ = [ 0.1, -0.1,  0.7, -0.7 ]  → "banks vs oil"
w₄ = [ 0.6, -0.6,  0.1, -0.1 ]  → "AAPL vs GOOG specific"
```

**The key property**: eigenvectors are **orthogonal** (perpendicular to each other). This means these themes are **completely independent**. The market factor and the tech-vs-finance factor have zero correlation. We've taken 4 correlated assets and re-expressed them as 4 uncorrelated themes.

Eigenvalues tell you each theme's importance:

```
Λ = diag([ 0.12, 0.04, 0.02, 0.005 ])

λ₁ = 0.12  → "market" explains 67% of total variance (most risk here)
λ₂ = 0.04  → "tech vs finance" explains 22%
λ₃ = 0.02  → "banks vs oil" explains 11%
λ₄ = 0.005 → idiosyncratic noise, only 3%
```

Sorted descending: w₁ is the most important direction, w₄ the least.

### Visualizing It: 2D Example

Forget 4 assets. Imagine just 2 correlated stocks:

```
     Stock B ↑
             |        . .  .
             |      . . . . .
             |    . . . . . . .        ← cloud of daily returns
             |  . . . . . . . . .         tilted because A and B
             | . . . . . . . . .          are correlated
             |. . . . . . . .
             +------------------------→ Stock A
```

The return cloud is an **ellipse tilted at an angle** because the stocks are correlated. PCA finds:

```
     Stock B ↑
             |
             |         ╱ w₁ (long axis = "market")
             |       ╱    λ₁ = large (lots of variance here)
             |     ╱
             |   ╱─────── w₂ (short axis = "spread")
             | ╱           λ₂ = small (little variance here)
             +------------------------→ Stock A
```

- **w₁** (first eigenvector) = long axis of the ellipse = "both stocks move together" = the market factor
- **w₂** (second eigenvector) = short axis (perpendicular!) = "Stock A goes up while B goes down" = the spread
- **λ₁** = length of long axis = how much variance the market factor carries
- **λ₂** = length of short axis = how much variance the spread carries

**The spectral decomposition rotates your coordinate system from "Stock A, Stock B" (correlated) to "Market, Spread" (uncorrelated).**

This is exactly 3B1B's "change of basis" chapter. The original basis is {Stock A, Stock B}. The new basis is {w₁, w₂} = {Market, Spread}. Same data, cleaner coordinate system.

### Layer 3: β = "Projection on the Orthogonal Basis"

#### The 3B1B Connection: Change of Basis

In 3B1B's change of basis video, Grant shows: if you have a vector expressed in one coordinate system, you can re-express it in another by multiplying by the inverse of the new basis matrix.

That's exactly what β = W'ω is.

You have portfolio weights `ω` in the **original basis** (how much AAPL, GOOG, etc.):

```
ω = [ 0.25, 0.25, 0.25, 0.25 ]   ← "25% in each stock"
```

The projection:

```
β = W'ω
```

translates from "asset language" to "factor language":

```
Original: ω = [ 25% AAPL, 25% GOOG, 25% JPM, 25% XOM ]

Projected: β = [ 0.50 market,  0.05 tech-vs-finance,  0.02 banks-vs-oil,  0.01 idio ]
```

Now you can see: "My equal-weight portfolio is basically a 50% bet on the market, with tiny exposure to everything else."

**Why W' and not W⁻¹?** Because eigenvectors of a symmetric matrix (and covariance matrices are always symmetric) are orthogonal. For orthogonal matrices, the transpose equals the inverse: W' = W⁻¹. This is the "orthonormal basis" property from 3B1B — when your basis vectors are perpendicular and unit-length, converting between coordinate systems is just a transpose, which is computationally trivial.

Think of it physically: you're standing in a room. "3 meters from north wall, 2 meters from east wall" (original basis) vs. "2.5 meters along the diagonal, 0.5 meters perpendicular to it" (rotated basis). Same position, different description. β is the second description.

### Layer 4: Portfolio Risk σ² in the New Basis

In the original basis:

```
σ² = ω'Vω
```

Weights × covariance × weights. Correct but opaque — you can't see WHERE risk comes from.

Now substitute V = WΛW' (the spectral decomposition rearranged):

```
σ² = ω'Vω = ω'(WΛW')ω = (W'ω)'Λ(W'ω) = β'Λβ
```

Since Λ is diagonal, this expands to:

```
σ² = β₁²λ₁ + β₂²λ₂ + β₃²λ₃ + β₄²λ₄
```

**Portfolio risk = sum of (exposure to each theme)² × (risk of that theme)**

Each term is independent. You can finally SEE where risk lives:

```
Theme       | βₙ (exposure) | λₙ (theme risk) | βₙ²λₙ (contribution) | % of total
------------|---------------|------------------|----------------------|----------
Market      | 0.50          | 0.12             | 0.030                | 83%
Tech vs Fin | 0.05          | 0.04             | 0.0001               | 0.3%
Banks vs Oil| 0.02          | 0.02             | 0.000008             | ~0%
Idiosyncratic| 0.01         | 0.005            | 0.00000005           | ~0%
                                         Total: σ² ≈ 0.030
```

83% of your portfolio risk comes from the "market" theme alone.

### Layer 5: Rₙ — The Risk Distribution

LdP defines:

```
Rₙ = βₙ² × λₙ / σ²
```

This is the **fraction** of total risk from theme n. The set `{Rₙ}` sums to 1 — it's a probability distribution over risk sources.

### Layer 6: The Punchline — Choosing ω to Get a Desired R

You get to **choose** how you want risk distributed:

```
Option A: R = [1, 0, 0, 0]
  → ALL risk from market factor → basically buying the index

Option B: R = [0, 0, 0, 1]
  → ALL risk from smallest eigenvector (idiosyncratic)
  → Market-neutral, factor-neutral portfolio
  → This is LdP's default when riskDist=None in Snippet 2.1

Option C: R = [0.25, 0.25, 0.25, 0.25]
  → Equal risk from each theme → "PCA risk parity"
```

**Working backward from R to ω**:

Given desired risk fraction Rₙ:

```
βₙ = σ × √(Rₙ / λₙ)       ← solve for exposure in PCA space
ω = Wβ                      ← convert back to asset weights
```

### Why Figure 2.2 Looks The Way It Does

The bar chart compares two portfolios across 10 principal components:

**Inverse Variance Portfolio** (traditional risk parity):
- Allocates by 1/variance of each asset
- Risk spread across all components — bars relatively even
- Still has huge market exposure (component 1)

**PCA Portfolio** (LdP's approach, riskDist=None):
- Puts ALL risk in last component (smallest eigenvalue)
- Only component 10 has a tall bar, everything else near zero
- **Market-neutral, sector-neutral** — only bets on idiosyncratic spread
- The purest possible statistical arbitrage portfolio

### The Full 3B1B → Finance Translation Table

| 3B1B Concept | Finance Meaning |
|---|---|
| Vector | Portfolio weights ω, or a single observation of returns |
| Matrix | The covariance matrix V — a transformation that maps weights to risk |
| Linear transformation | Applying V to ω gives you the portfolio's risk exposure |
| Eigenvector | An independent risk theme (market, sector, idiosyncratic) |
| Eigenvalue | The variance (= risk) along that theme's direction |
| Basis | The coordinate system — either {assets} or {PCA themes} |
| Change of basis | β = W'ω — re-expressing weights in the PCA coordinate system |
| Span | The set of all portfolios you can construct from N assets |
| Determinant | Product of eigenvalues — total "volume" of risk in the system |
| Rank | Number of truly independent risk sources (if rank < N, some assets are redundant) |

### Connection to Alpha Lab

Alpha Lab implements HRP (Hierarchical Risk Parity) in `risk/position_sizing/`, which uses a related but different approach — it clusters assets by correlation and allocates risk hierarchically instead of through full eigendecomposition. The PCA approach here is the analytical foundation that HRP improves upon (HRP handles the instability of eigenvectors in high dimensions, which is PCA's practical weakness).

---

## Q6: What is the Triple Barrier Method and how does it actually work? (Pages 44-47, Ch 3, Section 3.3-3.4)

### The Core Idea in One Sentence

Instead of asking "where is the price in h days?" (Fixed Time Horizon), ask **"which of these three exit conditions does the price hit FIRST?"**

The three barriers form a box around the price:
- **Upper horizontal barrier** = take-profit level
- **Lower horizontal barrier** = stop-loss level
- **Vertical barrier** = time expiry (max holding period)

Whichever the price touches first determines the label.

### Why "Barrier"?

Think of a ball bouncing inside a box. The ball is the price, the walls are the barriers. The ball will eventually hit one of the walls. Which wall it hits first tells you the outcome of the trade.

```
Price
  |
  |  ═══════════════════════════════  UPPER BARRIER (take profit)
  |                                |
  |      price path wanders        |
  |    inside this box until        |  VERTICAL BARRIER
  |    it hits a wall               |  (time expiry)
  |                                |
  |  ═══════════════════════════════  LOWER BARRIER (stop loss)
  |
  t₀                              t₀ + h
  (entry)                         (max hold)
```

### Section 3.3: Dynamic Thresholds — Making the Box Adapt

Before defining the barriers, LdP solves the fixed-τ problem from Section 3.2. Instead of a fixed threshold like τ = 2%, he scales barriers by the **current daily volatility**.

**Snippet 3.1 — getDailyVol**: computes an exponentially weighted moving standard deviation of daily returns. This is σ_{t_{i,0}} — the volatility at the time the observation was made.

```
getDailyVol(close, span=100):
    1. Compute daily returns: r_t = close_t / close_{t-1} - 1
    2. Apply EWMA with span=100 to get rolling σ
    3. Return the series of daily volatilities
```

Why EWMA instead of simple rolling window? Because recent volatility matters more than old volatility. After a crash, vol spikes — EWMA captures this faster than a simple average.

**The barrier widths are then**:

```
Upper barrier = entry_price × (1 + profit_taking × σ_{t_{i,0}})
Lower barrier = entry_price × (1 - stop_loss × σ_{t_{i,0}})
```

Where `profit_taking` and `stop_loss` are multipliers (e.g., 2.0 means "2 daily standard deviations").

This means **the box expands in volatile markets and shrinks in quiet markets** — exactly what a real trader does.

### Full Numerical Walkthrough

Let's trace through a complete example step by step.

**Setup**:
- AAPL entry price: **$180.00** on Day 0
- Daily volatility at entry: **σ = 1.5%** (= 0.015)
- profit_taking = 2.0 (take profit at 2× daily vol)
- stop_loss = 2.0 (stop loss at 2× daily vol)
- max_holding_period = 10 days

**Step 1: Compute barrier levels**

```
Upper barrier = $180 × (1 + 2.0 × 0.015) = $180 × 1.03 = $185.40
Lower barrier = $180 × (1 - 2.0 × 0.015) = $180 × 0.97 = $174.60
Vertical barrier = Day 10
```

**Step 2: Walk through the price path day by day**

Now we simulate the price and check each day: has any barrier been hit?

#### Scenario A: Upper barrier hit first (Label = +1)

```
Day  | Price   | vs Upper ($185.40) | vs Lower ($174.60) | Barrier hit?
-----|---------|--------------------|--------------------|-------------
  0  | $180.00 | entry              | entry              | —
  1  | $181.20 | below              | above              | No
  2  | $182.50 | below              | above              | No
  3  | $183.80 | below              | above              | No
  4  | $184.10 | below              | above              | No
  5  | $186.20 | ABOVE! ✓           |                    | UPPER HIT!
```

```
Price
$186 |                          ✖ (Day 5: Hit!)
     |  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ $185.40 (upper)
$184 |                    •
$183 |              •
$182 |         •
$181 |    •
$180 | •                                            ← entry
     |
     |  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ $174.60 (lower)
     +---|---|---|---|---|---|---|---|---|---→ Time
       0   1   2   3   4   5   6   7   8  9  10
```

**Result**: Label = **+1**, barrier_hit = "upper", return = +3.4%, holding_period = 5

The price rose steadily and crossed the take-profit. We stop tracking here — days 6-10 don't matter. The trade was a winner.

#### Scenario B: Lower barrier hit first (Label = -1)

```
Day  | Price   | vs Upper ($185.40) | vs Lower ($174.60) | Barrier hit?
-----|---------|--------------------|--------------------|-------------
  0  | $180.00 | entry              | entry              | —
  1  | $178.50 | below              | above              | No
  2  | $176.00 | below              | above              | No
  3  | $174.20 | below              | BELOW! ✓           | LOWER HIT!
```

```
Price
     |  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ $185.40 (upper)
     |
$180 | •                                            ← entry
$179 |    •
$176 |         •
$174 |              ✖ (Day 3: Hit!)
     |  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ $174.60 (lower)
     +---|---|---|---|---|---|---|---|---|---→ Time
       0   1   2   3   4   5   6   7   8  9  10
```

**Result**: Label = **-1**, barrier_hit = "lower", return = -3.2%, holding_period = 3

The price dropped and hit the stop-loss on Day 3. We exit. This was a losing trade — and it's labeled honestly as a loss.

#### Scenario C: Vertical barrier hit first (Label = 0)

```
Day  | Price   | vs Upper ($185.40) | vs Lower ($174.60) | Barrier hit?
-----|---------|--------------------|--------------------|-------------
  0  | $180.00 | entry              | entry              | —
  1  | $181.00 | below              | above              | No
  2  | $179.50 | below              | above              | No
  3  | $180.80 | below              | above              | No
  4  | $179.20 | below              | above              | No
  5  | $181.50 | below              | above              | No
  6  | $180.00 | below              | above              | No
  7  | $179.80 | below              | above              | No
  8  | $181.20 | below              | above              | No
  9  | $180.50 | below              | above              | No
 10  | $181.00 | below              | above              | TIME'S UP!
```

```
Price
     |  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  $185.40 (upper)
     |
$181 |    •         •         •         •    •  |
$180 | •      •  •      •         •         •  | ← vertical barrier
$179 |           •         •    •    •          |
     |                                          |
     |  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  $174.60 (lower)
     +---|---|---|---|---|---|---|---|---|---|----→ Time
       0   1   2   3   4   5   6   7   8   9  10
```

**Result**: Label = **0**, barrier_hit = "vertical", return = +0.6%, holding_period = 10

The price bounced around inside the box for 10 days without hitting either horizontal barrier. Time ran out. This was a non-event — the trade didn't really go anywhere. Labeling it 0 is honest: there was no significant move.

### Why This Is So Much Better Than Fixed Time Horizon

Let's replay the "pathological" example from Q3 that broke Fixed Time Horizon:

```
Day 0:  $180  (entry)
Day 1:  $175  ← HIT LOWER BARRIER ($174.60)!
```

Fixed Time Horizon: waits until Day 10, sees $185 → label = +1 (BUY!)
Triple Barrier: stops at Day 1 when stop-loss is hit → label = **-1** (LOSS!)

The triple barrier label matches what would **actually happen** to a trader with risk management.

### The Barrier Configuration Triplet [pt, sl, t1]

LdP uses [pt, sl, t1] to denote which barriers are active:
- **1** = barrier is active
- **0** = barrier is disabled

| Config | Meaning | Use Case |
|--------|---------|----------|
| [1,1,1] | All three active | **Standard** — the default, most realistic |
| [0,1,1] | No take-profit, just stop-loss + time limit | "Exit after h bars unless stopped out" |
| [1,1,0] | Take-profit + stop-loss, no time limit | "Hold until resolved, however long it takes" |
| [0,0,1] | Only vertical barrier | **Equivalent to Fixed Time Horizon!** |
| [1,0,1] | Take-profit + time limit, no stop-loss | "Hold until profit or timeout" — dangerous |
| [1,0,0] | Only take-profit | "Hold until profit no matter what" — locked on a loser potentially forever |
| [0,1,0] | Only stop-loss | "Aimless — hold until stopped out" |
| [0,0,0] | No barriers at all | No label generated — position locked forever |

**Key insight**: [0,0,1] = Fixed Time Horizon. The triple barrier method is a strict generalization — it includes the fixed-time method as a special case (the worst one).

### How the Barriers Scale With Volatility — The Critical Feature

Let's compare the same multipliers across two volatility regimes:

```
Settings: profit_taking = 2.0, stop_loss = 2.0

                     Quiet Market (σ=0.5%)        Volatile Market (σ=3%)
                     ────────────────────          ────────────────────
Entry price:         $180.00                       $180.00
Upper barrier:       $180 × (1 + 2×0.005)          $180 × (1 + 2×0.03)
                     = $181.80 (+1.0%)              = $190.80 (+6.0%)
Lower barrier:       $180 × (1 - 2×0.005)          $180 × (1 - 2×0.03)
                     = $178.20 (-1.0%)              = $169.20 (-6.0%)
Box width:           $3.60                          $21.60
```

In quiet markets, the box is tight ($3.60 wide) — even small moves trigger labels.
In volatile markets, the box is wide ($21.60) — only large moves trigger labels.

**This is exactly what a trader does**: widen stops in volatile markets, tighten in quiet ones. The labels automatically adapt, producing consistent signal quality across regimes.

### The Math — Formally

**Notation**:
- `t_{i,0}` = bar index where observation X_i occurs (entry time)
- `h` = max holding period (number of bars until vertical barrier)
- `σ_{t_{i,0}}` = daily volatility at entry, from getDailyVol (Snippet 3.1)
- `pt` = profit-taking multiplier (e.g., 2.0)
- `sl` = stop-loss multiplier (e.g., 2.0)

**Barrier levels**:

```
Upper barrier price:  p_{t_{i,0}} × (1 + pt × σ_{t_{i,0}})
Lower barrier price:  p_{t_{i,0}} × (1 - sl × σ_{t_{i,0}})
Vertical barrier time: t_{i,0} + h
```

**First touch time** `t_{i,1}`:

```
t_{i,1} = min(t_upper, t_lower, t_vertical)

where:
  t_upper    = first t ∈ [t_{i,0}+1, ..., t_{i,0}+h] where p_t ≥ upper barrier
  t_lower    = first t ∈ [t_{i,0}+1, ..., t_{i,0}+h] where p_t ≤ lower barrier
  t_vertical = t_{i,0} + h
```

**The label**:

```
y_i = { +1    if t_{i,1} = t_upper    (take-profit hit first)
      { -1    if t_{i,1} = t_lower    (stop-loss hit first)
      {  0    if t_{i,1} = t_vertical  (time expired, or sign of return at expiry)
```

**The return** associated with the observation:

```
r_{t_{i,0}, t_{i,1}} = p_{t_{i,1}} / p_{t_{i,0}} - 1
```

This is the return at the FIRST barrier touch — not at a fixed future time. It reflects the actual P&L of a trade with proper risk management.

**Important**: `t_{i,1} ≤ t_{i,0} + h`. The first touch can happen at any time from the very next bar to the last bar. The holding period is variable — this is path-dependent labeling.

### Note on Asymmetric Barriers

LdP says: "the horizontal barriers are not necessarily symmetric." You can set:

```
profit_taking = 3.0   (take profit at 3σ — let winners run)
stop_loss = 1.5        (stop loss at 1.5σ — cut losers fast)
```

This creates a **tall, narrow box** — favoring trades with large reward-to-risk ratios. The asymmetry reflects a real trading principle: "cut your losses short, let your profits run."

```
Price
     |  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  $188.10 (upper: +3σ = +4.5%)
     |                       |
     |                       |    tall: lots of room for profit
     |                       |
$180 | • entry               |
     |                       |    short: cut losses quickly  
     |  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  $175.95 (lower: -1.5σ = -2.25%)
     +---|---|---|---|---|----→ Time
```

### How Alpha Lab Implements It

In `models/training/labeling.py:107-139`, the core loop:

```python
for t in range(n):
    vol_t = daily_vol[t]                                    # Step 1: get σ
    upper = close[t] * (1.0 + self.profit_taking * vol_t)   # Step 2: set barriers
    lower = close[t] * (1.0 - self.stop_loss * vol_t)
    end = min(t + self.max_holding_period, n - 1)           # vertical barrier

    for j in range(t + 1, end + 1):                         # Step 3: walk forward
        if close[j] >= upper:                                # upper hit?
            hit_label = 1; break
        if close[j] <= lower:                                # lower hit?
            hit_label = -1; break
    # if neither hit → label = 0 (vertical barrier / timeout)
```

This is a direct implementation of Snippet 3.2 from the book, translated from Pandas to Polars/NumPy.

### The Key Insight: Path-Dependent vs Point-in-Time

```
Fixed Time Horizon:   only looks at price[t + h]
                      ignores the entire path between t and t+h
                      → labels lie about what would happen to a real trader

Triple Barrier:       scans every bar from t+1 to t+h
                      checks barriers at EACH step
                      → labels reflect path-dependent reality of trading
```

This is arguably LdP's single most important practical contribution. Every ML model trained on triple-barrier labels learns to predict **tradeable outcomes**, not academic price forecasts.

---

## Q7: What is Meta-Labeling and why does LdP call it essential? (Pages 48-54, Ch 3, Sections 3.5-3.8)

### The Problem: One Model Doing Two Jobs

With standard triple-barrier labeling, you train a single ML model to learn TWO things simultaneously:

1. **Which direction?** (long or short — the "side")
2. **How confident?** (should I bet big, small, or not at all — the "size")

These are fundamentally different questions. Imagine asking one person to simultaneously:
- Pick which horse will win the race (direction)
- Decide how much money to bet (size)

It's harder than splitting it into two specialized decisions. And in ML, forcing one model to do both leads to worse performance on each.

### The Solution: Two Models, Two Jobs

Meta-labeling splits the decision into a pipeline:

```
┌─────────────────────┐         ┌──────────────────────┐
│   PRIMARY MODEL      │         │   SECONDARY MODEL     │
│   (any model at all) │         │   (the "meta" model)  │
│                      │         │                       │
│   Input: features    │────→    │   Input: features +   │
│   Output: DIRECTION  │  side   │          primary's    │
│   {-1, +1}           │         │          prediction   │
│                      │         │   Output: BET or NOT  │
│   "Go long AAPL"     │         │   {0, 1}              │
│                      │         │                       │
│   Can be: ML model,  │         │   "Should I trust     │
│   moving avg cross,  │         │    the primary model   │
│   fundamental rule,  │         │    this time?"         │
│   human intuition    │         │                       │
└─────────────────────┘         └──────────────────────┘
         │                                │
         │ direction = +1                 │ probability = 0.73
         │ (go long)                      │ (73% chance primary is right)
         │                                │
         ▼                                ▼
┌──────────────────────────────────────────────────┐
│   FINAL DECISION                                  │
│                                                   │
│   Position = direction × bet_size(probability)    │
│            = +1 × f(0.73)                         │
│            = long, moderate size                   │
└──────────────────────────────────────────────────┘
```

### How Meta-Labels Are Constructed

**Step 1**: Run your primary model to get direction predictions.

```
Primary model says:
  Day 1: "Go long AAPL"   (direction = +1)
  Day 2: "Go short GOOG"  (direction = -1)
  Day 3: "Go long TSLA"   (direction = +1)
  Day 4: "Go short MSFT"  (direction = -1)
```

**Step 2**: Apply triple-barrier labeling to get the ACTUAL outcomes.

With the direction known, barriers can be asymmetric now:
- If primary says LONG: upper barrier = take-profit, lower barrier = stop-loss
- If primary says SHORT: upper barrier = stop-loss, lower barrier = take-profit

```
Actual outcomes (from triple barrier):
  Day 1: AAPL hit upper barrier   → actual = +1 (win)
  Day 2: GOOG hit upper barrier   → actual = +1 (but we were short → loss!)
  Day 3: TSLA hit lower barrier   → actual = -1 (but we were long → loss!)
  Day 4: MSFT hit lower barrier   → actual = -1 (we were short → win!)
```

**Step 3**: Compare primary prediction to actual outcome → meta-label.

```
Day 1: primary = +1, actual = +1 → MATCH    → meta_label = 1 ✓
Day 2: primary = -1, actual = +1 → MISMATCH → meta_label = 0 ✗
Day 3: primary = +1, actual = -1 → MISMATCH → meta_label = 0 ✗
Day 4: primary = -1, actual = -1 → MATCH    → meta_label = 1 ✓
```

**The meta-label is binary: 1 = "the primary model was right," 0 = "the primary model was wrong."**

The secondary ML model learns to predict THIS — not the direction, but whether the primary model's direction call will be correct.

### A Concrete Trading Example

**Primary model**: 50-day / 200-day moving average crossover.

```
When 50-day MA crosses ABOVE 200-day MA → go LONG
When 50-day MA crosses BELOW 200-day MA → go SHORT
```

This is a classic trend-following signal. It catches big trends but generates lots of false signals (whipsaws) in choppy markets.

```
Month | MA Signal | What Actually Happened  | Meta-Label
------|-----------|------------------------|----------
Jan   | LONG      | Stock rallied 8%        | 1 (correct)
Feb   | SHORT     | Stock rallied 3%        | 0 (wrong!)
Mar   | LONG      | Stock dropped 5%        | 0 (wrong!)
Apr   | LONG      | Stock rallied 12%       | 1 (correct)
May   | SHORT     | Stock dropped 7%        | 1 (correct)
Jun   | LONG      | Stock went sideways     | 0 (wrong!)
```

The primary model is right 50% of the time — basically coin-flip accuracy. Terrible, right?

Now the meta-model trains on features like:
- Volatility level when the signal fired
- Volume on the crossover day
- How far apart the MAs are
- Market-wide trend (S&P500 direction)
- VIX level

And learns patterns like:
- "MA crossovers during HIGH volatility are usually wrong (whipsaws)"
- "MA crossovers with EXPANDING volume are usually correct"
- "MA crossovers AGAINST the broad market trend are usually wrong"

```
Month | MA Signal | Meta-Model Confidence | Decision
------|-----------|----------------------|----------
Jan   | LONG      | 0.82 → BET           | Long, full size
Feb   | SHORT     | 0.35 → SKIP          | No trade (saved from loss!)
Mar   | LONG      | 0.41 → SKIP          | No trade (saved from loss!)
Apr   | LONG      | 0.88 → BET           | Long, full size
May   | SHORT     | 0.71 → BET           | Short, moderate size
Jun   | LONG      | 0.29 → SKIP          | No trade (saved from flat)
```

**Result**: Without meta-labeling: 3 wins, 3 losses = 50% accuracy, mediocre P&L.
**With meta-labeling**: 3 wins, 0 losses = 100% accuracy on trades taken. We dodged all the bad signals.

### Why LdP Says It Achieves Higher F1-Scores (Page 52-53)

This connects to precision vs recall:

```
                              PRIMARY MODEL ALONE
                              ────────────────────
                              Makes lots of calls (high recall)
                              Many of them wrong (low precision)
                              F1 = mediocre

                              PRIMARY + META-LABELING
                              ────────────────────────
                              Step 1: Primary still makes lots of calls (high recall)
                              Step 2: Meta-model filters out the bad ones (high precision)
                              F1 = much better!
```

The trick: it's easier to build a high-recall primary model and then filter, than to build a single model that has both high recall AND high precision.

**Analogy**: Imagine a spam filter.
- Primary model: flag everything that MIGHT be spam (catches 99% of spam, but also flags 30% of real emails as spam)
- Meta-model: for each flagged email, decide if it's REALLY spam (filters out the false positives)
- Result: 99% spam caught, only 2% false positive rate

### The "Quantamental Way" — Section 3.8

This is the big picture application. LdP says meta-labeling is how **discretionary hedge funds become quantitative**:

```
┌────────────────────────┐
│  HUMAN PM / ANALYST     │     ← The "fundamental" part
│  (or fundamental model) │
│                         │
│  "I think AAPL should   │
│   go up because of      │
│   strong iPhone demand"  │
│                         │
│  Output: direction = +1 │
└───────────┬─────────────┘
            │
            ▼
┌────────────────────────┐
│  ML META-MODEL          │     ← The "quantitative" part
│                         │
│  Features:              │
│  - PM's historical      │
│    accuracy in this     │
│    sector               │
│  - Market conditions    │
│  - Sentiment data       │
│  - PM's stress levels   │     ← LdP actually suggests biometrics! (page 54)
│  - Time since last      │
│    vacation              │
│                         │
│  Output: P(PM is right) │
│         = 0.72          │
└───────────┬─────────────┘
            │
            ▼
┌────────────────────────┐
│  POSITION SIZE          │
│  = direction × f(0.72) │
│  = long AAPL, 72% of   │
│    max position         │
└────────────────────────┘
```

The meta-model learns WHEN the PM is good (sector expertise, calm markets) and when they're bad (stressed, unfamiliar territory, volatile markets). It doesn't replace the PM — it modulates their confidence.

LdP literally says the meta-model could incorporate **biometric data** (sleep, stress, weight changes) as features. A PM who hasn't slept in 3 days probably shouldn't be making full-size bets.

### How Alpha Lab Implements It

In `models/training/labeling.py:155-193`:

```python
def meta_label(self, primary_signals, labels):
    # Join primary direction predictions with actual triple-barrier labels
    joined = primary_signals.join(labels.select("date", "label"), on="date")

    # meta_label = 1 if direction matches reality, 0 otherwise
    meta = joined.with_columns(
        pl.when(
            ((pl.col("direction") > 0) & (pl.col("label") > 0))
            | ((pl.col("direction") < 0) & (pl.col("label") < 0))
        )
        .then(pl.lit(1))
        .otherwise(pl.lit(0))
        .alias("meta_label")
    )
```

The primary model provides direction, triple-barrier provides ground truth, and the comparison produces binary meta-labels. Simple implementation, powerful concept.

### Connection to Bet Sizing (Ch 10)

Meta-labeling outputs a probability P(primary is correct). This probability feeds directly into **bet sizing** (AFML Ch 10, which we'll build in Sprint A):

```
bet_size = (2P - 1) × max_position

P = 0.50 → bet_size = 0.0  (no edge, don't trade)
P = 0.65 → bet_size = 0.3  (modest edge, small position)
P = 0.85 → bet_size = 0.7  (strong edge, large position)
P = 1.00 → bet_size = 1.0  (certain, max position)
```

This is the full pipeline: **primary model → direction → meta-model → confidence → bet sizing → position size**. Each piece does one job well.

---

## Q8: What is a "bar" and what does `sample_weight = uniqueness` mean? (Foundation for Ch 4)

### What Is a "Bar"?

A **bar** is one row in your price data. That's it.

If you're using daily data (which Alpha Lab does via YFinance):

```
Bar 1 = Day 1 = { date: 2026-01-02, open: 180, high: 182, low: 179, close: 181, volume: 50M }
Bar 2 = Day 2 = { date: 2026-01-03, open: 181, high: 183, low: 180, close: 182, volume: 45M }
Bar 3 = Day 3 = ...
```

LdP uses "bar" instead of "day" because the concept works for ANY sampling method:

| Data Type | What One "Bar" Is |
|---|---|
| Daily OHLCV (Alpha Lab) | One trading day |
| Hourly data | One hour |
| Volume bars (Ch 2) | Every N shares traded |
| Dollar bars (Ch 2) | Every $N transacted |
| Tick bars (Ch 2) | Every N trades |

**In your case, just mentally replace "bar" with "day."** When LdP says "Label A spans bars 1-5," it means the trade was open from Day 1 to Day 5.

### What Is `sample_weight = uniqueness`?

This is a feature of scikit-learn (and most ML libraries). When you train a model, you can tell it: **"some training samples matter more than others."**

**Without sample_weight (default)**:

```python
model.fit(X, y)
```

Every training row is treated equally. 1000 samples → each contributes 1/1000th to learning. The model doesn't know that some samples share information.

**With sample_weight**:

```python
model.fit(X, y, sample_weight=weights)
```

Each row gets a **multiplier** — "how much should this sample count?"

```
Sample | Features       | Label | Weight | Effect
-------|----------------|-------|--------|------------------------------------
  A    | [0.3, 1.2, ..] |  +1   |  0.67  | Counts as 0.67 of a full sample
  B    | [0.5, 0.8, ..] |  -1   |  0.47  | Counts as only 0.47 (heavily overlaps)
  C    | [0.2, 1.5, ..] |  +1   |  0.67  | Counts as 0.67
  D    | [0.8, 0.3, ..] |  -1   |  1.00  | FULL sample (no overlap with others)
  E    | [0.1, 0.9, ..] |  +1   |  0.85  | Counts as 0.85
```

What the model "sees" internally:

```
Without weights: A, B, C, D, E all equally important → 5 equal votes

With weights:    A counts as 0.67 votes
                 B counts as 0.47 votes    ← downweighted, redundant
                 D counts as 1.00 votes    ← full vote, unique info
```

### How It Works Under the Hood

When a decision tree decides where to split, it minimizes a loss function (like Gini impurity). Sample weights modify this:

```
Without weights:
  Gini = Σ (misclassifications)
  → every mistake counts equally

With weights:
  Gini = Σ (weight × misclassification)
  → misclassifying D (weight=1.0) is penalized MORE
  → misclassifying B (weight=0.47) is penalized LESS

The model tries HARDER to get unique samples right,
and doesn't worry as much about redundant ones.
```

### The Full Connection

```
Triple barrier labels (Ch 3)
  → some labels OVERLAP in time (share the same days)
  → compute UNIQUENESS for each label (Ch 4)
     (= fraction of its time span NOT shared with other labels)
  → pass uniqueness as sample_weight to sklearn
  → model pays more attention to independent observations
  → no double-counting of the same market events
```

---

## Q9: How does Bet Sizing work — converting ML probability to position size? (Pages 141-149, Ch 10)

### The Core Insight: Poker Analogy

The best poker players aren't the ones who pick the best hands — they're the ones who **size their bets correctly**. Same in trading. Your ML model predicts direction (from meta-labeling). But how much of your portfolio should you stake?

```
Two traders, same predictions, different sizing:

Trader A: Always bets 10% regardless    → Total: +0.2%  (mediocre)
Trader B: Sizes bets by confidence      → Total: +2.96% (15x better!)
```

### The Main Formula: Probability → z-stat → Bet Size

**Step 1**: ML classifier outputs p[x=1] (probability label is +1).

**Step 2**: Compute z-statistic — how far is this probability from random chance (0.5)?

```
z = (p[x=1] - 0.5) / √(p[x=1] × (1 - p[x=1]))
```

**Step 3**: Map z to bet size via the normal CDF Φ:

```
m = x × (2Φ(z) - 1)       where x = direction (+1 or -1)
```

### The Probability → Bet Size Table

```
Probability  | Direction | z-stat | Bet Size | In English
-------------|-----------|--------|----------|---------------------------
    0.50      |    —      |  0.00  |   0.00   | "Coin flip — don't trade"
    0.60      |   Long    |  0.20  |   0.16   | "Small edge — small position"
    0.70      |   Long    |  0.43  |   0.34   | "Good — a third"
    0.80      |   Long    |  0.75  |   0.55   | "Very strong — over half"
    0.90      |   Long    |  1.33  |   0.82   | "Very high — four-fifths"
    0.99      |   Long    |  4.92  |   1.00   | "Near certain — full position"
```

The S-shaped curve means: no position at 50%, gradual increase for moderate confidence, near-max for high confidence.

### Averaging Active Bets (Section 10.4)

Multiple signals may be active simultaneously. Average all active bet sizes at each point in time rather than replacing old with new — this reduces turnover.

### Size Discretization (Section 10.5)

Round to discrete steps to avoid overtrading: `m* = round(m/d) × d`. A raw bet of 0.05 rounds to 0.0 → naturally filters out marginal signals.

### Dynamic Bet Sizing (Section 10.6)

As market price moves toward your forecast, reduce position (take profit). As it moves away, increase (the expected return got bigger):

```
m[ω, x] = x / √(ω + x²)     where x = forecast - current price
```

### The Full Pipeline

```
ML probability (0.73) → z-stat (0.517) → raw bet (0.39) → average active (0.31)
→ discretize (0.3) → position ($30K) → limit price ($97.50) → submit order
```

### Connection to Alpha Lab

Alpha Lab currently uses fixed Kelly criterion in `risk/position_sizing/engine.py`. The AFML bet sizing approach (Sprint A, Task A4) will replace this with dynamic ML-probability-based sizing via `risk/position_sizing/bet_sizing.py`, connecting meta-labeling output directly to position sizes.

---
