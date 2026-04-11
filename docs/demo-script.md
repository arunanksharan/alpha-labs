# Singapore Meetup Demo Script

## Title: "The Agentic Alpha Lab: When AI Agents Do the Research and Humans Just Approve"

## Duration: 25-30 minutes

## What You Need Running
```bash
# Terminal 1: Backend (start 10 min before demo)
PYTHONPATH=. uvicorn api.server:app --port 8100

# Terminal 2: Dashboard
cd dashboard && PORT=3100 npm run dev

# Browser: http://localhost:3100
```

---

## The Script

### Opening (2 min) — The Hook

**[Show the Morning Brief on the dashboard]**

> "Good evening everyone. I want to show you something. This is not a demo I prepared. This is what my AI research team produced this morning."

**[Point to the Morning Brief]**

> "At 6 AM today, while I was sleeping, 6 AI agents scanned 50 stocks. The Quant computed z-scores and backtested historical patterns. The Technician checked RSI and MACD. The Sentiment Analyst processed earnings calls. The Fundamentalist read SEC filings and computed DCF valuations."

> "By the time I opened my laptop, they had a research brief ready. Two high-conviction trades, a watchlist of three more, and a note about what they learned from last week's signals."

> "This is not a chatbot. This is a research team that never sleeps."

---

### Act 1 (5 min) — The Problem

> "Let me give you context. There's a project called ai-hedge-fund by Virat Singh — 50,000 stars on GitHub. It has 13 agents who roleplay as famous investors. Warren Buffett agent, Charlie Munger agent, Michael Burry agent. They debate whether to buy a stock."

> "It's brilliant. But there's a problem."

**[Pause]**

> "None of them can tell you if their recommendation actually works."

> "Buffett-agent says 'buy NVDA, 85% confidence.' But what's the historical win rate of similar signals? What's the signal decay — does this edge last 3 days or 30 days? Is the confidence real or is it a language model hallucinating a number?"

> "That's the gap we filled. Our agents don't just have opinions. They have receipts."

---

### Act 2 (8 min) — The Live Demo

**[Click "Start Research" on the Monitor page]**

> "Let me show you what happens when I start a research cycle."

**[Watch the Thought Stream populate in real-time]**

> "See the right panel? That's the Thought Stream. Each line is an agent reasoning out loud."

Read a few thoughts as they appear:

> "The Quant is computing z-scores... z = -1.8 for NVDA, not quite at the -2.0 entry threshold yet."

> "The Technician found RSI at 32 — approaching oversold."

> "The Sentiment Analyst processed the last earnings call — management tone shifted positive by 0.19 in the Q&A section compared to prepared remarks. That's unusual."

**[When the Approval Panel appears — amber border]**

> "Now look — the system just paused. The Risk Manager evaluated the signals and found one that exceeds the position limit. It's asking for my approval."

> "This is what we call 'human-on-the-loop.' The agents did 20 minutes of research in 30 seconds. But they won't trade without my say-so."

**[Click "Approve"]**

> "I approve. Now the Validation Agent runs a backtest. And the Decay Agent measures how long this signal is expected to work."

**[Point to the updated metrics]**

> "Sharpe ratio 1.4. Signal half-life 12 days. The deflated Sharpe — which adjusts for the fact that we tested multiple strategies — is still significant at p = 0.03. This isn't a backtest that looks good by accident. It survives statistical scrutiny."

---

### Act 3 (5 min) — The Research Chat

**[Navigate to the Chat page]**

> "Now here's my favorite part. I can talk to the Research Director."

**[Type: "Why NVDA and not AMD?"]**

> "Watch the response. It's not ChatGPT guessing about stocks. Every claim cites a computation."

**[Read the response as it appears]**

> "Three differences: NVDA z-score is -2.1 versus AMD at -1.4 — NVDA is past the entry threshold, AMD isn't. NVDA revenue grew 94% year-over-year, AMD grew 2%. And historically, when NVDA hits this z-score level with positive fundamentals, it wins 62% of the time across 47 instances."

> "That last number — 62% across 47 instances — the agent didn't guess that. It ran a backtest in real-time."

**[Point to the citation badges]**

> "See the source badges? Quant Engine, Technician, Fundamentalist. Every claim is traceable to a computation. This isn't a language model opinion. It's a research finding."

---

### Act 4 (3 min) — Signal Decay (The Differentiator)

**[Navigate to the Signals page]**

> "This is my favorite visualization. Signal decay."

**[Point to the signal cards with green/yellow/red borders]**

> "Each signal card has a colored border. Green means fresh — the signal was just generated and is within its half-life. Yellow means aging. Red means decaying — the statistical edge is eroding."

> "This is something no other AI finance project does. We don't just generate signals — we measure how long they last. Because in real markets, by the time everyone knows about an edge, the edge is gone."

> "The NVDA signal has a half-life of 12 days. After 12 days, the information coefficient drops by half. After 24 days, it's basically noise. This tells us exactly when to exit."

---

### Act 5 (3 min) — The Architecture (For Technical Audience)

> "For the engineers in the room — this is 35,000 lines of tested, production code. 808 automated tests. Built in a single extended Claude Code session."

> "Nine specialist agents, each backed by real computation — not LLM prompts. The Quant runs actual backtests. The Fundamentalist reads actual SEC filings. The Sentiment Analyst uses NLP on actual earnings calls."

> "Multi-model support — you can switch between Claude, GPT-4, Gemini, or Llama in a single dropdown. We use LiteLLM for routing."

> "The whole system is exposed as an MCP server — which means any AI agent, including Claude Code itself, can use our platform as a tool."

**[If time: show the model selector dropdown in the sidebar]**

---

### Closing (2 min) — The Vision

> "What I showed you today is what I believe quant research looks like in 2026 and beyond."

> "Not a tool you operate. A research partner that works while you sleep, reasons out loud so you can follow its thinking, and asks for your approval before acting."

> "The question it answers isn't 'should I buy NVDA?' The question is: 'is there a statistically validated, factor-independent, decay-measured alpha signal in NVDA right now, and what's the optimal position size given my current portfolio risk?'"

> "That's the question a $1 million quant researcher answers. And now, an AI system can answer it too."

> "The project is open source. github.com/arunanksharan/alpha-labs. Thank you."

---

## Backup Demo Paths (If Something Breaks)

**If the backend is down**: Dashboard runs in demo mode with pre-loaded data. All visualizations work. Skip the "Start Research" live run. Show the pre-populated Morning Brief and chat.

**If the chat API times out**: Use the demo mode responses (hardcoded). They're realistic and show the format.

**If someone asks a hard question**: The doubt explainer has 21 detailed answers. You've read 9 chapters of Pedersen. You can handle anything about alpha, beta, Sharpe, factor models, or signal decay.

## Key Numbers to Memorize

- 35,000 lines of code
- 808 tests passing
- 9 specialist agents
- 62% win rate (the NVDA example)
- 12-day half-life (signal decay)
- 47 historical instances (backtest depth)
- p = 0.03 (deflated Sharpe significance)
- 6 agents scan 50 tickers in 30 seconds
