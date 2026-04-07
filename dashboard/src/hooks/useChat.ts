"use client";

import { useState, useCallback } from "react";
import { API_URL } from "@/lib/utils";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  actions?: string[];
  agent_traces?: string[];
  timestamp: string;
}

interface ChatApiResponse {
  answer: string;
  citations: string[];
  actions: string[];
  agent_traces: string[];
}

const DEMO_RESPONSES: Record<string, ChatApiResponse> = {
  "what's interesting today?": {
    answer: `**Three setups cleared our filters this morning.**

1. **NVDA** is sitting at a z-score of -2.1 on the 20-day mean-reversion signal. RSI hit 28 yesterday — firmly oversold. Sentiment flipped positive (+0.19) after Jensen's GTC comments. Historical: 62% win rate across 47 similar instances, +2.1% average 5-day return.

2. **AAPL** earnings volatility crush is pricing in a 4.2% move, but realized vol over the last 8 reports averaged 5.8%. The options market is underpricing the event. Our straddle model flags this as a 1.4x edge.

3. **SPY** put/call ratio spiked to 1.8 — highest since October. Contrarian signal has a 58% hit rate at these levels. Mean reversion within 3 days is the base case.

Bottom line: NVDA is the highest-conviction play. The signal convergence is rare — we see this pattern maybe 3-4 times a year.`,
    citations: ["Quant Engine", "Sentiment Agent", "Technical Agent", "Risk Model"],
    actions: ["Run Backtest on NVDA", "Approve NVDA Trade", "Compare NVDA vs AMD"],
    agent_traces: [
      "quant_agent: z-score=-2.1, lookback=20d, signal=mean_reversion",
      "technical_agent: RSI=28, MACD bearish crossover 3d ago, support at $118",
      "sentiment_agent: score=+0.19, source=earnings_call+news, shift=negative_to_positive",
      "risk_agent: position_size=2.1% of portfolio, stop_loss=$115.50, risk_reward=2.8:1",
    ],
  },
  "why nvda": {
    answer: `**NVDA over AMD comes down to three quantitative edges.**

1. **Signal strength.** NVDA's z-score is -2.1 vs AMD's -0.8. The mean-reversion signal is 2.6x stronger. In our backtest, entries below -2.0 have a 62% win rate; entries at -0.8 are coin-flip territory at 51%.

2. **Sentiment divergence.** NVDA sentiment flipped positive this week (+0.19). AMD is still negative (-0.07). When we see a sentiment flip coincide with an oversold technical reading, the 5-day forward return averages +2.1% vs +0.4% without the flip.

3. **Liquidity edge.** NVDA's average daily volume is 3.2x AMD's. Tighter spreads mean better fills and lower slippage. Our execution model estimates 0.03% slippage on NVDA vs 0.11% on AMD for a $500K position.

AMD isn't a bad stock — it's just not signaling right now. We're watching for a z-score below -1.5 to reconsider.`,
    citations: ["Quant Engine", "Sentiment Agent", "Execution Model"],
    actions: ["Run Backtest on AMD", "Side-by-Side Comparison", "Set AMD Alert at z=-1.5"],
    agent_traces: [
      "quant_agent: NVDA z=-2.1 vs AMD z=-0.8, threshold=-2.0 for high-conviction",
      "sentiment_agent: NVDA=+0.19 (flipped), AMD=-0.07 (still negative)",
      "execution_agent: NVDA slippage=0.03%, AMD slippage=0.11% at $500K",
    ],
  },
  "how did last week go?": {
    answer: `**Last week's performance: +1.8% portfolio return, 4 of 5 trades profitable.**

1. **MSFT long** (+2.4%) — entered on oversold RSI + positive earnings sentiment. Closed at target on Thursday. Clean execution.

2. **TSLA short** (+1.1%) — mean-reversion short after z-score hit +2.8. Covered at the 20-day mean. Risk/reward played out exactly as modeled.

3. **AMZN long** (+0.6%) — momentum continuation trade. Smaller win, but the signal decay model correctly predicted the move would fade by day 3.

4. **META long** (-0.8%) — the only loss. Entered on a sentiment flip, but the broader tech selloff on Wednesday overwhelmed the signal. Stop hit at -0.8%.

5. **GOOGL long** (+0.5%) — late-week entry on a vol crush setup. Still open, trailing stop in place.

**Sharpe for the week: 2.1.** The risk model kept position sizes disciplined — max drawdown was just -0.8% intraweek.`,
    citations: ["Portfolio Tracker", "Risk Model", "Execution Log"],
    actions: ["View Full Trade Log", "Run Weekly Attribution", "Export Report"],
    agent_traces: [
      "portfolio_agent: weekly_return=+1.8%, win_rate=80%, sharpe=2.1",
      "risk_agent: max_drawdown=-0.8%, largest_position=3.2% of AUM",
    ],
  },
  "build me a momentum strategy": {
    answer: `**Here's a momentum strategy framework based on our factor library.**

The core idea: buy stocks with strong 12-1 month momentum that are also showing **accelerating earnings revisions**. This dual signal filters out momentum traps.

**Entry rules:**
1. 12-1 month return in the top decile of the universe
2. Earnings revision breadth > 0.6 (more upgrades than downgrades)
3. RSI between 40-70 (not overbought, confirms trend health)
4. Average daily volume > $50M (liquidity filter)

**Exit rules:**
1. Trailing stop at 2x ATR (adapts to volatility)
2. Hard stop at -5% from entry
3. Take profit at +8% or after 20 trading days, whichever comes first

**Backtest preview (2020-2024):**
- Annual return: +18.2%
- Sharpe: 1.54
- Max drawdown: -14.1%
- Win rate: 57%
- Profit factor: 1.9x

The strategy underperforms in sharp reversals (Q1 2022 was -6.2% in one month). Adding a regime filter — long only when SPY is above its 200-day MA — improves the Sharpe to 1.72 and cuts max drawdown to -9.8%.

Want me to run a full backtest with your preferred parameters?`,
    citations: ["Quant Engine", "Factor Library", "Backtest Engine"],
    actions: ["Run Full Backtest", "Customize Parameters", "Add Regime Filter"],
    agent_traces: [
      "quant_agent: strategy=momentum+revisions, universe=SP500, rebalance=weekly",
      "backtest_agent: sharpe=1.54, max_dd=-14.1%, annual_return=18.2%",
      "risk_agent: regime_filter improves sharpe from 1.54 to 1.72",
    ],
  },
};

function getDemoResponse(message: string): ChatApiResponse {
  const lower = message.toLowerCase().trim();

  for (const [key, response] of Object.entries(DEMO_RESPONSES)) {
    if (lower.includes(key)) {
      return response;
    }
  }

  return {
    answer: `**I'll research that for you.**

In live mode, I'd pull real-time data across our quant engine, sentiment pipeline, and technical analysis agents to give you a grounded answer.

For now, try one of these to see the full experience:
1. "What's interesting today?" — morning market brief
2. "Why NVDA not AMD?" — comparative analysis
3. "How did last week go?" — performance review
4. "Build me a momentum strategy" — strategy construction`,
    citations: ["System"],
    actions: [],
    agent_traces: ["system: demo_mode, no live data available"],
  };
}

let messageIdCounter = 0;
function generateId(): string {
  messageIdCounter += 1;
  return `msg_${Date.now()}_${messageIdCounter}`;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const send = useCallback(async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed) return;

    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed }),
      });

      if (!res.ok) {
        throw new Error(`Request failed (${res.status})`);
      }

      const data: ChatApiResponse = await res.json();

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: data.answer,
        citations: data.citations,
        actions: data.actions,
        agent_traces: data.agent_traces,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      // Demo mode fallback
      await new Promise((r) => setTimeout(r, 1200));
      const demo = getDemoResponse(trimmed);

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: demo.answer,
        citations: demo.citations,
        actions: demo.actions,
        agent_traces: demo.agent_traces,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, send, clear, loading };
}
