# Demo Script: Building with Claude Code in Fintech

**Event**: Singapore Claude Code + Fintech Meetup
**Duration**: 15-20 minutes
**Date**: April 2026

---

## Setup (Before Demo)

```bash
# Terminal 1 -- Backend (start 10 min before)
cd quant-researcher
conda activate zucol
PYTHONPATH=. uvicorn api.server:app --host 0.0.0.0 --port 8100 --reload

# Terminal 2 -- Dashboard
cd dashboard
npm install && npm run dev
```

**Pre-flight checklist**:
- Verify http://localhost:3000 loads
- Browser open to Monitor page
- At least one LLM API key configured in Settings
- Run a quick analysis on D05.SI to warm the cache

---

## Demo Flow

### Act 1: The Morning Brief (3 min)

**Navigate to**: Monitor page

> "This is what your morning looks like as a quant researcher. Six agents ran overnight, analyzed stocks across SGX, NSE, and NYSE, and produced this brief."

**Point out on screen**:
- D05.SI (DBS) -- LONG, 84% confidence
- RELIANCE.NS -- LONG, 78% confidence
- The Thought Stream on the right -- each agent's reasoning appearing in real-time

**Key talking point**:

> "Six agents analyzed this stock. The Quant computed z-scores and mean reversion half-life. The Technician checked RSI and MACD. The Macro Strategist pulled live VIX data. The Sentiment Analyst scored earnings call transcripts. Then they synthesized into one view with a confidence score. Every number is computed from real data -- the LLM only synthesizes, it never fabricates."

---

### Act 2: Deep Dive via Chat (4 min)

**Action**: Click "Dig Deeper" on D05.SI -- auto-navigates to Chat page

Or type: "Analyze D05.SI for mean reversion"

**Show on screen**:
- Agent traces appearing one by one
- Quant agent: z-score calculation, half-life estimate
- Technician agent: RSI value, MACD crossover status
- Macro agent: VIX at 19.2 (live data), yield curve state

**Key talking point**:

> "Every number you see here is computed, not hallucinated. The z-score comes from a real statistical calculation on real price data. The RSI is computed from 14 days of closing prices. The LLM synthesizes these findings into a narrative -- but the math happens first. That is what compute-first, LLM-second means."

---

### Act 3: Run a Live Backtest (3 min)

**Navigate to**: Backtest page

**Enter**:
- Ticker: D05.SI
- Strategy: Mean Reversion
- Start: 2024-01-01
- End: 2026-04-11

**Click**: Run Backtest

**Show on screen**:
- Equity curve building in real-time
- Drawdown chart
- Monthly returns heatmap
- Key metrics: Sharpe ratio, max drawdown, win rate

**Key talking point**:

> "This is running against real YFinance data. Real transaction costs are included. No look-ahead bias -- the strategy only sees data available at each point in time. This is the difference between a research toy and a research tool."

---

### Act 4: The Settings Story (3 min)

**Navigate to**: Settings page

**Show each section**:

1. **API Keys** -- "Users bring their own keys. OpenAI, Anthropic, Gemini, Groq, DeepSeek. Your keys, your data, your costs."

2. **Model Selector** -- "Choose your LLM. GPT-5-mini for speed, Claude for reasoning, Gemini for long context, Llama for local inference. Switch models without changing code."

3. **Agent System Prompts** -- "Each agent has a customizable system prompt. Want the Contrarian to be more aggressive? Edit the prompt. Want the Fundamentalist to weight DCF higher? Change it here."

**Key talking point**:

> "Open source, bring your own LLM, own your data. No vendor lock-in. No data leaving your machine unless you choose to send it to an LLM provider."

---

### Act 5: Performance and Signal Health (2 min)

**Navigate to**: Performance page

**Show on screen**:
- Strategy breakdown by type (mean reversion, momentum, sentiment)
- Agent accuracy over time
- Signal Decay chart

**Key talking point**:

> "Most platforms tell you WHAT to trade. This one tells you WHEN your signal stops working. See this signal decay chart -- it shows you the half-life of each signal type. When the edge disappears, the system tells you. That is how you avoid trading on stale signals."

---

## Key Messages to Land

1. **Claude Code can build production-grade fintech in weeks** -- this entire platform was built with Claude Code as the primary development tool.

2. **Compute-first, LLM-second prevents hallucination in finance** -- every metric is calculated from real data before the LLM synthesizes. No fabricated numbers.

3. **Multi-agent architecture gives diverse perspectives** -- like a real trading desk with specialists who disagree, debate, and converge on a view.

4. **Open source, bring your own keys, own your data** -- no vendor lock-in, no data exfiltration, full transparency.

---

## Q&A Prep

**"Is this production-ready?"**
> Research-grade, yes. Production execution requires regulatory compliance, broker integration, and risk management infrastructure that goes beyond research tooling. The backtesting and signal generation are solid. Execution is a different problem.

**"How do you prevent look-ahead bias?"**
> Purged cross-validation for any ML model -- no standard k-fold. Feature computation uses only data available at each timestamp. The backtest engine enforces this at the framework level.

**"Why not just use ChatGPT?"**
> ChatGPT cannot compute z-scores, run backtests, or track signal decay. It can talk about these concepts, but it cannot do the math. This platform does the math first, then uses the LLM to synthesize findings into actionable research. The LLM is the narrator, not the analyst.

**"What exchanges do you support?"**
> Any ticker YFinance supports -- SGX, NSE, NYSE, NASDAQ, LSE, HKEX, TSE, and more. No API key required for market data.

**"How many agents? Can I add more?"**
> Six specialist agents today. The architecture is modular -- each agent implements an ABC interface. Adding a new agent means implementing the interface and registering it. The system prompt is editable from the Settings page.

**"What models work best?"**
> GPT-5-mini gives the best speed-to-quality ratio for agent reasoning. Claude is strongest for long-form synthesis. For local/private deployment, Llama via Groq or Ollama works well. The LiteLLM abstraction means you can switch without code changes.
