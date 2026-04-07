"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  CheckCircle,
  XCircle,
  Search,
  TrendingUp,
  TrendingDown,
  Shield,
  ArrowRight,
  Sparkles,
} from "lucide-react";

/* ── Types ── */

interface AgentThought {
  name: string;
  thought: string;
}

interface HistoricalStats {
  win_rate: number;
  avg_return: number;
  hold_days: number;
  instances: number;
}

interface SignalEntry {
  ticker: string;
  direction: string;
  confidence: number;
  agents: AgentThought[];
  historical?: HistoricalStats;
}

interface WatchlistItem {
  ticker: string;
  status: string;
  note: string;
}

interface PortfolioHealth {
  pnl: string;
  sharpe: number;
  var: number;
  decayOk: boolean;
}

export interface MorningBriefProps {
  greeting?: string;
  signals: SignalEntry[];
  watchlist: WatchlistItem[];
  portfolioHealth: PortfolioHealth;
  whatILearned?: string;
  onApprove: (ticker: string) => void;
  onReject: (ticker: string) => void;
  onDigDeeper: (ticker: string) => void;
}

/* ── Agent icon/color map ── */

const AGENT_META: Record<string, { icon: string; color: string }> = {
  Quant: { icon: "\uD83D\uDD2C", color: "text-violet-400" },
  Technician: { icon: "\uD83D\uDCCA", color: "text-cyan-400" },
  Contrarian: { icon: "\uD83D\uDE08", color: "text-red-400" },
  Sentiment: { icon: "\uD83D\uDCAC", color: "text-amber-400" },
  Fundamentalist: { icon: "\uD83D\uDCCB", color: "text-emerald-400" },
  Macro: { icon: "\uD83C\uDF10", color: "text-blue-400" },
  Risk: { icon: "\uD83D\uDEE1\uFE0F", color: "text-orange-400" },
  Director: { icon: "\uD83D\uDC64", color: "text-zinc-200" },
};

function getAgentMeta(name: string) {
  // Match partial names (e.g. "The Quant" -> "Quant")
  for (const [key, meta] of Object.entries(AGENT_META)) {
    if (name.toLowerCase().includes(key.toLowerCase())) return meta;
  }
  return { icon: "\uD83E\uDD16", color: "text-zinc-400" };
}

/* ── Greeting helper ── */

function getTimeGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function getFormattedDate(): string {
  return new Date().toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
  });
}

/* ── Spring config ── */

const spring = { type: "spring" as const, stiffness: 400, damping: 30 };
const staggerContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};
const staggerChild = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: spring },
};

/* ── Status color for watchlist ── */

function statusColor(status: string): string {
  const s = status.toLowerCase();
  if (s.includes("strengthen") || s.includes("bullish")) return "bg-emerald-400";
  if (s.includes("weaken") || s.includes("short") || s.includes("bearish")) return "bg-red-400";
  if (s.includes("approach") || s.includes("spread") || s.includes("pair")) return "bg-amber-400";
  return "bg-zinc-500";
}

/* ── Component ── */

export function MorningBrief({
  greeting,
  signals,
  watchlist,
  portfolioHealth,
  whatILearned,
  onApprove,
  onReject,
  onDigDeeper,
}: MorningBriefProps) {
  const timeGreeting = useMemo(() => greeting || getTimeGreeting(), [greeting]);
  const dateStr = useMemo(() => getFormattedDate(), []);

  const pendingCount = signals.length;
  const topSignal = signals[0];

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* ── Greeting ── */}
      <motion.div variants={staggerChild}>
        <div className="flex items-baseline justify-between">
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-50">
            {timeGreeting}, <span className="text-violet-400">Parul</span>.
          </h1>
          <span className="text-sm text-zinc-500 tabular-nums" suppressHydrationWarning>
            {dateStr}
          </span>
        </div>
        <div className="mt-1.5 h-px bg-gradient-to-r from-violet-500/40 via-zinc-800 to-transparent" />
      </motion.div>

      {/* ── Status line ── */}
      <motion.div
        variants={staggerChild}
        className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm"
      >
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
          <span className="text-zinc-300">
            {pendingCount} new signal{pendingCount !== 1 ? "s" : ""}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full bg-amber-400" />
          <span className="text-zinc-300">
            {pendingCount} pending approval
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          {portfolioHealth.pnl.startsWith("+") ? (
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
          ) : (
            <span className="inline-block h-2 w-2 rounded-full bg-red-400" />
          )}
          <span className="text-zinc-300">
            Portfolio: {portfolioHealth.pnl} since last session
          </span>
        </span>
      </motion.div>

      {/* ── TOP CONVICTION ── */}
      <motion.div variants={staggerChild}>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
            Top Conviction
          </h2>
          <div className="flex-1 h-px bg-zinc-800" />
        </div>
      </motion.div>

      <AnimatePresence mode="popLayout">
        {signals.map((signal, i) => (
          <motion.div
            key={signal.ticker}
            variants={staggerChild}
            layout
            className={cn(
              "group relative rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-sm",
              "border-l-2 border-l-violet-500",
              "hover:border-zinc-700 transition-colors duration-200"
            )}
          >
            {/* Header row */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-xl font-bold text-zinc-50 tracking-tight">
                  {signal.ticker}
                </span>
                <span
                  className={cn(
                    "rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider border",
                    signal.direction.toUpperCase() === "LONG"
                      ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20"
                      : "text-red-400 bg-red-400/10 border-red-400/20"
                  )}
                >
                  {signal.direction}
                </span>
                <span className="text-sm text-zinc-400">
                  Confidence:{" "}
                  <span className="font-semibold text-zinc-200">
                    {(signal.confidence * 100).toFixed(0)}%
                  </span>
                </span>
              </div>
            </div>

            {/* Agent thoughts feed */}
            <div className="space-y-2 mb-4">
              {signal.agents.map((agent, j) => {
                const meta = getAgentMeta(agent.name);
                return (
                  <div key={j} className="flex items-start gap-2.5 text-sm">
                    <span className="shrink-0 mt-px text-base leading-none">
                      {meta.icon}
                    </span>
                    <span className={cn("shrink-0 font-medium", meta.color)}>
                      {agent.name}:
                    </span>
                    <span className="text-zinc-400">{agent.thought}</span>
                  </div>
                );
              })}
            </div>

            {/* Historical stats pills */}
            {signal.historical && (
              <div className="flex items-center gap-2 mb-5">
                <span className="text-xs text-zinc-500 mr-1">Historical:</span>
                <span className="inline-flex items-center rounded-full bg-zinc-800 px-2.5 py-1 text-[11px] font-medium text-zinc-300">
                  {(signal.historical.win_rate * 100).toFixed(0)}% win
                </span>
                <span className="inline-flex items-center rounded-full bg-zinc-800 px-2.5 py-1 text-[11px] font-medium text-zinc-300">
                  {signal.historical.avg_return > 0 ? "+" : ""}
                  {signal.historical.avg_return.toFixed(1)}% avg
                </span>
                <span className="inline-flex items-center rounded-full bg-zinc-800 px-2.5 py-1 text-[11px] font-medium text-zinc-300">
                  {signal.historical.hold_days}d hold
                </span>
                <span className="inline-flex items-center rounded-full bg-zinc-800 px-2.5 py-1 text-[11px] font-medium text-zinc-500">
                  {signal.historical.instances} samples
                </span>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex items-center gap-2.5">
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                transition={spring}
                onClick={() => onApprove(signal.ticker)}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium",
                  "bg-emerald-500/90 text-white",
                  "hover:bg-emerald-400 transition-colors"
                )}
              >
                <CheckCircle className="h-3.5 w-3.5" />
                Approve
                {signal.historical && (
                  <span className="ml-0.5 text-emerald-100/80">
                    $4,200
                  </span>
                )}
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                transition={spring}
                onClick={() => onDigDeeper(signal.ticker)}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium",
                  "border border-violet-500/30 text-violet-400",
                  "hover:bg-violet-500/10 transition-colors"
                )}
              >
                <Search className="h-3.5 w-3.5" />
                Dig Deeper
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                transition={spring}
                onClick={() => onReject(signal.ticker)}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium",
                  "border border-red-500/20 text-red-400",
                  "hover:bg-red-500/10 transition-colors"
                )}
              >
                <XCircle className="h-3.5 w-3.5" />
                Reject
              </motion.button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      {/* ── WATCHLIST ── */}
      {watchlist.length > 0 && (
        <motion.div variants={staggerChild}>
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Watchlist
            </h2>
            <div className="flex-1 h-px bg-zinc-800" />
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 divide-y divide-zinc-800/60 overflow-hidden">
            {watchlist.map((item, i) => (
              <motion.div
                key={item.ticker}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.06, ...spring }}
                className="flex items-center justify-between px-4 py-3 hover:bg-zinc-800/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      "h-2 w-2 rounded-full shrink-0",
                      statusColor(item.status)
                    )}
                  />
                  <span className="text-sm font-semibold text-zinc-200 w-24">
                    {item.ticker}
                  </span>
                  <span className="text-sm text-zinc-400">{item.status}</span>
                </div>
                <span className="text-xs text-zinc-500 font-mono">
                  {item.note}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── PORTFOLIO HEALTH ── */}
      <motion.div variants={staggerChild}>
        <div className="flex items-center gap-3 mb-3">
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
            Portfolio Health
          </h2>
          <div className="flex-1 h-px bg-zinc-800" />
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
          <div className="flex items-center gap-6 flex-wrap">
            <HealthPill
              label="P&L"
              value={portfolioHealth.pnl}
              positive={portfolioHealth.pnl.startsWith("+")}
            />
            <div className="h-5 w-px bg-zinc-800" />
            <HealthPill
              label="Sharpe"
              value={portfolioHealth.sharpe.toFixed(2)}
              positive={portfolioHealth.sharpe > 1}
            />
            <div className="h-5 w-px bg-zinc-800" />
            <HealthPill
              label="VaR"
              value={`${portfolioHealth.var.toFixed(1)}%`}
              positive={Math.abs(portfolioHealth.var) < 3}
            />
            <div className="h-5 w-px bg-zinc-800" />
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-zinc-500">Decay</span>
              {portfolioHealth.decayOk ? (
                <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <XCircle className="h-3.5 w-3.5 text-red-400" />
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── WHAT I LEARNED ── */}
      {whatILearned && (
        <motion.div variants={staggerChild}>
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
              What I Learned
            </h2>
            <div className="flex-1 h-px bg-zinc-800" />
          </div>
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/30 p-4">
            <div className="flex items-start gap-3">
              <Sparkles className="h-4 w-4 shrink-0 mt-0.5 text-violet-400/60" />
              <p className="text-sm italic text-zinc-400 leading-relaxed whitespace-pre-line">
                {whatILearned}
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}

/* ── Tiny sub-component ── */

function HealthPill({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-zinc-500">{label}</span>
      <span
        className={cn(
          "text-sm font-semibold tabular-nums",
          positive ? "text-emerald-400" : "text-red-400"
        )}
      >
        {value}
      </span>
    </div>
  );
}
