"use client";

import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Play, RefreshCw, Activity, Shield, BarChart3, Zap, ChevronDown, Loader2 } from "lucide-react";
import { cn, API_URL, href } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { MorningBrief } from "@/components/MorningBrief";
import { ThoughtStream } from "@/components/ThoughtStream";
import { EquityCurveChart } from "@/components/EquityCurveChart";
import { SignalDecayChart } from "@/components/SignalDecayChart";
import { SignalCard } from "@/components/SignalCard";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAgents } from "@/hooks/useAgents";
import type { AgentEvent, Signal, BacktestMetrics, EquityCurvePoint, ICCurvePoint } from "@/types";

/* ══════════════════════════════════════════════════════════════════
   DEMO DATA — rich, realistic, shown before live data arrives
   ══════════════════════════════════════════════════════════════════ */

const DEMO_METRICS: BacktestMetrics = {
  strategy_name: "mean_reversion",
  total_return: 0.186,
  annualized_return: 0.124,
  sharpe_ratio: 1.87,
  sortino_ratio: 2.43,
  max_drawdown: -0.067,
  calmar_ratio: 1.85,
  win_rate: 0.58,
  profit_factor: 1.41,
  var_95: -0.0152,
  cvar_95: -0.0219,
};

const DEMO_EQUITY: EquityCurvePoint[] = Array.from({ length: 252 }, (_, i) => ({
  date: new Date(2023, 0, 3 + i).toISOString().split("T")[0],
  equity: 100000 * Math.exp(i * 0.0005 + Math.sin(i / 20) * 0.02),
}));

const DEMO_IC: ICCurvePoint[] = Array.from({ length: 30 }, (_, i) => ({
  horizon: i + 1,
  ic: 0.08 * Math.exp(-i / 12) + (Math.random() - 0.5) * 0.005,
  ic_std: 0.02,
  is_significant: i < 20,
}));

const DEMO_SIGNALS: Signal[] = [
  { ticker: "D05.SI", date: "2026-04-12", direction: 1.0, confidence: 0.82 },
  { ticker: "RELIANCE.NS", date: "2026-04-12", direction: 1.0, confidence: 0.91 },
  { ticker: "O39.SI", date: "2026-04-12", direction: 1.0, confidence: 0.74 },
  { ticker: "TCS.NS", date: "2026-04-12", direction: -1.0, confidence: 0.65 },
  { ticker: "C6L.SI", date: "2026-04-12", direction: 0, confidence: 1.0 },
  { ticker: "INFY.NS", date: "2026-04-12", direction: -1.0, confidence: 0.58 },
];

const DEMO_EVENTS: AgentEvent[] = [
  { agent_name: "research", status: "completed", message: "Fetched 500 days of OHLCV for 6 tickers", data: {}, timestamp: new Date(Date.now() - 300000).toISOString() },
  { agent_name: "research", status: "completed", message: "Computed z-score, momentum, RSI features", data: {}, timestamp: new Date(Date.now() - 240000).toISOString() },
  { agent_name: "research", status: "completed", message: "Generated 6 trading signals", data: {}, timestamp: new Date(Date.now() - 180000).toISOString() },
  { agent_name: "risk", status: "completed", message: "5 approved, 1 rejected (TSLA: exposure limit)", data: {}, timestamp: new Date(Date.now() - 120000).toISOString() },
  { agent_name: "risk", status: "awaiting_approval", message: "Awaiting human approval for 5 signals", data: {}, timestamp: new Date(Date.now() - 60000).toISOString() },
];

/* ── Morning Brief demo data ── */

const DEMO_BRIEF_SIGNALS = [
  {
    ticker: "D05.SI",
    direction: "LONG",
    confidence: 0.84,
    agents: [
      { name: "The Quant", thought: "z=-2.1, 62% win rate, 47 samples" },
      { name: "The Technician", thought: "RSI=28, MACD crossover forming" },
      { name: "Sentiment", thought: "DBS earnings beat, +0.19 tone shift" },
      { name: "Risk", thought: "VaR +0.3%, Kelly sizing SGD 5,800" },
    ],
    historical: { win_rate: 0.62, avg_return: 2.1, hold_days: 12, instances: 47 },
  },
  {
    ticker: "RELIANCE.NS",
    direction: "LONG",
    confidence: 0.78,
    agents: [
      { name: "The Quant", thought: "z=-1.8, mean reversion setup" },
      { name: "The Technician", thought: "Oversold bounce at 200 DMA" },
      { name: "Fundamentalist", thought: "PE ratio compressed, Jio growth intact" },
      { name: "Risk", thought: "VaR +0.2%, Kelly sizing INR 2,40,000" },
    ],
    historical: { win_rate: 0.57, avg_return: 1.6, hold_days: 8, instances: 34 },
  },
];

const DEMO_WATCHLIST = [
  { ticker: "TCS.NS", status: "SHORT strengthening", note: "Conf: 0.67" },
  { ticker: "O39.SI", status: "Approaching reversion", note: "z=-1.7" },
  { ticker: "D05.SI/O39.SI", status: "Pairs spread widening", note: "z=1.8" },
];

const DEMO_PORTFOLIO_HEALTH = {
  pnl: "+1.2%",
  sharpe: 1.43,
  var: -1.8,
  decayOk: true,
};

const DEMO_WHAT_I_LEARNED = `Mean reversion on SGX banks: 4/6 profitable (+1.8%)
Momentum on NSE large-caps: 2/5 profitable (-0.3%)
\u2192 Adjusting: \u2191 mean reversion weight on SG, \u2193 momentum on India`;

const DEMO_THOUGHTS = [
  { timestamp: new Date(Date.now() - 420000).toISOString(), agent: "Director", message: "Initiating morning research cycle for SGX + NSE universe (6 tickers).", type: "info" as const },
  { timestamp: new Date(Date.now() - 360000).toISOString(), agent: "Macro", message: "VIX at 19.2, MAS holding rates steady. Risk-on regime for APAC equities.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 300000).toISOString(), agent: "Quant", message: "DBS (D05.SI) z-score hit -2.1 on 20d mean reversion. Top decile signal historically.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 240000).toISOString(), agent: "Technician", message: "D05.SI RSI=28, oversold. MACD histogram turning positive. Volume confirming.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 180000).toISOString(), agent: "Sentiment", message: "DBS Q1 earnings beat expectations. Tone shift +0.19, institutional flow bullish.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 150000).toISOString(), agent: "Contrarian", message: "Crowd is still bearish on SG banks. Contrarian signal: BUY. Fade the fear.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 120000).toISOString(), agent: "Risk", message: "D05.SI position within VaR limits. Kelly criterion suggests SGD 5,800 sizing.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 90000).toISOString(), agent: "Director", message: "Consensus reached: D05.SI LONG at 84% confidence. Routing to approval gate.", type: "decision" as const },
  { timestamp: new Date(Date.now() - 60000).toISOString(), agent: "Quant", message: "RELIANCE.NS z=-1.8, mean reversion signal. Jio subscriber growth accelerating.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 30000).toISOString(), agent: "Risk", message: "Portfolio VaR remains at -1.8% with proposed additions. All risk limits clear.", type: "info" as const },
  { timestamp: new Date(Date.now() - 10000).toISOString(), agent: "Director", message: "Morning brief compiled. 2 actionable signals, 3 watchlist items. Awaiting human review.", type: "decision" as const },
];

/* ══════════════════════════════════════════════════════════════════
   HELPERS — convert API signals to component formats
   ══════════════════════════════════════════════════════════════════ */

interface ApiSignal {
  ticker: string;
  strategy: string;
  signals_count: number;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
}

/** Convert an API signal to the Signal card format */
function apiSignalToSignal(s: ApiSignal): Signal {
  const absReturn = Math.abs(s.total_return);
  const direction = absReturn < 0.001 ? 0 : s.total_return > 0 ? 1 : -1;
  const confidence = Math.min(Math.abs(s.sharpe_ratio) / 5, 1);
  const today = new Date().toISOString().split("T")[0];
  return { ticker: s.ticker, date: today, direction, confidence };
}

/** Convert top API signals to MorningBrief SignalEntry format */
function apiSignalsToBriefSignals(signals: ApiSignal[]) {
  // Sort by absolute total_return descending, pick top 2
  const sorted = [...signals].sort((a, b) => Math.abs(b.total_return) - Math.abs(a.total_return));
  const top = sorted.slice(0, 2);

  return top.map((s) => {
    const direction = s.total_return >= 0 ? "LONG" : "SHORT";
    const confidence = Math.min(Math.abs(s.sharpe_ratio) / 5, 1);
    return {
      ticker: s.ticker,
      direction,
      confidence: Math.round(confidence * 100) / 100,
      agents: [
        { name: "The Quant", thought: `${s.strategy}, ${s.signals_count} signals generated` },
        { name: "Risk", thought: `Sharpe ${s.sharpe_ratio.toFixed(2)}, Max DD ${(s.max_drawdown * 100).toFixed(1)}%` },
        { name: "Backtest", thought: `Return ${(s.total_return * 100).toFixed(1)}%, Win rate ${(s.win_rate * 100).toFixed(0)}%` },
      ],
      historical: {
        win_rate: s.win_rate,
        avg_return: s.total_return * 100,
        hold_days: Math.round(s.signals_count / 10) || 5,
        instances: s.signals_count,
      },
    };
  });
}

/** Build watchlist from signals that aren't top 2 */
function apiSignalsToWatchlist(signals: ApiSignal[]) {
  const sorted = [...signals].sort((a, b) => Math.abs(b.total_return) - Math.abs(a.total_return));
  const rest = sorted.slice(2, 5);
  return rest.map((s) => ({
    ticker: s.ticker,
    status: s.total_return >= 0 ? "LONG building" : "SHORT strengthening",
    note: `Sharpe: ${s.sharpe_ratio.toFixed(2)}`,
  }));
}

/** Build portfolio health summary from all signals */
function apiSignalsToPortfolioHealth(signals: ApiSignal[]) {
  if (signals.length === 0) return DEMO_PORTFOLIO_HEALTH;
  const avgReturn = signals.reduce((sum, s) => sum + s.total_return, 0) / signals.length;
  const avgSharpe = signals.reduce((sum, s) => sum + s.sharpe_ratio, 0) / signals.length;
  const worstDD = Math.min(...signals.map((s) => s.max_drawdown));
  return {
    pnl: `${avgReturn >= 0 ? "+" : ""}${(avgReturn * 100).toFixed(1)}%`,
    sharpe: Math.round(avgSharpe * 100) / 100,
    var: Math.round(worstDD * 100 * 10) / 10,
    decayOk: avgSharpe > 0,
  };
}

/** Build "what I learned" summary */
function apiSignalsToLearned(signals: ApiSignal[]) {
  if (signals.length === 0) return DEMO_WHAT_I_LEARNED;
  const profitable = signals.filter((s) => s.total_return > 0);
  const losing = signals.filter((s) => s.total_return <= 0);
  const lines: string[] = [];
  if (profitable.length > 0) {
    const avgRet = profitable.reduce((s, x) => s + x.total_return, 0) / profitable.length;
    lines.push(`${profitable.length} profitable signals (avg +${(avgRet * 100).toFixed(1)}%): ${profitable.map((s) => s.ticker).join(", ")}`);
  }
  if (losing.length > 0) {
    const avgRet = losing.reduce((s, x) => s + x.total_return, 0) / losing.length;
    lines.push(`${losing.length} losing signals (avg ${(avgRet * 100).toFixed(1)}%): ${losing.map((s) => s.ticker).join(", ")}`);
  }
  const bestStrategy = signals.reduce((best, s) => (s.total_return > best.total_return ? s : best), signals[0]);
  lines.push(`\u2192 Best performing: ${bestStrategy.ticker} via ${bestStrategy.strategy} (+${(bestStrategy.total_return * 100).toFixed(1)}%)`);
  return lines.join("\n");
}

/** Build BacktestMetrics from the best signal */
function apiSignalsToMetrics(signals: ApiSignal[]): BacktestMetrics | null {
  if (signals.length === 0) return null;
  const best = [...signals].sort((a, b) => b.sharpe_ratio - a.sharpe_ratio)[0];
  return {
    strategy_name: best.strategy,
    total_return: best.total_return,
    annualized_return: best.total_return, // approximate
    sharpe_ratio: best.sharpe_ratio,
    sortino_ratio: best.sharpe_ratio * 1.2, // approximate
    max_drawdown: best.max_drawdown,
    calmar_ratio: best.total_return / Math.abs(best.max_drawdown || 0.01),
    win_rate: best.win_rate,
    profit_factor: best.win_rate / (1 - best.win_rate || 0.5),
  };
}

/* ══════════════════════════════════════════════════════════════════
   HELPER — optional auth header
   ══════════════════════════════════════════════════════════════════ */

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/* ══════════════════════════════════════════════════════════════════
   PAGE COMPONENT
   ══════════════════════════════════════════════════════════════════ */

export default function MonitorPage() {
  const store = useAppStore();
  const router = useRouter();
  const { events: wsEvents, connected } = useWebSocket();
  const { startRun, approve, reject } = useAgents();

  /* ── API-fetched state ── */
  const [apiSignals, setApiSignals] = useState<ApiSignal[]>([]);
  const [universeTickers, setUniverseTickers] = useState<string[]>([]);
  const [apiLoading, setApiLoading] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  /* ── Fetch real data on mount ── */
  useEffect(() => {
    let cancelled = false;

    async function fetchSignals() {
      try {
        const res = await fetch(`${API_URL}/api/universe/signals`, {
          headers: { ...authHeaders() },
        });
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json();
        if (!cancelled && data.signals && data.signals.length > 0) {
          setApiSignals(data.signals);
        }
      } catch {
        // Silently fall back to demo data
      }
    }

    async function fetchUniverse() {
      try {
        const res = await fetch(`${API_URL}/api/universe`, {
          headers: { ...authHeaders() },
        });
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json();
        if (!cancelled && data.tickers && data.tickers.length > 0) {
          setUniverseTickers(data.tickers);
          setSelectedTicker(data.tickers[0]);
        }
      } catch {
        // Silently fall back — no universe available
      }
    }

    Promise.all([fetchSignals(), fetchUniverse()]).finally(() => {
      if (!cancelled) setApiLoading(false);
    });

    return () => { cancelled = true; };
  }, []);

  /* ── Close dropdown on outside click ── */
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  /* ── Merge WebSocket events into store ── */
  useEffect(() => {
    if (wsEvents.length > 0) {
      const latest = wsEvents[wsEvents.length - 1];
      store.addEvent(latest);

      if (latest.status === "awaiting_approval") {
        store.setApprovalPending(true);
      }
      if (latest.status === "completed" && latest.agent_name === "report") {
        store.setApprovalPending(false);
      }

      // Parse run_completed events for results
      if ((latest as any).type === "run_completed" && (latest as any).result) {
        const r = (latest as any).result;
        if (r.backtest_result) {
          store.setMetrics(r.backtest_result as BacktestMetrics);
        }
        if (r.signals) {
          store.setSignals(
            r.signals.map((s: any) => ({
              ticker: s.ticker,
              date: s.date,
              direction: s.direction,
              confidence: s.confidence,
            }))
          );
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsEvents]);

  /* ── Derived: has real API data? ── */
  const hasApiData = apiSignals.length > 0;

  /* ── Resolve data: live store > API > demo ── */
  const mode = store.mode;
  const metrics = store.metrics || (hasApiData ? apiSignalsToMetrics(apiSignals) : null) || DEMO_METRICS;
  const events = store.events.length > 0 ? store.events : DEMO_EVENTS;
  const signals: Signal[] = store.signals.length > 0
    ? store.signals
    : hasApiData
    ? apiSignals.map(apiSignalToSignal)
    : DEMO_SIGNALS;
  const equity = DEMO_EQUITY;
  const icCurve = DEMO_IC;

  /* ── Morning Brief: live API > demo ── */
  const briefSignals = useMemo(
    () => (hasApiData ? apiSignalsToBriefSignals(apiSignals) : DEMO_BRIEF_SIGNALS),
    [hasApiData, apiSignals],
  );
  const watchlist = useMemo(
    () => (hasApiData ? apiSignalsToWatchlist(apiSignals) : DEMO_WATCHLIST),
    [hasApiData, apiSignals],
  );
  const portfolioHealth = useMemo(
    () => (hasApiData ? apiSignalsToPortfolioHealth(apiSignals) : DEMO_PORTFOLIO_HEALTH),
    [hasApiData, apiSignals],
  );
  const whatILearned = useMemo(
    () => (hasApiData ? apiSignalsToLearned(apiSignals) : DEMO_WHAT_I_LEARNED),
    [hasApiData, apiSignals],
  );

  /* ── Research state ── */
  const [researching, setResearching] = useState(false);
  const [liveThoughts, setLiveThoughts] = useState<typeof DEMO_THOUGHTS>([]);
  const [researchResult, setResearchResult] = useState<string | null>(null);
  const isRunning = researching;

  /* ── Thought Stream data: live agent thoughts take priority ── */
  const thoughtStreamData = useMemo(() => {
    if (liveThoughts.length > 0) return liveThoughts;
    return [];
  }, [liveThoughts]);

  /* ── Handlers ── */
  const handleRun = useCallback(async () => {
    const ticker = selectedTicker || (universeTickers.length > 0 ? universeTickers[0] : "AAPL");
    setResearching(true);
    setLiveThoughts([]);
    setResearchResult(null);

    // Add initial "thinking" thought
    const addThought = (agent: string, message: string, type: "info" | "analysis" | "decision" = "analysis") => {
      setLiveThoughts((prev) => [...prev, {
        timestamp: new Date().toISOString(),
        agent,
        message,
        type,
      }]);
    };

    addThought("Director", `Initiating analysis for ${ticker}...`, "info");

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ message: `Analyze ${ticker} for mean reversion` }),
      });

      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();

      // Parse agent_traces and add them one by one with delays
      const traces = data.agent_traces || [];
      for (let i = 0; i < traces.length; i++) {
        const trace = traces[i];
        const agentName = String(trace.agent || "Agent").replace("the_", "").replace("_", " ");
        const capitalized = agentName.charAt(0).toUpperCase() + agentName.slice(1);
        const thoughts = trace.thoughts || [];
        const signal = trace.signal || "neutral";
        const conf = trace.confidence || 0;
        const summary = thoughts[0] || `Signal: ${signal} (${(conf * 100).toFixed(0)}%)`;

        // Stagger each agent's appearance
        await new Promise((r) => setTimeout(r, 300));
        addThought(capitalized, summary);
      }

      // Final synthesis
      await new Promise((r) => setTimeout(r, 400));
      const answer = data.answer || "";
      const signal = answer.includes("bullish") ? "BULLISH" : answer.includes("bearish") ? "BEARISH" : "NEUTRAL";
      addThought("Director", `Consensus: ${signal} on ${ticker}. ${data.citations?.[0] || ""}`, "decision");
      setResearchResult(answer);

    } catch (err) {
      addThought("Director", `Analysis failed: ${err instanceof Error ? err.message : "unknown error"}`, "info");
    } finally {
      setResearching(false);
    }
  }, [selectedTicker, universeTickers]);

  const handleApprove = useCallback(
    async (ticker: string) => {
      store.setApprovalPending(false);
      // Submit a backtest job for this ticker and navigate to Jobs
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;
        await fetch(`${API_URL}/api/jobs/submit`, {
          method: "POST",
          headers,
          body: JSON.stringify({ ticker, strategy: "mean_reversion", start_date: "2023-01-01", end_date: "2026-04-13" }),
        });
      } catch {}
      router.push(href("/jobs"));
    },
    [router]
  );

  const handleReject = useCallback(
    async (ticker: string) => {
      store.setApprovalPending(false);
      // Remove from view — just clear the signal from the API data
      setApiSignals((prev) => prev.filter((s) => s.ticker !== ticker));
    },
    [store]
  );

  const handleDigDeeper = useCallback((ticker: string) => {
    router.push(href(`/chat?q=${encodeURIComponent(`Deep dive on ${ticker} — analyze technicals, fundamentals, and macro outlook`)}`));
  }, [router]);

  /* ── Data source label ── */
  const dataSourceLabel = useMemo(() => {
    if (mode === "live") return connected ? "Live" : "Connecting...";
    if (hasApiData) return `API (${apiSignals.length} signals)`;
    return "Demo Mode";
  }, [mode, connected, hasApiData, apiSignals.length]);

  return (
    <div className="flex h-full">
      {/* ── LEFT COLUMN: Morning Brief + Charts + Signals ── */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 sm:p-6 space-y-5 sm:space-y-6 max-w-[1100px]">
          {/* Header bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-violet-400" />
                <h2 className="text-base sm:text-lg font-semibold text-zinc-50">
                  Agentic Alpha Lab
                </h2>
              </div>
              <div className="h-4 w-px bg-zinc-800" />
              <p className="text-xs text-zinc-500" suppressHydrationWarning>
                {dataSourceLabel}
              </p>
              {connected && (
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                </span>
              )}
              {apiLoading && (
                <Loader2 className="h-3 w-3 text-zinc-500 animate-spin" />
              )}
            </div>

            {/* Start Research button with ticker dropdown */}
            <div className="flex items-center gap-2 w-full sm:w-auto" ref={dropdownRef}>
              {/* Ticker selector dropdown */}
              {universeTickers.length > 0 && (
                <div className="relative">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => setDropdownOpen(!dropdownOpen)}
                    className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 sm:py-2.5 text-xs sm:text-sm text-zinc-300 hover:border-zinc-700 hover:text-zinc-100 transition-all"
                  >
                    <span className="font-mono">{selectedTicker || universeTickers[0]}</span>
                    <ChevronDown className={cn("h-3 w-3 transition-transform", dropdownOpen && "rotate-180")} />
                  </motion.button>
                  <AnimatePresence>
                    {dropdownOpen && (
                      <motion.div
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={{ duration: 0.15 }}
                        className="absolute right-0 top-full mt-1 z-50 w-44 rounded-lg border border-zinc-800 bg-zinc-900 shadow-xl shadow-black/40 overflow-hidden"
                      >
                        <div className="max-h-56 overflow-y-auto py-1">
                          {universeTickers.map((ticker) => (
                            <button
                              key={ticker}
                              onClick={() => {
                                setSelectedTicker(ticker);
                                setDropdownOpen(false);
                              }}
                              className={cn(
                                "w-full text-left px-3 py-1.5 text-xs font-mono transition-colors",
                                ticker === selectedTicker
                                  ? "bg-violet-500/10 text-violet-400"
                                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                              )}
                            >
                              {ticker}
                            </button>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={handleRun}
                disabled={isRunning}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-4 py-2 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-medium transition-all flex-1 sm:flex-none justify-center",
                  isRunning
                    ? "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                    : "bg-violet-500 text-white hover:bg-violet-400 shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30"
                )}
              >
                {isRunning ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {isRunning ? "Analyzing..." : "Start Research"}
              </motion.button>
            </div>
          </div>

          {/* ── Morning Brief ── */}
          <MorningBrief
            signals={briefSignals}
            watchlist={watchlist}
            portfolioHealth={portfolioHealth}
            whatILearned={whatILearned}
            onApprove={handleApprove}
            onReject={handleReject}
            onDigDeeper={handleDigDeeper}
          />

          {/* ── Charts ── */}
          <div className="grid gap-4 sm:gap-6 grid-cols-1 lg:grid-cols-2">
            <EquityCurveChart data={equity} />
            <SignalDecayChart data={icCurve} halfLife={12.3} />
          </div>

          {/* ── Signal Cards Grid ── */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
                Active Signals
              </h2>
              <div className="flex-1 h-px bg-zinc-800" />
              <span className="text-xs text-zinc-600 tabular-nums">
                {signals.filter((s) => s.direction !== 0).length} active
              </span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {signals.map((signal, i) => (
                <div
                  key={`${signal.ticker}-${i}`}
                  className="cursor-pointer transition-transform hover:scale-[1.02]"
                  onClick={() => router.push(href(`/chat?q=${encodeURIComponent(`Analyze ${signal.ticker} for mean reversion`)}`))}
                >
                  <SignalCard
                    signal={signal}
                    index={i}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="flex flex-wrap items-center gap-4 sm:gap-6 pt-4 border-t border-zinc-800 text-xs text-zinc-600">
            <span className="flex items-center gap-1">
              <Activity className="h-3 w-3" /> {events.length} events
            </span>
            <span className="flex items-center gap-1">
              <Shield className="h-3 w-3" />{" "}
              {signals.filter((s) => s.direction !== 0).length} active signals
            </span>
            <span className="flex items-center gap-1">
              <BarChart3 className="h-3 w-3" /> Sharpe{" "}
              {metrics.sharpe_ratio.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* ── RIGHT COLUMN: Thought Stream (sticky) ── */}
      <div className="hidden lg:block w-[380px] shrink-0 border-l border-zinc-800 h-full">
        {thoughtStreamData.length > 0 ? (
          <ThoughtStream
            thoughts={thoughtStreamData}
            isLive={researching}
            className="h-full rounded-none border-0"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center px-6 text-center">
            <div className="h-10 w-10 rounded-xl bg-violet-500/10 flex items-center justify-center mb-3">
              <Zap className="h-5 w-5 text-violet-400/50" />
            </div>
            <p className="text-xs text-zinc-600 leading-relaxed">
              Click <span className="text-violet-400">Start Research</span> to see live agent reasoning
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
