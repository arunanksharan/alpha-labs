"use client";

import {
  useState,
  useCallback,
  useEffect,
  useRef,
  useMemo,
  Suspense,
} from "react";
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
  Legend,
} from "recharts";
import {
  Play,
  Loader2,
  AlertCircle,
  X,
  BarChart3,
  Pin,
  Trash2,
  Printer,
  ChevronDown,
  ArrowUpDown,
  SlidersHorizontal,
} from "lucide-react";
import { cn, API_URL } from "@/lib/utils";
import { MetricCard } from "@/components/MetricCard";
import type { BacktestMetrics, EquityCurvePoint } from "@/types";

/* ================================================================
   Types
   ================================================================ */

interface Trade {
  date: string;
  ticker: string;
  side: "buy" | "sell";
  price: number;
  quantity: number;
  pnl: number;
}

interface MonthlyReturn {
  year: number;
  month: number;
  return: number;
}

interface BacktestResult {
  equity_curve: EquityCurvePoint[];
  trades?: Trade[];
  monthly_returns?: MonthlyReturn[];
}

interface JobResult {
  backtest: BacktestMetrics & BacktestResult;
  signals_count: number;
}

interface JobStatus {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  progress_stage: string;
  progress_message: string;
  result: JobResult | null;
  error: string | null;
}

interface SliderValues {
  entry_threshold: number;
  lookback_window: number;
  commission_bps: number;
  slippage_bps: number;
}

interface RunResult {
  metrics: BacktestMetrics;
  equity: EquityCurvePoint[];
  drawdown: { date: string; drawdown: number }[];
  monthly: { month: string; value: number }[];
  trades: Trade[];
}

type SortKey = "date" | "pnl";
type SortDir = "asc" | "desc";

/* ================================================================
   Helpers
   ================================================================ */

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

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function formatMonthlyReturns(
  raw?: MonthlyReturn[]
): { month: string; value: number }[] {
  if (!raw || raw.length === 0) return [];
  return raw.map((r) => ({
    month: `${MONTH_NAMES[r.month - 1]} ${r.year}`,
    value: parseFloat((r.return * 100).toFixed(2)),
  }));
}

function mergeEquityCurves(
  a: EquityCurvePoint[],
  b: EquityCurvePoint[]
): { date: string; equityA: number | null; equityB: number | null }[] {
  const map = new Map<
    string,
    { equityA: number | null; equityB: number | null }
  >();
  for (const pt of a) {
    map.set(pt.date, { equityA: pt.equity, equityB: null });
  }
  for (const pt of b) {
    const existing = map.get(pt.date);
    if (existing) {
      existing.equityB = pt.equity;
    } else {
      map.set(pt.date, { equityA: null, equityB: pt.equity });
    }
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, vals]) => ({ date, ...vals }));
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (typeof window !== "undefined") {
    const token =
      localStorage.getItem("access_token") ||
      localStorage.getItem("token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/* ================================================================
   Sub-components
   ================================================================ */

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
      <button
        onClick={onClose}
        className="ml-2 text-red-400 hover:text-red-200"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </motion.div>
  );
}

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
  if (data.length === 0) {
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
        <p className="text-sm text-zinc-600">
          No monthly returns data available.
        </p>
      </motion.div>
    );
  }

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
                d.value > 0
                  ? "text-emerald-200"
                  : d.value < 0
                    ? "text-red-200"
                    : "text-zinc-400"
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

/* ---------- Parameter Sensitivity Slider ---------- */

function ParamSlider({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-zinc-400">{label}</label>
        <span className="rounded-md bg-zinc-800 px-2 py-0.5 text-xs tabular-nums font-semibold text-violet-300">
          {step < 1 ? value.toFixed(1) : value}
          {unit && <span className="ml-0.5 text-zinc-500">{unit}</span>}
        </span>
      </div>
      <div className="relative">
        <div className="pointer-events-none absolute top-1/2 h-1.5 w-full -translate-y-1/2 overflow-hidden rounded-full bg-zinc-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-600 to-violet-400"
            style={{ width: `${pct}%` }}
          />
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="relative z-10 h-1.5 w-full cursor-pointer appearance-none bg-transparent
            [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:appearance-none [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-violet-400 [&::-moz-range-thumb]:bg-zinc-950 [&::-moz-range-thumb]:shadow-md
            [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-violet-400 [&::-webkit-slider-thumb]:bg-zinc-950 [&::-webkit-slider-thumb]:shadow-md"
        />
      </div>
      <div className="flex justify-between text-[10px] text-zinc-600">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

/* ---------- Trades Table ---------- */

function TradesTable({ trades }: { trades: Trade[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "pnl" ? "desc" : "asc");
    }
  };

  const sorted = useMemo(() => {
    const copy = [...trades];
    copy.sort((a, b) => {
      if (sortKey === "date") {
        return sortDir === "asc"
          ? a.date.localeCompare(b.date)
          : b.date.localeCompare(a.date);
      }
      return sortDir === "asc" ? a.pnl - b.pnl : b.pnl - a.pnl;
    });
    return copy;
  }, [trades, sortKey, sortDir]);

  if (trades.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.25 }}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
    >
      <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
        Trades
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-xs uppercase tracking-wider text-zinc-500">
              <th className="pb-3 pr-4">
                <button
                  onClick={() => toggleSort("date")}
                  className="flex items-center gap-1 hover:text-zinc-300"
                >
                  Date
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
              <th className="pb-3 pr-4">Ticker</th>
              <th className="pb-3 pr-4">Side</th>
              <th className="pb-3 pr-4 text-right">Price</th>
              <th className="pb-3 pr-4 text-right">Qty</th>
              <th className="pb-3 text-right">
                <button
                  onClick={() => toggleSort("pnl")}
                  className="ml-auto flex items-center gap-1 hover:text-zinc-300"
                >
                  P&L
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((t, i) => (
              <motion.tr
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.02 }}
                className="border-b border-zinc-800/50 last:border-0"
              >
                <td className="py-2.5 pr-4 tabular-nums text-zinc-300">
                  {t.date}
                </td>
                <td className="py-2.5 pr-4 font-mono text-zinc-200">
                  {t.ticker}
                </td>
                <td className="py-2.5 pr-4">
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                      t.side === "buy"
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "bg-red-500/15 text-red-400"
                    )}
                  >
                    {t.side}
                  </span>
                </td>
                <td className="py-2.5 pr-4 text-right tabular-nums text-zinc-300">
                  ${t.price.toFixed(2)}
                </td>
                <td className="py-2.5 pr-4 text-right tabular-nums text-zinc-300">
                  {t.quantity}
                </td>
                <td
                  className={cn(
                    "py-2.5 text-right tabular-nums font-medium",
                    t.pnl > 0
                      ? "text-emerald-400"
                      : t.pnl < 0
                        ? "text-red-400"
                        : "text-zinc-400"
                  )}
                >
                  {t.pnl > 0 ? "+" : ""}
                  ${t.pnl.toFixed(2)}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

/* ---------- Comparison Metrics Table ---------- */

function ComparisonTable({
  runA,
  runB,
}: {
  runA: RunResult;
  runB: RunResult;
}) {
  const rows: { label: string; a: string; b: string; better: "a" | "b" | "same" }[] = [
    {
      label: "Total Return",
      a: `${(runA.metrics.total_return * 100).toFixed(1)}%`,
      b: `${(runB.metrics.total_return * 100).toFixed(1)}%`,
      better:
        runA.metrics.total_return > runB.metrics.total_return
          ? "a"
          : runA.metrics.total_return < runB.metrics.total_return
            ? "b"
            : "same",
    },
    {
      label: "Sharpe Ratio",
      a: runA.metrics.sharpe_ratio.toFixed(2),
      b: runB.metrics.sharpe_ratio.toFixed(2),
      better:
        runA.metrics.sharpe_ratio > runB.metrics.sharpe_ratio
          ? "a"
          : runA.metrics.sharpe_ratio < runB.metrics.sharpe_ratio
            ? "b"
            : "same",
    },
    {
      label: "Sortino",
      a: runA.metrics.sortino_ratio.toFixed(2),
      b: runB.metrics.sortino_ratio.toFixed(2),
      better:
        runA.metrics.sortino_ratio > runB.metrics.sortino_ratio
          ? "a"
          : runA.metrics.sortino_ratio < runB.metrics.sortino_ratio
            ? "b"
            : "same",
    },
    {
      label: "Max Drawdown",
      a: `${(runA.metrics.max_drawdown * 100).toFixed(1)}%`,
      b: `${(runB.metrics.max_drawdown * 100).toFixed(1)}%`,
      better:
        Math.abs(runA.metrics.max_drawdown) < Math.abs(runB.metrics.max_drawdown)
          ? "a"
          : Math.abs(runA.metrics.max_drawdown) > Math.abs(runB.metrics.max_drawdown)
            ? "b"
            : "same",
    },
    {
      label: "Win Rate",
      a: `${(runA.metrics.win_rate * 100).toFixed(0)}%`,
      b: `${(runB.metrics.win_rate * 100).toFixed(0)}%`,
      better:
        runA.metrics.win_rate > runB.metrics.win_rate
          ? "a"
          : runA.metrics.win_rate < runB.metrics.win_rate
            ? "b"
            : "same",
    },
    {
      label: "VaR 95%",
      a: runA.metrics.var_95 != null ? `${(runA.metrics.var_95 * 100).toFixed(2)}%` : "N/A",
      b: runB.metrics.var_95 != null ? `${(runB.metrics.var_95 * 100).toFixed(2)}%` : "N/A",
      better: "same",
    },
    {
      label: "CVaR 95%",
      a: runA.metrics.cvar_95 != null ? `${(runA.metrics.cvar_95 * 100).toFixed(2)}%` : "N/A",
      b: runB.metrics.cvar_95 != null ? `${(runB.metrics.cvar_95 * 100).toFixed(2)}%` : "N/A",
      better: "same",
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
    >
      <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
        Run A vs Run B
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-xs uppercase tracking-wider text-zinc-500">
              <th className="pb-3 text-left">Metric</th>
              <th className="pb-3 text-right">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-violet-500" />
                  Run A
                </span>
              </th>
              <th className="pb-3 text-right">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-cyan-500" />
                  Run B
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.label}
                className="border-b border-zinc-800/50 last:border-0"
              >
                <td className="py-2.5 text-zinc-400">{row.label}</td>
                <td
                  className={cn(
                    "py-2.5 text-right tabular-nums font-medium",
                    row.better === "a"
                      ? "text-emerald-400"
                      : "text-zinc-300"
                  )}
                >
                  {row.a}
                </td>
                <td
                  className={cn(
                    "py-2.5 text-right tabular-nums font-medium",
                    row.better === "b"
                      ? "text-emerald-400"
                      : "text-zinc-300"
                  )}
                >
                  {row.b}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

/* ================================================================
   Main Page
   ================================================================ */

export default function BacktestPage() {
  return (
    <Suspense>
      <BacktestPageInner />
    </Suspense>
  );
}

function BacktestPageInner() {
  const searchParams = useSearchParams();

  /* ---------- Form state ---------- */
  const [ticker, setTicker] = useState("D05.SI");
  const [strategy, setStrategy] = useState("mean_reversion");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");

  /* ---------- Advanced config (collapsible) ---------- */
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [initialCapital, setInitialCapital] = useState("100000");
  const [configCommission, setConfigCommission] = useState("0.001");
  const [configSlippage, setConfigSlippage] = useState("0.0005");
  const [riskFreeRate, setRiskFreeRate] = useState("0.04");

  /* ---------- Parameter sensitivity sliders ---------- */
  const [sliderValues, setSliderValues] = useState<SliderValues>({
    entry_threshold: 2.0,
    lookback_window: 20,
    commission_bps: 10,
    slippage_bps: 5,
  });
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  /* ---------- Job state ---------- */
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [jobStage, setJobStage] = useState("");
  const [jobMessage, setJobMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ---------- Results ---------- */
  const [results, setResults] = useState<RunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  /* ---------- Comparison mode ---------- */
  const [pinnedRun, setPinnedRun] = useState<RunResult | null>(null);

  /* ---------- Accept ticker from query param ---------- */
  useEffect(() => {
    const t = searchParams.get("ticker");
    if (t) setTicker(t);
  }, [searchParams]);

  /* ---------- Cleanup polling on unmount ---------- */
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  /* ---------- Build the job submission body ---------- */
  const buildJobBody = useCallback(() => {
    return {
      ticker,
      strategy,
      start_date: startDate,
      end_date: endDate,
      config: {
        initial_capital: parseFloat(initialCapital),
        commission: sliderValues.commission_bps / 10000,
        slippage: sliderValues.slippage_bps / 10000,
        risk_free_rate: parseFloat(riskFreeRate),
        strategy_params: {
          entry_threshold: sliderValues.entry_threshold,
          window: sliderValues.lookback_window,
        },
      },
    };
  }, [
    ticker,
    strategy,
    startDate,
    endDate,
    initialCapital,
    riskFreeRate,
    sliderValues,
  ]);

  /* ---------- Process completed job into RunResult ---------- */
  const processJobResult = useCallback((data: JobStatus): RunResult => {
    const bt = data.result!.backtest;
    const equity = bt.equity_curve ?? [];
    const drawdown = computeDrawdownFromEquity(equity);
    const monthly = formatMonthlyReturns(bt.monthly_returns);
    const trades = bt.trades ?? [];

    return {
      metrics: bt,
      equity,
      drawdown,
      monthly,
      trades,
    };
  }, []);

  /* ---------- Poll a job until completion ---------- */
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
            setResults(processJobResult(data));
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
    [processJobResult]
  );

  /* ---------- Submit a job ---------- */
  const submitJob = useCallback(
    async (body: ReturnType<typeof buildJobBody>) => {
      setSubmitting(true);
      setError(null);
      // Don't clear results if we have a pinned run (comparison mode)
      if (!pinnedRun) setResults(null);

      try {
        const res = await fetch(`${API_URL}/api/jobs/submit`, {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify(body),
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
    },
    [pollJob, pinnedRun]
  );

  /* ---------- Run backtest (button click) ---------- */
  const handleRun = useCallback(async () => {
    setResults(null);
    setJobId(null);
    await submitJob(buildJobBody());
  }, [submitJob, buildJobBody]);

  /* ---------- Slider change with debounce ---------- */
  const handleSliderChange = useCallback(
    (key: keyof SliderValues, value: number) => {
      setSliderValues((prev) => ({ ...prev, [key]: value }));
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        // Build a fresh body with the updated slider value
        const updated = { ...sliderValues, [key]: value };
        const body = {
          ticker,
          strategy,
          start_date: startDate,
          end_date: endDate,
          config: {
            initial_capital: parseFloat(initialCapital),
            commission: updated.commission_bps / 10000,
            slippage: updated.slippage_bps / 10000,
            risk_free_rate: parseFloat(riskFreeRate),
            strategy_params: {
              entry_threshold: updated.entry_threshold,
              window: updated.lookback_window,
            },
          },
        };
        submitJob(body);
      }, 500);
    },
    [
      sliderValues,
      ticker,
      strategy,
      startDate,
      endDate,
      initialCapital,
      riskFreeRate,
      submitJob,
    ]
  );

  /* ---------- Pin / clear comparison ---------- */
  const handlePin = useCallback(() => {
    if (results) setPinnedRun(results);
  }, [results]);

  const handleClearComparison = useCallback(() => {
    setPinnedRun(null);
  }, []);

  /* ---------- Export report ---------- */
  const handleExport = useCallback(() => {
    window.print();
  }, []);

  /* ---------- Merged equity data for comparison chart ---------- */
  const comparisonEquityData = useMemo(() => {
    if (!pinnedRun || !results) return null;
    return mergeEquityCurves(pinnedRun.equity, results.equity);
  }, [pinnedRun, results]);

  const isRunning = submitting || polling;

  const dateInputClass =
    "w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 [color-scheme:dark]";

  const inputClass =
    "w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500";

  /* ---------- Which results to show ---------- */
  // Only show results if metrics are fully populated
  const displayResults = results?.metrics?.sharpe_ratio != null ? results : null;
  const isComparing = pinnedRun !== null && displayResults !== null;

  return (
    <div className="min-h-screen bg-zinc-950 print:bg-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-lg print:hidden">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
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
            {displayResults && (
              <div className="flex items-center gap-2">
                {!pinnedRun && (
                  <motion.button
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handlePin}
                    className="flex items-center gap-2 rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-2 text-sm font-medium text-violet-300 transition-colors hover:bg-violet-500/20"
                  >
                    <Pin className="h-3.5 w-3.5" />
                    Pin Current Result
                  </motion.button>
                )}
                {pinnedRun && (
                  <motion.button
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleClearComparison}
                    className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm font-medium text-red-300 transition-colors hover:bg-red-500/20"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Clear Comparison
                  </motion.button>
                )}
                <motion.button
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleExport}
                  className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-zinc-700"
                >
                  <Printer className="h-3.5 w-3.5" />
                  Export Report
                </motion.button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Print-only header */}
      <div className="hidden print:block print:px-8 print:py-6">
        <h1 className="text-2xl font-bold text-black">Backtest Report</h1>
        <p className="mt-1 text-sm text-gray-600">
          {ticker} / {strategy} / {startDate} - {endDate}
        </p>
        <p className="text-xs text-gray-400">
          Generated {new Date().toLocaleDateString()}
        </p>
      </div>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:space-y-8 sm:px-6 sm:py-8">
        {/* ============ Input Form ============ */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 print:hidden"
        >
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
            Configuration
          </h2>

          {/* Row 1: Ticker, Strategy, Start, End, Run */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
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

            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className={dateInputClass}
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs text-zinc-500">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className={dateInputClass}
              />
            </div>

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
                {submitting
                  ? "Submitting..."
                  : polling
                    ? "Running..."
                    : "Run Backtest"}
              </motion.button>
            </div>
          </div>

          {/* Advanced Config (collapsible) */}
          <div className="mt-4">
            <button
              onClick={() => setShowAdvanced((v) => !v)}
              className="flex items-center gap-2 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-300"
            >
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 transition-transform duration-200",
                  showAdvanced && "rotate-180"
                )}
              />
              Advanced Config
            </button>
            <AnimatePresence>
              {showAdvanced && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
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
                        value={configCommission}
                        onChange={(e) => setConfigCommission(e.target.value)}
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
                        value={configSlippage}
                        onChange={(e) => setConfigSlippage(e.target.value)}
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
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* ============ Parameter Sensitivity Sliders ============ */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 print:hidden"
        >
          <div className="mb-5 flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 text-violet-400" />
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
              Parameter Sensitivity
            </h2>
            <span className="ml-auto text-[10px] text-zinc-600">
              Adjusting auto-submits a new run
            </span>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <ParamSlider
              label="Entry Threshold"
              value={sliderValues.entry_threshold}
              min={0.5}
              max={4.0}
              step={0.1}
              unit="σ"
              onChange={(v) => handleSliderChange("entry_threshold", v)}
            />
            <ParamSlider
              label="Lookback Window"
              value={sliderValues.lookback_window}
              min={10}
              max={100}
              step={5}
              unit="d"
              onChange={(v) => handleSliderChange("lookback_window", v)}
            />
            <ParamSlider
              label="Commission"
              value={sliderValues.commission_bps}
              min={0}
              max={30}
              step={1}
              unit="bps"
              onChange={(v) => handleSliderChange("commission_bps", v)}
            />
            <ParamSlider
              label="Slippage"
              value={sliderValues.slippage_bps}
              min={0}
              max={20}
              step={1}
              unit="bps"
              onChange={(v) => handleSliderChange("slippage_bps", v)}
            />
          </div>
        </motion.div>

        {/* ============ Job progress ============ */}
        {polling && jobId && (
          <JobProgressBar
            progress={jobProgress}
            stage={jobStage}
            message={jobMessage}
          />
        )}

        {/* ============ Empty state ============ */}
        {!displayResults && !polling && !submitting && (
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

        {/* ============ Results ============ */}
        <AnimatePresence>
          {displayResults && !polling && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="space-y-6"
            >
              {/* Comparison mode indicator */}
              {isComparing && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-3 rounded-lg border border-violet-500/20 bg-violet-500/5 px-4 py-2.5"
                >
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-violet-500" />
                    <span className="text-sm font-medium text-violet-300">
                      Run A (Pinned)
                    </span>
                  </div>
                  <span className="text-zinc-600">vs</span>
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-cyan-500" />
                    <span className="text-sm font-medium text-cyan-300">
                      Run B (Current)
                    </span>
                  </div>
                </motion.div>
              )}

              {/* Metrics row */}
              <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4 lg:grid-cols-8">
                <MetricCard
                  label="Total Return"
                  value={`${(displayResults.metrics.total_return * 100).toFixed(1)}%`}
                  trend={
                    displayResults.metrics.total_return > 0 ? "up" : "down"
                  }
                />
                <MetricCard
                  label="Ann. Return"
                  value={`${(displayResults.metrics.annualized_return * 100).toFixed(1)}%`}
                  trend={
                    displayResults.metrics.annualized_return > 0
                      ? "up"
                      : "down"
                  }
                />
                <MetricCard
                  label="Sharpe Ratio"
                  value={displayResults.metrics.sharpe_ratio.toFixed(2)}
                  trend={
                    displayResults.metrics.sharpe_ratio > 1 ? "up" : "neutral"
                  }
                />
                <MetricCard
                  label="Sortino"
                  value={displayResults.metrics.sortino_ratio.toFixed(2)}
                  trend={
                    displayResults.metrics.sortino_ratio > 1 ? "up" : "neutral"
                  }
                />
                <MetricCard
                  label="Max Drawdown"
                  value={`${(displayResults.metrics.max_drawdown * 100).toFixed(1)}%`}
                  trend="down"
                />
                <MetricCard
                  label="Win Rate"
                  value={`${(displayResults.metrics.win_rate * 100).toFixed(0)}%`}
                  trend={
                    displayResults.metrics.win_rate > 0.5 ? "up" : "down"
                  }
                />
                <MetricCard
                  label="VaR 95%"
                  value={
                    displayResults.metrics.var_95 != null
                      ? `${(displayResults.metrics.var_95 * 100).toFixed(2)}%`
                      : "N/A"
                  }
                  trend="down"
                />
                <MetricCard
                  label="CVaR 95%"
                  value={
                    displayResults.metrics.cvar_95 != null
                      ? `${(displayResults.metrics.cvar_95 * 100).toFixed(2)}%`
                      : "N/A"
                  }
                  trend="down"
                />
              </div>

              {/* Comparison table (when comparing) */}
              {isComparing && pinnedRun && (
                <ComparisonTable runA={pinnedRun} runB={displayResults} />
              )}

              {/* Equity curve */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.1 }}
                className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
              >
                <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
                  Equity Curve
                  {isComparing && (
                    <span className="ml-2 text-[10px] font-normal normal-case text-zinc-600">
                      (overlay comparison)
                    </span>
                  )}
                </h3>
                <ResponsiveContainer width="100%" height={320}>
                  {isComparing && comparisonEquityData ? (
                    <AreaChart data={comparisonEquityData}>
                      <defs>
                        <linearGradient
                          id="gradA"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="0%"
                            stopColor="#8b5cf6"
                            stopOpacity={0.2}
                          />
                          <stop
                            offset="100%"
                            stopColor="#8b5cf6"
                            stopOpacity={0}
                          />
                        </linearGradient>
                        <linearGradient
                          id="gradB"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="0%"
                            stopColor="#06b6d4"
                            stopOpacity={0.2}
                          />
                          <stop
                            offset="100%"
                            stopColor="#06b6d4"
                            stopOpacity={0}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#27272a"
                      />
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
                        formatter={(value, name) => {
                          if (value == null) return ["--", String(name)];
                          const label =
                            name === "equityA" ? "Run A" : "Run B";
                          return [
                            `$${Number(value).toLocaleString()}`,
                            label,
                          ];
                        }}
                      />
                      <Legend
                        formatter={(value: string) =>
                          value === "equityA" ? "Run A (Pinned)" : "Run B (Current)"
                        }
                        wrapperStyle={{ fontSize: 11, color: "#a1a1aa" }}
                      />
                      <Area
                        type="monotone"
                        dataKey="equityA"
                        stroke="#8b5cf6"
                        strokeWidth={2}
                        fill="url(#gradA)"
                        connectNulls
                      />
                      <Area
                        type="monotone"
                        dataKey="equityB"
                        stroke="#06b6d4"
                        strokeWidth={2}
                        fill="url(#gradB)"
                        connectNulls
                      />
                    </AreaChart>
                  ) : (
                    <AreaChart data={displayResults.equity}>
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
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#27272a"
                      />
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
                  )}
                </ResponsiveContainer>
              </motion.div>

              {/* Trades table */}
              {displayResults.trades.length > 0 && (
                <TradesTable trades={displayResults.trades} />
              )}

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
                  <AreaChart data={displayResults.drawdown}>
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
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#27272a"
                    />
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
              <MonthlyReturnsHeatmap data={displayResults.monthly} />
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
