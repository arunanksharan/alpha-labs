"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence, LayoutGroup } from "framer-motion";
import {
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  ChevronDown,
  SlidersHorizontal,
  ArrowUpDown,
  X,
  FlaskConical,
  BarChart3,
  MessageSquare,
  ShieldCheck,
  Loader2,
  Inbox,
  Search,
  RefreshCw,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { cn, API_URL, href } from "@/lib/utils";


/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ApiSignal {
  ticker: string;
  strategy: string;
  signals_count: number;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
}

interface ApiSignalsResponse {
  signals: ApiSignal[];
  count: number;
}

interface AgentReasoning {
  agent: string;
  icon: "quant" | "tech" | "sentiment" | "risk" | "contrarian";
  summary: string;
}

interface BoardSignal {
  id: string;
  ticker: string;
  direction: "long" | "short" | "neutral";
  confidence: number;
  age_days: number;
  half_life: number;
  strategy: string;
  generated_date: string;
  agents: AgentReasoning[];
  potential_return: number;
  ic_curve: { horizon: number; ic: number }[];
  // Raw API data for expanded view
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  signals_count: number;
}

type SortField = "confidence" | "age_days" | "ticker" | "potential_return";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function generateICCurve(halfLife: number, sharpe: number): { horizon: number; ic: number }[] {
  const amplitude = Math.min(Math.abs(sharpe) * 0.06, 0.15);
  return Array.from({ length: 30 }, (_, i) => ({
    horizon: i + 1,
    ic:
      amplitude * Math.exp((-0.693 * (i + 1)) / halfLife) +
      (Math.random() - 0.5) * 0.02,
  }));
}

function deriveDirection(totalReturn: number): "long" | "short" | "neutral" {
  if (totalReturn > 0.005) return "long";
  if (totalReturn < -0.005) return "short";
  return "neutral";
}

function deriveConfidence(sharpe: number): number {
  return Math.min(Math.max(Math.abs(sharpe) / 5, 0), 1);
}

function deriveHalfLife(strategy: string): number {
  switch (strategy) {
    case "mean_reversion":
      return 12;
    case "momentum":
      return 20;
    case "sentiment":
      return 8;
    default:
      return 15;
  }
}

function deriveAgeDays(signalsCount: number): number {
  // More signals typically means longer running — approximate days
  return Math.max(1, Math.min(Math.round(signalsCount / 10), 30));
}

function buildAgentReasoning(signal: ApiSignal): AgentReasoning[] {
  const agents: AgentReasoning[] = [];
  const dir = signal.total_return > 0 ? "bullish" : "bearish";
  const sharpeStr = signal.sharpe_ratio.toFixed(2);
  const returnStr = (signal.total_return * 100).toFixed(2);
  const drawdownStr = (signal.max_drawdown * 100).toFixed(1);
  const winStr = (signal.win_rate * 100).toFixed(0);

  agents.push({
    agent: "The Quant",
    icon: "quant",
    summary: `Sharpe ratio: ${sharpeStr}. ${signal.signals_count} signals generated. ${signal.strategy === "mean_reversion" ? "Mean-reversion" : signal.strategy === "momentum" ? "Momentum" : "Strategy"} signal active on ${signal.ticker}.`,
  });

  agents.push({
    agent: "The Technician",
    icon: "tech",
    summary: `Total return: ${returnStr}%. Win rate: ${winStr}%. ${dir === "bullish" ? "Positive" : "Negative"} trend in backtest results.`,
  });

  agents.push({
    agent: "Sentiment Analyst",
    icon: "sentiment",
    summary: `Signal direction is ${dir}. Max drawdown: ${drawdownStr}%. ${Math.abs(signal.max_drawdown) < 0.05 ? "Risk contained." : "Elevated drawdown risk."}`,
  });

  agents.push({
    agent: "Risk Manager",
    icon: "risk",
    summary: `Max drawdown: ${drawdownStr}%. Sharpe: ${sharpeStr}. ${Math.abs(signal.sharpe_ratio) > 1 ? "Within risk budget." : "Below Sharpe threshold — caution advised."}`,
  });

  return agents;
}

function apiSignalToBoard(signal: ApiSignal, index: number): BoardSignal {
  const direction = deriveDirection(signal.total_return);
  const confidence = deriveConfidence(signal.sharpe_ratio);
  const halfLife = deriveHalfLife(signal.strategy);
  const ageDays = deriveAgeDays(signal.signals_count);

  return {
    id: `sig-${signal.ticker}-${signal.strategy}-${index}`,
    ticker: signal.ticker,
    direction,
    confidence,
    age_days: ageDays,
    half_life: halfLife,
    strategy: signal.strategy,
    generated_date: new Date().toISOString().split("T")[0],
    potential_return: signal.total_return,
    agents: buildAgentReasoning(signal),
    ic_curve: generateICCurve(halfLife, signal.sharpe_ratio),
    sharpe_ratio: signal.sharpe_ratio,
    max_drawdown: signal.max_drawdown,
    win_rate: signal.win_rate,
    signals_count: signal.signals_count,
  };
}

function getAgingStatus(ageDays: number, halfLife: number) {
  const ratio = ageDays / halfLife;
  if (ratio < 0.3) return { label: "Fresh", color: "emerald", dot: "bg-emerald-400" };
  if (ratio < 0.7) return { label: "Aging", color: "yellow", dot: "bg-yellow-400" };
  return { label: "Decaying", color: "red", dot: "bg-red-400" };
}

function getAgingBorder(ageDays: number, halfLife: number) {
  const ratio = ageDays / halfLife;
  if (ratio < 0.3) return "border-emerald-500/40 hover:border-emerald-500/60";
  if (ratio < 0.7) return "border-yellow-500/40 hover:border-yellow-500/60";
  return "border-red-500/40 hover:border-red-500/60";
}

const AGENT_ICONS: Record<string, typeof FlaskConical> = {
  quant: FlaskConical,
  tech: BarChart3,
  sentiment: MessageSquare,
  risk: ShieldCheck,
  contrarian: ArrowDownRight,
};

const AGENT_COLORS: Record<string, string> = {
  quant: "text-cyan-400",
  tech: "text-violet-400",
  sentiment: "text-amber-400",
  risk: "text-emerald-400",
  contrarian: "text-red-400",
};

const STRATEGY_LABELS: Record<string, string> = {
  mean_reversion: "Mean Reversion",
  momentum: "Momentum",
  sentiment: "Sentiment",
};

/* ------------------------------------------------------------------ */
/*  Mini IC Sparkline                                                  */
/* ------------------------------------------------------------------ */

function MiniICChart({
  data,
  halfLife,
}: {
  data: { horizon: number; ic: number }[];
  halfLife: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={120}>
      <LineChart data={data}>
        <XAxis
          dataKey="horizon"
          tick={{ fill: "#71717a", fontSize: 9 }}
          tickLine={false}
          axisLine={{ stroke: "#27272a" }}
        />
        <YAxis
          tick={{ fill: "#71717a", fontSize: 9 }}
          tickLine={false}
          axisLine={{ stroke: "#27272a" }}
          domain={[-0.02, 0.15]}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#18181b",
            border: "1px solid #3f3f46",
            borderRadius: "8px",
            color: "#f4f4f5",
            fontSize: 11,
          }}
          formatter={(value) => [Number(value).toFixed(4), "IC"]}
        />
        <ReferenceLine y={0} stroke="#3f3f46" strokeDasharray="3 3" />
        <ReferenceLine
          x={Math.round(halfLife)}
          stroke="#8b5cf6"
          strokeDasharray="5 5"
          label={{
            value: "\u00bd",
            fill: "#8b5cf6",
            position: "top",
            fontSize: 10,
          }}
        />
        <Line
          type="monotone"
          dataKey="ic"
          stroke="#06b6d4"
          strokeWidth={1.5}
          dot={false}
          activeDot={{ r: 3, fill: "#06b6d4" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ */
/*  Filter / Sort Dropdown                                             */
/* ------------------------------------------------------------------ */

function Dropdown({
  label,
  icon: Icon,
  open,
  onToggle,
  children,
}: {
  label: string;
  icon: typeof SlidersHorizontal;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="relative">
      <button
        type="button"
        onClick={onToggle}
        className={cn(
          "flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
          open
            ? "border-violet-500/50 bg-violet-500/10 text-violet-300"
            : "border-zinc-700 bg-zinc-800/50 text-zinc-400 hover:text-zinc-200"
        )}
      >
        <Icon className="h-3.5 w-3.5" />
        {label}
        <ChevronDown
          className={cn("h-3 w-3 transition-transform", open && "rotate-180")}
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 z-20 mt-1 w-56 rounded-lg border border-zinc-700 bg-zinc-900 p-3 shadow-xl"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function SignalsPage() {
  const router = useRouter();

  // Data state
  const [signals, setSignals] = useState<BoardSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // UI state
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const [sortOpen, setSortOpen] = useState(false);

  // Filters
  const [strategyFilter, setStrategyFilter] = useState<string>("all");
  const [directionFilter, setDirectionFilter] = useState<string>("all");
  const [confidenceMin, setConfidenceMin] = useState(0);

  // Sort
  const [sortBy, setSortBy] = useState<SortField>("confidence");
  const [sortAsc, setSortAsc] = useState(false);

  /* ---- Fetch signals ---- */
  const fetchSignals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/universe/signals`);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data: ApiSignalsResponse = await res.json();

      const boardSignals = data.signals.map((s, i) => apiSignalToBoard(s, i));
      setSignals(boardSignals);
    } catch (err) {
      console.error("Failed to fetch signals:", err);
      setError(
        err instanceof Error ? err.message : "Failed to fetch signals"
      );
      setSignals([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  /* ---- Dismiss handler ---- */
  const handleDismiss = useCallback((id: string) => {
    setDismissedIds((prev) => new Set(prev).add(id));
    setExpandedId(null);
  }, []);

  /* ---- Filter & Sort ---- */
  const availableSignals = useMemo(
    () => signals.filter((s) => !dismissedIds.has(s.id)),
    [signals, dismissedIds]
  );

  const filtered = useMemo(() => {
    let result = availableSignals.filter((s) => {
      if (strategyFilter !== "all" && s.strategy !== strategyFilter) return false;
      if (directionFilter !== "all" && s.direction !== directionFilter) return false;
      if (s.confidence < confidenceMin) return false;
      return true;
    });

    result.sort((a, b) => {
      let cmp = 0;
      switch (sortBy) {
        case "confidence":
          cmp = a.confidence - b.confidence;
          break;
        case "age_days":
          cmp = a.age_days - b.age_days;
          break;
        case "ticker":
          cmp = a.ticker.localeCompare(b.ticker);
          break;
        case "potential_return":
          cmp = Math.abs(a.potential_return) - Math.abs(b.potential_return);
          break;
      }
      return sortAsc ? cmp : -cmp;
    });

    return result;
  }, [availableSignals, strategyFilter, directionFilter, confidenceMin, sortBy, sortAsc]);

  const hasActiveFilters =
    strategyFilter !== "all" || directionFilter !== "all" || confidenceMin > 0;

  /* ---- Loading State ---- */
  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-zinc-50">Signal Board</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Live trading signals with decay tracking
          </p>
        </div>
        <div className="flex flex-col items-center justify-center py-24">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 className="h-8 w-8 text-violet-400" />
          </motion.div>
          <p className="mt-4 text-sm text-zinc-500">Loading signals from universe cache...</p>
        </div>
      </div>
    );
  }

  /* ---- Error State ---- */
  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-zinc-50">Signal Board</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Live trading signals with decay tracking
          </p>
        </div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24"
        >
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-6 py-5 text-center">
            <p className="text-sm font-medium text-red-400">
              Failed to load signals
            </p>
            <p className="mt-1 text-xs text-zinc-500">{error}</p>
            <button
              type="button"
              onClick={fetchSignals}
              className="mt-3 flex items-center gap-1.5 rounded-lg bg-zinc-800 px-3 py-1.5 text-xs text-zinc-300 transition-colors hover:bg-zinc-700 mx-auto"
            >
              <RefreshCw className="h-3 w-3" />
              Retry
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  /* ---- Empty State ---- */
  if (signals.length === 0) {
    return (
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-zinc-50">Signal Board</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Live trading signals with decay tracking
          </p>
        </div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24"
        >
          <Inbox className="h-12 w-12 text-zinc-600" />
          <p className="mt-4 text-sm font-medium text-zinc-400">
            No signals available
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            Add tickers and refresh your universe in Settings
          </p>
          <button
            type="button"
            onClick={() => router.push(href("/settings"))}
            className="mt-4 flex items-center gap-1.5 rounded-lg bg-violet-500/20 px-4 py-2 text-xs font-medium text-violet-300 transition-colors hover:bg-violet-500/30"
          >
            <Search className="h-3.5 w-3.5" />
            Go to Settings
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mb-8"
      >
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-zinc-50">Signal Board</h1>
            <p className="mt-1 text-sm text-zinc-500">
              {availableSignals.length} signal{availableSignals.length !== 1 ? "s" : ""} from universe cache
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={fetchSignals}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800/50 px-2.5 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              <RefreshCw className="h-3 w-3" />
              Refresh
            </button>
            {hasActiveFilters && (
              <motion.button
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                type="button"
                onClick={() => {
                  setStrategyFilter("all");
                  setDirectionFilter("all");
                  setConfidenceMin(0);
                }}
                className="flex items-center gap-1 rounded-lg border border-zinc-700 bg-zinc-800/50 px-2.5 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
              >
                <X className="h-3 w-3" />
                Clear
              </motion.button>
            )}
            <Dropdown
              label="Filter"
              icon={SlidersHorizontal}
              open={filterOpen}
              onToggle={() => {
                setFilterOpen(!filterOpen);
                setSortOpen(false);
              }}
            >
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                    Strategy
                  </label>
                  <select
                    value={strategyFilter}
                    onChange={(e) => setStrategyFilter(e.target.value)}
                    className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-xs text-zinc-300 outline-none focus:border-violet-500"
                  >
                    <option value="all">All Strategies</option>
                    <option value="mean_reversion">Mean Reversion</option>
                    <option value="momentum">Momentum</option>
                    <option value="sentiment">Sentiment</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                    Direction
                  </label>
                  <select
                    value={directionFilter}
                    onChange={(e) => setDirectionFilter(e.target.value)}
                    className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-xs text-zinc-300 outline-none focus:border-violet-500"
                  >
                    <option value="all">All Directions</option>
                    <option value="long">Long</option>
                    <option value="short">Short</option>
                    <option value="neutral">Neutral</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                    Min Confidence: {(confidenceMin * 100).toFixed(0)}%
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={confidenceMin}
                    onChange={(e) =>
                      setConfidenceMin(parseFloat(e.target.value))
                    }
                    className="w-full accent-violet-500"
                  />
                </div>
              </div>
            </Dropdown>
            <Dropdown
              label="Sort"
              icon={ArrowUpDown}
              open={sortOpen}
              onToggle={() => {
                setSortOpen(!sortOpen);
                setFilterOpen(false);
              }}
            >
              <div className="space-y-1">
                {(
                  [
                    ["confidence", "Confidence"],
                    ["age_days", "Age"],
                    ["ticker", "Ticker"],
                    ["potential_return", "Potential Return"],
                  ] as [SortField, string][]
                ).map(([field, label]) => (
                  <button
                    key={field}
                    type="button"
                    onClick={() => {
                      if (sortBy === field) {
                        setSortAsc(!sortAsc);
                      } else {
                        setSortBy(field);
                        setSortAsc(false);
                      }
                    }}
                    className={cn(
                      "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-xs transition-colors",
                      sortBy === field
                        ? "bg-violet-500/10 text-violet-300"
                        : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                    )}
                  >
                    {label}
                    {sortBy === field && (
                      <span className="text-[10px]">
                        {sortAsc ? "ASC" : "DESC"}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </Dropdown>
          </div>
        </div>
      </motion.div>

      {/* Signal Grid */}
      <LayoutGroup>
        <motion.div
          layout
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        >
          <AnimatePresence mode="popLayout">
            {filtered.map((signal, i) => {
              const aging = getAgingStatus(signal.age_days, signal.half_life);
              const isExpanded = expandedId === signal.id;
              const DirIcon =
                signal.direction === "long"
                  ? ArrowUpRight
                  : signal.direction === "short"
                    ? ArrowDownRight
                    : Minus;
              const dirColor =
                signal.direction === "long"
                  ? "text-emerald-400"
                  : signal.direction === "short"
                    ? "text-red-400"
                    : "text-zinc-400";
              const dirBadge =
                signal.direction === "long"
                  ? "bg-emerald-400/10 border-emerald-400/20 text-emerald-400"
                  : signal.direction === "short"
                    ? "bg-red-400/10 border-red-400/20 text-red-400"
                    : "bg-zinc-400/10 border-zinc-400/20 text-zinc-400";

              return (
                <motion.div
                  key={signal.id}
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                  className={cn(
                    "cursor-pointer rounded-xl border-2 bg-zinc-900/50 p-4 backdrop-blur-sm transition-shadow hover:shadow-lg",
                    getAgingBorder(signal.age_days, signal.half_life),
                    isExpanded && "col-span-full"
                  )}
                  onClick={() =>
                    setExpandedId(isExpanded ? null : signal.id)
                  }
                >
                  {/* Card Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold text-zinc-50">
                        {signal.ticker}
                      </span>
                      <span
                        className={cn(
                          "rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase",
                          dirBadge
                        )}
                      >
                        {signal.direction}
                      </span>
                    </div>
                    <DirIcon className={cn("h-5 w-5", dirColor)} />
                  </div>

                  {/* Confidence bar */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase text-zinc-500">
                        Confidence
                      </span>
                      <span className="text-xs font-semibold text-zinc-300">
                        {(signal.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 rounded-full bg-zinc-800">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{
                          width: `${signal.confidence * 100}%`,
                        }}
                        transition={{
                          duration: 0.6,
                          delay: i * 0.05 + 0.2,
                        }}
                        className="h-full rounded-full bg-violet-500"
                      />
                    </div>
                  </div>

                  {/* Status row */}
                  <div className="mt-3 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={cn("h-2 w-2 rounded-full", aging.dot)}
                      />
                      <span className="text-zinc-400">{aging.label}</span>
                    </div>
                    <span className="text-zinc-500">
                      {signal.age_days}d old
                    </span>
                  </div>

                  {/* Half-life & Strategy */}
                  <div className="mt-2 flex items-center justify-between text-xs text-zinc-500">
                    <span>HL: {signal.half_life}d</span>
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                      {STRATEGY_LABELS[signal.strategy] || signal.strategy}
                    </span>
                  </div>

                  {/* Expanded Detail */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                        className="overflow-hidden"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="mt-4 border-t border-zinc-800 pt-4">
                          <h3 className="text-sm font-semibold text-zinc-200">
                            {signal.ticker} —{" "}
                            {STRATEGY_LABELS[signal.strategy] || signal.strategy}{" "}
                            <span className="capitalize">
                              {signal.direction}
                            </span>
                          </h3>
                          <p className="mt-1 text-xs text-zinc-500">
                            Generated: {signal.generated_date}
                          </p>

                          {/* Key Metrics */}
                          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                            {[
                              {
                                label: "Sharpe",
                                value: signal.sharpe_ratio.toFixed(2),
                              },
                              {
                                label: "Return",
                                value: `${(signal.potential_return * 100).toFixed(2)}%`,
                              },
                              {
                                label: "Max DD",
                                value: `${(signal.max_drawdown * 100).toFixed(1)}%`,
                              },
                              {
                                label: "Win Rate",
                                value: `${(signal.win_rate * 100).toFixed(0)}%`,
                              },
                            ].map((metric) => (
                              <div
                                key={metric.label}
                                className="rounded-lg bg-zinc-800/50 px-3 py-2"
                              >
                                <p className="text-[10px] uppercase text-zinc-500">
                                  {metric.label}
                                </p>
                                <p className="text-sm font-semibold text-zinc-200">
                                  {metric.value}
                                </p>
                              </div>
                            ))}
                          </div>

                          {/* Agent Reasoning */}
                          <div className="mt-4 space-y-3">
                            <h4 className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                              Agent Reasoning
                            </h4>
                            {signal.agents.map((agent) => {
                              const AgentIcon =
                                AGENT_ICONS[agent.icon] || FlaskConical;
                              const agentColor =
                                AGENT_COLORS[agent.icon] || "text-zinc-400";
                              return (
                                <motion.div
                                  key={agent.agent}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ duration: 0.2 }}
                                  className="flex gap-3 rounded-lg bg-zinc-800/50 p-3"
                                >
                                  <AgentIcon
                                    className={cn(
                                      "mt-0.5 h-4 w-4 shrink-0",
                                      agentColor
                                    )}
                                  />
                                  <div>
                                    <p
                                      className={cn(
                                        "text-xs font-medium",
                                        agentColor
                                      )}
                                    >
                                      {agent.agent}
                                    </p>
                                    <p className="mt-0.5 text-xs text-zinc-400">
                                      {agent.summary}
                                    </p>
                                  </div>
                                </motion.div>
                              );
                            })}
                          </div>

                          {/* Signal Decay Chart */}
                          <div className="mt-4">
                            <h4 className="mb-2 text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                              Signal Decay
                            </h4>
                            <div className="rounded-lg bg-zinc-800/30 p-3">
                              <MiniICChart
                                data={signal.ic_curve}
                                halfLife={signal.half_life}
                              />
                            </div>
                            <div className="mt-2 flex items-center gap-4 text-xs text-zinc-500">
                              <span>
                                Half-life: {signal.half_life} days
                              </span>
                              <span>Age: {signal.age_days} days</span>
                              <span className="flex items-center gap-1">
                                <span
                                  className={cn(
                                    "h-1.5 w-1.5 rounded-full",
                                    aging.dot
                                  )}
                                />
                                {aging.label}
                              </span>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div className="mt-4 flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() =>
                                router.push(href(
                                  `/chat?q=Analyze ${signal.ticker}`
                                ))
                              }
                              className="rounded-lg bg-violet-500/20 px-4 py-2 text-xs font-medium text-violet-400 transition-colors hover:bg-violet-500/30"
                            >
                              Analyze
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                router.push(href(
                                  `/backtest?ticker=${signal.ticker}`
                                ))
                              }
                              className="rounded-lg bg-cyan-500/20 px-4 py-2 text-xs font-medium text-cyan-400 transition-colors hover:bg-cyan-500/30"
                            >
                              Run Backtest
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDismiss(signal.id)}
                              className="rounded-lg bg-red-500/20 px-4 py-2 text-xs font-medium text-red-400 transition-colors hover:bg-red-500/30"
                            >
                              Dismiss
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </motion.div>
      </LayoutGroup>

      {filtered.length === 0 && availableSignals.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-12 text-center"
        >
          <p className="text-sm text-zinc-500">
            No signals match your filters.
          </p>
          <button
            type="button"
            onClick={() => {
              setStrategyFilter("all");
              setDirectionFilter("all");
              setConfidenceMin(0);
            }}
            className="mt-2 text-xs text-violet-400 hover:text-violet-300"
          >
            Clear all filters
          </button>
        </motion.div>
      )}

      {filtered.length === 0 && availableSignals.length === 0 && signals.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-12 text-center"
        >
          <p className="text-sm text-zinc-500">
            All signals have been dismissed.
          </p>
          <button
            type="button"
            onClick={() => setDismissedIds(new Set())}
            className="mt-2 text-xs text-violet-400 hover:text-violet-300"
          >
            Restore all signals
          </button>
        </motion.div>
      )}
    </div>
  );
}
