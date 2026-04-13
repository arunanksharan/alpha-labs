"use client";

import { useState, useCallback, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
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
import { Play, Loader2, AlertCircle, X, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { API_URL } from "@/lib/utils";
import { MetricCard } from "@/components/MetricCard";
import type { BacktestMetrics, EquityCurvePoint } from "@/types";

/* ---------- Placeholder data (drawdown + monthly only) ---------- */

function computeDrawdownFromEquity(
  equity: EquityCurvePoint[]
): { date: string; drawdown: number }[] {
  let peak = -Infinity;
  return equity.map((pt) => {
    if (pt.equity > peak) peak = pt.equity;
    const dd = ((pt.equity - peak) / peak) * 100;
    return { date: pt.date, drawdown: parseFloat(dd.toFixed(2)) };
  });
}

function generateMonthlyReturns(): { month: string; value: number }[] {
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  const years = [2023, 2024];
  const data: { month: string; value: number }[] = [];
  for (const year of years) {
    for (const month of months) {
      data.push({
        month: `${month} ${year}`,
        value: parseFloat(((Math.random() - 0.4) * 8).toFixed(2)),
      });
    }
  }
  return data;
}

const DEMO_MONTHLY = generateMonthlyReturns();

/* ---------- Job polling types ---------- */

interface JobStatus {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  progress_stage: string;
  progress_message: string;
  result: {
    backtest: BacktestMetrics & { equity_curve: EquityCurvePoint[] };
    signals_count: number;
  } | null;
  error: string | null;
}

/* ---------- Toast ---------- */

function Toast({
  message,
  onClose,
}: {
  message: string;
  onClose: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 40 }}
      className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-xl border border-red-800 bg-red-950/90 px-4 py-3 text-sm text-red-200 shadow-lg backdrop-blur-sm"
    >
      <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
      <span>{message}</span>
      <button onClick={onClose} className="ml-2 text-red-400 hover:text-red-200">
        <X className="h-3.5 w-3.5" />
      </button>
    </motion.div>
  );
}

/* ---------- Progress bar ---------- */

function JobProgressBar({
  progress,
  stage,
  message,
}: {
  progress: number;
  stage: string;
  message: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin text-violet-400" />
          <span className="text-sm font-medium text-zinc-200">
            {stage || "Initializing"}
          </span>
        </div>
        <span className="text-sm tabular-nums text-zinc-400">
          {Math.round(progress)}%
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-violet-600 to-violet-400"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>
      {message && (
        <p className="mt-2 text-xs text-zinc-500">{message}</p>
      )}
    </motion.div>
  );
}

/* ---------- Monthly returns heatmap ---------- */

function MonthlyReturnsHeatmap({
  data,
}: {
  data: { month: string; value: number }[];
}) {
  const maxAbs = Math.max(...data.map((d) => Math.abs(d.value)), 1);

  function cellColor(val: number): string {
    const intensity = Math.min(Math.abs(val) / maxAbs, 1);
    if (val > 0) {
      const alpha = (0.15 + intensity * 0.6).toFixed(2);
      return `rgba(52, 211, 153, ${alpha})`;
    }
    if (val < 0) {
      const alpha = (0.15 + intensity * 0.6).toFixed(2);
      return `rgba(248, 113, 113, ${alpha})`;
    }
    return "rgba(113, 113, 122, 0.15)";
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
    >
      <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
        Monthly Returns
      </h3>
      <div className="grid grid-cols-6 gap-1.5 sm:grid-cols-8 md:grid-cols-12">
        {data.map((d, i) => (
          <div
            key={i}
            className="group relative flex aspect-square items-center justify-center rounded-md text-[10px] font-medium transition-transform hover:scale-110"
            style={{ backgroundColor: cellColor(d.value) }}
          >
            <span
              className={cn(
                d.value > 0 ? "text-emerald-200" : d.value < 0 ? "text-red-200" : "text-zinc-400"
              )}
            >
              {d.value > 0 ? "+" : ""}
              {d.value}%
            </span>
            <div className="pointer-events-none absolute -top-8 left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded bg-zinc-800 px-2 py-1 text-[10px] text-zinc-300 shadow-lg group-hover:block">
              {d.month}
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

/* ---------- Page ---------- */

export default function BacktestPage() {
  return (
    <Suspense>
      <BacktestPageInner />
    </Suspense>
  );
}

function BacktestPageInner() {
  const searchParams = useSearchParams();

  // Form state
  const [ticker, setTicker] = useState("D05.SI");
  const [strategy, setStrategy] = useState("mean_reversion");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");

  // Config fields
  const [initialCapital, setInitialCapital] = useState("100000");
  const [commission, setCommission] = useState("0.001");
  const [slippage, setSlippage] = useState("0.0005");
  const [riskFreeRate, setRiskFreeRate] = useState("0.04");

  // Job state
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [jobStage, setJobStage] = useState("");
  const [jobMessage, setJobMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Results
  const [results, setResults] = useState<{
    metrics: BacktestMetrics;
    equity: EquityCurvePoint[];
    drawdown: { date: string; drawdown: number }[];
    monthly: { month: string; value: number }[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Accept ticker from query param
  useEffect(() => {
    const t = searchParams.get("ticker");
    if (t) setTicker(t);
  }, [searchParams]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  function getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  const pollJob = useCallback(
    (id: string) => {
      setPolling(true);
      setJobProgress(0);
      setJobStage("Queued");
      setJobMessage("Waiting for worker...");

      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_URL}/api/jobs/${id}`, {
            headers: getAuthHeaders(),
          });
          if (!res.ok) throw new Error(`Poll returned ${res.status}`);

          const data: JobStatus = await res.json();

          setJobProgress(data.progress ?? 0);
          setJobStage(data.progress_stage ?? "");
          setJobMessage(data.progress_message ?? "");

          if (data.status === "completed" && data.result) {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            setPolling(false);
            setJobId(null);

            const bt = data.result.backtest;
            const equity = bt.equity_curve ?? [];
            const drawdown = computeDrawdownFromEquity(equity);

            setResults({
              metrics: bt,
              equity,
              drawdown,
              monthly: DEMO_MONTHLY,
            });
          }

          if (data.status === "failed") {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            setPolling(false);
            setJobId(null);
            setError(data.error ?? "Job failed with no error message");
          }
        } catch {
          // Swallow transient network errors; keep polling
        }
      }, 2000);
    },
    []
  );

  const handleRun = useCallback(async () => {
    setSubmitting(true);
    setError(null);
    setResults(null);
    setJobId(null);

    try {
      const res = await fetch(`${API_URL}/api/jobs/submit`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          ticker,
          strategy,
          start_date: startDate,
          end_date: endDate,
          config: {
            initial_capital: parseFloat(initialCapital),
            commission: parseFloat(commission),
            slippage: parseFloat(slippage),
            risk_free_rate: parseFloat(riskFreeRate),
          },
        }),
      });

      if (!res.ok) throw new Error(`Submit returned ${res.status}`);

      const data = await res.json();
      setJobId(data.job_id);
      pollJob(data.job_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? `Failed to submit job: ${err.message}`
          : "Failed to submit backtest job"
      );
    } finally {
      setSubmitting(false);
    }
  }, [ticker, strategy, startDate, endDate, initialCapital, commission, slippage, riskFreeRate, pollJob]);

  const isRunning = submitting || polling;

  const inputClass =
    "w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500";

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-lg">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xl font-semibold text-zinc-50"
          >
            Backtest Runner
          </motion.h1>
          <p className="mt-1 text-sm text-zinc-500">
            Configure and execute strategy backtests with full analytics
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 sm:space-y-8 px-4 sm:px-6 py-6 sm:py-8">
        {/* Input Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
        >
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
            Configuration
          </h2>

          {/* Row 1: Ticker, Strategy, Start, End, Run */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {/* Ticker */}
            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                Ticker
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="AAPL"
                className={inputClass}
              />
            </div>

            {/* Strategy */}
            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                Strategy
              </label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className={inputClass}
              >
                <option value="mean_reversion">Mean Reversion</option>
                <option value="momentum">Momentum</option>
              </select>
            </div>

            {/* Start Date */}
            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className={cn(inputClass, "[color-scheme:dark]")}
              />
            </div>

            {/* End Date */}
            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className={cn(inputClass, "[color-scheme:dark]")}
              />
            </div>

            {/* Run Button */}
            <div className="flex items-end">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={handleRun}
                disabled={isRunning}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                  isRunning
                    ? "cursor-not-allowed bg-zinc-800 text-zinc-500"
                    : "bg-violet-500 text-white hover:bg-violet-400"
                )}
              >
                {isRunning ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {submitting ? "Submitting..." : polling ? "Running..." : "Run Backtest"}
              </motion.button>
            </div>
          </div>

          {/* Row 2: Per-request config */}
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                Initial Capital ($)
              </label>
              <input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(e.target.value)}
                min="1000"
                step="1000"
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                Commission (%)
              </label>
              <input
                type="number"
                value={commission}
                onChange={(e) => setCommission(e.target.value)}
                min="0"
                step="0.0001"
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                Slippage (%)
              </label>
              <input
                type="number"
                value={slippage}
                onChange={(e) => setSlippage(e.target.value)}
                min="0"
                step="0.0001"
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                Risk-Free Rate
              </label>
              <input
                type="number"
                value={riskFreeRate}
                onChange={(e) => setRiskFreeRate(e.target.value)}
                min="0"
                max="1"
                step="0.01"
                className={inputClass}
              />
            </div>
          </div>
        </motion.div>

        {/* Job progress */}
        {polling && jobId && (
          <JobProgressBar
            progress={jobProgress}
            stage={jobStage}
            message={jobMessage}
          />
        )}

        {/* Empty state */}
        {!results && !polling && !submitting && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-zinc-800 py-20"
          >
            <BarChart3 className="h-10 w-10 text-zinc-700" />
            <p className="text-sm text-zinc-500">
              Submit a backtest to see results
            </p>
          </motion.div>
        )}

        {/* Results */}
        <AnimatePresence>
          {results && !polling && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="space-y-6"
            >
              {/* Metrics row */}
              <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-6">
                <MetricCard
                  label="Total Return"
                  value={`${(results.metrics.total_return * 100).toFixed(1)}%`}
                  trend={results.metrics.total_return > 0 ? "up" : "down"}
                />
                <MetricCard
                  label="Ann. Return"
                  value={`${(results.metrics.annualized_return * 100).toFixed(1)}%`}
                  trend={results.metrics.annualized_return > 0 ? "up" : "down"}
                />
                <MetricCard
                  label="Sharpe Ratio"
                  value={results.metrics.sharpe_ratio.toFixed(2)}
                  trend={results.metrics.sharpe_ratio > 1 ? "up" : "neutral"}
                />
                <MetricCard
                  label="Sortino"
                  value={results.metrics.sortino_ratio.toFixed(2)}
                  trend="up"
                />
                <MetricCard
                  label="Max Drawdown"
                  value={`${(results.metrics.max_drawdown * 100).toFixed(1)}%`}
                  trend="down"
                />
                <MetricCard
                  label="Win Rate"
                  value={`${(results.metrics.win_rate * 100).toFixed(0)}%`}
                  trend={results.metrics.win_rate > 0.5 ? "up" : "down"}
                />
              </div>

              {/* Equity curve */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.1 }}
                className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
              >
                <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
                  Equity Curve
                </h3>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={results.equity}>
                    <defs>
                      <linearGradient
                        id="btEquityGrad"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="#8b5cf6"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="100%"
                          stopColor="#8b5cf6"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "#71717a", fontSize: 10 }}
                      tickLine={false}
                      axisLine={{ stroke: "#27272a" }}
                    />
                    <YAxis
                      tick={{ fill: "#71717a", fontSize: 10 }}
                      tickLine={false}
                      axisLine={{ stroke: "#27272a" }}
                      tickFormatter={(v: number) =>
                        `$${(v / 1000).toFixed(0)}k`
                      }
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#18181b",
                        border: "1px solid #3f3f46",
                        borderRadius: "8px",
                        color: "#f4f4f5",
                      }}
                      formatter={(value) => [
                        `$${Number(value).toLocaleString()}`,
                        "Equity",
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="#8b5cf6"
                      strokeWidth={2}
                      fill="url(#btEquityGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </motion.div>

              {/* Drawdown chart */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.2 }}
                className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
              >
                <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
                  Drawdown
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={results.drawdown}>
                    <defs>
                      <linearGradient
                        id="ddGrad"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="#ef4444"
                          stopOpacity={0}
                        />
                        <stop
                          offset="100%"
                          stopColor="#ef4444"
                          stopOpacity={0.4}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "#71717a", fontSize: 10 }}
                      tickLine={false}
                      axisLine={{ stroke: "#27272a" }}
                    />
                    <YAxis
                      tick={{ fill: "#71717a", fontSize: 10 }}
                      tickLine={false}
                      axisLine={{ stroke: "#27272a" }}
                      tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#18181b",
                        border: "1px solid #3f3f46",
                        borderRadius: "8px",
                        color: "#f4f4f5",
                      }}
                      formatter={(value) => [
                        `${Number(value).toFixed(2)}%`,
                        "Drawdown",
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="drawdown"
                      stroke="#ef4444"
                      strokeWidth={1.5}
                      fill="url(#ddGrad)"
                      baseValue={0}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </motion.div>

              {/* Monthly returns heatmap */}
              <MonthlyReturnsHeatmap data={results.monthly} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Error toast */}
      <AnimatePresence>
        {error && <Toast message={error} onClose={() => setError(null)} />}
      </AnimatePresence>
    </div>
  );
}
