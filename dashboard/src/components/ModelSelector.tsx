"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Check, Cpu, Sparkles, Zap, Cloud, Brain } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { API_URL } from "@/lib/utils";

interface ModelOption {
  alias: string;
  model: string;
  provider: string;
  available: boolean;
}

const PROVIDER_META: Record<string, { icon: typeof Cpu; color: string; label: string }> = {
  anthropic: { icon: Sparkles, color: "text-violet-400", label: "Anthropic" },
  openai: { icon: Zap, color: "text-emerald-400", label: "OpenAI" },
  gemini: { icon: Brain, color: "text-blue-400", label: "Google" },
  groq: { icon: Cpu, color: "text-amber-400", label: "Groq" },
  deepseek: { icon: Cloud, color: "text-cyan-400", label: "DeepSeek" },
};

const DEFAULT_MODELS: ModelOption[] = [
  { alias: "claude-sonnet", model: "anthropic/claude-sonnet-4-20250514", provider: "anthropic", available: false },
  { alias: "gpt-4o", model: "openai/gpt-4o", provider: "openai", available: false },
  { alias: "gemini-flash", model: "gemini/gemini-2.5-flash", provider: "gemini", available: false },
  { alias: "llama-70b", model: "groq/llama-3.3-70b-versatile", provider: "groq", available: false },
  { alias: "deepseek", model: "deepseek/deepseek-chat", provider: "deepseek", available: false },
  { alias: "claude-haiku", model: "anthropic/claude-haiku-4-5-20251001", provider: "anthropic", available: false },
  { alias: "gpt-4o-mini", model: "openai/gpt-4o-mini", provider: "openai", available: false },
  { alias: "gemini-pro", model: "gemini/gemini-2.5-pro", provider: "gemini", available: false },
];

// Friendly display names
const MODEL_LABELS: Record<string, string> = {
  "claude-sonnet": "Claude Sonnet 4",
  "claude-haiku": "Claude Haiku 4.5",
  "claude-opus": "Claude Opus 4",
  "gpt-4o": "GPT-4o",
  "gpt-4o-mini": "GPT-4o Mini",
  "o3": "o3",
  "o4-mini": "o4 Mini",
  "gemini-flash": "Gemini 2.5 Flash",
  "gemini-pro": "Gemini 2.5 Pro",
  "llama-70b": "Llama 3.3 70B",
  "llama-8b": "Llama 3.1 8B",
  "deepseek": "DeepSeek V3",
};

export function ModelSelector({ expanded }: { expanded: boolean }) {
  const { selectedModel, setSelectedModel } = useAppStore();
  const [open, setOpen] = useState(false);
  const [models, setModels] = useState<ModelOption[]>(DEFAULT_MODELS);
  const ref = useRef<HTMLDivElement>(null);

  // Fetch available models from API
  useEffect(() => {
    fetch(`${API_URL}/api/models`)
      .then((r) => r.json())
      .then((data) => {
        if (data.models) {
          // Deduplicate by alias, keep only the "primary" models
          const primaryAliases = new Set([
            "claude-sonnet", "gpt-4o", "gemini-flash", "llama-70b", "deepseek",
            "claude-haiku", "gpt-4o-mini", "gemini-pro",
          ]);
          const filtered = (data.models as ModelOption[]).filter(
            (m) => primaryAliases.has(m.alias)
          );
          if (filtered.length > 0) setModels(filtered);
        }
      })
      .catch(() => {
        // Use defaults silently
      });
  }, []);

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const currentMeta = PROVIDER_META[
    models.find((m) => m.alias === selectedModel)?.provider || "anthropic"
  ] || PROVIDER_META.anthropic;
  const CurrentIcon = currentMeta.icon;

  if (!expanded) {
    // Collapsed: just show the provider icon
    return (
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-center py-1"
        title={`Model: ${MODEL_LABELS[selectedModel] || selectedModel}`}
      >
        <CurrentIcon className={cn("h-4 w-4", currentMeta.color)} />
      </button>
    );
  }

  return (
    <div ref={ref} className="relative">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left transition-colors",
          "border border-zinc-700/50 bg-zinc-800/50 hover:bg-zinc-800",
        )}
      >
        <CurrentIcon className={cn("h-3.5 w-3.5 shrink-0", currentMeta.color)} />
        <span className="flex-1 truncate text-xs font-medium text-zinc-300">
          {MODEL_LABELS[selectedModel] || selectedModel}
        </span>
        <ChevronDown
          className={cn(
            "h-3 w-3 shrink-0 text-zinc-500 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.15, ease: [0, 0, 0.2, 1] }}
            className="absolute bottom-full left-0 right-0 mb-1 z-50 rounded-lg border border-zinc-700 bg-zinc-900 shadow-xl shadow-black/40 overflow-hidden"
          >
            <div className="px-2.5 py-2 border-b border-zinc-800">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                Select Model
              </p>
            </div>
            <div className="max-h-64 overflow-y-auto py-1">
              {models.map((m) => {
                const meta = PROVIDER_META[m.provider] || PROVIDER_META.anthropic;
                const Icon = meta.icon;
                const isSelected = m.alias === selectedModel;

                return (
                  <button
                    key={m.alias}
                    type="button"
                    onClick={() => {
                      setSelectedModel(m.alias);
                      setOpen(false);
                    }}
                    className={cn(
                      "flex w-full items-center gap-2.5 px-2.5 py-2 text-left transition-colors",
                      isSelected
                        ? "bg-violet-500/10 text-violet-300"
                        : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200",
                    )}
                  >
                    <Icon className={cn("h-3.5 w-3.5 shrink-0", meta.color)} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate">
                        {MODEL_LABELS[m.alias] || m.alias}
                      </p>
                      <p className="text-[10px] text-zinc-600">{meta.label}</p>
                    </div>
                    {m.available ? (
                      <span className="shrink-0 h-1.5 w-1.5 rounded-full bg-emerald-400" title="API key configured" />
                    ) : (
                      <span className="shrink-0 h-1.5 w-1.5 rounded-full bg-zinc-600" title="No API key" />
                    )}
                    {isSelected && <Check className="h-3 w-3 shrink-0 text-violet-400" />}
                  </button>
                );
              })}
            </div>
            <div className="px-2.5 py-1.5 border-t border-zinc-800">
              <p className="text-[10px] text-zinc-600">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400 mr-1" />
                API key set
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-zinc-600 mx-1 ml-3" />
                Not configured
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
