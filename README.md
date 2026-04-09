# The Agentic Alpha Lab

**A quant research platform where 9 specialist agents — backed by 28,000 lines of real computation — discover alpha, reason out loud, and ask for your approval before they act.**

> Not an AI chatbot that talks about finance. A research lab that runs overnight, writes you a morning brief, and waits for your sign-off before it trades.

![Python](https://img.shields.io/badge/Python-28%2C230_lines-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-6%2C787_lines-blue)
![Tests](https://img.shields.io/badge/tests-808_passing-brightgreen)
![Models](https://img.shields.io/badge/LLM-OpenAI%20|%20Anthropic%20|%20Gemini%20|%20Groq-violet)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What you see when you open the dashboard at 8am

```
Good morning, Parul.                                       April 9, 2026

I ran the overnight cycle across 50 tickers. Here's what matters:

━━━ TOP CONVICTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NVDA  │  LONG  │  Confidence: 0.84  │  5/6 agents bullish
  The Quant:           z-score = -2.1 (entry zone), half-life 12 days
  The Technician:      RSI = 28 (oversold), MACD crossover imminent
  The Sentiment:       Earnings call tone shift +0.19, "AI infra" 14x
  The Contrarian:      Short interest 1.2% — not crowded, no objection
  → Historical: 62% win rate, +2.1% avg return, 47 instances (p=0.03)
  → Kelly sizing: $4,200 (4.2% of $100K portfolio)

                              [Approve] [Dig Deeper] [Reject]

━━━ WATCHLIST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TSLA  │  SHORT signal strengthening  │  Confidence: 0.67
  Sentiment deteriorating + momentum weakening. Not yet at entry.

AAPL  │  Approaching mean reversion zone  │  z = -1.7
  Watching for -2.0. Fundamentals still strong (margin of safety 27%).

MSFT/GOOG │  Pairs spread widening  │  z = 1.8
  Approaching entry. Cointegration holds (p=0.02). 2 days from signal.

━━━ PORTFOLIO HEALTH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

P&L this week: +1.2% ($1,200)    Sharpe (30d): 1.43
Signal decay:  All signals within half-life ✓
Risk:          VaR -1.8% (limit: 3%) ✓

━━━ WHAT I LEARNED ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mean reversion signals last week: 4/6 profitable (+1.8% net)
Momentum signals last week:       2/5 profitable (-0.3% net)
→ Adjusting: increasing mean reversion weight, reducing momentum.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                         [View Full Dashboard]  [Chat]
```

---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [How It Works — The Research Cycle](#how-it-works--the-research-cycle)
- [The 9 Specialist Agents](#the-9-specialist-agents)
- [The Dashboard — 6 Pages](#the-dashboard--6-pages)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Multi-Model LLM Support](#multi-model-llm-support)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [The Prompt System](#the-prompt-system)
- [Technical Deep Dives](#technical-deep-dives)
- [Comparison with Alternatives](#comparison-with-alternatives)
- [Roadmap](#roadmap)
- [Credits and Built With](#credits-and-built-with)

---

## Why This Exists

### The Problem: Most AI-Finance Projects Produce Opinions, Not Signals

Ask ChatGPT about NVDA. It will give you a thoughtful essay about the semiconductor market. Ask most AI trading agents the same question. You will get a "bullish" verdict with 85% confidence and no way to verify it.

The fundamental problem is architectural: these systems use language models to generate financial opinions, then present those opinions as if they were research. There is no backtesting to confirm the signal actually works. No signal decay measurement to know when it stops working. No statistical validation to guard against the overfitting that plagues most strategy research.

Real quantitative research follows a different process: compute first, reason second, validate third, act only when the evidence supports it.

### The Inspiration: What Virat Got Right (And What He Left Out)

[Virat Singh's ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) earned 50,000+ stars because it cracked something genuinely clever: domain-specific personas with structured disagreement. Warren Buffett says "bullish, 85% confidence — strong moat, growing owner earnings." Michael Burry says "bearish — overvalued relative to book, accounting concerns." The agents actually compute DCF values and factor exposures before the LLM reasons, which is the right instinct.

But the project stops there. It has no way to answer the most important question: **is the signal actually right?**

| Dimension | Virat's ai-hedge-fund | Agentic Alpha Lab |
|---|---|---|
| Agent approach | 13 investor personas (LLM-first) | 9 specialists (compute-first, LLM-synthesize) |
| Backtesting | None | Vectorized engine with Almgren-Chriss market impact |
| Signal validation | None | Deflated Sharpe ratio (Bailey & López de Prado) |
| Signal decay | None | IC curves, half-life measurement, rolling IC |
| Risk management | Basic position limits | Kelly criterion, Monte Carlo VaR, circuit breakers |
| Portfolio construction | None | HRP, Black-Litterman, risk parity, efficient frontier |
| ML pipeline | None | Triple barrier labeling, purged K-fold CV, LightGBM |
| Continuous operation | Run once, read terminal output | Daily/weekly autonomous cycles, background scheduler |
| Human interaction | Read terminal output | Morning brief + chat + approval queue |
| Data sources | Paid (Financial Datasets API) | Free (YFinance, FRED API, SEC EDGAR) |
| RAG over filings | None | LanceDB vector store over actual 10-K/10-Q text |
| Thought stream | Hidden | Real-time WebSocket broadcast, every step visible |
| Learning from outcomes | None | Weekly meta-review, weight adjustment by strategy |

**We start where Virat ends.**

### Our Thesis: Computation First, LLM Synthesis Second

The analytics engine is 28,000 lines. The agent prompts are thousands of words. But the agents do not read the prompts first — they run the computation first. A language model has no business forming a view on NVDA's mean reversion potential without first seeing the z-score, the historical win rate across 47 instances, the signal half-life, and the deflated Sharpe p-value.

That ordering — compute everything, format it as structured context, then optionally use an LLM to synthesize insight — is the architectural decision that makes the platform's outputs defensible.

Every claim the Research Director makes in the morning brief has a computation behind it. "62% win rate" is not an estimate. It is the output of `VectorizedBacktestEngine` run on 47 historical instances of the same signal pattern.

### The Living Lab Concept

Most tools you operate. You open them, enter a query, read the result, close them. The Agentic Alpha Lab operates in the other direction: it works while you sleep, presents its findings when you wake, and waits for your judgment before it acts.

The platform runs a pre-market scan at 5am, generates signals by 6am, evaluates risk by 7am, and has a morning brief ready on your dashboard at 8am — without you touching anything. When you approve an NVDA long, it sizes the position using Kelly criterion, routes it to paper trading, and starts monitoring for the exit signal. Friday afternoon it reviews what worked, adjusts strategy weights accordingly, and incorporates that learning into the following week.

You provide direction, judgment, and the contextual knowledge the agent cannot have. The agent provides breadth, computation, and memory. Together you form a research team that is better than either alone.

---

## How It Works — The Research Cycle

### A Complete Day in the Life of the Platform

```
05:00 AM  PRE-MARKET SCAN
          │
          ├─ The Technician:       RSI, MACD, Bollinger for 50 tickers
          ├─ The Quant:            z-scores, momentum ranks, factor exposures
          └─ The Macro Strategist: FRED yield curve, VIX, overnight regime check

06:00 AM  SIGNAL GENERATION
          │
          ├─ Research Director:   Identify tickers with converging signals
          ├─ The Fundamentalist:  RAG over latest 10-K/10-Q for top candidates
          └─ The Sentiment:       Earnings call tone analysis for top candidates

07:00 AM  RISK EVALUATION
          │
          ├─ Risk Manager:        Portfolio-level VaR with proposed positions
          └─ Portfolio Architect: Kelly + risk parity sizing for approved shapes

07:30 AM  MORNING BRIEF GENERATED
          │
          └─ Research Director:   Compile findings → write brief → queue approvals

08:00 AM  HUMAN OPENS DASHBOARD
          │
          ├─ Reads morning brief
          ├─ Approves/rejects/asks questions via chat
          └─ Approved trades routed to paper trading

09:30 AM  MARKET OPEN
          │
          └─ Execution Strategist: VWAP/TWAP scheduling for approved trades

04:00 PM  MARKET CLOSE — DAILY REVIEW
          │
          ├─ The Quant:           Daily P&L, factor exposure update
          └─ Risk Manager:        Drawdown check, circuit breaker evaluation

05:00 PM  POST-MARKET
          │
          ├─ The Fundamentalist:  Process new SEC filings (EDGAR RSS)
          ├─ The Sentiment:       Process new earnings transcripts
          └─ The Quant:           Update signal decay metrics for all live signals

06:00 PM  WEEKLY REVIEW (Fridays only)
          │
          ├─ Research Director:   Which strategies worked? Which failed?
          ├─ The Quant:           Full IC decay analysis, regime detection
          └─ Portfolio Architect: Rebalancing proposal with turnover estimate
```

### Step 1: Pre-Market Scan — What Actually Runs

When The Technician scans 50 tickers, it is not asking an LLM to guess which look interesting. It calls `indicators.py` for every ticker and computes RSI(14), MACD(12,26,9), Bollinger %B, ATR(14), and OBV from raw OHLCV data. The output is a ranked list with specific numbers:

```
The Technician: Scanning 50 tickers for RSI/MACD signals...
The Technician: Found 3 oversold candidates: NVDA (RSI=28), AMD (RSI=31), QCOM (RSI=33)
The Technician: MACD crossover imminent on NVDA: hist=-0.12, approaching signal line
The Quant:      Computing z-scores for oversold candidates...
The Quant:      NVDA z=-2.1 (ENTRY), AMD z=-1.4 (watching), QCOM z=-0.8 (no signal)
```

### Step 2: Signal Generation — From Numbers to Validated Signals

When NVDA clears the z-score threshold, The Quant does not stop at "oversold." It runs a historical backtest of every prior instance where NVDA hit z < -2.0 and measures outcomes at 1, 5, 10, 15, 20, and 30-day horizons. It computes the IC curve to find the signal half-life. It applies the deflated Sharpe ratio to adjust for the number of parameter combinations tested.

Only when the historical win rate exceeds 55% AND the deflated Sharpe p-value is below 0.05 does The Quant return a bullish signal:

```python
# Decision logic — no LLM involved
if z_value < -2.0 and win_rate > 55.0:
    signal = "bullish"
    confidence = min(win_rate / 100, abs(z_value) / 4, 1.0)
elif z_value > 2.0 and win_rate > 55.0:
    signal = "bearish"
    confidence = min(win_rate / 100, z_value / 4, 1.0)
else:
    signal = "neutral"
    confidence = 0.0
```

### Step 3: Risk Evaluation — The Mandatory Gate

Every signal that clears statistical validation goes to the Risk Manager, which has veto authority. It computes the portfolio-level VaR impact of adding the proposed position, checks sector exposure limits (40% cap), verifies position size limits (10% cap), and sizes the position using Kelly criterion. If adding NVDA would push tech sector exposure to 41%, the trade is blocked regardless of signal quality.

```
Risk Manager: Adding NVDA long: portfolio VaR changes from -1.8% to -2.1% (within 3% limit)
Risk Manager: Sector tech exposure: 36% (within 40% limit) ✓
Risk Manager: Kelly sizing on $100K: f* = 0.042 → $4,200 position
```

### Step 4: Human Approval — The Gate That Matters

High-conviction signals (confidence > 0.70, 5+ agents agreeing) generate pending approvals in the morning brief. The approval flow is a first-class UI element — not buried in a menu. Each pending approval shows the full reasoning chain, which agents agree, historical win rate, and Kelly sizing.

The human's approval captures context the agent cannot have: "I already have conviction in the semiconductor space" or "I know NVDA has a product launch next week that changes the risk profile." The agent provides the research. The human provides the judgment.

### Step 5: Execution — Paper Trading

Approved trades go to the Execution Strategist, which schedules VWAP or TWAP orders to minimize market impact. The platform currently runs in paper trading mode via simulated execution. The position is then monitored continuously against the signal's half-life — if NVDA's z-score reverts before the 12-day half-life, the exit signal fires.

### Step 6: Post-Market Review — What the Agent Learned

The weekly review cycle is where the platform earns the word "learning." The Research Director reviews which signals fired, which were approved, and which were profitable. It detects if a strategy's IC is decaying (the edge is disappearing) and adjusts strategy weights accordingly. "Last week's momentum signals: 2/5 profitable. Increasing mean reversion weight." This is systematic meta-research applied to the platform's own track record.

---

## The 9 Specialist Agents

Each agent is a Python class with a `run(ticker, start_date, end_date)` method that returns an `AgentFinding` dataclass:

```python
@dataclass
class AgentFinding:
    agent_name: str
    ticker: str
    signal: str          # "bullish" | "bearish" | "neutral"
    confidence: float    # 0.0 to 1.0
    reasoning: str       # One-line summary with specific numbers
    details: dict        # All computed metrics
    thoughts: list[str]  # The thought stream — every step, visible to user
```

Every agent broadcasts its `thoughts` as WebSocket events in real-time. The dashboard renders them as a live feed. Each thought line is clickable — expand to see the raw computation.

---

### The Quant

The statistical edge-finder. Hunts for mean-reversion opportunities by computing z-scores, backtesting historical signal performance, measuring signal decay half-lives, and validating results with the deflated Sharpe ratio to guard against overfitting. The Quant is skeptical by default — it only elevates a signal when the historical evidence meets strict quantitative thresholds.

**What it computes:**

| Metric | Formula / Source | Threshold |
|---|---|---|
| Rolling z-score | `(price - mean_20d) / std_20d` | Signal when `|z| >= 2.0` |
| Momentum rank | Cross-sectional 12-1 momentum, percentile rank | Confirms or contradicts mean-reversion |
| Historical win rate | Backtest on prior `z < -2.0` instances | Must exceed 55% across `n >= 10` |
| Signal half-life | Days for IC curve to decay to 50% of peak IC | 10-30 days = actionable |
| Deflated Sharpe ratio | Bailey & López de Prado, 10 trials adjusted | p < 0.05 required |

**Confidence formula:** `min(win_rate / 100, |z_value| / 4, 1.0)`

**Example thought stream:**
```
Fetched 504 price bars for NVDA.
Computing z-score for NVDA... z = -2.1
Z-score at -2.1 -- past -2.0 entry threshold.
Backtesting 47 historical instances of z < -2.0...
Historical: 47 instances, 62.0% win rate, +2.1% avg return.
Signal half-life: 12.3 days (IC peaks at day 5, decays by day 17).
Deflated Sharpe p=0.031 -- significant (accounting for 10 parameter trials).
Final signal: bullish (confidence: 0.53).
```

**Example finding:**
```json
{
  "agent_name": "the_quant",
  "ticker": "NVDA",
  "signal": "bullish",
  "confidence": 0.53,
  "reasoning": "Z-score deeply negative (-2.1) with 62% historical win rate across 47 instances -- mean reversion buy.",
  "details": {
    "zscore": -2.1,
    "momentum": -0.031,
    "backtest_win_rate": 62.0,
    "backtest_avg_return": 2.1,
    "backtest_n_signals": 47,
    "backtest_sharpe": 0.91,
    "signal_half_life": 12.3,
    "ic_curve_summary": {"peak_ic": 0.14, "horizon_at_peak": 5, "half_life": 12.3},
    "deflated_sharpe": 0.58,
    "deflated_sharpe_pvalue": 0.031
  }
}
```

**Signal rules (no LLM required):**
- Bullish: `z < -2.0` AND `win_rate > 55%`
- Bearish: `z > +2.0` AND `win_rate > 55%`
- Neutral: all other cases, including insufficient historical sample

---

### The Technician

Chart pattern recognition and momentum indicator analysis. Computes every standard technical indicator from raw OHLCV data — not from a library that might have look-ahead bias. The Technician scores each indicator independently and aggregates into a consensus technical signal. No LLM required.

**What it computes:**

| Indicator | Computation | Bullish Rule |
|---|---|---|
| RSI(14) | `100 - (100 / (1 + avg_gain / avg_loss))` | RSI < 30 (oversold) |
| MACD(12,26,9) | `EMA_12 - EMA_26`, signal = `EMA_9(MACD)` | MACD crosses above signal |
| Bollinger %B | `(price - lower_band) / (upper_band - lower_band)` | %B < 0.05 (extreme low) |
| ATR(14) | Average true range, normalized | Volatility context only |
| OBV | Cumulative volume + price direction | OBV uptrend confirms |

**Example thought stream:**
```
Computing RSI(14) for NVDA... RSI = 28.4 (oversold territory).
MACD(12,26,9): MACD=-0.12, Signal=-0.18, Hist=+0.06. Crossover imminent.
Bollinger Bands: %B = 0.04 -- price at extreme lower band.
OBV trend: rising -- volume confirms potential reversal.
Technical consensus: bullish (3/4 indicators aligned).
```

**Signal rules:** Bullish when 3 or more of 4 indicators signal oversold/reversal. Bearish when 3 or more signal overbought/breakdown.

---

### The Contrarian

Looks for crowded trades, tail risks, and volatility anomalies. The Contrarian does not follow momentum — it checks whether the crowd already agrees with the proposed trade, because crowded trades have asymmetric downside. Inspired by Burry and Taleb, it asks: who is on the other side of this trade, and what happens if they all exit at once?

**What it computes:**

| Metric | Source | Bearish Concern |
|---|---|---|
| Implied vs realized vol | `analytics/options.py` (Black-Scholes IV vs GARCH realized) | IV > 1.4x realized = expensive risk premium |
| Short interest proxy | Momentum factor crowding (top 10% momentum = crowded) | Top decile = crowded long |
| Monte Carlo stress VaR | Cholesky-correlated 10,000-path simulation | 2x vol shock stress-test |
| Put/call ratio proxy | Derived from option surface skew | Elevated skew = tail fear |

**Example thought stream:**
```
NVDA implied vol: 42% vs realized vol: 28%. IV premium: 14%.
Checking momentum crowding... NVDA momentum rank: 72nd percentile. Not top-decile crowded.
Short interest proxy: 1.2% -- not a crowded long.
Monte Carlo stress test (2x vol shock): max drawdown -8.2%.
Risk/reward is balanced. No objection to the long thesis.
Final signal: neutral (confidence: 0.30). Contrarian is not blocking.
```

**Signal rules:** Bearish override when implied vol premium exceeds 40%, momentum crowding in top 10th percentile, or stress VaR exceeds 15%.

---

### The Sentiment Analyst

NLP analysis of earnings calls, SEC filings, and news sentiment. Uses Loughran-McDonald financial word lists — the industry standard for financial text, which treats words like "liability" as neutral rather than negative. The key differentiator is tone shift analysis: comparing management language in prepared remarks versus the Q&A session, which often reveals unscripted confidence or anxiety.

**What it computes:**

| Metric | Source | What It Reveals |
|---|---|---|
| L-M positive/negative ratio | `research/nlp/sentiment.py` | Overall document sentiment |
| Tone shift (prepared vs Q&A) | Per-section analysis | Unscripted confidence level |
| Quarter-over-quarter drift | Rolling sentiment across last 4 calls | Trend in management outlook |
| Key phrase frequency | "AI infrastructure", "cautious", "headwinds" | Thematic shifts |
| Forward guidance language | Explicit guidance sentences | Revenue/margin trajectory |

**Example thought stream:**
```
Analyzing NVDA Q3 2024 earnings call transcript (47 pages)...
Loughran-McDonald sentiment: positive ratio 0.31, negative ratio 0.08.
Management tone (prepared): +0.24. Management tone (Q&A): +0.43.
Tone shift: +0.19 (CEO more confident in Q&A than prepared remarks -- bullish signal).
Key phrases: "AI infrastructure" 14x (vs 3x last year), "data center" 22x.
Quarter-over-quarter drift: improving (+0.12 over 3 quarters).
Final signal: bullish (confidence: 0.68).
```

**Signal rules:** Bullish when tone shift > +0.15 and positive/negative ratio > 3.0. Bearish when tone shift < -0.15 or drift is declining across 3+ quarters.

---

### The Fundamentalist

Reads actual SEC filings via EDGAR XBRL data, computes intrinsic value using a 3-stage DCF model, and calculates margin of safety. Unlike agents that rely on pre-digested financial data, The Fundamentalist uses the platform's RAG pipeline to read the actual 10-K text and identify qualitative changes — "what changed in the latest filing vs prior year?"

**What it computes:**

| Metric | Formula | Threshold |
|---|---|---|
| Revenue growth (YoY) | `(rev_t - rev_{t-1}) / rev_{t-1}` | Positive + accelerating = bullish |
| Gross margin | `gross_profit / revenue` | Trend matters more than level |
| Free cash flow yield | `FCF / market_cap` | > 4% = attractive |
| DCF intrinsic value | 3-stage: growth → transition → terminal | Industry-appropriate discount rate |
| Margin of safety | `(intrinsic - price) / intrinsic` | > 15% = buy, < 0% = avoid |
| Earnings consistency | Trend over 4+ quarters | Smooth growth = higher quality |

**Example thought stream:**
```
Fetching NVDA 10-K filed 2024-10-31 via EDGAR XBRL...
Revenue: $60.9B (+94% YoY). Gross margin: 72.7% (expanding).
FCF: $15.2B. FCF yield: 2.8% at current price.
Running 3-stage DCF: growth 45% yr1-3, 20% yr4-6, 4% terminal...
DCF intrinsic value: $187. Current price: $173. Margin of safety: 8%.
RAG query: "What changed vs prior year?" → Data center: 87% of revenue (vs 56%).
Earnings consistency: 6 consecutive quarters of beat-and-raise.
Final signal: bullish (confidence: 0.61). Margin of safety thin but fundamentals improving.
```

**Signal rules:** Bullish when margin of safety > 10% AND revenue growth is positive AND FCF yield > 2%. Bearish when price > intrinsic value by more than 20%.

---

### The Macro Strategist

Analyzes the macroeconomic environment using FRED data, yield curves, and regime detection. The key insight is that not all signals perform equally in all regimes — momentum strategies historically underperform in late-cycle high-volatility regimes by 3-4%, while mean-reversion strategies thrive in low-volatility regimes. The Macro Strategist provides this regime context to calibrate conviction in other agents' signals.

**What it computes:**

| Metric | Source | What It Signals |
|---|---|---|
| Yield curve spread (10Y-2Y) | FRED API | Inversion = recession risk |
| VIX level + trend | Market data | Vol regime classification |
| Unemployment trend | FRED | Cycle position |
| Fed funds rate vs historical | FRED | Policy stance |
| Regime classification | Rule-based: low/high vol, trending/mean-reverting | Strategy performance adjustment |

**Example thought stream:**
```
Fetching FRED macro data...
Yield curve (10Y-2Y): +0.45% (not inverted -- no near-term recession signal).
VIX: 14.2 (low-volatility regime, 30th percentile historically).
Unemployment: 4.1% (stable, no deterioration trend).
Regime: LOW_VOL_TRENDING -- momentum historically +2.1% alpha in this environment.
Mean reversion note: low-vol regimes are favorable (less noise contamination).
Final signal: bullish (confidence: 0.52). Macro supports risk-taking.
```

**Signal rules:** Bearish override when yield curve is inverted AND VIX > 25 (recession + high-vol). Bullish when yield curve positive AND VIX < 18.

---

### The Risk Manager

The only agent with true veto power over all signals. It does not generate trade ideas — it evaluates whether proposed positions are safe to hold at the portfolio level. It computes portfolio-wide VaR with the proposed new position, checks all limit constraints, and sizes positions using the full Kelly criterion.

**What it computes:**

| Metric | Formula | Hard Limit |
|---|---|---|
| Portfolio VaR (95%) | `percentile(portfolio_returns, 5%)` with new position | 3% per day |
| Portfolio CVaR | `mean(returns[returns < VaR])` | 5% per day |
| Position size | Kelly: `f* = (p*b - q) / b` | 10% max per position |
| Sector exposure | Sum of long weights per GICS sector | 40% max per sector |
| Correlation check | New position correlation to existing portfolio | Flag if > 0.7 |
| Drawdown check | Rolling max drawdown vs circuit breaker | -15% triggers halt |

**Example thought stream:**
```
Evaluating NVDA LONG proposal for portfolio risk impact...
Current portfolio VaR (95%): -1.8%. Adding NVDA at 4.2%...
New portfolio VaR: -2.1% (within 3% limit ✓).
Sector tech exposure post-add: 36% (within 40% limit ✓).
Correlation of NVDA with existing positions: 0.42 (moderate, acceptable ✓).
Kelly sizing: f* = (0.62 * 2.1 - 0.38) / 2.1 = 0.042 → $4,200 on $100K.
Circuit breaker check: rolling 30d drawdown = -3.2% (far from -15% limit ✓).
Decision: APPROVED. Kelly position: $4,200.
```

**Veto conditions:** Triggers if VaR limit would be breached, sector limit exceeded, or drawdown circuit breaker is active.

---

### The Portfolio Architect

Constructs the optimal portfolio from all approved signals, solving for the allocation that maximizes risk-adjusted return given the constraint structure. Implements Hierarchical Risk Parity (HRP), Black-Litterman with agent signals as views, and risk parity as alternative weighting schemes.

**What it computes:**

| Method | What It Solves | When Used |
|---|---|---|
| HRP (Hierarchical Risk Parity) | Cluster-based allocation without matrix inversion | Default — robust to estimation error |
| Black-Litterman | Equilibrium returns + agent signals as views | When agent signals are strong |
| Risk parity | Equal risk contribution per position | Regime-uncertain environments |
| Efficient frontier | Maximum Sharpe subject to constraints | When return estimates are reliable |

**Example thought stream:**
```
Collecting approved signals: NVDA LONG, MSFT LONG, TSLA SHORT.
Running Hierarchical Risk Parity optimization...
HRP clusters: [NVDA, MSFT] correlated cluster vs [TSLA] independent.
HRP weights: NVDA 4.2%, MSFT 3.8%, TSLA 2.1% (short).
Estimated turnover from current portfolio: 8.3%.
Transaction cost estimate at 5bps: $415 on $100K.
Risk parity comparison: similar weights, negligible difference.
Recommendation: HRP allocation. Minimal rebalancing required.
```

---

### The Research Director

The orchestrator and the voice you interact with. The Research Director dispatches the six research specialists in parallel, collects their `AgentFinding` objects, aggregates votes, resolves disagreements, and synthesizes everything into the morning brief and chat responses. It coordinates those who compute, and uses language to present the synthesis with a direct, confident voice.

**Orchestration logic:**

1. Dispatch all 6 research agents in parallel for the target ticker
2. Collect findings: `{bullish: N, bearish: N, neutral: N}`
3. Consensus signal = majority vote; confidence = mean agent confidence
4. High conviction flag = True when consensus has > 4/6 votes
5. Route to Risk Manager → Portfolio Architect → approval queue
6. Write morning brief ordered by consensus confidence

**Voice guidelines (from the system prompt):**
- "My view is bullish" — not "the signal might lean slightly positive"
- "4/6 agents bullish. The Quant sees z=-2.34 with 62% win rate."
- "The team is split 3/3 — here is why the disagreement exists."
- Every answer ends with what to do next

**Example chat interaction:**
```
You: Why NVDA not AMD? Both are oversold.

Research Director: Good question — three key differences separate them.

Signal strength: NVDA z=-2.1 (past the -2.0 entry threshold). AMD z=-1.4
(approaching but not there). We require z < -2.0 for mean reversion entry.

Fundamental backing: NVDA revenue +94% YoY with expanding margins.
AMD revenue +2% — the oversold condition may be justified by slowing growth,
not a temporary dip. The Fundamentalist sees no margin of safety on AMD.

Historical edge: When NVDA hits z=-2.0 with positive fundamentals,
win rate is 62% over 47 instances. AMD in similar conditions: 41% over
23 instances. The edge is weaker and the sample is thin.

Bottom line: NVDA is oversold AND fundamentally strong. AMD is just oversold.
I would wait for AMD to show fundamental improvement before entering.

[Run NVDA backtest]  [Compare NVDA vs AMD]  [Add AMD to watchlist]
```

---

## The Dashboard — 6 Pages

### Monitor (`/`)

The default landing page. Designed to be the first thing you see each morning — a personalized research brief, not a data terminal.

**What it shows:**
- Personalized greeting with date and overnight scan summary count
- Top Conviction section: highest-confidence signals with multi-agent reasoning chains
- Watchlist: tickers approaching entry thresholds, with distance to signal
- Portfolio Health panel: P&L, Sharpe (rolling 30d), VaR status, signal decay health
- "What I Learned" section: meta-learning from recent signal performance
- Thought Stream sidebar: real-time WebSocket feed of agent reasoning

**Key UX features:**
- Approve/Reject/Dig Deeper buttons directly on each conviction card — no navigation required
- Thought stream entries are expandable (click to see raw computation output)
- Agent status bar at top: "3 agents active · 47 tasks today · Next cycle: 2h 14m"
- Signal cards age visually in real-time — green fades toward yellow as half-life approaches

**Backend connection:** Polls `GET /api/agents/status` on load; subscribes to `/ws` for live thought stream events; posts to `/api/agents/approve` on user action.

---

### Chat (`/chat`)

The research conversation interface. Every response from the Research Director is grounded in computation — not retrieved from memory or generated speculatively.

**What it shows:**
- Message thread with rich card rendering for responses
- Each response includes: answer text, inline data tables, agent trace (expandable), action buttons
- Citation badges on every factual claim: "Source: The Quant, 47 backtest instances"
- Sparkline charts inline for trend data
- Suggested actions rendered as clickable buttons: "Run Backtest", "Approve Trade", "Compare with peers"

**Key UX features:**
- Agent trace is collapsible — you can see which of the 6 specialists were consulted
- Action buttons route directly to the relevant workflow (approve → approval queue)
- Conversation history persists across sessions

**Backend connection:** `POST /api/chat` for each message; response includes `answer`, `citations`, `actions`, `agent_traces`.

---

### Signals (`/signals`)

The signal board — a grid view of all active signals with visual decay aging.

**What it shows:**
- Signal cards: ticker, direction (LONG/SHORT), confidence bar, strategy type, age
- Visual aging: signal cards transition green → yellow → orange → red as they approach their half-life
- Expanded view: full reasoning chain with all 6 agent votes
- Signal graveyard: recently expired signals with outcome (profitable/not profitable)

**Key UX features:**
- Filter by strategy (mean reversion, momentum, pairs, fundamental)
- Filter by agent (show only signals where The Quant has high conviction)
- Sort by confidence, age, or potential return estimate
- Color encoding is semantically meaningful — red means aging, not bearish

---

### Performance (`/performance`)

Track record and signal quality metrics. Honest accounting of what worked and what did not.

**What it shows:**
- Equity curve (paper trading P&L over time)
- Signal scorecard: "This period: 7/12 signals profitable, +2.3% net"
- Strategy breakdown: mean reversion vs momentum vs fundamental vs pairs
- Agent accuracy table: per-agent win rate across approved signals
- Signal decay monitor: IC curves for active signals, half-life remaining

**Key UX features:**
- Monthly returns heatmap (green/red calendar view)
- Drawdown overlay on equity curve
- Agent accuracy sorts reveal which specialists are most predictive in current regime

---

### Agents (`/agents`)

The technical page — 3D visualizations and agent activity timeline.

**What it shows:**
- Agent activity timeline: which agents ran, when, and what they found
- 3D volatility surface: implied vol across strike and time (Three.js + React Three Fiber)
- 3D correlation heatmap: portfolio position correlations in 3D space
- Factor exposure scatter: position-level Fama-French factor loadings

---

### Settings (`/settings`)

Configuration and connectivity.

**What it shows:**
- API key status for each LLM provider (green/red indicators)
- Model selector: switch default LLM with a dropdown
- Demo/Live toggle: demo mode uses pre-fetched data, live mode hits live APIs
- Ticker universe configuration: add/remove tickers from the scan universe
- Pre-fetch button: download and cache data for offline demo

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CONSUMER LAYER                                │
│                                                                      │
│   Next.js Dashboard    Research Chat     CLI        MCP Server      │
│   (6 pages, React 19)  (WebSocket)    (scripts/)  (7 tools, STDIO)  │
└────────────────────────────┬────────────────────────────────────────┘
                             │  HTTP + WebSocket
┌────────────────────────────▼────────────────────────────────────────┐
│                    API LAYER  (FastAPI, port 8100)                   │
│                                                                      │
│   POST /api/research         POST /api/chat                         │
│   POST /api/agents/run       POST /api/agents/approve               │
│   POST /api/cycles/run-daily GET  /api/models                       │
│   POST /api/backtest         POST /api/signal-decay                 │
│   WS   /ws  (event stream)                                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│               AGENT ORCHESTRATION (LangGraph DAG)                   │
│                                                                      │
│   Research Director                                                  │
│   ├── [parallel] The Quant                                          │
│   ├── [parallel] The Technician                                     │
│   ├── [parallel] The Contrarian                                     │
│   ├── [parallel] The Sentiment Analyst                              │
│   ├── [parallel] The Fundamentalist                                 │
│   └── [parallel] The Macro Strategist                               │
│         │                                                            │
│   [Human Approval Gate] ──── pending_approvals queue               │
│         │                                                            │
│   Risk Manager (veto authority)                                     │
│   Portfolio Architect (sizing + optimization)                       │
│   Execution Strategist (VWAP/TWAP scheduling)                       │
│                                                                      │
│   Background Scheduler: DailyCycle + WeeklyCycle (asyncio)         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                     ANALYTICS ENGINE  (~8,984 lines)                 │
│                                                                      │
│   analytics/         features/          strategies/                 │
│   ├─ returns.py      ├─ technical/      ├─ mean_reversion/          │
│   ├─ statistics.py   │  ├─ indicators   ├─ momentum/                │
│   ├─ signal_decay    │  ├─ zscore       └─ combiner.py              │
│   ├─ factors.py      │  └─ momentum     risk/                       │
│   ├─ options.py      └─ store.py (DDB) ├─ manager.py                │
│   └─ microstructure  models/           ├─ position_sizing/          │
│                      ├─ training/      ├─ var/monte_carlo           │
│   backtest/          │  ├─ labeling    └─ monitoring/               │
│   ├─ engine/         │  └─ cross_val   portfolio/                   │
│   ├─ validation.py   └─ inference/     └─ optimization/             │
│   └─ execution_model                                                 │
│                      research/nlp/     execution/                   │
│                      ├─ sentiment      ├─ algorithms/               │
│                      ├─ document_proc  └─ paper_trader              │
│                      └─ rag_pipeline                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         DATA LAYER                                   │
│                                                                      │
│   YFinance (OHLCV)    FRED API (macro)    SEC EDGAR (filings)       │
│   DuckDB + Parquet    LanceDB (vectors)   In-memory Polars frames    │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow: From YFinance to Dashboard

```
YFinance OHLCV
    │
    ▼
data/fetchers/market.py
    │  Polars DataFrame: date, open, high, low, close, volume
    ▼
features/technical/indicators.py
    │  RSI, MACD, Bollinger, ATR, OBV (no look-ahead)
    ├─ features/technical/zscore.py    → rolling 20-day z-score
    └─ features/technical/momentum.py  → 12-1 momentum rank
    │
    ▼
strategies/mean_reversion/  or  strategies/momentum/
    │  signal DataFrame: date, signal (1/-1/0), position
    ▼
backtest/engine/vectorized.py  (Polars-native)
    │  BacktestResult: equity_curve, trades, metrics
    ├─ backtest/validation.py     → deflated Sharpe, Bonferroni
    └─ analytics/signal_decay.py  → IC curve, half-life
    │
    ▼
agents/specialists/the_quant.py
    │  AgentFinding: signal, confidence, reasoning, thoughts
    ▼
agents/specialists/research_director.py
    │  Synthesis: vote aggregation, morning brief JSON
    ▼
api/server.py  (FastAPI)
    │  JSON response + WebSocket events
    ▼
dashboard/src/  (Next.js 15)
    │  Morning brief, thought stream, signal cards
    ▼
User
```

### How the Thought Stream Works (WebSocket)

Every agent emits thoughts as they compute. These are broadcast via `api/events.py` to all connected WebSocket clients:

```python
# Each thought emitted as an event
await event_manager.broadcast({
    "type": "agent_thought",
    "agent": "the_quant",
    "ticker": "NVDA",
    "thought": "Computing z-score for NVDA... z = -2.1",
    "timestamp": "2026-04-09T16:42:33Z"
})
```

The dashboard subscribes to `/ws` and appends each event to the thought stream UI. No polling — pure WebSocket push.

### How the Approval Gate Works

```
Research Director → pending_approvals queue
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    Dashboard:      Chat response:   API polling:
    Approve card    "Trade ready"    GET /api/agents/status
         │
    User clicks [Approve]
         │
    POST /api/agents/approve
         │
    Risk Manager: final VaR check
         │
    Portfolio Architect: sizing confirmation
         │
    Execution Strategist: VWAP schedule
         │
    Paper trading execution
```

---

## API Reference

### `GET /api/health`

```json
{"status": "ok", "platform": "Agentic Alpha Lab"}
```

---

### `GET /api/strategies`

```json
{"strategies": ["mean_reversion", "momentum", "pairs_trading", "fundamental"]}
```

---

### `GET /api/models`

List configured LLM models and API key status.

```json
{
  "default_model": "claude-sonnet",
  "api_keys": {"anthropic": true, "openai": false, "gemini": true},
  "models": [
    {"alias": "claude-sonnet", "model_id": "anthropic/claude-sonnet-4-20250514", "available": true},
    {"alias": "gpt-4o", "model_id": "openai/gpt-4o", "available": false}
  ]
}
```

---

### `POST /api/research`

Run the full research pipeline for one ticker. Synchronous.

```json
// Request
{
  "ticker": "NVDA",
  "strategy": "mean_reversion",
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000.0
}

// Response
{
  "ticker": "NVDA",
  "signal": {"direction": "bullish", "confidence": 0.53, "zscore": -2.1},
  "backtest": {
    "total_return": 0.241, "sharpe_ratio": 0.91,
    "max_drawdown": -0.142, "win_rate": 0.62, "n_trades": 47
  },
  "signal_decay": {"half_life": 12.3, "peak_ic": 0.14, "peak_horizon": 5},
  "validation": {"deflated_sharpe": 0.58, "deflated_sharpe_pvalue": 0.031}
}
```

---

### `POST /api/chat`

Research chat with computation-backed responses.

```json
// Request
{
  "message": "Why NVDA not AMD?",
  "history": [{"role": "user", "content": "Analyze NVDA"}, {"role": "assistant", "content": "..."}],
  "model": "claude-sonnet"
}

// Response
{
  "answer": "**Three key differences separate NVDA from AMD right now.**\n\n...",
  "citations": [
    "the_quant: NVDA z=-2.1 (entry), AMD z=-1.4 (watching). Win rates: 62% vs 41%.",
    "the_fundamentalist: NVDA revenue +94% YoY vs AMD +2%."
  ],
  "actions": ["Run NVDA backtest", "Compare NVDA vs AMD", "Add AMD to watchlist"],
  "agent_traces": [
    {"agent": "the_quant", "signal": "bullish", "confidence": 0.53, "thoughts": ["..."]}
  ]
}
```

---

### `POST /api/agents/run`

Start the multi-agent pipeline. Asynchronous — results stream via WebSocket.

```json
// Request
{"ticker": "NVDA", "agents": ["all"]}

// Response (immediate)
{"status": "running", "run_id": "run_20260409_164231", "websocket": "/ws"}
```

---

### `POST /api/agents/approve`

Approve or reject a pending signal.

```json
// Request
{"ticker": "NVDA", "action": "approve", "run_id": "run_20260409_164231"}

// Response
{"status": "approved", "trade": {"ticker": "NVDA", "direction": "long", "size": 4200.0}}
```

---

### `GET /api/agents/status`

```json
{
  "active_agents": 3,
  "tasks_today": 47,
  "next_cycle": "2026-04-09T05:00:00Z",
  "pending_approvals": 1,
  "last_brief_at": "2026-04-09T07:30:00Z"
}
```

---

### `POST /api/cycles/run-daily`

Manually trigger the daily research cycle.

```json
// Request
{"tickers": ["NVDA", "AAPL", "MSFT"]}

// Response
{"status": "started", "cycle_id": "daily_20260409"}
```

---

### `POST /api/backtest`

```json
// Request
{
  "signals_csv": "date,signal\n2020-01-02,1\n2020-01-03,0\n...",
  "prices_csv": "date,close\n2020-01-02,315.42\n...",
  "initial_capital": 100000.0
}

// Response
{
  "total_return": 0.241, "sharpe_ratio": 0.91,
  "max_drawdown": -0.142, "n_trades": 47,
  "equity_curve": [...]
}
```

---

### `POST /api/signal-decay`

```json
// Request
{"signals_csv": "...", "prices_csv": "...", "max_horizon": 60}

// Response
{
  "ic_curve": [{"horizon": 1, "ic": 0.11}, {"horizon": 5, "ic": 0.14}],
  "half_life": 12.3,
  "summary": {"peak_ic": 0.14, "horizon_at_peak": 5, "decays_to_zero_by": 28}
}
```

---

### `POST /api/models/test`

```json
// Request
{"model": "claude-sonnet", "prompt": "Current outlook for US equities?"}

// Response
{"model": "claude-sonnet", "response": "...", "tokens_used": 142, "latency_ms": 1840}
```

---

### `WS /ws` — Real-Time Event Stream

```json
// Agent reasoning
{"type": "agent_thought", "agent": "the_quant", "ticker": "NVDA", "thought": "z = -2.1", "timestamp": "..."}

// Signal generated
{"type": "signal_generated", "ticker": "NVDA", "signal": "bullish", "confidence": 0.84}

// Human action required
{"type": "approval_required", "ticker": "NVDA", "run_id": "run_...", "rationale": "5/6 agents bullish"}

// Cycle lifecycle
{"type": "cycle_started", "cycle": "daily", "tickers": 50}
{"type": "cycle_complete", "cycle": "daily", "duration_seconds": 847}
```

### MCP Server (7 Tools)

The platform exposes its analytics engine via Model Context Protocol, allowing any MCP-compatible agent to use these tools:

| Tool | What It Does |
|---|---|
| `research_strategy` | Full pipeline: data → signals → backtest → findings |
| `fetch_market_data` | OHLCV data for any ticker, any date range |
| `run_backtest` | Backtest signal DataFrame with transaction costs |
| `analyze_sentiment` | Loughran-McDonald sentiment on financial text |
| `compute_risk_metrics` | VaR, CVaR, Sharpe, max drawdown |
| `analyze_signal_decay` | IC curve + half-life for a signal series |
| `research_filing` | RAG query over SEC 10-K/10-Q documents |

---

## Multi-Model LLM Support

### How Routing Works

Every LLM call goes through `core/llm.py`, which uses LiteLLM as a unified routing layer. Switch between providers by changing a single environment variable — the prompt structure, response parsing, and error handling remain identical.

```python
# core/llm.py — model aliases (excerpt)
MODEL_ALIASES: dict[str, str] = {
    "claude-opus":   "anthropic/claude-opus-4-20250514",
    "claude-sonnet": "anthropic/claude-sonnet-4-20250514",
    "claude-haiku":  "anthropic/claude-haiku-4-5-20251001",
    "gpt-4o":        "openai/gpt-4o",
    "gpt-4o-mini":   "openai/gpt-4o-mini",
    "o3":            "openai/o3",
    "o4-mini":       "openai/o4-mini",
    "gemini-flash":  "gemini/gemini-2.5-flash",
    "gemini-pro":    "gemini/gemini-2.5-pro",
    # ... Groq, DeepSeek
}
```

### Model Reference Table

| Provider | Alias | Full Model ID | Best For |
|---|---|---|---|
| Anthropic | `claude-sonnet` | `anthropic/claude-sonnet-4-20250514` | Nuanced financial reasoning |
| Anthropic | `claude-opus` | `anthropic/claude-opus-4-20250514` | Deep analysis, complex synthesis |
| Anthropic | `claude-haiku` | `anthropic/claude-haiku-4-5-20251001` | Fast synthesis, lower cost |
| OpenAI | `gpt-4o` | `openai/gpt-4o` | Strong general analysis |
| OpenAI | `o3` | `openai/o3` | Reasoning-intensive tasks |
| OpenAI | `o4-mini` | `openai/o4-mini` | Fast reasoning, cost-effective |
| Google | `gemini-flash` | `gemini/gemini-2.5-flash` | Real-time synthesis, lowest latency |
| Google | `gemini-pro` | `gemini/gemini-2.5-pro` | Deep research tasks |
| Groq | `llama-70b` | `groq/llama-3.3-70b-versatile` | Open source, fast inference |
| DeepSeek | `deepseek` | `deepseek/deepseek-chat` | Cost-effective alternative |

### Usage Examples

```python
from core.llm import llm_call

# Use default model from QR_DEFAULT_MODEL in .env
response = llm_call("Synthesize these agent findings into a morning brief", context=findings)

# Override per-call
response = llm_call("Analyze NVDA", model="claude-sonnet")   # Anthropic
response = llm_call("Analyze NVDA", model="gpt-4o")          # OpenAI
response = llm_call("Analyze NVDA", model="gemini-flash")    # Google (fastest)
response = llm_call("Analyze NVDA", model="llama-70b")       # Groq (open source)

# Full LiteLLM model string also accepted
response = llm_call("Analyze NVDA", model="anthropic/claude-opus-4-20250514")
```

### Adding a New Provider

LiteLLM supports 100+ providers. Adding one takes three steps:

```bash
# 1. Add the API key to .env
COHERE_API_KEY=your_key_here
```

```python
# 2. Add alias to core/llm.py
MODEL_ALIASES["command-r"] = "cohere/command-r-plus"
```

Select the alias from the Settings page dropdown. No other changes required.

### Which Agents Require LLMs

| Agent | LLM Required? | Without LLM |
|---|---|---|
| The Quant | No | Rule-based signal from z-score + win rate |
| The Technician | No | Indicator scoring aggregation |
| The Contrarian | No | Crowding + vol computation |
| The Sentiment Analyst | Optional | L-M scores only, no interpretation |
| The Fundamentalist | Optional | DCF output only, no filing narrative |
| The Macro Strategist | Optional | Regime label only, no narrative |
| Risk Manager | No | Kelly + VaR output |
| Portfolio Architect | No | HRP weights output |
| Research Director | Optional | Rule-based brief template |

The platform runs fully without any API key — agents produce signals, thought streams, and AgentFinding objects. LLM keys enable natural-language morning briefs and the chat interface.

---

## Getting Started

### Prerequisites

| Tool | Version | Required? |
|---|---|---|
| Python | 3.12+ | Yes |
| Node.js | 18+ | Yes (dashboard) |
| Poetry | Latest | Recommended |
| Any LLM API key | — | No (enables chat) |

### Step 1: Clone and Install

```bash
git clone <repo-url>
cd quant-researcher

# Python backend
pip install -e ".[dev]"
# or with Poetry (recommended):
poetry install

# Dashboard
cd dashboard && npm install && cd ..
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Open `.env` and configure:

```bash
# LLM Providers — at least one enables the chat interface.
# The platform runs without any key (computation-only mode).
ANTHROPIC_API_KEY=sk-ant-...    # Claude — best for financial reasoning
OPENAI_API_KEY=sk-...           # GPT-4o — strong alternative
GEMINI_API_KEY=AI...            # Gemini Flash — fastest synthesis
GROQ_API_KEY=gsk_...            # Llama 70B — open source option
DEEPSEEK_API_KEY=sk-...         # DeepSeek V3 — cost-effective

# Default model alias (see model table above)
QR_DEFAULT_MODEL=claude-sonnet

# Financial data — all optional. YFinance works without keys.
# FRED key enables full macro regime analysis (free).
FRED_API_KEY=                   # https://fred.stlouisfed.org/docs/api/api_key.html
ALPHA_VANTAGE_API_KEY=          # Optional alternative price data
POLYGON_API_KEY=                # Optional options data

QR_LOG_LEVEL=INFO
```

### Step 3: Pre-Fetch Demo Data (Recommended)

Downloads ~2 years of daily OHLCV for 10 tickers. Enables offline demo.

```bash
PYTHONPATH=. python scripts/prefetch_demo_data.py
```

### Step 4: Start the Servers

```bash
# Terminal 1 — Python backend (port 8100)
PYTHONPATH=. uvicorn api.server:app --port 8100 --reload

# Terminal 2 — Next.js dashboard (port 3100)
cd dashboard && PORT=3100 npm run dev
```

### Step 5: Open the Dashboard

Navigate to **http://localhost:3100**

With pre-fetched data, the morning brief generates automatically within 30-60 seconds.

### First Interaction Options

**A. Run a research cycle manually:**
```bash
curl -X POST http://localhost:8100/api/cycles/run-daily \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["NVDA", "AAPL", "MSFT"]}'
```

Watch the thought stream in the dashboard as agents analyze each ticker in real-time.

**B. Ask the research chat:**

Open `/chat` and try:
- `"What is your view on NVDA?"`
- `"Compare AAPL and MSFT"`
- `"Why is the contrarian agent neutral?"`
- `"Build me a mean reversion strategy for semiconductors"`

**C. Call the API directly:**
```bash
curl -X POST http://localhost:8100/api/research \
  -H "Content-Type: application/json" \
  -d '{"ticker": "NVDA", "strategy": "mean_reversion", "start_date": "2020-01-01", "end_date": "2024-12-31"}'
```

---

## Project Structure

```
quant-researcher/
│
├── analytics/                    # Core quant analytics library (~1,778 lines)
│   ├── returns.py               # Sharpe, Sortino, VaR, CVaR, drawdown, beta, alpha (314 lines)
│   ├── statistics.py            # ADF, KPSS, Hurst exponent, cointegration, OU half-life (290 lines)
│   ├── signal_decay.py          # IC curves, half-life, rolling IC, decay comparison (348 lines)
│   ├── factors.py               # Fama-French 3/5, factor attribution, rolling exposure (282 lines)
│   ├── options.py               # Black-Scholes, Greeks, implied vol, GARCH (292 lines)
│   └── microstructure.py        # VWAP, TWAP, Amihud illiquidity, Kyle's lambda (252 lines)
│
├── strategies/                   # Trading strategy implementations (~688 lines)
│   ├── mean_reversion/          # Z-score + cointegrated pairs trading
│   ├── momentum/                # Cross-sectional 12-1 momentum (long top 20%, short bottom 20%)
│   └── combiner.py              # Multi-strategy portfolio with optimal weighting
│
├── features/                     # Feature engineering pipeline (~433 lines)
│   ├── technical/
│   │   ├── indicators.py        # RSI, MACD, Bollinger, ATR, OBV from scratch (273 lines)
│   │   ├── zscore.py            # Rolling z-score with configurable window
│   │   ├── momentum.py          # Cross-sectional momentum ranking
│   │   └── spread.py            # Pairs spread computation
│   └── store.py                 # DuckDB-backed feature store
│
├── models/                       # ML signal generation pipeline (~802 lines)
│   ├── training/
│   │   ├── labeling.py          # Triple barrier labeling, meta-labeling (260 lines)
│   │   ├── cross_validation.py  # Purged K-fold CV for financial data (260 lines)
│   │   └── feature_importance.py # MDI, MDA, SFI importance metrics
│   └── inference/
│       └── signal_generator.py  # Walk-forward ML signal generation (282 lines)
│
├── backtest/                     # Backtesting and validation (~860 lines)
│   ├── engine/
│   │   └── vectorized.py        # Polars-native vectorized backtester (430 lines)
│   ├── validation.py            # Deflated Sharpe, Bonferroni/BH, CPCV, permutation tests (430 lines)
│   ├── execution_model.py       # Almgren-Chriss market impact modeling
│   └── reports/tearsheet.py     # Equity curve, drawdown, monthly heatmap
│
├── risk/                         # Risk management (~891 lines)
│   ├── manager.py               # Position limits, exposure caps, VaR constraints
│   ├── position_sizing/engine.py # Kelly, risk parity, inverse vol, vol targeting
│   ├── var/monte_carlo.py       # Monte Carlo VaR/CVaR, Cholesky-correlated paths
│   └── monitoring/circuit_breaker.py  # Drawdown monitor, configurable triggers
│
├── portfolio/                    # Portfolio optimization (~671 lines)
│   └── optimization/optimizer.py # Markowitz, HRP, Black-Litterman, efficient frontier
│
├── research/                     # NLP and document research (~841 lines)
│   └── nlp/
│       ├── sentiment.py         # Loughran-McDonald sentiment analysis (331 lines)
│       ├── document_processor.py # SEC filing chunking, section extraction (260 lines)
│       ├── rag_pipeline.py      # LanceDB vector store + RAG queries (250 lines)
│   └── reports/generator.py     # Automated HTML research reports (300 lines)
│
├── execution/                    # Order execution (~543 lines)
│   └── algorithms/
│       ├── vwap_twap.py         # VWAP/TWAP order scheduling
│       └── paper_trader.py      # Simulated paper trading engine
│
├── agents/                       # Multi-agent system (~1,680 lines)
│   ├── specialists/
│   │   ├── __init__.py          # AgentFinding dataclass
│   │   ├── the_quant.py         # Statistical edge-finder (~200 lines)
│   │   ├── the_technician.py    # Technical indicator analyst (~120 lines)
│   │   ├── the_contrarian.py    # Crowding + vol anomaly detector (~120 lines)
│   │   ├── the_sentiment_analyst.py  # NLP earnings call analyst (~120 lines)
│   │   ├── the_fundamentalist.py     # SEC filing + DCF analyst (~180 lines)
│   │   ├── the_macro_strategist.py   # FRED macro + regime analyst (~120 lines)
│   │   ├── risk_manager_agent.py     # Portfolio risk evaluator (veto) (~120 lines)
│   │   ├── portfolio_architect_agent.py  # HRP/BL optimizer (~100 lines)
│   │   └── research_director.py      # Orchestrator + morning brief (~300 lines)
│   ├── chat.py                  # Research chat handler (~200 lines)
│   └── scheduler.py             # DailyCycle + WeeklyCycle scheduler (~150 lines)
│
├── api/                          # FastAPI backend (~481 lines)
│   ├── server.py                # Main app + core routes
│   ├── agent_routes.py          # Agent run/approve/status endpoints
│   ├── chat_routes.py           # Chat endpoint
│   ├── cycle_routes.py          # Daily/weekly cycle endpoints
│   ├── events.py                # WebSocket event manager
│   └── mcp_server.py            # MCP server (7 tools, STDIO)
│
├── core/                         # Shared infrastructure (~696 lines)
│   ├── llm.py                   # LiteLLM multi-model routing + aliases
│   ├── orchestrator.py          # ResearchOrchestrator (strategy runner)
│   ├── serialization.py         # Polars ↔ JSON serialization
│   └── adapters.py              # CSV/dict → Polars adapters
│
├── data/                         # Data layer (~500 lines)
│   └── fetchers/
│       ├── market.py            # YFinance OHLCV fetcher
│       ├── fred.py              # FRED macro data fetcher
│       └── edgar.py             # SEC EDGAR XBRL + filing fetcher
│
├── dashboard/                    # Next.js 15 frontend (6,787 lines)
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Monitor (morning brief + thought stream)
│       │   ├── chat/page.tsx    # Research chat
│       │   ├── signals/page.tsx # Signal board with decay aging
│       │   ├── performance/page.tsx  # Equity curve + agent accuracy
│       │   ├── agents/page.tsx  # Agent timeline + 3D visualizations
│       │   └── settings/page.tsx # Config + model selector
│       ├── components/
│       │   ├── morning-brief/   # Morning brief card components
│       │   ├── thought-stream/  # Real-time thought feed (WebSocket)
│       │   ├── charts/          # Recharts financial charts
│       │   └── 3d/             # Three.js vol surface + correlation heatmap
│       ├── lib/api.ts           # API client hooks (@tanstack/react-query)
│       ├── lib/store.ts         # Zustand state management
│       └── hooks/useWebSocket.ts  # WebSocket subscription hook
│
├── tests/                        # 808 passing tests
├── docs/
│   ├── prompts/                 # All 9 agent prompt specifications
│   ├── 12-refined-vision.md     # The Living Lab vision document
│   └── 13-living-lab-roadmap.md # Detailed build roadmap
├── scripts/prefetch_demo_data.py
├── .env.example                 # All environment variables documented
├── CLAUDE.md                    # Project context for AI-assisted development
└── pyproject.toml               # Python dependencies + build config
```

### Line Count Summary

| Layer | Lines |
|---|---|
| Analytics (`analytics/`) | 1,778 |
| Strategies (`strategies/`) | 688 |
| Features (`features/`) | 433 |
| ML Pipeline (`models/`) | 802 |
| Backtesting (`backtest/`) | 860 |
| Risk (`risk/`) | 891 |
| Portfolio (`portfolio/`) | 671 |
| Research/NLP (`research/`) | 841 |
| Execution (`execution/`) | 543 |
| Agents (`agents/`) | ~1,680 |
| API (`api/`) | 481 |
| Core (`core/`) | 696 |
| Data (`data/`) | ~500 |
| **Python total** | **28,230** |
| Dashboard (`dashboard/src/`) | 6,787 |
| **Grand total** | **35,017** |

---

## Testing

### Running Tests

```bash
# All 808 tests
PYTHONPATH=. pytest tests/

# Verbose output
PYTHONPATH=. pytest tests/ -v

# With HTML coverage report
PYTHONPATH=. pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html

# Specific module
PYTHONPATH=. pytest tests/test_specialist_agents.py -v

# Single test
PYTHONPATH=. pytest tests/test_analytics_returns.py::test_sharpe_ratio -v
```

### Test Categories

| Category | What They Test |
|---|---|
| Analytics (`test_analytics_*.py`) | Sharpe/Sortino/VaR computation, IC curves, factor models |
| Strategies (`test_strategies_*.py`) | Signal generation, no look-ahead bias verification |
| Backtesting (`test_backtest_*.py`) | Vectorized engine, deflated Sharpe, execution costs |
| Risk (`test_risk_*.py`) | Kelly sizing, Monte Carlo VaR, circuit breakers |
| Agents (`test_specialist_agents.py`) | All 9 agent signals, AgentFinding structure |
| API (`test_api_*.py`) | Endpoint response structure, error handling |
| Integration (`test_integration_*.py`) | Full pipeline: data → signals → backtest → finding |

### Example Output

```
$ PYTHONPATH=. pytest tests/test_specialist_agents.py -v

tests/test_specialist_agents.py::test_quant_bullish_signal PASSED        [  8%]
tests/test_specialist_agents.py::test_quant_neutral_when_zscore_low PASSED   [ 16%]
tests/test_specialist_agents.py::test_quant_confidence_formula PASSED   [ 25%]
tests/test_specialist_agents.py::test_technician_rsi_oversold PASSED    [ 33%]
tests/test_specialist_agents.py::test_contrarian_crowding_detection PASSED   [ 41%]
tests/test_specialist_agents.py::test_risk_manager_veto_var_breach PASSED    [ 50%]
tests/test_specialist_agents.py::test_research_director_vote_aggregation PASSED  [ 58%]
tests/test_specialist_agents.py::test_agent_finding_structure PASSED    [ 66%]
tests/test_specialist_agents.py::test_thought_stream_population PASSED  [ 75%]
tests/test_specialist_agents.py::test_high_conviction_flag PASSED       [ 83%]
tests/test_specialist_agents.py::test_morning_brief_structure PASSED    [ 91%]
tests/test_specialist_agents.py::test_approval_queue_logic PASSED       [100%]

12 passed in 4.31s
```

### Key Testing Invariants

**No look-ahead bias:** Every strategy test verifies signals at time `t` only use data through `t-1`. The suite constructs synthetic price series with known properties and confirms signal generation cannot "see the future."

**Deflated Sharpe null hypothesis:** Tests verify that random signals fail the deflated Sharpe test (p > 0.05) while real strategies pass it. This validates the statistical filter is working correctly.

**Purged CV fold structure:** ML cross-validation tests verify the embargo gap between train and test sets is correctly enforced, preventing information leakage across fold boundaries.

---

## The Prompt System

### The Compute-First Architecture

```
Step 1: Pure computation (no LLM)
        Agent calls analytics engine → metrics DataFrame

Step 2: Structure the context
        Format metrics as structured JSON context block

Step 3: LLM synthesis (optional)
        System prompt (persona + rules) + computed context → LLM → insight text

Step 4: Return AgentFinding
        signal   (from computation — always deterministic)
        confidence (from computation — always deterministic)
        reasoning  (LLM synthesis or rule-based string)
        thoughts   (all steps, broadcast as WebSocket events)
```

`signal` and `confidence` always come from computation. The LLM only synthesizes natural-language reasoning. If the LLM is unavailable, the agent still produces a correct signal — it returns a formulaic reasoning string instead of a synthesized one.

### Complete Example: The Quant's Prompt Flow

```python
# Step 1: Compute (no LLM)
zscore    = ZScoreFeature(window=20).compute(prices).get_latest()
win_rate  = VectorizedBacktestEngine().run(signals, prices).win_rate
half_life = SignalDecayAnalyzer(max_horizon=30).compute_ic_half_life(ic_curve)
p_value   = BacktestValidator().deflated_sharpe_ratio(returns, n_trials=10).pvalue

# Step 2: Decide (no LLM)
if zscore < -2.0 and win_rate > 55.0:
    signal = "bullish"
    confidence = min(win_rate / 100, abs(zscore) / 4, 1.0)
else:
    signal = "neutral"
    confidence = 0.0

# Step 3: Synthesize (optional LLM)
context = {"ticker": "NVDA", "zscore": -2.1, "win_rate": 62.0, "n": 47, "half_life": 12.3, "p": 0.031}
if llm_enabled:
    # System prompt: "You are a senior quantitative researcher..."
    reasoning = llm_call(QUANT_SYSTEM_PROMPT, context=context, model=model)
else:
    reasoning = f"Z-score {zscore:.2f} with {win_rate:.0f}% win rate ({n} instances) — mean reversion buy."

# Step 4: Return
return AgentFinding(agent_name="the_quant", ticker="NVDA",
                    signal=signal, confidence=confidence,
                    reasoning=reasoning, details=context, thoughts=thoughts)
```

### The Quant's System Prompt (Excerpt)

```
You are a senior quantitative researcher at a systematic trading firm. Your mandate is to
identify statistically validated trading edges using rigorous quantitative methods.
You think in z-scores, p-values, and information coefficients -- never in narratives or sentiment.

Your analytical framework:
1. STATISTICAL ANOMALY DETECTION: Compute rolling z-scores. Signal when |z| >= 2.0.
2. HISTORICAL VALIDATION: Only trust signals where win rate > 55% across n >= 10 instances.
3. SIGNAL DECAY ANALYSIS: Signals with half-lives of 10-30 days are actionable.
4. OVERFITTING GUARD: Apply deflated Sharpe ratio. p < 0.05 confirms real edge.
5. MOMENTUM CROSS-CHECK: Momentum-z divergence increases conviction.

You must be skeptical by default. Most apparent patterns are noise.
```

### Customizing Agent Prompts

1. Read the specification in `docs/prompts/<agent_name>.md`
2. Edit the `SYSTEM_PROMPT` constant in `agents/specialists/<agent_name>.py`
3. All prompts are multi-model compatible (Claude, GPT-4o, Gemini, Llama)

All prompts use structured JSON output format — no provider-specific conventions.

---

## Technical Deep Dives

<details>
<summary><strong>Signal Decay: What It Is and Why It Matters</strong></summary>

### The Problem

Most strategy research reports a Sharpe ratio computed over the entire backtest period. This hides a critical question: does the signal predict well at 5 days? At 20? A signal that predicts well at 2 days but not at 20 requires fundamentally different position management than one that predicts steadily across horizons.

### The Information Coefficient Curve

The IC (Information Coefficient) measures rank correlation between a signal and subsequent returns at each forward horizon:

```
IC(h) = rank_correlation(signal_t, return_{t,t+h})  for h in 1..N
```

A well-behaved mean-reversion signal looks like:

```
IC
0.15 │    *
     │  *   *
0.10 │*       *
     │           *
0.05 │                *   *
     │                          *   *   *
0.00 │─────────────────────────────────────
     0    5    10    15    20    25    30  days
```

### Half-Life Computation

The half-life is the horizon at which IC decays to 50% of its peak value. The platform monitors all live signals against their half-life — a signal card turns red when approaching expiry. This is the exit trigger for systematic positions, not arbitrary time stops.

### Why Standard Research Ignores This

Academic backtests report a single Sharpe ratio. This hides signal decay entirely. A signal with a 12-day half-life held for 30 days produces mediocre returns not because the strategy is wrong, but because you are holding past the signal's useful life.

</details>

<details>
<summary><strong>Deflated Sharpe Ratio: Why Most Backtests Lie</strong></summary>

### The Multiple Testing Problem

If you test 100 strategy parameter combinations and report the one with the best Sharpe ratio, you are almost certainly reporting noise. The probability of finding a Sharpe ratio of 1.0 by chance across 100 trials on random data is not negligible.

Bailey & López de Prado (2014) quantify this with the Deflated Sharpe Ratio: an adjusted Sharpe that accounts for the number of trials performed, the sample size, and the skewness and kurtosis of returns (which conventional t-tests ignore).

### The Formula

```
DSR = SR * sqrt(T - 1) * (1 - gamma_3 * SR + ((gamma_4 - 1)/4) * SR^2)^(-0.5)
```

Where `T` is sample size, `gamma_3` is return skewness, `gamma_4` is excess kurtosis. The p-value is computed with Bonferroni correction for `N` trials: `p_bonferroni = p_raw * N`.

A signal is genuinely significant only when `p_bonferroni < 0.05`.

### In Practice

The Quant applies the deflated Sharpe with `N=10` trials. For NVDA with raw Sharpe 0.87, deflated Sharpe is 0.58 with p=0.031 — significant. For weaker signals that appeared to work over one backtest window, the deflated p-value often exceeds 0.20, correctly filtering them out. This is why The Quant's signals are rare.

</details>

<details>
<summary><strong>Purged Cross-Validation: Why Standard K-Fold Fails in Finance</strong></summary>

### The Leakage Problem

Standard K-fold cross-validation splits data randomly. For financial time series, this creates two leakage forms:

1. **Look-ahead leakage**: A test sample at time `t` may have adjacent training samples at time `t+1` that "know" the future.
2. **Overlap leakage**: Labels derived from overlapping return windows (e.g., a 20-day return label at `t=1` and `t=2`) carry correlated information across fold boundaries.

Both make the model appear to perform better in CV than it will live.

### The Solution

López de Prado's Purged K-Fold:
1. **Purge**: Remove training samples whose label window overlaps with any test sample's feature window.
2. **Embargo**: Exclude training samples within `k` days of the test boundary.

```
Standard:  TRAIN │ TEST │ TRAIN │ TEST
Purged:    TRAIN │ [gap] │ TEST │ [gap] │ TRAIN
                   ^ purged        ^ purged
```

Every ML signal in the platform uses purged K-fold. Standard K-fold is intentionally unavailable.

</details>

<details>
<summary><strong>Triple Barrier Labeling: The Right Way to Label Financial ML</strong></summary>

### The Problem with Simple Labels

The naive ML labeling approach: "did price go up or down over the next N days?" This has two problems:
1. Fixed horizon ignores stop-losses and take-profits (how the position actually exits)
2. The label does not reflect the trading outcome

### Triple Barrier Labels

López de Prado's method labels each observation based on which barrier is hit first:

```
                    Upper barrier (+profit_target%)
                    ─────────────────────────────
Start ●───────────────────── price path ─────────
                    ─────────────────────────────
                    Lower barrier (-stop_loss%)
                              │
                    Time barrier (max_holding days)
```

- Upper barrier first: label = +1 (profitable long)
- Lower barrier first: label = -1 (stopped out)
- Time barrier first: label = sign of return at expiry

### Meta-Labeling

The platform also implements meta-labeling: a secondary model predicts whether the primary signal (e.g., The Quant's z-score rule) will be profitable given that it fired. This increases precision by filtering false positives without reducing recall on the primary strategy.

</details>

---

## Comparison with Alternatives

| Dimension | Agentic Alpha Lab | Virat's ai-hedge-fund | QuantConnect | Bloomberg Terminal | ChatGPT |
|---|---|---|---|---|---|
| Primary use case | Alpha discovery + validation | Portfolio discussion | Strategy backtesting | Data access | General Q&A |
| Continuous operation | Daily/weekly cycles | None | Strategy-triggered | None | None |
| Signal validation | Deflated Sharpe, purged CV | None | Configurable | None | None |
| Signal decay | IC curves, half-life | None | None | None | None |
| Agent thought stream | Real-time WebSocket | None | N/A | N/A | N/A |
| Human approval gate | First-class UI | None | N/A | N/A | N/A |
| RAG over filings | LanceDB over 10-K/10-Q | None | None | Yes (paid) | No |
| Portfolio optimization | HRP, Black-Litterman, risk parity | None | Full framework | None | None |
| Risk management | Kelly, Monte Carlo VaR, circuit breakers | Basic limits | Full framework | None | None |
| Data cost | Free | Paid API | Varies | $24K/year | None |
| Self-hosted | Yes | Yes | Partial | No | No |
| Open source | Yes | Yes | Partial | No | No |

### Against QuantConnect

QuantConnect has a more mature backtesting framework and live trading connectivity. It does not reason about why signals work, detect when they stop working, or synthesize cross-domain findings. It requires you to write the strategy. The Agentic Alpha Lab helps you discover it.

### Against Bloomberg Terminal

Bloomberg gives you every data point you could want. It does not interpret the data, generate hypotheses, validate them statistically, or write you a morning brief. It costs $24,000 per year per seat.

### Against ChatGPT with Finance Prompts

ChatGPT can discuss NVDA intelligently. It cannot tell you whether "RSI=28 AND z-score=-2.1" has historically predicted a profitable reversal, because it cannot run the backtest. Every factual claim in this platform is traceable to a computation. No claim in a ChatGPT response is.

---

## Roadmap

### What Is Built (Weeks 1-13)

| Phase | Key Modules | Status |
|---|---|---|
| Data + Analytics | `analytics/`, `features/`, `data/fetchers/` | Complete |
| Strategies | Mean reversion, momentum, pairs | Complete |
| Risk + Portfolio | Kelly, VaR, HRP, Black-Litterman | Complete |
| ML Pipeline | Triple barrier labeling, purged CV, LightGBM | Complete |
| Options + Microstructure | Black-Scholes, Greeks, VWAP, Amihud | Complete |
| Research/NLP | Loughran-McDonald, EDGAR RAG | Complete |
| Backtesting + Validation | Deflated Sharpe, CPCV, execution model | Complete |
| 9 Specialist Agents | All specialists + Research Director | Complete |
| Research Chat | Grounded chat with citations | Complete |
| Daily/Weekly Cycles | Background scheduler | Complete |
| Dashboard (6 pages) | Morning brief, chat, signals, performance | Complete |
| MCP Server | 7 tools via STDIO | Complete |

### What Comes Next

**Live Trading**
- Alpaca broker connection for real (small) live trades
- IBKR integration for options execution
- Execution quality analytics: VWAP slippage measurement

**Advanced ML**
- LightGBM + XGBoost ensemble on triple-barrier labels
- Feature importance monitoring (MDI, MDA, SFI)
- Signal combination via stacking

**Regime-Adaptive Weights**
- Hidden Markov Model regime detection
- Automatic strategy weight adjustment by detected regime
- Walk-forward regime labeling

**Multi-Asset**
- Fixed income (yield curve trading, duration strategies)
- Commodities (mean reversion, seasonal patterns)

### Contributing

Contributions are welcome. The codebase conventions:
- Python 3.12+, type hints everywhere, Polars for DataFrames
- Every new module requires a corresponding test file
- No look-ahead bias in any feature or signal computation
- Purged cross-validation for any ML model
- Run `PYTHONPATH=. pytest tests/` before opening a PR

For larger changes, open an issue first to discuss the approach.

---

## Credits and Built With

### Built With Claude Code

This entire platform — 35,017 lines across 188 files — was built using [Claude Code](https://claude.ai/claude-code), Anthropic's agentic CLI coding tool. The development followed a 13-week roadmap accelerated by AI-assisted development:

- Weeks 1-4: Data pipeline, analytics engine, strategies, risk management, factor models
- Weeks 5-8: ML pipeline, signal decay, NLP/RAG, backtest validation
- Weeks 9-11: Options pricing, microstructure, portfolio optimization
- Weeks 12-13: Agent-native architecture, 9 specialist agents, dashboard

The project itself is a demonstration of the thesis it argues: that AI-assisted development, with a human providing direction and judgment, produces better systems faster than either working alone.

### Key Libraries

| Library | Role |
|---|---|
| **Polars** | Primary DataFrame library — 5-10x faster than Pandas for vectorized operations |
| **DuckDB** | Analytical SQL over Parquet files — replaces a database server for local analytics |
| **LanceDB** | Embedded vector database for RAG over SEC filings — no server required |
| **FastAPI** | Async API server with WebSocket support for real-time thought streaming |
| **LiteLLM** | Unified LLM routing across 100+ providers via a single interface |
| **LangGraph** | Multi-agent orchestration DAG for the 9-agent pipeline |
| **Next.js 15** | React framework with app router and server components |
| **Three.js + R3F** | 3D volatility surface and correlation heatmap |
| **Recharts** | 2D financial charts and equity curves |
| **Zustand** | Client-side state management |
| **Framer Motion** | UI animations |
| **Geist** | Font — Sans + Mono |

### Intellectual Acknowledgments

- **Marcos López de Prado** — Triple barrier labeling, deflated Sharpe ratio, purged cross-validation (*Advances in Financial Machine Learning*, 2018)
- **Ernie Chan** — Mean reversion strategies, Ornstein-Uhlenbeck process in trading (*Algorithmic Trading*, 2013)
- **Bailey, Borwein, de Prado, Zhu** — The deflated Sharpe ratio (*Journal of Portfolio Management*, 2014)
- **Grinold & Kahn** — Information coefficient and the fundamental law of active management (*Active Portfolio Management*, 1999)
- **Almgren & Chriss** — Optimal execution of portfolio transactions (*Journal of Risk*, 2000)
- **Loughran & McDonald** — When is a liability not a liability? Textual analysis, dictionaries, and 10-Ks (*Journal of Finance*, 2011)
- **Virat Singh** — For the [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) project that demonstrated the power of agentic financial research and inspired this platform to go further

---

## License

MIT — use it, fork it, build on it.

---

## Disclaimer

This project is for **educational and research purposes only**. It is not intended for real trading or investment decisions. The authors are not responsible for any financial losses incurred from using this software.

Past performance of any strategy, signal, or backtest does not guarantee future results. Statistical significance (p < 0.05) in historical testing does not eliminate the risk of loss in live trading. All signals should be treated as research starting points, not trading recommendations.

Signal win rates, Sharpe ratios, and other metrics cited in this README are computed from historical backtests on the platform's analytics engine and are provided for illustrative purposes only.
