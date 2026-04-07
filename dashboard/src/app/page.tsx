"use client";

import { useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { Activity, Shield, BarChart3, Play, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { MetricCard } from "@/components/MetricCard";
import { EquityCurveChart } from "@/components/EquityCurveChart";
import { SignalDecayChart } from "@/components/SignalDecayChart";
import { AgentActivityFeed } from "@/components/AgentActivityFeed";
import { SignalCard } from "@/components/SignalCard";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAgents } from "@/hooks/useAgents";
import { API_URL } from "@/lib/utils";
import type { AgentEvent, Signal, BacktestMetrics, EquityCurvePoint, ICCurvePoint } from "@/types";

/* ── Demo data (shown when mode === "demo" or no live data yet) ── */

const DEMO_METRICS: BacktestMetrics = {
  strategy_name: "mean_reversion",
  total_return: 0.186, annualized_return: 0.124,
  sharpe_ratio: 1.87, sortino_ratio: 2.43,
  max_drawdown: -0.067, calmar_ratio: 1.85,
  win_rate: 0.58, profit_factor: 1.41,
  var_95: -0.0152, cvar_95: -0.0219,
};

const DEMO_EQUITY: EquityCurvePoint[] = Array.from({ length: 252 }, (_, i) => ({
  date: new Date(2023, 0, 3 + i).toISOString().split("T")[0],
  equity: 100000 * Math.exp(i * 0.0005 + Math.sin(i / 20) * 0.02),
}));

const DEMO_IC: ICCurvePoint[] = Array.from({ length: 30 }, (_, i) => ({
  horizon: i + 1,
  ic: 0.08 * Math.exp(-i / 12) + (Math.random() - 0.5) * 0.005,
  ic_std: 0.02, is_significant: i < 20,
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
  { agent_name: "research", status: "completed", message: "Fetched 500 days of OHLCV for 6 tickers", data: {}, timestamp: new Date().toISOString() },
  { agent_name: "research", status: "completed", message: "Computed z-score, momentum, RSI features", data: {}, timestamp: new Date().toISOString() },
  { agent_name: "research", status: "completed", message: "Generated 6 trading signals", data: {}, timestamp: new Date().toISOString() },
  { agent_name: "risk", status: "completed", message: "5 approved, 1 rejected (TSLA: exposure limit)", data: {}, timestamp: new Date().toISOString() },
  { agent_name: "risk", status: "awaiting_approval", message: "Awaiting human approval for 5 signals", data: {}, timestamp: new Date().toISOString() },
];

/* ── Page ── */

export default function MonitorPage() {
  const store = useAppStore();
  const { events: wsEvents, connected } = useWebSocket();
  const { startRun, approve, reject } = useAgents();

  // Merge WebSocket events into store
  useEffect(() => {
    if (wsEvents.length > 0) {
      const latest = wsEvents[wsEvents.length - 1];
      store.addEvent(latest);

      // Parse agent events for approval state
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
          store.setSignals(r.signals.map((s: any) => ({
            ticker: s.ticker, date: s.date,
            direction: s.direction, confidence: s.confidence,
          })));
        }
      }
    }
  }, [wsEvents]);

  // Resolve data: live store data if available, else demo
  const mode = store.mode;
  const metrics = store.metrics || DEMO_METRICS;
  const events = store.events.length > 0 ? store.events : DEMO_EVENTS;
  const signals = store.signals.length > 0 ? store.signals : DEMO_SIGNALS;
  const equity = DEMO_EQUITY; // TODO: parse from live backtest result
  const icCurve = DEMO_IC;
  const isRunning = events.some(e => e.status === "running");

  const handleRun = useCallback(async () => {
    store.clearEvents();
    store.setApprovalPending(false);
    await startRun("AAPL", "mean_reversion", "2022-01-01", "2024-12-31");
  }, [startRun, store]);

  const handleApprove = useCallback(async () => {
    store.setApprovalPending(false);
    await approve();
  }, [approve, store]);

  const handleReject = useCallback(async () => {
    store.setApprovalPending(false);
    await reject();
  }, [reject, store]);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-zinc-50">Monitor</h2>
          <p className="text-sm text-zinc-500">
            {mode === "demo" ? "Demo Mode — showing sample data" : connected ? "Live — connected to agents" : "Live — connecting..."}
          </p>
        </div>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleRun}
          disabled={isRunning}
          className={cn(
            "flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-colors",
            isRunning
              ? "bg-zinc-800 text-zinc-500 cursor-not-allowed"
              : "bg-violet-500 text-white hover:bg-violet-400"
          )}
        >
          {isRunning ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {isRunning ? "Agents Running..." : "Start Research"}
        </motion.button>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <MetricCard label="Total Return" value={`${(metrics.total_return * 100).toFixed(1)}%`} trend={metrics.total_return > 0 ? "up" : "down"} />
        <MetricCard label="Sharpe Ratio" value={metrics.sharpe_ratio.toFixed(2)} trend={metrics.sharpe_ratio > 1 ? "up" : "neutral"} />
        <MetricCard label="Sortino" value={metrics.sortino_ratio.toFixed(2)} trend="up" />
        <MetricCard label="Max Drawdown" value={`${(metrics.max_drawdown * 100).toFixed(1)}%`} trend="down" />
        <MetricCard label="Win Rate" value={`${(metrics.win_rate * 100).toFixed(0)}%`} trend={metrics.win_rate > 0.5 ? "up" : "down"} />
        <MetricCard label="VaR (95%)" value={`${((metrics.var_95 || 0) * 100).toFixed(2)}%`} subtext="Daily" trend="neutral" />
      </div>

      {/* Approval Panel */}
      <ApprovalPanel
        signalsCount={signals.filter(s => s.direction !== 0).length}
        rejectedCount={1}
        warnings={["Position capped by risk manager"]}
        onApprove={handleApprove}
        onReject={handleReject}
        isPending={store.approvalPending}
      />

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <EquityCurveChart data={equity} />
        <SignalDecayChart data={icCurve} halfLife={12.3} />
      </div>

      {/* Signals + Activity */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">Active Signals</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {signals.map((signal, i) => (
              <SignalCard key={`${signal.ticker}-${i}`} signal={signal} index={i} />
            ))}
          </div>
        </div>
        <AgentActivityFeed events={events} />
      </div>

      {/* Footer stats */}
      <div className="flex items-center gap-6 pt-4 border-t border-zinc-800 text-xs text-zinc-600">
        <span className="flex items-center gap-1"><Activity className="h-3 w-3" /> {events.length} events</span>
        <span className="flex items-center gap-1"><Shield className="h-3 w-3" /> {signals.filter(s => s.direction !== 0).length} active signals</span>
        <span className="flex items-center gap-1"><BarChart3 className="h-3 w-3" /> Sharpe {metrics.sharpe_ratio.toFixed(2)}</span>
      </div>
    </div>
  );
}
