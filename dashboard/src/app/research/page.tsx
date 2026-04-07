"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { Brain, TrendingUp, BarChart3, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

/* ---------- Sentiment analysis (local demo) ---------- */

const POSITIVE_WORDS = [
  "growth",
  "strong",
  "exceeded",
  "beat",
  "outperform",
  "increase",
  "positive",
  "momentum",
  "record",
  "robust",
  "accelerate",
  "expand",
  "profit",
  "revenue",
  "upgrade",
  "bullish",
  "upside",
  "optimistic",
  "improve",
  "gain",
  "confident",
  "opportunity",
  "innovative",
  "margin",
  "efficient",
];

const NEGATIVE_WORDS = [
  "decline",
  "weak",
  "miss",
  "risk",
  "headwind",
  "concern",
  "loss",
  "negative",
  "slowdown",
  "challenge",
  "uncertainty",
  "pressure",
  "decrease",
  "downturn",
  "bearish",
  "downside",
  "cautious",
  "deteriorate",
  "impair",
  "contraction",
  "volatility",
  "inflation",
  "recession",
  "layoff",
  "restructuring",
];

interface SentimentResult {
  score: number;
  magnitude: number;
  label: "bullish" | "bearish" | "neutral";
  positiveWords: string[];
  negativeWords: string[];
}

function analyzeSentiment(text: string): SentimentResult {
  const lower = text.toLowerCase();
  const words = lower.split(/\W+/);
  const found_positive = POSITIVE_WORDS.filter((w) => words.includes(w));
  const found_negative = NEGATIVE_WORDS.filter((w) => words.includes(w));
  const total = found_positive.length + found_negative.length || 1;
  const score = (found_positive.length - found_negative.length) / total;
  const magnitude = total / Math.max(words.length, 1);
  const label =
    score > 0.15 ? "bullish" : score < -0.15 ? "bearish" : "neutral";
  return {
    score: parseFloat(score.toFixed(3)),
    magnitude: parseFloat(magnitude.toFixed(4)),
    label,
    positiveWords: found_positive,
    negativeWords: found_negative,
  };
}

/* ---------- Signal decay synthetic data ---------- */

type SignalPreset = "technical" | "momentum" | "sentiment";

const DECAY_PARAMS: Record<
  SignalPreset,
  { label: string; halfLife: number; ic0: number; color: string }
> = {
  technical: {
    label: "Technical Signals",
    halfLife: 5,
    ic0: 0.12,
    color: "#8b5cf6",
  },
  momentum: {
    label: "Momentum Signals",
    halfLife: 15,
    ic0: 0.08,
    color: "#06b6d4",
  },
  sentiment: {
    label: "Sentiment Signals",
    halfLife: 25,
    ic0: 0.06,
    color: "#f59e0b",
  },
};

function generateDecayCurve(
  halfLife: number,
  ic0: number,
  horizons: number
): number[] {
  const lambda = Math.log(2) / halfLife;
  return Array.from({ length: horizons }, (_, i) => {
    const noise = (Math.random() - 0.5) * 0.004;
    return parseFloat((ic0 * Math.exp(-lambda * (i + 1)) + noise).toFixed(4));
  });
}

function buildChartData(presets: SignalPreset[]) {
  const horizons = 30;
  const curves: Record<string, number[]> = {};
  for (const key of presets) {
    const p = DECAY_PARAMS[key];
    curves[key] = generateDecayCurve(p.halfLife, p.ic0, horizons);
  }
  return Array.from({ length: horizons }, (_, i) => {
    const point: Record<string, number> = { horizon: i + 1 };
    for (const key of presets) {
      point[key] = curves[key][i];
    }
    return point;
  });
}

/* ---------- Page ---------- */

export default function ResearchPage() {
  /* Sentiment state */
  const [text, setText] = useState("");
  const [sentimentResult, setSentimentResult] =
    useState<SentimentResult | null>(null);

  /* Signal decay state */
  const [activePresets, setActivePresets] = useState<SignalPreset[]>([
    "technical",
    "momentum",
    "sentiment",
  ]);

  const chartData = useMemo(
    () => buildChartData(activePresets),
    [activePresets]
  );

  function handleAnalyze() {
    if (!text.trim()) return;
    setSentimentResult(analyzeSentiment(text));
  }

  function togglePreset(preset: SignalPreset) {
    setActivePresets((prev) =>
      prev.includes(preset)
        ? prev.filter((p) => p !== preset)
        : [...prev, preset]
    );
  }

  const labelColor = (label: string) => {
    if (label === "bullish") return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30";
    if (label === "bearish") return "text-red-400 bg-red-500/10 border-red-500/30";
    return "text-zinc-400 bg-zinc-500/10 border-zinc-500/30";
  };

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
            Research Tools
          </motion.h1>
          <p className="mt-1 text-sm text-zinc-500">
            Sentiment analysis and signal decay comparison
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* ----- Left: Sentiment Analysis ----- */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-4"
          >
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <div className="mb-4 flex items-center gap-2">
                <Brain className="h-4 w-4 text-violet-400" />
                <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
                  Sentiment Analysis
                </h2>
              </div>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={8}
                placeholder="Paste earnings call transcript, press release, or analyst note here..."
                className="w-full resize-none rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={handleAnalyze}
                className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-violet-500 px-4 py-2 text-sm font-medium text-white hover:bg-violet-400 transition-colors"
              >
                <Zap className="h-4 w-4" />
                Analyze Sentiment
              </motion.button>
            </div>

            {/* Results */}
            {sentimentResult && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4"
              >
                <h3 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
                  Result
                </h3>

                {/* Score row */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-center">
                    <p className="text-xs text-zinc-500">Score</p>
                    <p
                      className={cn(
                        "mt-1 text-xl font-semibold",
                        sentimentResult.score > 0
                          ? "text-emerald-400"
                          : sentimentResult.score < 0
                            ? "text-red-400"
                            : "text-zinc-400"
                      )}
                    >
                      {sentimentResult.score > 0 ? "+" : ""}
                      {sentimentResult.score}
                    </p>
                  </div>
                  <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-center">
                    <p className="text-xs text-zinc-500">Magnitude</p>
                    <p className="mt-1 text-xl font-semibold text-zinc-300">
                      {sentimentResult.magnitude}
                    </p>
                  </div>
                  <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-center">
                    <p className="text-xs text-zinc-500">Label</p>
                    <span
                      className={cn(
                        "mt-1 inline-block rounded-full border px-3 py-0.5 text-xs font-medium capitalize",
                        labelColor(sentimentResult.label)
                      )}
                    >
                      {sentimentResult.label}
                    </span>
                  </div>
                </div>

                {/* Key phrases */}
                {sentimentResult.positiveWords.length > 0 && (
                  <div>
                    <p className="mb-1.5 text-xs text-zinc-500">
                      Positive phrases
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {sentimentResult.positiveWords.map((w) => (
                        <span
                          key={w}
                          className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs text-emerald-300"
                        >
                          {w}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {sentimentResult.negativeWords.length > 0 && (
                  <div>
                    <p className="mb-1.5 text-xs text-zinc-500">
                      Negative phrases
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {sentimentResult.negativeWords.map((w) => (
                        <span
                          key={w}
                          className="rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-0.5 text-xs text-red-300"
                        >
                          {w}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </motion.div>

          {/* ----- Right: Signal Decay Comparison ----- */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="space-y-4"
          >
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
              <div className="mb-4 flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-cyan-400" />
                <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
                  Signal Decay Comparison
                </h2>
              </div>

              {/* Preset buttons */}
              <div className="mb-4 flex flex-wrap gap-2">
                {(
                  Object.entries(DECAY_PARAMS) as [
                    SignalPreset,
                    (typeof DECAY_PARAMS)[SignalPreset],
                  ][]
                ).map(([key, params]) => (
                  <button
                    key={key}
                    onClick={() => togglePreset(key)}
                    className={cn(
                      "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors border",
                      activePresets.includes(key)
                        ? "border-violet-500/50 bg-violet-500/20 text-violet-300"
                        : "border-zinc-700 bg-zinc-800 text-zinc-500 hover:text-zinc-300"
                    )}
                  >
                    {params.label}
                  </button>
                ))}
              </div>

              {/* Chart */}
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis
                    dataKey="horizon"
                    tick={{ fill: "#71717a", fontSize: 10 }}
                    tickLine={false}
                    axisLine={{ stroke: "#27272a" }}
                    label={{
                      value: "Horizon (days)",
                      position: "insideBottom",
                      offset: -4,
                      fill: "#52525b",
                      fontSize: 10,
                    }}
                  />
                  <YAxis
                    tick={{ fill: "#71717a", fontSize: 10 }}
                    tickLine={false}
                    axisLine={{ stroke: "#27272a" }}
                    label={{
                      value: "IC",
                      angle: -90,
                      position: "insideLeft",
                      fill: "#52525b",
                      fontSize: 10,
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#18181b",
                      border: "1px solid #3f3f46",
                      borderRadius: "8px",
                      color: "#f4f4f5",
                    }}
                    formatter={(value, name) => [
                      Number(value).toFixed(4),
                      DECAY_PARAMS[String(name) as SignalPreset]?.label ?? String(name),
                    ]}
                  />
                  <Legend
                    formatter={(value: string) =>
                      DECAY_PARAMS[value as SignalPreset]?.label ?? value
                    }
                    wrapperStyle={{ fontSize: 11, color: "#a1a1aa" }}
                  />
                  {activePresets.map((key) => (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      stroke={DECAY_PARAMS[key].color}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 3 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Half-life info cards */}
            <div className="grid grid-cols-3 gap-3">
              {(
                Object.entries(DECAY_PARAMS) as [
                  SignalPreset,
                  (typeof DECAY_PARAMS)[SignalPreset],
                ][]
              ).map(([key, params]) => (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className={cn(
                    "rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-center transition-opacity",
                    !activePresets.includes(key) && "opacity-40"
                  )}
                >
                  <div
                    className="mx-auto mb-2 h-2 w-2 rounded-full"
                    style={{ backgroundColor: params.color }}
                  />
                  <p className="text-xs text-zinc-500">{params.label}</p>
                  <p className="mt-1 text-lg font-semibold text-zinc-50">
                    {params.halfLife}d
                  </p>
                  <p className="text-[10px] text-zinc-600">half-life</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
