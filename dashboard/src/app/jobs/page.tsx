"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import {
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Plus,
  Ban,
  RotateCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useJobs, type BacktestConfigInput, type JobData } from "@/hooks/useJobs";

const STATUS_CONFIG: Record<string, { color: string; bg: string; icon: typeof Clock; label: string }> = {
  pending: { color: "text-zinc-400", bg: "bg-zinc-500/15", icon: Clock, label: "Pending" },
  running: { color: "text-violet-400", bg: "bg-violet-500/15", icon: Loader2, label: "Running" },
  completed: { color: "text-emerald-400", bg: "bg-emerald-500/15", icon: CheckCircle2, label: "Completed" },
  failed: { color: "text-red-400", bg: "bg-red-500/15", icon: XCircle, label: "Failed" },
  cancelled: { color: "text-zinc-500", bg: "bg-zinc-500/15", icon: Ban, label: "Cancelled" },
};

export default function JobsPage() {
  const { jobs, submitJob, loading } = useJobs();
  const [showForm, setShowForm] = useState(false);
  const [expandedJob, setExpandedJob] = useState<string | null>(null);

  // Form state
  const [ticker, setTicker] = useState("D05.SI");
  const [strategy, setStrategy] = useState("mean_reversion");
  const [startDate, setStartDate] = useState("2022-01-01");
  const [endDate, setEndDate] = useState("2026-04-13");
  const [capital, setCapital] = useState("100000");
  const [commission, setCommission] = useState("0.001");
  const [slippage, setSlippage] = useState("0.0005");
  const [riskFreeRate, setRiskFreeRate] = useState("0.05");

  const handleSubmit = useCallback(async () => {
    const config: BacktestConfigInput = {
      initial_capital: parseFloat(capital),
      commission: parseFloat(commission),
      slippage: parseFloat(slippage),
      risk_free_rate: parseFloat(riskFreeRate),
    };
    await submitJob(ticker, strategy, startDate, endDate, config);
    setShowForm(false);
  }, [ticker, strategy, startDate, endDate, capital, commission, slippage, riskFreeRate, submitJob]);

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-lg">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-zinc-50">Jobs</h1>
              <p className="mt-1 text-sm text-zinc-500">Submit and track research & backtest jobs</p>
            </div>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              onClick={() => setShowForm(!showForm)}
              className="flex items-center gap-2 rounded-lg bg-violet-500 px-4 py-2 text-sm font-medium text-white hover:bg-violet-400">
              <Plus className="h-4 w-4" /> New Backtest
            </motion.button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 py-6 space-y-4">
        {/* New backtest form */}
        <AnimatePresence>
          {showForm && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
              className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
              <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">New Backtest Job</h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">Ticker</label>
                  <input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 font-mono focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">Strategy</label>
                  <select value={strategy} onChange={(e) => setStrategy(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 focus:border-violet-500 focus:outline-none">
                    <option value="mean_reversion">Mean Reversion</option>
                    <option value="momentum">Momentum</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">Start Date</label>
                  <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 focus:border-violet-500 focus:outline-none [color-scheme:dark]" />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">End Date</label>
                  <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 focus:border-violet-500 focus:outline-none [color-scheme:dark]" />
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">Initial Capital</label>
                  <input type="number" value={capital} onChange={(e) => setCapital(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 font-mono focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">Commission</label>
                  <input type="number" step="0.0001" value={commission} onChange={(e) => setCommission(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 font-mono focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">Slippage</label>
                  <input type="number" step="0.0001" value={slippage} onChange={(e) => setSlippage(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 font-mono focus:border-violet-500 focus:outline-none" />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-zinc-500">Risk-Free Rate</label>
                  <input type="number" step="0.01" value={riskFreeRate} onChange={(e) => setRiskFreeRate(e.target.value)}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 font-mono focus:border-violet-500 focus:outline-none" />
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button onClick={() => setShowForm(false)}
                  className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-400 hover:bg-zinc-800">
                  Cancel
                </button>
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                  onClick={handleSubmit} disabled={loading}
                  className="flex items-center gap-2 rounded-lg bg-violet-500 px-4 py-2 text-sm font-medium text-white hover:bg-violet-400">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  Submit Job
                </motion.button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Jobs list */}
        {jobs.length === 0 ? (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-12 text-center">
            <Clock className="mx-auto h-8 w-8 text-zinc-600 mb-3" />
            <p className="text-sm text-zinc-500">No jobs yet. Click &quot;New Backtest&quot; to submit one.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {jobs.map((job) => (
              <JobRow key={job.id} job={job} expanded={expandedJob === job.id}
                onToggle={() => setExpandedJob(expandedJob === job.id ? null : job.id)} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function JobRow({ job, expanded, onToggle }: { job: JobData; expanded: boolean; onToggle: () => void }) {
  const config = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
  const Icon = config.icon;
  const params = job.params || {};
  const duration = job.started_at && job.completed_at
    ? `${((new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()) / 1000).toFixed(1)}s`
    : job.started_at ? "running..." : "—";

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 overflow-hidden">
      <button type="button" onClick={onToggle}
        className="flex w-full items-center gap-4 px-4 py-3 text-left hover:bg-zinc-800/30 transition-colors">
        <Icon className={cn("h-4 w-4 shrink-0", config.color, job.status === "running" && "animate-spin")} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-medium text-zinc-200">{params.ticker as string || "—"}</span>
            <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-violet-300">{params.strategy as string || "—"}</span>
            <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", config.bg, config.color)}>
              {config.label}
            </span>
          </div>
          {job.status === "running" && (
            <div className="mt-1.5 flex items-center gap-2">
              <div className="flex-1 h-1 rounded-full bg-zinc-800 overflow-hidden">
                <motion.div className="h-full bg-violet-500 rounded-full"
                  initial={{ width: 0 }} animate={{ width: `${job.progress * 100}%` }}
                  transition={{ duration: 0.3 }} />
              </div>
              <span className="text-[10px] text-zinc-500 shrink-0">{Math.round(job.progress * 100)}%</span>
              <span className="text-[10px] text-zinc-600 truncate max-w-[200px]">{job.progress_message}</span>
            </div>
          )}
        </div>
        <span className="text-xs text-zinc-600 tabular-nums shrink-0">{duration}</span>
        {expanded ? <ChevronUp className="h-3.5 w-3.5 text-zinc-500" /> : <ChevronDown className="h-3.5 w-3.5 text-zinc-500" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }}
            className="overflow-hidden border-t border-zinc-800">
            <div className="px-4 py-3 text-xs space-y-2">
              <div className="flex gap-6">
                <span className="text-zinc-500">Job ID: <span className="font-mono text-zinc-400">{job.id}</span></span>
                <span className="text-zinc-500">Created: <span className="text-zinc-400">{new Date(job.created_at).toLocaleString()}</span></span>
              </div>
              {job.error && (
                <div className="rounded bg-red-950/30 border border-red-800/30 px-3 py-2 text-red-300">{job.error}</div>
              )}
              {job.result && (() => {
                const bt = (job.result as Record<string, unknown>).backtest as Record<string, unknown> | undefined;
                if (!bt) return <span className="text-zinc-500">No backtest results</span>;
                const equityCurve = (bt.equity_curve as { date: string; equity: number }[]) || [];

                return (
                  <div className="space-y-3">
                    {/* Metrics grid */}
                    <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                      {[
                        ["Return", `${((bt.total_return as number) * 100).toFixed(1)}%`],
                        ["Sharpe", (bt.sharpe_ratio as number)?.toFixed(2)],
                        ["Sortino", (bt.sortino_ratio as number)?.toFixed(2)],
                        ["Max DD", `${((bt.max_drawdown as number) * 100).toFixed(1)}%`],
                        ["Win Rate", `${((bt.win_rate as number) * 100).toFixed(0)}%`],
                        ["Signals", String((job.result as Record<string, unknown>).signals_count ?? "—")],
                      ].map(([label, val]) => (
                        <div key={String(label)} className="rounded bg-zinc-800/50 px-2 py-1.5 text-center">
                          <div className="text-[10px] text-zinc-600">{String(label)}</div>
                          <div className="font-mono text-zinc-300">{String(val ?? "—")}</div>
                        </div>
                      ))}
                    </div>

                    {/* Equity curve */}
                    {equityCurve.length > 5 && (
                      <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-3">
                        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Equity Curve</p>
                        <ResponsiveContainer width="100%" height={160}>
                          <AreaChart data={equityCurve}>
                            <defs>
                              <linearGradient id={`jobEq-${job.id}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.3} />
                                <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" />
                            <XAxis dataKey="date" tick={{ fill: "#52525b", fontSize: 9 }} tickLine={false} axisLine={false} />
                            <YAxis tick={{ fill: "#52525b", fontSize: 9 }} tickLine={false} axisLine={false}
                              tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
                            <Tooltip contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", borderRadius: "6px", fontSize: 11, color: "#f4f4f5" }}
                              formatter={(value) => [`$${Number(value).toLocaleString()}`, "Equity"]} />
                            <Area type="monotone" dataKey="equity" stroke="#8b5cf6" strokeWidth={1.5} fill={`url(#jobEq-${job.id})`} />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    )}

                    {/* Re-run button */}
                    <button
                      onClick={(e) => { e.stopPropagation(); window.location.href = `/backtest?ticker=${encodeURIComponent(String(job.params.ticker))}`; }}
                      className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-[10px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-violet-400 transition-colors">
                      <RotateCw className="h-3 w-3" /> Re-run with different params
                    </button>
                  </div>
                );
              })()}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
