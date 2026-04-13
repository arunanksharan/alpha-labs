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

const MODEL_LABELS: Record<string, string> = {
  "claude-sonnet": "Claude Sonnet 4",
  "claude-haiku": "Claude Haiku 4.5",
  "claude-opus": "Claude Opus 4",
  "gpt-4o": "GPT-4o",
  "gpt-4o-mini": "GPT-4o Mini",
  "gpt-5-mini": "GPT-5 Mini",
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
  const [models, setModels] = useState<ModelOption[]>([]);
  const [defaultModel, setDefaultModel] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/models`)
      .then((r) => r.json())
      .then((data) => {
        if (data.models) {
          setModels(data.models as ModelOption[]);
        }
        if (data.default_model && !defaultModel) {
          setDefaultModel(data.default_model);
          setSelectedModel(data.default_model);
        }
      })
      .catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Sort: available first, then alphabetical
  const sortedModels = [...models].sort((a, b) => {
    if (a.available !== b.available) return a.available ? -1 : 1;
    return (MODEL_LABELS[a.alias] || a.alias).localeCompare(MODEL_LABELS[b.alias] || b.alias);
  });

  const availableCount = models.filter((m) => m.available).length;

  const currentMeta = PROVIDER_META[
    models.find((m) => m.alias === selectedModel)?.provider || "openai"
  ] || PROVIDER_META.openai;
  const CurrentIcon = currentMeta.icon;

  if (!expanded) {
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
          className={cn("h-3 w-3 shrink-0 text-zinc-500 transition-transform", open && "rotate-180")}
        />
      </button>

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
                {availableCount > 0 ? `${availableCount} model${availableCount > 1 ? "s" : ""} available` : "No API keys configured"}
              </p>
            </div>
            <div className="max-h-64 overflow-y-auto py-1">
              {availableCount > 0 && sortedModels.some(m => m.available) && sortedModels.some(m => !m.available) && (
                <>
                  {/* Available models */}
                  {sortedModels.filter(m => m.available).map((m) => renderModelItem(m, selectedModel, setSelectedModel, setOpen))}
                  {/* Divider */}
                  <div className="mx-2.5 my-1 border-t border-zinc-800" />
                  <p className="px-2.5 py-1 text-[9px] uppercase tracking-wider text-zinc-600">Other models</p>
                  {/* Unavailable models */}
                  {sortedModels.filter(m => !m.available).map((m) => renderModelItem(m, selectedModel, setSelectedModel, setOpen))}
                </>
              )}
              {/* If no split needed, just render all */}
              {(availableCount === 0 || !sortedModels.some(m => !m.available)) &&
                sortedModels.map((m) => renderModelItem(m, selectedModel, setSelectedModel, setOpen))
              }
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

function renderModelItem(
  m: ModelOption,
  selectedModel: string,
  setSelectedModel: (s: string) => void,
  setOpen: (b: boolean) => void,
) {
  const meta = PROVIDER_META[m.provider] || PROVIDER_META.openai;
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
          : m.available
            ? "text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
            : "text-zinc-600 hover:bg-zinc-800/50 hover:text-zinc-500",
      )}
    >
      <Icon className={cn("h-3.5 w-3.5 shrink-0", m.available ? meta.color : "text-zinc-600")} />
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
}
