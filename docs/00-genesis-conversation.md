# Genesis Conversation — 2026-04-07

## Context

Initial planning session for the quant-researcher project at Kuzushi Labs. This document captures the strategic thinking, decisions, and reasoning from the founding conversation.

---

## 1. Career Thesis

**Observation**: The sectors paying the highest compensation are:
- **AI + Finance/Quant Research** — $500K-$1.5M+ TC
- **AI + Marketing/AdTech/GTM** — $300K-$765K+ TC

**Why these two**: Both have direct, measurable revenue leverage where small AI improvements × massive scale = outsized returns. They share:
- Tight feedback loops (you know if your model made money)
- Massive scale (small edges × huge volume)
- Quantifiable impact (P&L attribution)

**Other high-paying AI sectors** (not to be underweighted):
- AI infra / foundation models (OpenAI, Anthropic, xAI)
- Big Tech core ML (recommendation, search ranking)
- Biotech/pharma AI (drug discovery — lumpier liquidity events)
- Autonomous vehicles / robotics (equity-heavy)

**Core insight**: Highest-paying roles sit where **AI skill × domain-specific capital efficiency** is maximized.

---

## 2. Goal

**Target**: Head of AI in Quant Research within 1 quarter (by ~July 2026)

**Strategy**: Use Claude Code as a force multiplier to simultaneously:
1. Build production-grade quant research infrastructure
2. Accelerate domain expertise acquisition through building
3. Build tools for both quant AND adtech/GTM tracks in parallel

**Philosophy**: Build first, learn theory to explain why it broke.

---

## 3. Learning Path — First Principles Analysis

### What a Quant Researcher Does
Find statistical edges in financial markets, express them as mathematical models, validate them rigorously.

### Skill Stack (Priority Order)

1. **Probability & Statistics** — Foundation. Most quant interviews test stats, not options pricing.
   - "All of Statistics" — Larry Wasserman
   - "Statistical Consequences of Fat Tails" — Nassim Taleb
   - MIT 18.650 (YouTube)

2. **Linear Algebra + Calculus** — Fluent, not theoretical.
   - 3Blue1Brown "Essence of Linear Algebra"
   - Gilbert Strang MIT 18.06

3. **Programming (Python + some C++)** — Already strong, focus on:
   - NumPy/Pandas at deep level
   - Vectorized thinking
   - Proper backtesting (avoid look-ahead bias, survivorship bias)

4. **Finance** — Where Hull fits:
   - John C. Hull is a *reference book*, not a learning path
   - Start with Ernie Chan "Quantitative Trading" (gets you building immediately)
   - Use Hull when you hit derivatives (Week 9+)

### Book Priority

**Tier 1 — Read First:**
1. "Quantitative Trading" — Ernie Chan
2. "Advances in Financial ML" — Marcos López de Prado
3. "Active Portfolio Management" — Grinold & Kahn

**Tier 2 — Reference:**
4. "Options, Futures, and Other Derivatives" — John C. Hull
5. "Trading and Exchanges" — Larry Harris
6. "Volatility Trading" — Euan Sinclair

**Tier 3 — Deep Expertise:**
7. "Stochastic Calculus for Finance" — Shreve
8. "Statistical Consequences of Fat Tails" — Taleb
9. "Machine Learning for Asset Managers" — López de Prado
10. "Evidence-Based Technical Analysis" — Aronson

### Types of Quant (affects prioritization)
- **Stat arb / systematic equities** → Stats, ML, backtesting, López de Prado
- **Derivatives / vol trading** → Hull, Shreve, stochastic calc
- **HFT / market making** → Microstructure, C++/low-latency, order book dynamics
- **Macro / discretionary quant** → Economics, regime models, Bayesian methods

### YouTube / Free Resources
- QuantConnect / QuantPedia — strategy ideas + frameworks
- Stanford CS229 (Andrew Ng) — ML fundamentals
- Quantopian lectures (archived) — practical quant finance in Python
- Patrick Boyle — ex-hedge fund, real quant concepts
- AQR research papers (aqr.com) — free, practitioner-written

---

## 4. Reference Architecture: Virat Singh's AI Hedge Fund

**Who**: Virat Singh (@virattt) — Stanford, ex-Airbnb/Faire
**Repo**: github.com/virattt/ai-hedge-fund — 50,200+ stars, 8,700+ forks

**Architecture**: Multi-agent with 18 agents:
- 12 investor-persona agents (Buffett, Munger, Burry, Druckenmiller, etc.)
- 4 analysis agents (valuation, sentiment, fundamentals, technicals)
- 2 operations agents (risk manager, portfolio manager)

**Stack**: Python + LangGraph + OpenAI/Groq/Anthropic/DeepSeek. React/TS frontend. Docker.

**What it lacks** (our opportunity):
- No RAG over unstructured documents
- No real backtesting
- No statistical validation of signals
- No walk-forward testing

**Our version wins by**: Adding real backtesting, signal validation, RAG over SEC filings/earnings calls, and statistical rigor.

---

## 5. Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| Free/open-source only for data + tools | Maximize accessibility, lower barrier, suitable for open-source project + presentations |
| Modular layered architecture with connectors | Extensibility — swap data sources, strategies, execution targets without changing core |
| Build-first learning approach | Engineering is the existing strength; theory follows naturally when things break |
| Start with Ernie Chan, not Hull | Chan gets you building in week 1; Hull is reference for derivatives (Week 9) |
| Include Virat's AI hedge fund as reference | 50K+ star proof of concept; our version adds the missing rigor |
| Target Singapore Claude Code + Fintech meetup | First public demo opportunity; this project IS fintech |

---

## 6. Is This Fintech?

**Yes, definitively.** This project sits at the intersection of:
- **Financial technology** (market data pipelines, trading infrastructure)
- **AI/ML** (LLM-powered research, ML signal generation)
- **Quantitative finance** (backtesting, risk management, portfolio construction)

Fintech encompasses any technology that improves or automates financial services. An AI-powered quant research platform is textbook fintech — specifically "wealthtech" / "investment technology."

For the Singapore meetup, the Claude Code angle makes it even more compelling: demonstrating how AI-assisted development accelerates fintech prototyping.

---

## 7. Comp Landscape (Reference)

| Level | Base | Total Comp |
|-------|------|------------|
| Entry quant researcher | $190-250K | $300-500K |
| Senior quant researcher | $250-400K | $500K-1M+ |
| Head of AI at fund | $350-470K | $600K-1.5M+ |
| Top earners (PM with track record) | Variable | $1M-3M+ uncapped |

Notable: Point72 poached 29-year-old from Millennium as Head of AI. Five Rings pays $300K base consistently. D.E. Shaw $300K+ base for "members of technical staff."

---

## 8. Target Firms (Singapore / APAC)

Point72, Citadel, Two Sigma, Man AHL, GIC, Temasek, Millennium, D.E. Shaw, Five Rings, Jane Street

---

## 9. The Hybrid Quant Angle

Per Selby Jennings, the "engineering-hybrid quant" is the fastest-growing hire category. Funds want people who can:
1. Build production ML infrastructure
2. Generate and validate alpha signals
3. Work with domain experts to codify their judgment

No PhD required. Need to demonstrate: build a system that generates statistically valid signals from financial data — and ship it.
