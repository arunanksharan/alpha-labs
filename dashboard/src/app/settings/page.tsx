"use client";

import { useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Globe,
  ToggleLeft,
  ToggleRight,
  Download,
  Settings,
  Info,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_URL } from "@/lib/utils";

/* ---------- Strategy definitions ---------- */

const STRATEGIES = [
  {
    name: "Mean Reversion",
    key: "mean_reversion",
    params: [
      { label: "Lookback window", value: "20 days" },
      { label: "Z-score threshold", value: "2.0" },
      { label: "Exit threshold", value: "0.5" },
    ],
  },
  {
    name: "Momentum",
    key: "momentum",
    params: [
      { label: "Lookback window", value: "60 days" },
      { label: "Entry percentile", value: "80th" },
      { label: "Holding period", value: "10 days" },
    ],
  },
];

const TICKERS = ["AAPL", "MSFT", "NVDA", "GOOG", "TSLA", "META", "AMZN", "JPM", "V", "UNH"];

/* ---------- Page ---------- */

export default function SettingsPage() {
  const [demoMode, setDemoMode] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState<
    "checking" | "connected" | "disconnected"
  >("checking");
  const [prefetching, setPrefetching] = useState(false);
  const [prefetchResult, setPrefetchResult] = useState<string | null>(null);

  /* Check API connection on mount */
  useEffect(() => {
    async function check() {
      try {
        const res = await fetch(`${API_URL}/health`, {
          signal: AbortSignal.timeout(3000),
        });
        setConnectionStatus(res.ok ? "connected" : "disconnected");
        if (res.ok) setDemoMode(false);
      } catch {
        setConnectionStatus("disconnected");
      }
    }
    check();
  }, []);

  /* Pre-fetch handler */
  const handlePrefetch = useCallback(async () => {
    setPrefetching(true);
    setPrefetchResult(null);
    try {
      const res = await fetch(`${API_URL}/api/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: "AAPL",
          strategy: "mean_reversion",
          start_date: "2023-01-01",
          end_date: "2024-12-31",
        }),
        signal: AbortSignal.timeout(15000),
      });
      if (res.ok) {
        setPrefetchResult("Pre-fetch successful -- AAPL data cached");
      } else {
        setPrefetchResult(`API returned status ${res.status}`);
      }
    } catch {
      setPrefetchResult(
        "API unavailable -- demo mode will use synthetic data"
      );
    } finally {
      setPrefetching(false);
    }
  }, []);

  const sectionDelay = (i: number) => ({ delay: i * 0.1 });

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-lg">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 text-xl font-semibold text-zinc-50"
          >
            <Settings className="h-5 w-5 text-zinc-400" />
            Settings
          </motion.h1>
          <p className="mt-1 text-sm text-zinc-500">
            Platform configuration and connection management
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-6 py-8">
        {/* API Connection */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={sectionDelay(0)}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
        >
          <div className="mb-4 flex items-center gap-2">
            <Globe className="h-4 w-4 text-violet-400" />
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
              API Connection
            </h2>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-zinc-300">
                Endpoint:{" "}
                <code className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-violet-300">
                  {API_URL}
                </code>
              </p>
            </div>
            <div className="flex items-center gap-2">
              {connectionStatus === "checking" && (
                <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
              )}
              {connectionStatus === "connected" && (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              )}
              {connectionStatus === "disconnected" && (
                <XCircle className="h-4 w-4 text-red-400" />
              )}
              <span
                className={cn(
                  "rounded-full border px-2.5 py-0.5 text-xs font-medium",
                  connectionStatus === "connected"
                    ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-400"
                    : connectionStatus === "disconnected"
                      ? "border-red-500/40 bg-red-500/15 text-red-400"
                      : "border-zinc-700 bg-zinc-800 text-zinc-500"
                )}
              >
                {connectionStatus === "checking"
                  ? "Checking..."
                  : connectionStatus === "connected"
                    ? "Connected"
                    : "Disconnected"}
              </span>
            </div>
          </div>
        </motion.div>

        {/* Demo/Live toggle */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={sectionDelay(1)}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
        >
          <div className="mb-4 flex items-center gap-2">
            {demoMode ? (
              <ToggleLeft className="h-4 w-4 text-zinc-400" />
            ) : (
              <ToggleRight className="h-4 w-4 text-emerald-400" />
            )}
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
              Data Mode
            </h2>
          </div>

          <div className="flex items-center justify-between">
            <div className="max-w-md">
              <p className="text-sm text-zinc-300">
                {demoMode ? "Demo Mode" : "Live Mode"}
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                {demoMode
                  ? "Using synthetic data for all visualizations and backtests. No API connection required."
                  : "Connected to live API. All data is fetched from the backend in real time."}
              </p>
            </div>
            <button
              onClick={() => setDemoMode(!demoMode)}
              className={cn(
                "relative h-8 w-14 rounded-full transition-colors duration-200",
                demoMode ? "bg-zinc-700" : "bg-violet-500"
              )}
            >
              <motion.div
                className="absolute top-1 h-6 w-6 rounded-full bg-white shadow-sm"
                animate={{ left: demoMode ? 4 : 30 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              />
            </button>
          </div>
        </motion.div>

        {/* Pre-fetch */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={sectionDelay(2)}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
        >
          <div className="mb-4 flex items-center gap-2">
            <Download className="h-4 w-4 text-cyan-400" />
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
              Pre-fetch Data
            </h2>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-zinc-300">
                Pre-fetch Demo Data ({TICKERS.length} tickers)
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                Tests API connectivity by running a backtest on AAPL
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {TICKERS.map((t) => (
                  <span
                    key={t}
                    className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] font-mono text-zinc-500"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={handlePrefetch}
              disabled={prefetching}
              className={cn(
                "shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                prefetching
                  ? "cursor-not-allowed bg-zinc-800 text-zinc-500"
                  : "bg-violet-500 text-white hover:bg-violet-400"
              )}
            >
              {prefetching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Fetch"
              )}
            </motion.button>
          </div>

          {prefetchResult && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={cn(
                "mt-3 rounded-lg border px-3 py-2 text-xs",
                prefetchResult.includes("successful")
                  ? "border-emerald-800/50 bg-emerald-950/30 text-emerald-300"
                  : "border-amber-800/50 bg-amber-950/30 text-amber-300"
              )}
            >
              {prefetchResult}
            </motion.p>
          )}
        </motion.div>

        {/* Strategy Config */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={sectionDelay(3)}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
        >
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
            Strategy Configuration
          </h2>

          <div className="grid gap-4 md:grid-cols-2">
            {STRATEGIES.map((strat) => (
              <div
                key={strat.key}
                className="rounded-lg border border-zinc-800 bg-zinc-900 p-4"
              >
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-medium text-zinc-200">
                    {strat.name}
                  </h3>
                  <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-violet-300">
                    {strat.key}
                  </code>
                </div>
                <div className="space-y-2">
                  {strat.params.map((param) => (
                    <div
                      key={param.label}
                      className="flex items-center justify-between text-xs"
                    >
                      <span className="text-zinc-500">{param.label}</span>
                      <span className="font-mono text-zinc-300">
                        {param.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* About */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={sectionDelay(4)}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
        >
          <div className="mb-4 flex items-center gap-2">
            <Info className="h-4 w-4 text-zinc-400" />
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
              About
            </h2>
          </div>

          <div>
            <p className="text-sm text-zinc-300">
              Agentic Alpha Lab{" "}
              <span className="font-mono text-violet-300">v1.0.0</span>
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Built with Claude Code
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: "Dashboard Pages", value: "5" },
                { label: "Components", value: "12+" },
                { label: "Agent Types", value: "6" },
                { label: "Strategies", value: "2" },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-center"
                >
                  <p className="text-lg font-semibold text-zinc-50">
                    {stat.value}
                  </p>
                  <p className="text-[10px] text-zinc-600">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
