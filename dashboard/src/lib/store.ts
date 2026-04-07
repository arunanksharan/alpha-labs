import { create } from "zustand";
import type { AgentEvent, ResearchResult, Signal, BacktestMetrics } from "@/types";

interface AppState {
  // Mode
  mode: "demo" | "live";
  setMode: (mode: "demo" | "live") => void;

  // Connection
  connected: boolean;
  setConnected: (c: boolean) => void;

  // Agent events
  events: AgentEvent[];
  addEvent: (e: AgentEvent) => void;
  clearEvents: () => void;

  // Research results
  currentResult: ResearchResult | null;
  setResult: (r: ResearchResult | null) => void;

  // Signals
  signals: Signal[];
  setSignals: (s: Signal[]) => void;

  // Approval
  approvalPending: boolean;
  setApprovalPending: (p: boolean) => void;
  currentRunId: string | null;
  setCurrentRunId: (id: string | null) => void;

  // Metrics
  metrics: BacktestMetrics | null;
  setMetrics: (m: BacktestMetrics | null) => void;

  // Model selection
  selectedModel: string;
  setSelectedModel: (model: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Mode
  mode: "demo",
  setMode: (mode) => set({ mode }),

  // Connection
  connected: false,
  setConnected: (connected) => set({ connected }),

  // Agent events
  events: [],
  addEvent: (e) =>
    set((state) => ({ events: [...state.events.slice(-99), e] })),
  clearEvents: () => set({ events: [] }),

  // Research results
  currentResult: null,
  setResult: (currentResult) => set({ currentResult }),

  // Signals
  signals: [],
  setSignals: (signals) => set({ signals }),

  // Approval
  approvalPending: false,
  setApprovalPending: (approvalPending) => set({ approvalPending }),
  currentRunId: null,
  setCurrentRunId: (currentRunId) => set({ currentRunId }),

  // Metrics
  metrics: null,
  setMetrics: (metrics) => set({ metrics }),

  // Model selection
  selectedModel: "claude-sonnet",
  setSelectedModel: (selectedModel) => set({ selectedModel }),
}));
