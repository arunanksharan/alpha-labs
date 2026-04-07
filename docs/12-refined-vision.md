# The Agentic Alpha Lab — Refined Vision

## What We Learned From Virat's AI Hedge Fund

Virat built something that 50,000 people starred. Why? Not because it makes money — it doesn't backtest, doesn't validate, doesn't even trade. People starred it because **you can watch 13 famous investors argue about your stock**.

Warren Buffett says "bullish, 85% confidence — strong moat, owner earnings growing, 23% margin of safety." Michael Burry says "bearish, 72% confidence — overvalued relative to book, accounting concerns." Nassim Taleb says "neutral — no asymmetric payoff, position sizing should be minimal."

That's the magic: **structured disagreement between expert perspectives, resolved into a decision**.

What Virat got right:
- Domain-specific personas with genuine analytical frameworks (not generic prompts)
- Each agent does REAL computation (DCF, factor analysis, technicals) before the LLM reasons
- The LLM receives facts, not vibes — "ROE 22%, debt-to-equity 0.3, margin of safety 23%"
- Output is structured: signal + confidence + reasoning

What Virat is missing (our opportunity):
- No backtesting — does Buffett-agent actually outperform? Nobody knows
- No signal decay — does the signal work for 1 day or 1 year?
- No risk management — no position sizing, no portfolio construction
- No learning — agents don't adapt based on whether they were right
- No continuous operation — you run it once, read the output, done
- No RAG — agents reason over API data, not actual SEC filings

---

## Our Vision: Where Virat Ends, We Begin

Virat built the **debate**. We build the **research lab that runs the debate, validates the conclusions, and acts on them**.

### Layer 1: The Quant Research Engine (Already Built — Weeks 1-11)

This is our unfair advantage. 24,000 lines of production-grade:
- Real backtesting with transaction costs, slippage, market impact
- Deflated Sharpe ratio to detect overfitting
- Signal decay measurement (IC curves, half-life)
- Purged cross-validation for financial ML
- Risk management (Kelly, VaR, circuit breakers)
- Options pricing, microstructure analytics
- Portfolio optimization (HRP, Black-Litterman)

Virat has none of this. This is the **quant researcher's heart** — the ability to prove whether an idea actually works.

### Layer 2: The Expert Agent Team (Inspired by Virat, But Deeper)

Like Virat's 13 investor personas, but each agent is backed by our real analytics engine:

**Research Agents (Domain Experts):**

| Agent | Personality | What It Actually Computes |
|-------|-----------|--------------------------|
| **The Quant** | Data-driven, statistical | Runs factor models, computes IC, measures decay. "This signal has 62% win rate over 47 historical instances. Deflated Sharpe is significant at p=0.03." |
| **The Fundamentalist** | Buffett/Munger style | Reads 10-K filings via RAG, computes DCF, owner earnings, margin of safety. "Intrinsic value $187, current price $173, 8% margin of safety." |
| **The Technician** | Chart patterns, momentum | Computes RSI, MACD, Bollinger, momentum factor. "RSI at 28 (oversold), MACD crossover imminent, momentum bottom-decile — classic reversal setup." |
| **The Sentiment Analyst** | NLP-driven, earnings calls | Analyzes management tone, forward guidance, sentiment drift. "CEO confidence up +0.19 in Q&A vs prepared remarks. Bullish divergence." |
| **The Macro Strategist** | Druckenmiller/Dalio style | FRED data, yield curves, regime detection. "We're in a late-cycle regime. Historically, momentum underperforms by 3% in this environment." |
| **The Contrarian** | Burry/Taleb style | Looks for crowded trades, tail risks, vol anomalies. "Everyone is long NVDA. Implied vol is 40% vs 25% realized. The crowd is mispricing risk." |

**Operations Agents:**

| Agent | Role |
|-------|------|
| **The Risk Manager** | Evaluates every proposal against portfolio risk (VaR, exposure limits, correlation). Can veto. |
| **The Portfolio Architect** | Constructs optimal portfolio from approved signals (HRP, risk parity). Manages rebalancing. |
| **The Execution Strategist** | Plans order execution (VWAP, TWAP, optimal horizon). Estimates market impact. |

**Meta Agent:**

| Agent | Role |
|-------|------|
| **The Research Director** | Orchestrates the team. Decides which agents to consult for which tickers. Resolves disagreements. Writes the morning brief. **This is the "confident analyst" voice the user interacts with.** |

### Layer 3: The Living Lab Experience

**This is where Polsia's insight meets quant research.**

#### The Morning Brief

When you open the app:

```
Good morning, Parul.                                    April 8, 2026

I ran the overnight cycle across 50 tickers. Here's what matters:

━━━ TOP CONVICTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NVDA │ LONG │ Confidence: 0.84
The Quant: z-score hit -2.1 (entry zone), 12-day half-life
The Fundamentalist: Revenue +94% YoY, margins expanding
The Sentiment Analyst: Earnings call tone shift +0.19
The Contrarian: No objection — position isn't crowded
→ Historical: 62% win rate, +2.1% avg return over 12 days
→ Kelly sizing: $4,200 (4.2% of portfolio)
                                    [Approve] [Dig Deeper] [Reject]

━━━ WATCHLIST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TSLA │ SHORT signal strengthening │ Confidence: 0.67
  Sentiment deteriorating, momentum weakening. Not yet at entry threshold.

AAPL │ Approaching mean reversion zone │ z = -1.7
  Watching for -2.0. Fundamentals still strong.

MSFT/GOOG │ Pairs spread widening │ z = 1.8
  Approaching entry. Cointegration still holds (p=0.02).

━━━ PORTFOLIO HEALTH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

P&L this week: +1.2% ($1,200)
Sharpe (rolling 30d): 1.43
Signal decay status: All signals within half-life ✓
Risk: VaR -1.8% (limit: 3%) ✓

━━━ WHAT I LEARNED ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Last week's mean reversion signals: 4/6 profitable (+1.8% net)
Last week's momentum signals: 2/5 profitable (-0.3% net)
→ Adjusting: increasing mean reversion weight, reducing momentum

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                    [View Full Dashboard] [Chat]
```

This isn't a dashboard — it's a **research brief** written by an analyst who's been working since midnight.

#### The Thought Stream

Below the morning brief, a living feed of agent activity:

```
16:42:31 │ Research Director │ Starting afternoon scan...
16:42:33 │ The Technician │ Scanning 50 tickers for RSI/MACD signals...
16:42:35 │ The Technician │ Found 3 oversold candidates: NVDA (28), AMD (31), QCOM (33)
16:42:37 │ The Quant │ Computing z-scores for oversold candidates...
16:42:39 │ The Quant │ NVDA z=-2.1 (ENTRY), AMD z=-1.4 (watching), QCOM z=-0.8 (no signal)
16:42:41 │ The Fundamentalist │ Pulling NVDA 10-K... analyzing revenue trends...
16:42:48 │ The Fundamentalist │ NVDA: Revenue +94% YoY, gross margin 72.7%, FCF $15.2B
16:42:50 │ The Sentiment Analyst │ Checking recent NVDA earnings call...
16:42:55 │ The Sentiment Analyst │ Management tone: +0.31 (bullish). "AI infrastructure" mentioned 14x
16:42:57 │ The Contrarian │ Checking if NVDA is crowded...
16:42:59 │ The Contrarian │ Short interest 1.2%, options put/call 0.68 — not crowded
16:43:01 │ Risk Manager │ Evaluating NVDA long: VaR impact +0.3%, within limits
16:43:03 │ Portfolio Architect │ Kelly sizing: 4.2% = $4,200. Optimal via risk parity.
16:43:05 │ Research Director │ NVDA: 5/6 agents bullish. Generating proposal...
16:43:07 │ Research Director │ ⚡ NEW SIGNAL: NVDA LONG, confidence 0.84
         │                  │ Awaiting human approval.
```

You can watch this in real-time. Each line is clickable — expand to see the full computation behind it.

#### The Research Chat

The user can interrupt the stream at any point:

```
You: Why are you more bullish on NVDA than AMD? Both are oversold.

Research Director: Good question. Three key differences:

1. Signal strength: NVDA z=-2.1 (past entry threshold) vs AMD z=-1.4
   (not yet). We need z < -2.0 for mean reversion entry.

2. Fundamental backing: NVDA revenue +94% YoY with expanding margins.
   AMD revenue +2% — the oversold condition might be justified.

3. Historical: When NVDA hits z=-2.0 with positive fundamentals,
   win rate is 62% over 47 instances. AMD in similar conditions:
   only 41% over 23 instances. The edge is weaker.

Bottom line: NVDA is oversold AND fundamentally strong. AMD is just
oversold. I'd wait for AMD to show fundamental improvement before
entering.

Want me to run a pairs analysis on NVDA vs AMD instead?
```

This is NOT generic ChatGPT. Every claim is backed by a computation that ran on our engine. The agent cites z-scores, win rates, and instance counts because it actually computed them.

---

## The Research Cycle — How Discovery Works

### The Agent's Daily Life

```
5:00 AM   Pre-market scan
          │ The Technician: compute RSI, MACD, Bollinger for 50 tickers
          │ The Quant: compute z-scores, momentum ranks, factor exposures
          │ The Macro Strategist: check overnight FRED data, yield curve
          │
6:00 AM   Signal generation
          │ Research Director: which tickers have multiple signals converging?
          │ For each candidate: request analysis from relevant specialists
          │ The Fundamentalist: RAG over latest filings for top candidates
          │ The Sentiment Analyst: check recent earnings/news for top candidates
          │
7:00 AM   Risk evaluation
          │ Risk Manager: compute portfolio-level VaR with proposed positions
          │ Portfolio Architect: optimal sizing via Kelly + risk parity
          │
7:30 AM   Morning Brief generated
          │ Research Director: compile findings, write brief, queue for approval
          │
8:00 AM   Human opens dashboard
          │ → Sees morning brief with proposals
          │ → Approves/rejects/asks questions
          │
9:30 AM   Market open — execution
          │ Execution Strategist: VWAP/TWAP scheduling for approved trades
          │ Paper trading via Alpaca
          │
4:00 PM   Market close — daily review
          │ The Quant: compute daily P&L, update factor exposures
          │ Risk Manager: check drawdown, circuit breakers
          │ Research Director: any signals to exit?
          │
5:00 PM   Post-market
          │ The Fundamentalist: process any new SEC filings
          │ The Sentiment Analyst: process any earnings calls
          │ The Quant: update signal decay metrics
          │
6:00 PM   Weekly review (Fridays only)
          │ Research Director: which strategies worked? which didn't?
          │ The Quant: signal decay analysis, regime detection
          │ Portfolio Architect: rebalancing proposal
          │ "Last week's mean reversion: 4/6 profitable. Momentum: 2/5.
          │  Recommend shifting weight from momentum to mean reversion."
```

### How Alpha Discovery Actually Happens

Most alpha isn't found by scanning — it's found by **connecting dots across domains**:

**Example: The Cross-Domain Signal**

```
The Sentiment Analyst notices: "AAPL management used the word
'cautious' 6 times in the Q3 call, up from 1 time in Q2."

Research Director: "Interesting. Let me check if this correlates
with anything."

The Technician: "AAPL momentum has been weakening — dropped from
top 20% to top 40% over 3 months."

The Quant: "Running backtest: when management language shifts to
'cautious' AND momentum weakens, what happens?
...
Found 12 historical instances. 9/12 times the stock underperformed
by an average of -4.2% over the next 30 days."

Research Director: "That's a 75% hit rate with meaningful magnitude.
Let me check validation."

The Quant: "Deflated Sharpe adjusting for 12 trials: p=0.08.
Borderline significant. Not strong enough for a standalone trade,
but should factor into our AAPL view."

Research Director: "Noted. Downgrading AAPL conviction from bullish
to neutral. Adding a watchlist entry for potential short if z-score
deteriorates further."
```

THIS is what a real quant researcher does. Not one agent in isolation — multiple perspectives synthesized, validated statistically, and translated into a calibrated position.

---

## What Makes This Different From Everything Else

| Platform | What It Does | What It Doesn't Do |
|----------|-------------|-------------------|
| **Virat's ai-hedge-fund** | 13 investors debate a stock | Validate whether they're right |
| **QuantConnect** | Backtest strategies | Think independently |
| **Bloomberg Terminal** | Show you data | Interpret it for you |
| **ChatGPT + finance prompt** | Give opinions | Back them with real computation |
| **Our Agentic Alpha Lab** | **Discover + Validate + Act + Learn** | — |

Our platform is the only one that:
1. Has expert agents who do real computation (not just LLM reasoning)
2. Validates every signal against historical data (deflated Sharpe, IC decay)
3. Runs continuously without being asked (daily/weekly cycles)
4. Learns from outcomes (adjusts weights based on what worked)
5. Speaks with conviction backed by receipts
6. Lets you interrupt and redirect the research at any point

---

## The Soul of the Platform

The quant researcher agent is not a chatbot, not a dashboard, not a backtester. It's a **research partner with three qualities**:

1. **Curiosity** — it actively looks for patterns, anomalies, and cross-domain connections
2. **Rigor** — every claim is backed by statistical validation, not vibes
3. **Conviction** — it has opinions, states them clearly, and can defend them when challenged

The human's role is:
1. **Direction** — "I think tech is overextended" → agent investigates
2. **Judgment** — approve/reject proposals based on context the agent can't see
3. **Challenge** — "Why NVDA and not AMD?" → agent must justify with data

The agent's role is:
1. **Breadth** — scan 50 tickers, read 100 filings, compute 1000 features
2. **Depth** — when something looks interesting, go deep (10-K analysis, backtesting, factor decomposition)
3. **Memory** — "Last time a similar signal fired, it worked 62% of the time"
4. **Honesty** — "This signal is borderline. Deflated Sharpe p=0.08. I'd call it a watchlist item, not a trade."

Together, they form a research team that's **better than either alone**.
