"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  Zap,
  Shield,
  BarChart3,
  Wifi,
  WifiOff,
  Play,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { MetricCard } from "@/components/MetricCard";
import { EquityCurveChart } from "@/components/EquityCurveChart";
import { SignalDecayChart } from "@/components/SignalDecayChart";
import { AgentActivityFeed } from "@/components/AgentActivityFeed";
import { SignalCard } from "@/components/SignalCard";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { useWebSocket } from "@/hooks/useWebSocket";
import { API_URL } from "@/lib/utils";
import type {
  AgentEvent,
  Signal,
  BacktestMetrics,
  EquityCurvePoint,
  ICCurvePoint,
} from "@/types";

/* ---------- Demo data for meetup / offline mode ---------- */

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
  { agent_name: "research", status: "completed", message: "Fetched 500 days of OHLCV for 6 tickers", data: {}, timestamp: new Date().toISOString() },
  { agent_name: "research", status: "completed", message: "Computed z-score, momentum, RSI features", data: {}, timestamp: new Date().toISOString() },
  { agent_name: "research", status: "completed", message: "Generated 6 trading signals", data: {}, timestamp: new Date().toISOString() },
  { agent_name: "risk", status: "completed", message: "5 approved, 1 rejected (TSLA: exposure limit)", data: {}, timestamp: new Date().toISOString() },
  { agent_name: "risk", status: "awaiting_approval", message: "Awaiting human approval for 5 signals", data: {}, timestamp: new Date().toISOString() },
];

/* ---------- Dashboard ---------- */

export default function Dashboard() {
  const { events: wsEvents, connected } = useWebSocket();
  const [isRunning, setIsRunning] = useState(false);
  const [approvalPending, setApprovalPending] = useState(true);

  const events = wsEvents.length > 0 ? wsEvents : DEMO_EVENTS;
  const metrics = DEMO_METRICS;

  const handleRun = useCallback(async () => {
    setIsRunning(true);
    try {
      await fetch(`${API_URL}/api/agents/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: "AAPL",
          strategy: "mean_reversion",
          start_date: "2022-01-01",
          end_date: "2024-12-31",
        }),
      });
    } catch {
      /* API may not be running — demo mode */
    }
    setIsRunning(false);
  }, []);

  const handleApprove = useCallback(async () => {
    setApprovalPending(false);
    try {
      await fetch(`${API_URL}/api/agents/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved: true }),
      });
    } catch { /* demo */ }
  }, []);

  const handleReject = useCallback(async () => {
    setApprovalPending(false);
    try {
      await fetch(`${API_URL}/api/agents/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved: false }),
      });
    } catch { /* demo */ }
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-zinc-50">Agentic Alpha Lab</h1>
              <p className="text-xs text-zinc-500">Human-on-the-Loop Quant Research</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              {connected ? (
                <Wifi className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <WifiOff className="h-3.5 w-3.5 text-zinc-600" />
              )}
              <span className="text-xs text-zinc-500">
                {connected ? "Live" : "Demo Mode"}
              </span>
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleRun}
              disabled={isRunning}
              className={cn(
                "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                isRunning
                  ? "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                  : "bg-violet-500 text-white hover:bg-violet-400"
              )}
            >
              <Play className="h-3.5 w-3.5" />
              {isRunning ? "Running..." : "Start Research"}
            </motion.button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
        {/* Metrics */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
          <MetricCard label="Total Return" value={`${(metrics.total_return * 100).toFixed(1)}%`} trend={metrics.total_return > 0 ? "up" : "down"} />
          <MetricCard label="Sharpe Ratio" value={metrics.sharpe_ratio.toFixed(2)} trend={metrics.sharpe_ratio > 1 ? "up" : "neutral"} />
          <MetricCard label="Sortino" value={metrics.sortino_ratio.toFixed(2)} trend="up" />
          <MetricCard label="Max Drawdown" value={`${(metrics.max_drawdown * 100).toFixed(1)}%`} trend="down" />
          <MetricCard label="Win Rate" value={`${(metrics.win_rate * 100).toFixed(0)}%`} trend={metrics.win_rate > 0.5 ? "up" : "down"} />
          <MetricCard label="VaR (95%)" value={`${((metrics.var_95 || 0) * 100).toFixed(2)}%`} subtext="Daily" trend="neutral" />
        </div>

        {/* Approval */}
        <ApprovalPanel
          signalsCount={5}
          rejectedCount={1}
          warnings={["TSLA: rejected — total exposure would exceed 100%"]}
          onApprove={handleApprove}
          onReject={handleReject}
          isPending={approvalPending}
        />

        {/* Charts */}
        <div className="grid gap-6 lg:grid-cols-2">
          <EquityCurveChart data={DEMO_EQUITY} />
          <SignalDecayChart data={DEMO_IC} halfLife={12.3} />
        </div>

        {/* Signals + Activity */}
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">Active Signals</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {DEMO_SIGNALS.map((signal, i) => (
                <SignalCard key={`${signal.ticker}-${i}`} signal={signal} index={i} />
              ))}
            </div>
          </div>
          <AgentActivityFeed events={events} />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800 py-6">
        <div className="mx-auto max-w-7xl px-6 flex items-center justify-between">
          <p className="text-xs text-zinc-600">Agentic Alpha Lab — Built with Claude Code</p>
          <div className="flex items-center gap-4 text-xs text-zinc-600">
            <span className="flex items-center gap-1"><Activity className="h-3 w-3" /> {events.length} events</span>
            <span className="flex items-center gap-1"><Shield className="h-3 w-3" /> {DEMO_SIGNALS.filter(s => s.direction !== 0).length} active</span>
            <span className="flex items-center gap-1"><BarChart3 className="h-3 w-3" /> Sharpe {metrics.sharpe_ratio.toFixed(2)}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
