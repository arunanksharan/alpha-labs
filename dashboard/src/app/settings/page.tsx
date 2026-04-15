"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Globe,
  ToggleLeft,
  ToggleRight,
  Settings,
  Info,
  CheckCircle2,
  XCircle,
  Loader2,
  Key,
  Eye,
  EyeOff,
  Bot,
  Cpu,
  Save,
  Plus,
  Trash2,
  RefreshCw,
  Database,
  TrendingUp,
  TrendingDown,
  Search,
  Timer,
  Play,
  Square,
} from "lucide-react";
import { cn, BASE_PATH } from "@/lib/utils";
import { API_URL } from "@/lib/utils";

/* ---------- Constants ---------- */

const PROVIDERS = [
  { key: "openai", label: "OpenAI", placeholder: "sk-proj-..." },
  { key: "anthropic", label: "Anthropic", placeholder: "sk-ant-..." },
  { key: "gemini", label: "Google Gemini", placeholder: "AI..." },
  { key: "groq", label: "Groq", placeholder: "gsk_..." },
  { key: "deepseek", label: "DeepSeek", placeholder: "sk-..." },
] as const;

const AGENTS = [
  { key: "research_director", label: "Research Director" },
  { key: "the_quant", label: "The Quant" },
  { key: "the_technician", label: "The Technician" },
  { key: "sentiment_analyst", label: "Sentiment Analyst" },
  { key: "the_fundamentalist", label: "The Fundamentalist" },
  { key: "the_macro_strategist", label: "Macro Strategist" },
] as const;

const STRATEGIES = [
  {
    name: "Mean Reversion", key: "mean_reversion",
    params: [
      { label: "Lookback window", value: "20 days" },
      { label: "Z-score threshold", value: "2.0" },
      { label: "Exit threshold", value: "0.5" },
    ],
  },
  {
    name: "Momentum", key: "momentum",
    params: [
      { label: "Lookback window", value: "60 days" },
      { label: "Entry percentile", value: "80th" },
      { label: "Holding period", value: "10 days" },
    ],
  },
];

/* ---------- Types ---------- */

interface TickerStatus {
  ticker: string;
  has_data: boolean;
  strategies: {
    strategy: string;
    cached: boolean;
    signals?: number;
    sharpe?: number;
    total_return?: number;
  }[];
}

/* ---------- Page ---------- */

export default function SettingsPage() {
  const [connectionStatus, setConnectionStatus] = useState<"checking" | "connected" | "disconnected">("checking");

  // Config Agent
  const [configInput, setConfigInput] = useState("");
  const [configLoading, setConfigLoading] = useState(false);
  const [configResult, setConfigResult] = useState<{ changes: { key: string; previous: string; new: string; status: string }[] } | null>(null);

  // API Keys
  const [keyValues, setKeyValues] = useState<Record<string, string>>({});
  const [keyStatus, setKeyStatus] = useState<Record<string, boolean>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [savingKeys, setSavingKeys] = useState(false);
  const [keySaveResult, setKeySaveResult] = useState<string | null>(null);

  // Model
  const [models, setModels] = useState<{ alias: string; available: boolean }[]>([]);
  const [defaultModel, setDefaultModel] = useState("gpt-5-mini");
  const [savingModel, setSavingModel] = useState(false);

  // Prompts
  const [prompts, setPrompts] = useState<Record<string, string>>({});
  const [savingPrompts, setSavingPrompts] = useState(false);
  const [promptSaveResult, setPromptSaveResult] = useState<string | null>(null);

  // Universe
  const [universeTickers, setUniverseTickers] = useState<string[]>([]);
  const [universeStatus, setUniverseStatus] = useState<TickerStatus[]>([]);
  const [newTicker, setNewTicker] = useState("");
  const [addingTicker, setAddingTicker] = useState(false);
  const [refreshingTicker, setRefreshingTicker] = useState<string | null>(null);
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState<string | null>(null);

  // Cron
  const [cronEnabled, setCronEnabled] = useState(false);
  const [cronHour, setCronHour] = useState(6);
  const [cronMinute, setCronMinute] = useState(0);
  const [cronTzOffset, setCronTzOffset] = useState(8);
  const [cronRunning, setCronRunning] = useState(false);
  const [cronLastRun, setCronLastRun] = useState<string | null>(null);
  const [cronLastResult, setCronLastResult] = useState<string | null>(null);
  const [cronNextRun, setCronNextRun] = useState<string | null>(null);
  const [cronSaving, setCronSaving] = useState(false);
  const [cronTriggering, setCronTriggering] = useState(false);

  /* --- Init --- */
  useEffect(() => {
    async function init() {
      const [healthRes, modelsRes, keysRes, promptsRes, universeRes] = await Promise.allSettled([
        fetch(`${API_URL}/api/health`, { signal: AbortSignal.timeout(3000) }),
        fetch(`${API_URL}/api/models`, { signal: AbortSignal.timeout(3000) }),
        fetch(`${API_URL}/api/settings/keys`, { signal: AbortSignal.timeout(3000) }),
        fetch(`${API_URL}/api/settings/prompts`, { signal: AbortSignal.timeout(3000) }),
        fetch(`${API_URL}/api/universe`, { signal: AbortSignal.timeout(5000) }),
      ]);

      setConnectionStatus(
        healthRes.status === "fulfilled" && healthRes.value.ok ? "connected" : "disconnected"
      );

      if (modelsRes.status === "fulfilled" && modelsRes.value.ok) {
        const d = await modelsRes.value.json();
        setModels(d.models || []);
        if (d.default_model) setDefaultModel(d.default_model);
      }
      if (keysRes.status === "fulfilled" && keysRes.value.ok) {
        const d = await keysRes.value.json();
        setKeyStatus(d.keys || {});
      }
      if (promptsRes.status === "fulfilled" && promptsRes.value.ok) {
        const d = await promptsRes.value.json();
        setPrompts(d.prompts || {});
      }
      if (universeRes.status === "fulfilled" && universeRes.value.ok) {
        const d = await universeRes.value.json();
        setUniverseTickers(d.tickers || []);
        setUniverseStatus(d.status || []);
      }
      // Fetch cron status
      try {
        const cronRes = await fetch(`${API_URL}/api/cron/status`, { signal: AbortSignal.timeout(3000) });
        if (cronRes.ok) {
          const d = await cronRes.json();
          setCronEnabled(d.config?.enabled ?? false);
          setCronHour(d.config?.schedule_hour ?? 6);
          setCronMinute(d.config?.schedule_minute ?? 0);
          setCronTzOffset(d.config?.timezone_offset ?? 8);
          setCronRunning(d.status?.running ?? false);
          setCronLastRun(d.status?.last_run ?? null);
          setCronLastResult(d.status?.last_result ?? null);
          setCronNextRun(d.status?.next_run ?? null);
        }
      } catch {}
    }
    init();
  }, []);

  /* --- Cron handlers --- */
  const handleCronSave = useCallback(async () => {
    setCronSaving(true);
    try {
      await fetch(`${API_URL}/api/cron/config`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ schedule_hour: cronHour, schedule_minute: cronMinute, timezone_offset: cronTzOffset }),
      });
    } catch {} finally { setCronSaving(false); }
  }, [cronHour, cronMinute, cronTzOffset]);

  const handleCronToggle = useCallback(async () => {
    try {
      if (cronRunning) {
        await fetch(`${API_URL}/api/cron/stop`, { method: "POST" });
        setCronRunning(false);
        setCronEnabled(false);
      } else {
        await fetch(`${API_URL}/api/cron/start`, { method: "POST" });
        setCronRunning(true);
        setCronEnabled(true);
      }
      // Refresh status
      const res = await fetch(`${API_URL}/api/cron/status`);
      if (res.ok) {
        const d = await res.json();
        setCronNextRun(d.status?.next_run ?? null);
      }
    } catch {}
  }, [cronRunning]);

  const handleCronRunNow = useCallback(async () => {
    setCronTriggering(true);
    try {
      await fetch(`${API_URL}/api/cron/run-now`, { method: "POST" });
      // Refresh status after
      const res = await fetch(`${API_URL}/api/cron/status`);
      if (res.ok) {
        const d = await res.json();
        setCronLastRun(d.status?.last_run ?? null);
        setCronLastResult(d.status?.last_result ?? null);
      }
    } catch {} finally { setCronTriggering(false); }
  }, []);

  /* --- Universe handlers --- */
  const refreshUniverse = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/universe`);
      if (res.ok) {
        const d = await res.json();
        setUniverseTickers(d.tickers || []);
        setUniverseStatus(d.status || []);
      }
    } catch {}
  }, []);

  const handleAddTicker = useCallback(async () => {
    const ticker = newTicker.trim().toUpperCase();
    if (!ticker) return;
    setAddingTicker(true);
    try {
      const res = await fetch(`${API_URL}/api/universe/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
      });
      if (res.ok) {
        setNewTicker("");
        await refreshUniverse();
      }
    } catch {} finally {
      setAddingTicker(false);
    }
  }, [newTicker, refreshUniverse]);

  const handleRemoveTicker = useCallback(async (ticker: string) => {
    try {
      await fetch(`${API_URL}/api/universe/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
      });
      await refreshUniverse();
    } catch {}
  }, [refreshUniverse]);

  const handleRefreshTicker = useCallback(async (ticker: string) => {
    setRefreshingTicker(ticker);
    try {
      await fetch(`${API_URL}/api/universe/refresh/${ticker}?strategy=mean_reversion`, { method: "POST" });
      await refreshUniverse();
    } catch {} finally {
      setRefreshingTicker(null);
    }
  }, [refreshUniverse]);

  const handleRefreshAll = useCallback(async () => {
    setRefreshingAll(true);
    for (let i = 0; i < universeTickers.length; i++) {
      const ticker = universeTickers[i];
      setRefreshProgress(`${ticker} (${i + 1}/${universeTickers.length})`);
      try {
        await fetch(`${API_URL}/api/universe/refresh/${ticker}?strategy=mean_reversion`, { method: "POST" });
      } catch {}
    }
    setRefreshProgress(null);
    setRefreshingAll(false);
    await refreshUniverse();
  }, [universeTickers, refreshUniverse]);

  /* --- Keys --- */
  const handleSaveKeys = useCallback(async () => {
    setSavingKeys(true);
    setKeySaveResult(null);
    try {
      const res = await fetch(`${API_URL}/api/settings/keys`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(keyValues),
      });
      if (res.ok) {
        const d = await res.json();
        setKeyStatus(d.keys || {});
        setKeySaveResult(`Updated: ${(d.updated || []).join(", ") || "none"}`);
        setKeyValues({});
        const mRes = await fetch(`${API_URL}/api/models`);
        if (mRes.ok) setModels((await mRes.json()).models || []);
      }
    } catch { setKeySaveResult("API unavailable"); }
    finally { setSavingKeys(false); }
  }, [keyValues]);

  const handleSaveModel = useCallback(async () => {
    setSavingModel(true);
    try {
      await fetch(`${API_URL}/api/settings/model`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: defaultModel }),
      });
    } catch {} finally { setSavingModel(false); }
  }, [defaultModel]);

  const handleSavePrompts = useCallback(async () => {
    setSavingPrompts(true);
    setPromptSaveResult(null);
    try {
      const res = await fetch(`${API_URL}/api/settings/prompts`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompts }),
      });
      if (res.ok) {
        const d = await res.json();
        setPromptSaveResult(`Updated: ${(d.updated || []).join(", ")}`);
      }
    } catch { setPromptSaveResult("API unavailable"); }
    finally { setSavingPrompts(false); }
  }, [prompts]);

  /* --- Config Agent --- */
  const handleConfigAgent = useCallback(async () => {
    if (!configInput.trim()) return;
    setConfigLoading(true);
    setConfigResult(null);
    try {
      const res = await fetch(`${API_URL}/api/config-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json",
          ...(typeof window !== "undefined" && localStorage.getItem("access_token")
            ? { Authorization: `Bearer ${localStorage.getItem("access_token")}` } : {}) },
        body: JSON.stringify({ message: configInput }),
      });
      if (res.ok) {
        const data = await res.json();
        setConfigResult(data);
        setConfigInput("");
      }
    } catch {} finally {
      setConfigLoading(false);
    }
  }, [configInput]);

  const sectionDelay = (i: number) => ({ delay: i * 0.06 });
  const availableModels = models.filter((m) => m.available);

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-lg">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-5">
          <motion.h1 initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 text-lg font-semibold text-zinc-50">
            <Settings className="h-5 w-5 text-zinc-400" /> Settings
          </motion.h1>
          <p className="mt-1 text-sm text-zinc-500">Platform configuration, universe management, and connection settings</p>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-5 px-4 sm:px-6 py-6">

        {/* ── Config Agent ── */}
        <Section icon={<Bot className="h-4 w-4 text-violet-400" />} title="Configuration Agent" delay={sectionDelay(0)}>
          <p className="text-xs text-zinc-500 mb-3">
            Describe config changes in natural language. Example: &quot;set commission to 15 bps and Kelly fraction to 0.3&quot;
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={configInput}
              onChange={(e) => setConfigInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleConfigAgent()}
              placeholder="e.g. set risk-free rate to 4.5% and max drawdown to 20%"
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            />
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              onClick={handleConfigAgent} disabled={configLoading || !configInput.trim()}
              className={cn("flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors shrink-0",
                configLoading || !configInput.trim() ? "bg-zinc-800 text-zinc-500 cursor-not-allowed" : "bg-violet-500 text-white hover:bg-violet-400")}>
              {configLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Bot className="h-3.5 w-3.5" />}
              Apply
            </motion.button>
          </div>
          <AnimatePresence>
            {configResult && configResult.changes && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                className="mt-3 rounded-lg border border-zinc-800 overflow-hidden">
                {configResult.changes.map((c, i) => (
                  <div key={i} className={cn("flex items-center justify-between px-3 py-2 text-xs border-b border-zinc-800/50 last:border-0",
                    c.status === "applied" ? "bg-emerald-500/5" : "bg-red-500/5")}>
                    <span className="font-mono text-zinc-400">{c.key}</span>
                    <span className="flex items-center gap-2">
                      <span className="text-zinc-600">{c.previous}</span>
                      <span className="text-zinc-500">&rarr;</span>
                      <span className={c.status === "applied" ? "text-emerald-400 font-medium" : "text-red-400"}>{c.new || c.status}</span>
                    </span>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </Section>

        {/* ════════════════════════════════════════════════════════════
            RESEARCH UNIVERSE
           ════════════════════════════════════════════════════════════ */}
        <Section icon={<Database className="h-4 w-4 text-violet-400" />} title="Research Universe" delay={sectionDelay(1)}>
          <p className="text-xs text-zinc-500 mb-4">
            Your active research universe. Add tickers, fetch market data, and compute signals — all from here.
          </p>

          {/* Add ticker input */}
          <div className="flex gap-2 mb-4">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
              <input
                type="text"
                value={newTicker}
                onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && handleAddTicker()}
                placeholder="Add ticker (e.g. GRAB.SI, WIPRO.NS)"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800 pl-9 pr-3 py-2 text-sm text-zinc-50 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 font-mono"
              />
            </div>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              onClick={handleAddTicker} disabled={addingTicker || !newTicker.trim()}
              className={cn("flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors shrink-0",
                !newTicker.trim() ? "bg-zinc-800 text-zinc-500 cursor-not-allowed" : "bg-violet-500 text-white hover:bg-violet-400")}>
              {addingTicker ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Add
            </motion.button>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              onClick={handleRefreshAll} disabled={refreshingAll || universeTickers.length === 0}
              className={cn("flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors shrink-0",
                refreshingAll ? "bg-zinc-800 text-zinc-500 cursor-not-allowed" : "border border-violet-500/50 text-violet-400 hover:bg-violet-500/10")}>
              <RefreshCw className={cn("h-3.5 w-3.5", refreshingAll && "animate-spin")} />
              {refreshingAll ? "Refreshing..." : "Refresh All"}
            </motion.button>
          </div>

          {/* Progress indicator */}
          <AnimatePresence>
            {refreshProgress && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                className="mb-3 flex items-center gap-2 rounded-lg border border-violet-500/30 bg-violet-500/5 px-3 py-2 text-xs text-violet-300">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Fetching data & computing signals: {refreshProgress}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Ticker table */}
          {universeStatus.length > 0 ? (
            <div className="rounded-lg border border-zinc-800 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800 bg-zinc-900/50">
                      <th className="text-left px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-zinc-500">Ticker</th>
                      <th className="text-left px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-zinc-500">Data</th>
                      <th className="text-right px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-zinc-500">Signals</th>
                      <th className="text-right px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-zinc-500">Sharpe</th>
                      <th className="text-right px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-zinc-500">Return</th>
                      <th className="text-right px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-zinc-500">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {universeStatus.map((t, i) => {
                      const mr = t.strategies.find((s) => s.strategy === "mean_reversion");
                      const isRefreshing = refreshingTicker === t.ticker;
                      const ret = mr?.total_return ?? 0;

                      return (
                        <motion.tr key={t.ticker}
                          initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.03 }}
                          className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                          <td className="px-4 py-3">
                            <span className="font-mono font-medium text-zinc-200">{t.ticker}</span>
                          </td>
                          <td className="px-4 py-3">
                            {t.has_data ? (
                              <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Cached
                              </span>
                            ) : (
                              <span className="flex items-center gap-1.5 text-xs text-zinc-500">
                                <span className="h-1.5 w-1.5 rounded-full bg-zinc-600" /> No data
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-zinc-300">
                            {mr?.signals ?? "—"}
                          </td>
                          <td className="px-4 py-3 text-right font-mono">
                            <span className={cn(
                              (mr?.sharpe ?? 0) > 0 ? "text-emerald-400" : (mr?.sharpe ?? 0) < 0 ? "text-red-400" : "text-zinc-500"
                            )}>
                              {mr?.sharpe != null ? mr.sharpe.toFixed(2) : "—"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className={cn("flex items-center justify-end gap-1 font-mono text-xs",
                              ret > 0 ? "text-emerald-400" : ret < 0 ? "text-red-400" : "text-zinc-500")}>
                              {ret > 0 ? <TrendingUp className="h-3 w-3" /> : ret < 0 ? <TrendingDown className="h-3 w-3" /> : null}
                              {mr?.total_return != null ? `${(ret * 100).toFixed(1)}%` : "—"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button onClick={() => handleRefreshTicker(t.ticker)}
                                disabled={isRefreshing}
                                className="rounded p-1.5 text-zinc-500 hover:bg-zinc-700 hover:text-violet-400 transition-colors"
                                title="Fetch data & compute signals">
                                <RefreshCw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
                              </button>
                              <button onClick={() => handleRemoveTicker(t.ticker)}
                                className="rounded p-1.5 text-zinc-600 hover:bg-zinc-700 hover:text-red-400 transition-colors"
                                title="Remove from universe">
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </td>
                        </motion.tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="bg-zinc-900/30 px-4 py-2 text-[10px] text-zinc-600 flex items-center justify-between">
                <span>{universeTickers.length} tickers in universe</span>
                <span>{universeStatus.filter((t) => t.has_data).length} with cached data</span>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-8 text-center text-sm text-zinc-500">
              No tickers in universe. Add one above to get started.
            </div>
          )}
        </Section>

        {/* ── Cron Scheduler ── */}
        <Section icon={<Timer className="h-4 w-4 text-amber-400" />} title="Daily Research Schedule" delay={sectionDelay(1)}>
          <p className="text-xs text-zinc-500 mb-4">
            Automatically fetch data and compute signals for your entire universe on a schedule.
          </p>
          <div className="space-y-4">
            {/* Schedule config */}
            <div className="flex flex-col sm:flex-row sm:items-end gap-3">
              <div>
                <label className="mb-1 block text-xs text-zinc-500">Hour</label>
                <input type="number" min={0} max={23} value={cronHour} onChange={(e) => setCronHour(parseInt(e.target.value) || 0)}
                  className="w-20 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 font-mono focus:border-violet-500 focus:outline-none" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-zinc-500">Minute</label>
                <input type="number" min={0} max={59} value={cronMinute} onChange={(e) => setCronMinute(parseInt(e.target.value) || 0)}
                  className="w-20 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 font-mono focus:border-violet-500 focus:outline-none" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-zinc-500">Timezone (UTC offset)</label>
                <select value={cronTzOffset} onChange={(e) => setCronTzOffset(parseInt(e.target.value))}
                  className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 focus:border-violet-500 focus:outline-none">
                  <option value={-8}>UTC-8 (PST)</option>
                  <option value={-5}>UTC-5 (EST)</option>
                  <option value={0}>UTC+0 (GMT)</option>
                  <option value={1}>UTC+1 (CET)</option>
                  <option value={5}>UTC+5:30 (IST)</option>
                  <option value={8}>UTC+8 (SGT)</option>
                  <option value={9}>UTC+9 (JST)</option>
                </select>
              </div>
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                onClick={handleCronSave} disabled={cronSaving}
                className="flex items-center gap-1.5 rounded-lg bg-violet-500 px-4 py-2 text-xs font-medium text-white hover:bg-violet-400 shrink-0">
                {cronSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                Save Schedule
              </motion.button>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center gap-3">
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                onClick={handleCronToggle}
                className={cn("flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-medium transition-colors",
                  cronRunning ? "bg-red-500/15 border border-red-500/40 text-red-400 hover:bg-red-500/25" : "bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/25")}>
                {cronRunning ? <Square className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                {cronRunning ? "Stop Scheduler" : "Start Scheduler"}
              </motion.button>

              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                onClick={handleCronRunNow} disabled={cronTriggering}
                className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-4 py-2 text-xs font-medium text-zinc-400 hover:bg-zinc-800 hover:text-violet-400">
                {cronTriggering ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                Run Now
              </motion.button>

              {cronRunning && (
                <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                  <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" /></span>
                  Active
                </span>
              )}
            </div>

            {/* Status */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-3 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-zinc-500">Schedule</span>
                <span className="font-mono text-zinc-300">{String(cronHour).padStart(2, "0")}:{String(cronMinute).padStart(2, "0")} UTC{cronTzOffset >= 0 ? "+" : ""}{cronTzOffset}</span>
              </div>
              {cronNextRun && <div className="flex justify-between">
                <span className="text-zinc-500">Next run</span>
                <span className="text-zinc-400">{new Date(cronNextRun).toLocaleString()}</span>
              </div>}
              {cronLastRun && <div className="flex justify-between">
                <span className="text-zinc-500">Last run</span>
                <span className="text-zinc-400">{new Date(cronLastRun).toLocaleString()}</span>
              </div>}
              {cronLastResult && <div className="flex justify-between">
                <span className="text-zinc-500">Result</span>
                <span className="text-zinc-300">{cronLastResult}</span>
              </div>}
            </div>
          </div>
        </Section>

        {/* ── API Connection ── */}
        <Section icon={<Globe className="h-4 w-4 text-violet-400" />} title="API Connection" delay={sectionDelay(2)}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <p className="text-sm text-zinc-300">
              Endpoint: <code className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-violet-300">{API_URL}</code>
            </p>
            <StatusBadge status={connectionStatus} />
          </div>
        </Section>

        {/* ── API Keys ── */}
        <Section icon={<Key className="h-4 w-4 text-amber-400" />} title="API Keys" delay={sectionDelay(2)}>
          <p className="text-xs text-zinc-500 mb-4">Configure LLM provider keys. Stored in server memory only.</p>
          <div className="space-y-3">
            {PROVIDERS.map(({ key, label, placeholder }) => (
              <div key={key} className="flex flex-col sm:flex-row sm:items-center gap-2">
                <div className="flex items-center gap-2 w-full sm:w-36 shrink-0">
                  <span className={cn("h-2 w-2 rounded-full shrink-0", keyStatus[key] ? "bg-emerald-400" : "bg-zinc-600")} />
                  <span className="text-xs font-medium text-zinc-400">{label}</span>
                </div>
                <div className="relative flex-1">
                  <input
                    type={showKeys[key] ? "text" : "password"}
                    value={keyValues[key] || ""}
                    onChange={(e) => setKeyValues((p) => ({ ...p, [key]: e.target.value }))}
                    placeholder={keyStatus[key] ? "••••••• (configured)" : placeholder}
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 pr-9 text-xs text-zinc-50 placeholder:text-zinc-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 font-mono"
                  />
                  <button type="button" onClick={() => setShowKeys((p) => ({ ...p, [key]: !p[key] }))}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300">
                    {showKeys[key] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-3">
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }} onClick={handleSaveKeys}
              disabled={savingKeys || Object.values(keyValues).every((v) => !v.trim())}
              className={cn("flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-medium transition-colors",
                savingKeys || Object.values(keyValues).every((v) => !v.trim())
                  ? "cursor-not-allowed bg-zinc-800 text-zinc-500" : "bg-violet-500 text-white hover:bg-violet-400")}>
              {savingKeys ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
              Save Keys
            </motion.button>
            {keySaveResult && <span className="text-xs text-zinc-500">{keySaveResult}</span>}
          </div>
        </Section>

        {/* ── Default Model ── */}
        <Section icon={<Cpu className="h-4 w-4 text-emerald-400" />} title="Default Model" delay={sectionDelay(3)}>
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1">
              <p className="text-xs text-zinc-500 mb-2">Select the LLM for agent synthesis, chat, and research.</p>
              <select value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)}
                className="w-full sm:w-auto rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-50 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500">
                {availableModels.length > 0 && <optgroup label="Available">
                  {availableModels.map((m) => <option key={m.alias} value={m.alias}>{m.alias}</option>)}
                </optgroup>}
                <optgroup label="All models">
                  {models.filter((m) => !m.available).map((m) => <option key={m.alias} value={m.alias}>{m.alias} (no key)</option>)}
                </optgroup>
              </select>
            </div>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }} onClick={handleSaveModel}
              disabled={savingModel}
              className="flex items-center gap-2 rounded-lg bg-violet-500 px-4 py-2 text-xs font-medium text-white hover:bg-violet-400 shrink-0">
              {savingModel ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
              Save
            </motion.button>
          </div>
        </Section>

        {/* ── Agent Skills (link to /skills page) ── */}
        <Section icon={<Bot className="h-4 w-4 text-cyan-400" />} title="Agent Skills" delay={sectionDelay(4)}>
          <div className="flex items-center justify-between">
            <p className="text-xs text-zinc-500">Define each agent's expertise, methodology, and personality using markdown skill files.</p>
            <a href={`${BASE_PATH}/skills`}
              className="flex items-center gap-1.5 rounded-lg bg-violet-500/15 border border-violet-500/30 px-4 py-2 text-xs font-medium text-violet-400 hover:bg-violet-500/25 transition-colors shrink-0">
              Edit Skills
            </a>
          </div>
        </Section>

        {/* ── Strategy Config ── */}
        <Section icon={<Info className="h-4 w-4 text-zinc-400" />} title="Strategy Configuration" delay={sectionDelay(5)}>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
            {STRATEGIES.map((strat) => (
              <div key={strat.key} className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-medium text-zinc-200">{strat.name}</h3>
                  <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-violet-300">{strat.key}</code>
                </div>
                <div className="space-y-2">
                  {strat.params.map((p) => (
                    <div key={p.label} className="flex items-center justify-between text-xs">
                      <span className="text-zinc-500">{p.label}</span>
                      <span className="font-mono text-zinc-300">{p.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* ── MCP Server ── */}
        <Section icon={<Cpu className="h-4 w-4 text-emerald-400" />} title="MCP Server — AI Agent Access" delay={sectionDelay(6)}>
          <p className="text-xs text-zinc-500 mb-4">
            External AI agents (Claude, Cursor, Windsurf) can access your backtesting engine via the Model Context Protocol.
          </p>

          <div className="space-y-3">
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-3">
              <p className="text-xs font-medium text-zinc-400 mb-2">SSE Transport (Cursor, Windsurf)</p>
              <code className="block rounded bg-zinc-800 px-3 py-2 text-xs text-violet-300 font-mono">
                {API_URL}/mcp
              </code>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-3">
              <p className="text-xs font-medium text-zinc-400 mb-2">stdio Transport (Claude Desktop)</p>
              <pre className="rounded bg-zinc-800 px-3 py-2 text-[10px] text-zinc-300 font-mono overflow-x-auto">
{`{
  "mcpServers": {
    "alpha-labs": {
      "command": "python",
      "args": ["mcp_server.py"]
    }
  }
}`}
              </pre>
            </div>

            <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-3">
              <p className="text-xs font-medium text-zinc-400 mb-3">Available Tools</p>
              <div className="space-y-2">
                {[
                  { name: "research_ticker", desc: "6-agent stock analysis → consensus signal" },
                  { name: "run_backtest", desc: "Full backtest with custom strategy params" },
                  { name: "get_signals", desc: "Current signals for all tracked tickers" },
                  { name: "fetch_market_data", desc: "Real-time OHLCV from YFinance" },
                  { name: "get_platform_status", desc: "Universe, cache, API keys status" },
                ].map((tool) => (
                  <div key={tool.name} className="flex items-center gap-3">
                    <code className="rounded bg-violet-500/10 px-2 py-0.5 text-[10px] text-violet-300 font-mono shrink-0">
                      {tool.name}
                    </code>
                    <span className="text-[10px] text-zinc-500">{tool.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Section>

        {/* ── About ── */}
        <Section icon={<Info className="h-4 w-4 text-zinc-400" />} title="About" delay={sectionDelay(7)}>
          <p className="text-sm text-zinc-300">Agentic Alpha Lab <span className="font-mono text-violet-300">v1.0.0</span></p>
          <p className="mt-1 text-xs text-zinc-500">Built with Claude Code</p>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "Dashboard Pages", value: "7" },
              { label: "Components", value: "15+" },
              { label: "Agent Types", value: "6" },
              { label: "Strategies", value: "2" },
            ].map((stat) => (
              <div key={stat.label} className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-center">
                <p className="text-lg font-semibold text-zinc-50">{stat.value}</p>
                <p className="text-[10px] text-zinc-600">{stat.label}</p>
              </div>
            ))}
          </div>
        </Section>
      </main>
    </div>
  );
}

/* ── Helpers ── */

function Section({ icon, title, delay, children }: { icon: React.ReactNode; title: string; delay: { delay: number }; children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={delay}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 sm:p-5">
      <div className="mb-4 flex items-center gap-2">
        {icon}
        <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">{title}</h2>
      </div>
      {children}
    </motion.div>
  );
}

function StatusBadge({ status }: { status: "checking" | "connected" | "disconnected" }) {
  return (
    <div className="flex items-center gap-2">
      {status === "checking" && <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />}
      {status === "connected" && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
      {status === "disconnected" && <XCircle className="h-4 w-4 text-red-400" />}
      <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-medium",
        status === "connected" ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-400"
          : status === "disconnected" ? "border-red-500/40 bg-red-500/15 text-red-400"
            : "border-zinc-700 bg-zinc-800 text-zinc-500")}>
        {status === "checking" ? "Checking..." : status === "connected" ? "Connected" : "Disconnected"}
      </span>
    </div>
  );
}
