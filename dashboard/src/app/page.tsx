"use client";

import { useCallback, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { Play, RefreshCw, Activity, Shield, BarChart3, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
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
  { ticker: "AAPL", date: "2024-03-15", direction: 1.0, confidence: 0.82 },
  { ticker: "MSFT", date: "2024-03-15", direction: -1.0, confidence: 0.65 },
  { ticker: "NVDA", date: "2024-03-15", direction: 1.0, confidence: 0.91 },
  { ticker: "GOOG", date: "2024-03-15", direction: 0, confidence: 1.0 },
  { ticker: "TSLA", date: "2024-03-15", direction: -1.0, confidence: 0.73 },
  { ticker: "META", date: "2024-03-15", direction: 1.0, confidence: 0.58 },
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
    ticker: "NVDA",
    direction: "LONG",
    confidence: 0.84,
    agents: [
      { name: "The Quant", thought: "z=-2.1, 62% win rate, 47 samples" },
      { name: "The Technician", thought: "RSI=28, MACD crossover forming" },
      { name: "Sentiment", thought: "Tone shift +0.19, bullish rotation" },
      { name: "Risk", thought: "VaR +0.3%, Kelly sizing $4,200" },
    ],
    historical: { win_rate: 0.62, avg_return: 2.1, hold_days: 12, instances: 47 },
  },
  {
    ticker: "AAPL",
    direction: "LONG",
    confidence: 0.78,
    agents: [
      { name: "The Quant", thought: "z=-1.8, mean reversion setup" },
      { name: "The Technician", thought: "Oversold bounce at 200 DMA" },
      { name: "Fundamentalist", thought: "PE ratio compressed, earnings beat" },
      { name: "Risk", thought: "VaR +0.2%, Kelly sizing $3,100" },
    ],
    historical: { win_rate: 0.57, avg_return: 1.6, hold_days: 8, instances: 34 },
  },
];

const DEMO_WATCHLIST = [
  { ticker: "TSLA", status: "SHORT strengthening", note: "Conf: 0.67" },
  { ticker: "AAPL", status: "Approaching reversion", note: "z=-1.7" },
  { ticker: "MSFT/GOOG", status: "Pairs spread widening", note: "z=1.8" },
];

const DEMO_PORTFOLIO_HEALTH = {
  pnl: "+1.2%",
  sharpe: 1.43,
  var: -1.8,
  decayOk: true,
};

const DEMO_WHAT_I_LEARNED = `Mean reversion: 4/6 profitable (+1.8%)
Momentum: 2/5 profitable (-0.3%)
\u2192 Adjusting: \u2191 mean reversion weight, \u2193 momentum exposure`;

const DEMO_THOUGHTS = [
  { timestamp: new Date(Date.now() - 420000).toISOString(), agent: "Director", message: "Initiating morning research cycle for 12 tickers in the active universe.", type: "info" as const },
  { timestamp: new Date(Date.now() - 360000).toISOString(), agent: "Macro", message: "10Y yield down 4bp, VIX at 14.2. Risk-on regime confirmed. Favoring equity long exposure.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 300000).toISOString(), agent: "Quant", message: "NVDA z-score hit -2.1 on 20d mean reversion. Signal strength: top decile historically.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 240000).toISOString(), agent: "Technician", message: "NVDA RSI=28, oversold. MACD histogram turning positive. Volume confirming.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 180000).toISOString(), agent: "Sentiment", message: "NVDA social sentiment shifted +0.19 over 48h. Institutional flow turning bullish.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 150000).toISOString(), agent: "Contrarian", message: "Crowd is still bearish on NVDA. Contrarian signal: BUY. Fade the fear.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 120000).toISOString(), agent: "Risk", message: "NVDA position within VaR limits. Kelly criterion suggests $4,200 sizing. Max drawdown tolerable.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 90000).toISOString(), agent: "Director", message: "Consensus reached: NVDA LONG at 84% confidence. Routing to approval gate.", type: "decision" as const },
  { timestamp: new Date(Date.now() - 60000).toISOString(), agent: "Quant", message: "AAPL z=-1.8, secondary mean reversion signal detected. Moderate conviction.", type: "analysis" as const },
  { timestamp: new Date(Date.now() - 30000).toISOString(), agent: "Risk", message: "Portfolio VaR remains at -1.8% with proposed additions. All risk limits clear.", type: "info" as const },
  { timestamp: new Date(Date.now() - 10000).toISOString(), agent: "Director", message: "Morning brief compiled. 2 actionable signals, 3 watchlist items. Awaiting human review.", type: "decision" as const },
];

/* ══════════════════════════════════════════════════════════════════
   PAGE COMPONENT
   ══════════════════════════════════════════════════════════════════ */

export default function MonitorPage() {
  const store = useAppStore();
  const { events: wsEvents, connected } = useWebSocket();
  const { startRun, approve, reject } = useAgents();

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

  /* ── Resolve data: live vs demo ── */
  const mode = store.mode;
  const metrics = store.metrics || DEMO_METRICS;
  const events = store.events.length > 0 ? store.events : DEMO_EVENTS;
  const signals = store.signals.length > 0 ? store.signals : DEMO_SIGNALS;
  const equity = DEMO_EQUITY;
  const icCurve = DEMO_IC;
  const isRunning = events.some((e) => e.status === "running");

  /* ── Map store events to ThoughtStream format ── */
  const thoughtStreamData = useMemo(() => {
    if (store.events.length > 0) {
      return store.events.map((e) => ({
        timestamp: e.timestamp,
        agent: e.agent_name,
        message: e.message,
        type: (e.status === "awaiting_approval"
          ? "warning"
          : e.status === "completed"
          ? "info"
          : e.status === "running"
          ? "analysis"
          : "info") as "info" | "analysis" | "decision" | "warning",
      }));
    }
    return DEMO_THOUGHTS;
  }, [store.events]);

  /* ── Handlers ── */
  const handleRun = useCallback(async () => {
    store.clearEvents();
    store.setApprovalPending(false);
    store.setMode("live");
    await startRun("AAPL", "mean_reversion");
  }, [startRun, store]);

  const handleApprove = useCallback(
    async (ticker: string) => {
      store.setApprovalPending(false);
      await approve();
    },
    [approve, store]
  );

  const handleReject = useCallback(
    async (ticker: string) => {
      store.setApprovalPending(false);
      await reject();
    },
    [reject, store]
  );

  const handleDigDeeper = useCallback((ticker: string) => {
    // Future: navigate to deep-dive view for this ticker
    console.log("Dig deeper:", ticker);
  }, []);

  return (
    <div className="flex h-full">
      {/* ── LEFT COLUMN: Morning Brief + Charts + Signals ── */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6 max-w-[1100px]">
          {/* Header bar */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-violet-400" />
                <h2 className="text-lg font-semibold text-zinc-50">
                  Agentic Alpha Lab
                </h2>
              </div>
              <div className="h-4 w-px bg-zinc-800" />
              <p className="text-xs text-zinc-500" suppressHydrationWarning>
                {mode === "demo"
                  ? "Demo Mode"
                  : connected
                  ? "Live"
                  : "Connecting..."}
              </p>
              {connected && (
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                </span>
              )}
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={handleRun}
              disabled={isRunning}
              className={cn(
                "flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-all",
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
              {isRunning ? "Agents Running..." : "Start Research"}
            </motion.button>
          </div>

          {/* ── Morning Brief ── */}
          <MorningBrief
            signals={DEMO_BRIEF_SIGNALS}
            watchlist={DEMO_WATCHLIST}
            portfolioHealth={DEMO_PORTFOLIO_HEALTH}
            whatILearned={DEMO_WHAT_I_LEARNED}
            onApprove={handleApprove}
            onReject={handleReject}
            onDigDeeper={handleDigDeeper}
          />

          {/* ── Charts ── */}
          <div className="grid gap-6 lg:grid-cols-2">
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
                <SignalCard
                  key={`${signal.ticker}-${i}`}
                  signal={signal}
                  index={i}
                />
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center gap-6 pt-4 border-t border-zinc-800 text-xs text-zinc-600">
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
        <ThoughtStream
          thoughts={thoughtStreamData}
          isLive={connected || mode === "demo"}
          className="h-full rounded-none border-0"
        />
      </div>
    </div>
  );
}
