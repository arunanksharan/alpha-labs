"use client";

import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Legend,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import { cn } from "@/lib/utils";
import { MetricCard } from "@/components/MetricCard";

/* ------------------------------------------------------------------ */
/*  Demo data                                                          */
/* ------------------------------------------------------------------ */

const EQUITY_CURVE = Array.from({ length: 120 }, (_, i) => {
  const date = new Date(2024, 0, 1);
  date.setDate(date.getDate() + i);
  const base = 100000 + i * 180 + Math.sin(i / 15) * 2000;
  const noise = (Math.random() - 0.45) * 1500;
  return {
    date: date.toISOString().slice(0, 10),
    equity: Math.round(base + noise),
  };
});

const STRATEGY_BREAKDOWN = [
  {
    strategy: "Mean Reversion",
    signals: 12,
    winRate: 0.67,
    totalReturn: 0.031,
    sharpe: 1.8,
    color: "#8b5cf6",
  },
  {
    strategy: "Momentum",
    signals: 18,
    winRate: 0.5,
    totalReturn: 0.004,
    sharpe: 0.6,
    color: "#06b6d4",
  },
  {
    strategy: "Sentiment",
    signals: 8,
    winRate: 0.63,
    totalReturn: 0.012,
    sharpe: 1.1,
    color: "#f59e0b",
  },
  {
    strategy: "Contrarian",
    signals: 9,
    winRate: 0.44,
    totalReturn: -0.003,
    sharpe: 0.3,
    color: "#ef4444",
  },
];

const AGENT_ACCURACY = [
  { agent: "The Quant", calls: 35, correct: 22, accuracy: 0.63, color: "#06b6d4" },
  { agent: "The Technician", calls: 42, correct: 24, accuracy: 0.57, color: "#8b5cf6" },
  { agent: "Sentiment Analyst", calls: 28, correct: 18, accuracy: 0.64, color: "#f59e0b" },
  { agent: "The Contrarian", calls: 15, correct: 8, accuracy: 0.53, color: "#ef4444" },
  { agent: "Risk Manager", calls: 47, correct: 31, accuracy: 0.66, color: "#10b981" },
];

function generateDecayCurve(halfLife: number, color: string, key: string) {
  return Array.from({ length: 30 }, (_, i) => ({
    horizon: i + 1,
    [key]: parseFloat(
      (0.1 * Math.exp((-0.693 * (i + 1)) / halfLife) + (Math.random() - 0.5) * 0.015).toFixed(4)
    ),
  }));
}

const DECAY_STRATEGIES = [
  { key: "mean_reversion", label: "Mean Reversion", halfLife: 12, color: "#8b5cf6" },
  { key: "momentum", label: "Momentum", halfLife: 18, color: "#06b6d4" },
  { key: "sentiment", label: "Sentiment", halfLife: 8, color: "#f59e0b" },
];

// Merge decay curves into a single array
const DECAY_DATA = Array.from({ length: 30 }, (_, i) => {
  const point: Record<string, number> = { horizon: i + 1 };
  for (const s of DECAY_STRATEGIES) {
    point[s.key] = parseFloat(
      (0.1 * Math.exp((-0.693 * (i + 1)) / s.halfLife) + (Math.random() - 0.5) * 0.012).toFixed(4)
    );
  }
  return point;
});

const META_LEARNING = `Mean reversion is outperforming momentum this month with a 67% win rate vs 50%. The Quant and Sentiment Analyst agents show highest accuracy. Adjusting strategy weights: Mean Reversion 60% to 65%, Momentum 40% to 35%. Signal decay analysis shows momentum signals lose predictive power faster than expected -- consider shortening the holding period.`;

/* ------------------------------------------------------------------ */
/*  Animation helpers                                                  */
/* ------------------------------------------------------------------ */

const stagger = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function PerformancePage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mb-8"
      >
        <h1 className="text-2xl font-bold text-zinc-50">Performance</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Track signal accuracy and strategy returns
        </p>
      </motion.div>

      {/* Top Metrics */}
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <motion.div variants={fadeUp}>
          <MetricCard label="Win Rate" value="58%" trend="up" subtext="vs 54% last month" />
        </motion.div>
        <motion.div variants={fadeUp}>
          <MetricCard label="Net P&L" value="+2.3%" trend="up" subtext="+$4,620 realized" />
        </motion.div>
        <motion.div variants={fadeUp}>
          <MetricCard label="Sharpe Ratio" value="1.43" trend="up" subtext="Annualized" />
        </motion.div>
        <motion.div variants={fadeUp}>
          <MetricCard label="Total Signals" value="47" trend="neutral" subtext="12 active, 35 closed" />
        </motion.div>
      </motion.div>

      {/* Equity Curve */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="mb-8 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
      >
        <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
          Equity Curve
        </h3>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={EQUITY_CURVE}>
            <defs>
              <linearGradient id="perfEquityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#71717a", fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: "#27272a" }}
              interval={19}
            />
            <YAxis
              tick={{ fill: "#71717a", fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: "#27272a" }}
              tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#18181b",
                border: "1px solid #3f3f46",
                borderRadius: "8px",
                color: "#f4f4f5",
              }}
              formatter={(value) => [`$${Number(value).toLocaleString()}`, "Equity"]}
            />
            <Area
              type="monotone"
              dataKey="equity"
              stroke="#8b5cf6"
              strokeWidth={2}
              fill="url(#perfEquityGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </motion.div>

      {/* Strategy Breakdown */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="mb-8 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
      >
        <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
          Strategy Breakdown
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-[10px] font-medium uppercase tracking-wider text-zinc-500">
                <th className="pb-3 pr-4">Strategy</th>
                <th className="pb-3 pr-4 text-right">Signals</th>
                <th className="pb-3 pr-4 text-right">Win Rate</th>
                <th className="pb-3 pr-4 text-right">Return</th>
                <th className="pb-3 pr-4 text-right">Sharpe</th>
                <th className="pb-3 min-w-[120px]">Performance</th>
              </tr>
            </thead>
            <tbody>
              {STRATEGY_BREAKDOWN.map((s, i) => (
                <motion.tr
                  key={s.strategy}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.3 + i * 0.06 }}
                  className="border-b border-zinc-800/50"
                >
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: s.color }}
                      />
                      <span className="font-medium text-zinc-200">{s.strategy}</span>
                    </div>
                  </td>
                  <td className="py-3 pr-4 text-right text-zinc-400">{s.signals}</td>
                  <td className="py-3 pr-4 text-right text-zinc-400">
                    {(s.winRate * 100).toFixed(0)}%
                  </td>
                  <td
                    className={cn(
                      "py-3 pr-4 text-right font-medium",
                      s.totalReturn >= 0 ? "text-emerald-400" : "text-red-400"
                    )}
                  >
                    {s.totalReturn >= 0 ? "+" : ""}
                    {(s.totalReturn * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 pr-4 text-right text-zinc-400">{s.sharpe.toFixed(1)}</td>
                  <td className="py-3">
                    <div className="h-2 rounded-full bg-zinc-800">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{
                          width: `${Math.max(0, Math.min(100, ((s.totalReturn + 0.01) / 0.04) * 100))}%`,
                        }}
                        transition={{ duration: 0.6, delay: 0.4 + i * 0.06 }}
                        className="h-full rounded-full"
                        style={{ backgroundColor: s.color }}
                      />
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Agent Accuracy */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="mb-8 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
      >
        <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
          Agent Accuracy
        </h3>
        <div className="space-y-3">
          {AGENT_ACCURACY.map((agent, i) => (
            <motion.div
              key={agent.agent}
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.35 + i * 0.06 }}
              className="flex items-center gap-4"
            >
              <div className="w-36 shrink-0">
                <p className="text-xs font-medium text-zinc-200">{agent.agent}</p>
                <p className="text-[10px] text-zinc-500">
                  {agent.correct}/{agent.calls} calls
                </p>
              </div>
              <div className="flex-1">
                <div className="h-3 rounded-full bg-zinc-800">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${agent.accuracy * 100}%` }}
                    transition={{ duration: 0.8, delay: 0.4 + i * 0.08 }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: agent.color }}
                  />
                </div>
              </div>
              <span className="w-12 text-right text-xs font-semibold text-zinc-300">
                {(agent.accuracy * 100).toFixed(0)}%
              </span>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Signal Decay Health */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
        className="mb-8 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
            Signal Decay Health
          </h3>
          <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
            All signals within half-life
          </span>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={DECAY_DATA}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis
              dataKey="horizon"
              tick={{ fill: "#71717a", fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: "#27272a" }}
              label={{
                value: "Forward Days",
                position: "insideBottom",
                fill: "#71717a",
                offset: -5,
              }}
            />
            <YAxis
              tick={{ fill: "#71717a", fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: "#27272a" }}
              label={{ value: "IC", angle: -90, position: "insideLeft", fill: "#71717a" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#18181b",
                border: "1px solid #3f3f46",
                borderRadius: "8px",
                color: "#f4f4f5",
              }}
              formatter={(value, name) => {
                const label =
                  DECAY_STRATEGIES.find((s) => s.key === name)?.label || String(name);
                return [Number(value).toFixed(4), label];
              }}
            />
            <ReferenceLine y={0} stroke="#3f3f46" strokeDasharray="3 3" />
            <Legend
              wrapperStyle={{ fontSize: 11, color: "#a1a1aa" }}
              formatter={(value: string) =>
                DECAY_STRATEGIES.find((s) => s.key === value)?.label || value
              }
            />
            {DECAY_STRATEGIES.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 3, fill: s.color }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </motion.div>

      {/* What I Learned */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.5 }}
        className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
      >
        <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-zinc-400">
          What I Learned
        </h3>
        <p className="text-sm italic leading-relaxed text-zinc-300">{META_LEARNING}</p>
      </motion.div>
    </div>
  );
}
