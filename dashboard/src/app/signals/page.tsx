"use client";

import { useState, useMemo } from "react";
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
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

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
}

type FilterField = "strategy" | "direction" | "confidence";
type SortField = "confidence" | "age_days" | "ticker" | "potential_return";

/* ------------------------------------------------------------------ */
/*  Demo data                                                          */
/* ------------------------------------------------------------------ */

function generateICCurve(halfLife: number): { horizon: number; ic: number }[] {
  return Array.from({ length: 30 }, (_, i) => ({
    horizon: i + 1,
    ic: 0.12 * Math.exp(-0.693 * (i + 1) / halfLife) + (Math.random() - 0.5) * 0.02,
  }));
}

const DEMO_SIGNALS: BoardSignal[] = [
  {
    id: "sig-1",
    ticker: "NVDA",
    direction: "long",
    confidence: 0.84,
    age_days: 2,
    half_life: 12,
    strategy: "mean_reversion",
    generated_date: "2024-03-15",
    potential_return: 0.047,
    agents: [
      { agent: "The Quant", icon: "quant", summary: "z-score = -2.1, past entry threshold. Mean-reversion signal triggered on 20d window." },
      { agent: "The Technician", icon: "tech", summary: "RSI = 28 (oversold), MACD bullish crossover confirmed. Support at $845." },
      { agent: "Sentiment Analyst", icon: "sentiment", summary: "Tone shift +0.19 over 48h. Earnings call transcript sentiment improving." },
      { agent: "Risk Manager", icon: "risk", summary: "Kelly sizing: $4,200. Portfolio VaR impact: +0.3%. Within risk budget." },
    ],
    ic_curve: generateICCurve(12),
  },
  {
    id: "sig-2",
    ticker: "MSFT",
    direction: "short",
    confidence: 0.65,
    age_days: 8,
    half_life: 15,
    strategy: "momentum",
    generated_date: "2024-03-09",
    potential_return: -0.023,
    agents: [
      { agent: "The Quant", icon: "quant", summary: "Momentum factor decaying. 60d rolling return turning negative." },
      { agent: "The Technician", icon: "tech", summary: "Death cross forming on daily. RSI = 62, divergence from price." },
      { agent: "Sentiment Analyst", icon: "sentiment", summary: "Neutral sentiment. No significant catalyst detected." },
      { agent: "Risk Manager", icon: "risk", summary: "Kelly sizing: $2,100. Moderate conviction. VaR impact: +0.2%." },
    ],
    ic_curve: generateICCurve(15),
  },
  {
    id: "sig-3",
    ticker: "AAPL",
    direction: "long",
    confidence: 0.71,
    age_days: 11,
    half_life: 12,
    strategy: "mean_reversion",
    generated_date: "2024-03-06",
    potential_return: 0.031,
    agents: [
      { agent: "The Quant", icon: "quant", summary: "z-score = -1.8. Approaching half-life but still within threshold." },
      { agent: "The Technician", icon: "tech", summary: "Double bottom at $168. Volume confirmation on second touch." },
      { agent: "Sentiment Analyst", icon: "sentiment", summary: "Mixed signals. Product launch cycle creating noise." },
      { agent: "Risk Manager", icon: "risk", summary: "Kelly sizing: $3,500. VaR impact: +0.25%. Aging signal, caution." },
    ],
    ic_curve: generateICCurve(12),
  },
  {
    id: "sig-4",
    ticker: "TSLA",
    direction: "short",
    confidence: 0.73,
    age_days: 1,
    half_life: 8,
    strategy: "sentiment",
    generated_date: "2024-03-16",
    potential_return: -0.038,
    agents: [
      { agent: "The Quant", icon: "quant", summary: "Implied vol skew extreme. Put/call ratio at 1.4." },
      { agent: "The Technician", icon: "tech", summary: "Breakdown below 50d MA. Volume spike on sell-off." },
      { agent: "Sentiment Analyst", icon: "sentiment", summary: "Negative tone shift -0.31. Social media sentiment cratering." },
      { agent: "Risk Manager", icon: "risk", summary: "Kelly sizing: $1,800. High vol environment. Tight stop recommended." },
    ],
    ic_curve: generateICCurve(8),
  },
  {
    id: "sig-5",
    ticker: "META",
    direction: "long",
    confidence: 0.58,
    age_days: 5,
    half_life: 20,
    strategy: "momentum",
    generated_date: "2024-03-12",
    potential_return: 0.019,
    agents: [
      { agent: "The Quant", icon: "quant", summary: "Momentum factor positive. 20d return in top quartile." },
      { agent: "The Technician", icon: "tech", summary: "Consolidation above breakout level. Volume tapering, waiting for catalyst." },
      { agent: "Sentiment Analyst", icon: "sentiment", summary: "Mild positive. Ad revenue expectations lifting." },
      { agent: "Risk Manager", icon: "risk", summary: "Kelly sizing: $2,800. Lower conviction, half position recommended." },
    ],
    ic_curve: generateICCurve(20),
  },
  {
    id: "sig-6",
    ticker: "GOOG",
    direction: "neutral",
    confidence: 0.45,
    age_days: 3,
    half_life: 10,
    strategy: "mean_reversion",
    generated_date: "2024-03-14",
    potential_return: 0.005,
    agents: [
      { agent: "The Quant", icon: "quant", summary: "z-score = -0.4. No clear signal. Within normal range." },
      { agent: "The Technician", icon: "tech", summary: "Ranging between $148-$155. No breakout or breakdown." },
      { agent: "Sentiment Analyst", icon: "sentiment", summary: "Neutral. Antitrust headlines creating uncertainty." },
      { agent: "Contrarian", icon: "contrarian", summary: "Consensus is neutral — no contrarian edge here." },
    ],
    ic_curve: generateICCurve(10),
  },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

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

function MiniICChart({ data, halfLife }: { data: { horizon: number; ic: number }[]; halfLife: number }) {
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
          label={{ value: "\u00bd", fill: "#8b5cf6", position: "top", fontSize: 10 }}
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
        <ChevronDown className={cn("h-3 w-3 transition-transform", open && "rotate-180")} />
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

  const filtered = useMemo(() => {
    let result = DEMO_SIGNALS.filter((s) => {
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
  }, [strategyFilter, directionFilter, confidenceMin, sortBy, sortAsc]);

  const hasActiveFilters = strategyFilter !== "all" || directionFilter !== "all" || confidenceMin > 0;

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
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
              Live trading signals with decay tracking
            </p>
          </div>
          <div className="flex items-center gap-2">
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
              onToggle={() => { setFilterOpen(!filterOpen); setSortOpen(false); }}
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
                    onChange={(e) => setConfidenceMin(parseFloat(e.target.value))}
                    className="w-full accent-violet-500"
                  />
                </div>
              </div>
            </Dropdown>
            <Dropdown
              label="Sort"
              icon={ArrowUpDown}
              open={sortOpen}
              onToggle={() => { setSortOpen(!sortOpen); setFilterOpen(false); }}
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
                      <span className="text-[10px]">{sortAsc ? "ASC" : "DESC"}</span>
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
                  onClick={() => setExpandedId(isExpanded ? null : signal.id)}
                >
                  {/* Card Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold text-zinc-50">{signal.ticker}</span>
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
                      <span className="text-[10px] uppercase text-zinc-500">Confidence</span>
                      <span className="text-xs font-semibold text-zinc-300">
                        {(signal.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 rounded-full bg-zinc-800">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${signal.confidence * 100}%` }}
                        transition={{ duration: 0.6, delay: i * 0.05 + 0.2 }}
                        className="h-full rounded-full bg-violet-500"
                      />
                    </div>
                  </div>

                  {/* Status row */}
                  <div className="mt-3 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <span className={cn("h-2 w-2 rounded-full", aging.dot)} />
                      <span className="text-zinc-400">{aging.label}</span>
                    </div>
                    <span className="text-zinc-500">{signal.age_days}d old</span>
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
                            {signal.ticker} — {STRATEGY_LABELS[signal.strategy]}{" "}
                            <span className="capitalize">{signal.direction}</span>
                          </h3>
                          <p className="mt-1 text-xs text-zinc-500">
                            Generated: {signal.generated_date}
                          </p>

                          {/* Agent Reasoning */}
                          <div className="mt-4 space-y-3">
                            <h4 className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                              Agent Reasoning
                            </h4>
                            {signal.agents.map((agent) => {
                              const AgentIcon = AGENT_ICONS[agent.icon] || FlaskConical;
                              const agentColor = AGENT_COLORS[agent.icon] || "text-zinc-400";
                              return (
                                <motion.div
                                  key={agent.agent}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ duration: 0.2 }}
                                  className="flex gap-3 rounded-lg bg-zinc-800/50 p-3"
                                >
                                  <AgentIcon className={cn("mt-0.5 h-4 w-4 shrink-0", agentColor)} />
                                  <div>
                                    <p className={cn("text-xs font-medium", agentColor)}>
                                      {agent.agent}
                                    </p>
                                    <p className="mt-0.5 text-xs text-zinc-400">{agent.summary}</p>
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
                              <MiniICChart data={signal.ic_curve} halfLife={signal.half_life} />
                            </div>
                            <div className="mt-2 flex items-center gap-4 text-xs text-zinc-500">
                              <span>Half-life: {signal.half_life} days</span>
                              <span>Age: {signal.age_days} days</span>
                              <span className="flex items-center gap-1">
                                <span className={cn("h-1.5 w-1.5 rounded-full", aging.dot)} />
                                {aging.label}
                              </span>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div className="mt-4 flex gap-2">
                            <button
                              type="button"
                              className="rounded-lg bg-emerald-500/20 px-4 py-2 text-xs font-medium text-emerald-400 transition-colors hover:bg-emerald-500/30"
                            >
                              Approve Trade
                            </button>
                            <button
                              type="button"
                              className="rounded-lg bg-yellow-500/20 px-4 py-2 text-xs font-medium text-yellow-400 transition-colors hover:bg-yellow-500/30"
                            >
                              Extend Watch
                            </button>
                            <button
                              type="button"
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

      {filtered.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-12 text-center"
        >
          <p className="text-sm text-zinc-500">No signals match your filters.</p>
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
    </div>
  );
}
