"use client";

import { useState, useCallback, useEffect, useRef } from "react";
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

1. **D05.SI (DBS)** is sitting at a z-score of -2.1 on the 20-day mean-reversion signal. RSI hit 28 — firmly oversold. Sentiment flipped positive after Q1 earnings beat. Historical: 62% win rate across 47 similar instances, +2.1% average 5-day return.

2. **RELIANCE.NS** earnings volatility crush is pricing in a 3.8% move, but realized vol over the last 8 reports averaged 5.2%. Our straddle model flags this as a 1.4x edge.

3. **O39.SI (OCBC)** put/call ratio spiked — contrarian signal has a 58% hit rate at these levels.

Bottom line: D05.SI is the highest-conviction play.`,
    citations: ["Quant Engine", "Sentiment Agent", "Technical Agent", "Risk Model"],
    actions: ["Run backtest on D05.SI", "Compare D05.SI with peers", "Add D05.SI to watchlist"],
    agent_traces: [
      "quant_agent: z-score=-2.1, lookback=20d, signal=mean_reversion",
      "technical_agent: RSI=28, MACD crossover forming, support at SGD 55",
      "sentiment_agent: score=+0.19, source=earnings_call, shift=negative_to_positive",
      "risk_agent: position_size=2.1% of portfolio, Kelly sizing SGD 5,800",
    ],
  },
  "why nvda": {
    answer: `**NVDA over AMD comes down to three quantitative edges.**

1. **Signal strength.** NVDA's z-score is -2.1 vs AMD's -0.8. The mean-reversion signal is 2.6x stronger.
2. **Sentiment divergence.** NVDA sentiment flipped positive (+0.19). AMD is still negative (-0.07).
3. **Liquidity edge.** NVDA's average daily volume is 3.2x AMD's. Better fills, lower slippage.

AMD isn't bad — it's just not signaling right now.`,
    citations: ["Quant Engine", "Sentiment Agent", "Execution Model"],
    actions: ["Run backtest on AMD", "Run backtest on NVDA", "Compare NVDA with peers"],
    agent_traces: [
      "quant_agent: NVDA z=-2.1 vs AMD z=-0.8, threshold=-2.0 for high-conviction",
      "sentiment_agent: NVDA=+0.19 (flipped), AMD=-0.07 (still negative)",
    ],
  },
  "how did last week go?": {
    answer: `**Last week's performance: +1.8% portfolio return, 4 of 5 trades profitable.**

1. **D05.SI long** (+2.4%) — entered on oversold RSI + positive earnings sentiment. Closed at target.
2. **TCS.NS short** (+1.1%) — mean-reversion short after z-score hit +2.8. Covered at the 20-day mean.
3. **O39.SI long** (+0.6%) — momentum continuation trade.
4. **RELIANCE.NS long** (-0.8%) — broader market selloff overwhelmed the signal.
5. **INFY.NS long** (+0.5%) — late-week entry. Still open with trailing stop.

**Sharpe for the week: 2.1.** Max drawdown was just -0.8% intraweek.`,
    citations: ["Portfolio Tracker", "Risk Model", "Execution Log"],
    actions: ["Run backtest on D05.SI", "Run backtest on TCS.NS"],
    agent_traces: [
      "portfolio_agent: weekly_return=+1.8%, win_rate=80%, sharpe=2.1",
    ],
  },
  "build me a momentum strategy": {
    answer: `**Here's a momentum strategy framework based on our factor library.**

**Entry rules:**
1. 12-1 month return in the top decile of the universe
2. RSI between 40-70 (not overbought, confirms trend health)
3. Average daily volume > $50M (liquidity filter)

**Exit rules:**
1. Trailing stop at 2x ATR
2. Hard stop at -5% from entry
3. Take profit at +8% or after 20 trading days

**Backtest preview (2022-2025):**
- Annual return: +18.2% | Sharpe: 1.54 | Max drawdown: -14.1% | Win rate: 57%

Want me to run a full backtest with your preferred parameters?`,
    citations: ["Quant Engine", "Factor Library", "Backtest Engine"],
    actions: ["Run backtest on D05.SI", "Run backtest on RELIANCE.NS"],
    agent_traces: [
      "quant_agent: strategy=momentum, universe=SGX+NSE, rebalance=weekly",
      "backtest_agent: sharpe=1.54, max_dd=-14.1%, annual_return=18.2%",
    ],
  },
};

function getDemoResponse(message: string): ChatApiResponse {
  const lower = message.toLowerCase().trim();
  for (const [key, response] of Object.entries(DEMO_RESPONSES)) {
    if (lower.includes(key)) return response;
  }
  return {
    answer: `I'll research that for you. In live mode, I pull real-time data across our quant engine, sentiment pipeline, and technical analysis agents.\n\nTry: "What's interesting today?" or "Build me a momentum strategy"`,
    citations: ["System"],
    actions: [],
    agent_traces: ["system: demo_mode"],
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
  const historyLoaded = useRef(false);

  // Fetch existing chat history from backend on mount
  useEffect(() => {
    if (historyLoaded.current) return;
    historyLoaded.current = true;

    fetch(`${API_URL}/api/chat/history`)
      .then((r) => r.json())
      .then((data) => {
        const history: { role: string; content: string }[] = data.history || [];
        if (history.length > 0) {
          const restored: ChatMessage[] = history.map((h, i) => ({
            id: generateId(),
            role: h.role as "user" | "assistant",
            content: h.content,
            timestamp: new Date(Date.now() - (history.length - i) * 60000).toISOString(),
          }));
          setMessages(restored);
        }
      })
      .catch(() => {
        // Server not available, start fresh
      });
  }, []);

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

      if (!res.ok) throw new Error(`Request failed (${res.status})`);

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

  const clear = useCallback(async () => {
    setMessages([]);
    // Also clear server-side history
    try {
      await fetch(`${API_URL}/api/chat/history`, { method: "DELETE" });
    } catch {
      // Ignore if server unavailable
    }
  }, []);

  return { messages, send, clear, loading };
}
