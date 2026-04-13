"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Loader2, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { API_URL } from "@/lib/utils";
import { MetricCard } from "@/components/MetricCard";

interface JobResult {
  id: string;
  status: string;
  params: Record<string, unknown>;
  result: {
    ticker?: string;
    strategy_name?: string;
    signals_count?: number;
    backtest?: {
      total_return?: number;
      sharpe_ratio?: number;
      sortino_ratio?: number;
      max_drawdown?: number;
      win_rate?: number;
      equity_curve?: { date: string; equity: number }[];
    };
  } | null;
  created_at: string;
}

export default function PerformancePage() {
  const [jobs, setJobs] = useState<JobResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchJobs() {
      try {
        const token = localStorage.getItem("access_token");
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`${API_URL}/api/jobs?limit=100`, { headers });
        if (res.ok) {
          const data = await res.json();
          setJobs((data.jobs || []).filter((j: JobResult) => j.status === "completed" && j.result));
        }
      } catch {}
      finally { setLoading(false); }
    }
    fetchJobs();
  }, []);

  // Aggregate metrics from completed jobs
  const completedJobs = jobs.filter((j) => j.result?.backtest);
  const totalSignals = completedJobs.reduce((sum, j) => sum + (j.result?.signals_count || 0), 0);
  const avgReturn = completedJobs.length > 0
    ? completedJobs.reduce((sum, j) => sum + (j.result?.backtest?.total_return || 0), 0) / completedJobs.length
    : 0;
  const avgSharpe = completedJobs.length > 0
    ? completedJobs.reduce((sum, j) => sum + (j.result?.backtest?.sharpe_ratio || 0), 0) / completedJobs.length
    : 0;
  const avgWinRate = completedJobs.length > 0
    ? completedJobs.reduce((sum, j) => sum + (j.result?.backtest?.win_rate || 0), 0) / completedJobs.length
    : 0;

  // Strategy breakdown
  const strategyMap = new Map<string, { count: number; totalReturn: number; totalSharpe: number; totalWinRate: number; signals: number }>();
  for (const j of completedJobs) {
    const strategy = (j.result?.strategy_name || j.params?.strategy || "unknown") as string;
    const existing = strategyMap.get(strategy) || { count: 0, totalReturn: 0, totalSharpe: 0, totalWinRate: 0, signals: 0 };
    existing.count++;
    existing.totalReturn += j.result?.backtest?.total_return || 0;
    existing.totalSharpe += j.result?.backtest?.sharpe_ratio || 0;
    existing.totalWinRate += j.result?.backtest?.win_rate || 0;
    existing.signals += j.result?.signals_count || 0;
    strategyMap.set(strategy, existing);
  }

  // Most recent equity curve
  const latestWithCurve = completedJobs.find((j) => j.result?.backtest?.equity_curve?.length);
  const equityCurve = latestWithCurve?.result?.backtest?.equity_curve || [];

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (completedJobs.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-4">
        <BarChart3 className="h-12 w-12 text-zinc-700 mb-4" />
        <h2 className="text-lg font-semibold text-zinc-300">No performance data yet</h2>
        <p className="mt-2 text-sm text-zinc-500 text-center max-w-md">
          Run backtests from the Jobs page to see aggregated performance metrics, strategy comparisons, and equity curves here.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-2xl font-bold text-zinc-50">Performance</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Aggregated from {completedJobs.length} completed backtest{completedJobs.length !== 1 ? "s" : ""}
        </p>
      </motion.div>

      {/* Top Metrics */}
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Avg Win Rate" value={`${(avgWinRate * 100).toFixed(0)}%`} trend={avgWinRate > 0.5 ? "up" : "down"} />
        <MetricCard label="Avg Return" value={`${(avgReturn * 100).toFixed(1)}%`} trend={avgReturn > 0 ? "up" : "down"} />
        <MetricCard label="Avg Sharpe" value={avgSharpe.toFixed(2)} trend={avgSharpe > 0 ? "up" : "neutral"} />
        <MetricCard label="Total Signals" value={String(totalSignals)} trend="neutral" />
      </div>

      {/* Equity Curve */}
      {equityCurve.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="mb-8 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
            Latest Equity Curve — {latestWithCurve?.params?.ticker as string || ""}
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={equityCurve}>
              <defs>
                <linearGradient id="perfEqGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="date" tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "#27272a" }} />
              <YAxis tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "#27272a" }}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", borderRadius: "8px", color: "#f4f4f5" }}
                formatter={(value) => [`$${Number(value).toLocaleString()}`, "Equity"]} />
              <Area type="monotone" dataKey="equity" stroke="#8b5cf6" strokeWidth={2} fill="url(#perfEqGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>
      )}

      {/* Strategy Breakdown */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">Strategy Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="text-left px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Strategy</th>
                <th className="text-right px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Runs</th>
                <th className="text-right px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Signals</th>
                <th className="text-right px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Avg Return</th>
                <th className="text-right px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Avg Sharpe</th>
                <th className="text-right px-3 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Avg Win Rate</th>
              </tr>
            </thead>
            <tbody>
              {Array.from(strategyMap.entries()).map(([strategy, data]) => (
                <tr key={strategy} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                  <td className="px-3 py-3 font-mono text-zinc-200">{strategy}</td>
                  <td className="px-3 py-3 text-right text-zinc-400">{data.count}</td>
                  <td className="px-3 py-3 text-right text-zinc-400">{data.signals}</td>
                  <td className={cn("px-3 py-3 text-right font-mono",
                    data.totalReturn / data.count > 0 ? "text-emerald-400" : "text-red-400")}>
                    {((data.totalReturn / data.count) * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-zinc-300">
                    {(data.totalSharpe / data.count).toFixed(2)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-zinc-300">
                    {((data.totalWinRate / data.count) * 100).toFixed(0)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
