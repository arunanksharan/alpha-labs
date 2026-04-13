"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Search,
  Shield,
  UserCheck,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  Bot,
  RefreshCw,
  XCircle,
  Play,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_URL } from "@/lib/utils";

type StepStatus = "completed" | "running" | "awaiting" | "pending" | "failed";

interface PipelineStep {
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  status: StepStatus;
  message: string;
}

const STATUS_CONFIG: Record<StepStatus, { color: string; bg: string; border: string; label: string; pulse: boolean }> = {
  running: { color: "text-violet-400", bg: "bg-violet-500/15", border: "border-violet-500/40", label: "Running", pulse: true },
  completed: { color: "text-emerald-400", bg: "bg-emerald-500/15", border: "border-emerald-500/40", label: "Completed", pulse: false },
  awaiting: { color: "text-amber-400", bg: "bg-amber-500/15", border: "border-amber-500/40", label: "Awaiting", pulse: true },
  pending: { color: "text-zinc-500", bg: "bg-zinc-500/10", border: "border-zinc-700", label: "Pending", pulse: false },
  failed: { color: "text-red-400", bg: "bg-red-500/15", border: "border-red-500/40", label: "Failed", pulse: false },
};

interface JobData {
  id: string;
  status: string;
  params: Record<string, unknown>;
  progress: number;
  progress_stage: string;
  progress_message: string;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

// Map job progress_stage to pipeline step index
const STAGE_TO_STEP: Record<string, number> = {
  queued: -1,
  fetching_data: 0,
  resolving_strategy: 0,
  computing_features: 1,
  generating_signals: 1,
  evaluating_risk: 2,
  running_backtest: 3,
  validating: 4,
  signal_decay: 4,
  complete: 5,
};

function derivePipelineFromJob(job: JobData | null): PipelineStep[] {
  const steps: PipelineStep[] = [
    { name: "Data & Features", icon: Search, status: "pending", message: "Fetch OHLCV, compute z-scores, RSI, MACD" },
    { name: "Signal Generation", icon: Shield, status: "pending", message: "Strategy rules → entry/exit signals" },
    { name: "Risk Evaluation", icon: UserCheck, status: "pending", message: "Position limits, Kelly sizing, VaR" },
    { name: "Backtest Engine", icon: CheckCircle2, status: "pending", message: "Daily equity curve, transaction costs" },
    { name: "Validation & Decay", icon: Clock, status: "pending", message: "Deflated Sharpe, IC curve, half-life" },
    { name: "Results", icon: FileText, status: "pending", message: "Metrics, equity curve, report" },
  ];

  if (!job) return steps;

  if (job.status === "completed") {
    // All steps completed
    for (const s of steps) s.status = "completed";
    const bt = (job.result as Record<string, unknown>)?.backtest as Record<string, unknown> | undefined;
    if (bt) {
      steps[5].message = `Return ${((bt.total_return as number) * 100).toFixed(1)}%, Sharpe ${(bt.sharpe_ratio as number)?.toFixed(2)}`;
    }
    return steps;
  }

  if (job.status === "failed") {
    const failStep = STAGE_TO_STEP[job.progress_stage] ?? 0;
    for (let i = 0; i < failStep; i++) steps[i].status = "completed";
    steps[failStep].status = "failed";
    steps[failStep].message = job.error || "Failed";
    return steps;
  }

  if (job.status === "running") {
    const currentStep = STAGE_TO_STEP[job.progress_stage] ?? 0;
    for (let i = 0; i < currentStep; i++) steps[i].status = "completed";
    if (currentStep >= 0 && currentStep < steps.length) {
      steps[currentStep].status = "running";
      steps[currentStep].message = job.progress_message || job.progress_stage;
    }
    return steps;
  }

  return steps;
}

export default function AgentsPage() {
  const [jobs, setJobs] = useState<JobData[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function fetchJobs() {
      try {
        const token = localStorage.getItem("access_token");
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${API_URL}/api/jobs?limit=20`, { headers });
        if (res.ok) {
          const data = await res.json();
          setJobs(data.jobs || []);
        }
      } catch {} finally { setLoading(false); }
    }
    fetchJobs();
    const interval = setInterval(fetchJobs, 2000);
    return () => clearInterval(interval);
  }, []);

  // Derive pipeline from the most recent job (running > latest completed)
  const activeJob = jobs.find((j) => j.status === "running") || jobs.find((j) => j.status === "completed") || null;
  const pipelineSteps = useMemo(() => derivePipelineFromJob(activeJob), [activeJob]);
  const pipelineLabel = activeJob
    ? `${activeJob.params.ticker} / ${activeJob.params.strategy} — ${activeJob.status}`
    : "No active job";

  const runningJobs = jobs.filter((j) => j.status === "running");
  const completedJobs = jobs.filter((j) => j.status === "completed");

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-lg">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-zinc-50">Agent Pipeline</h1>
              <p className="mt-1 text-sm text-zinc-500">Monitor the agentic research pipeline in real time</p>
            </div>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              onClick={() => router.push("/jobs")}
              className="flex items-center gap-2 rounded-lg border border-violet-500/50 px-4 py-2 text-sm font-medium text-violet-400 hover:bg-violet-500/10">
              <Play className="h-3.5 w-3.5" /> Submit New Job
            </motion.button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 py-6 space-y-6">
        {/* Pipeline — derived from most recent job */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-400">Pipeline Status</h2>
            <span className="text-xs text-zinc-500 font-mono">{pipelineLabel}</span>
          </div>
          <div className="relative pl-8">
            {pipelineSteps.map((step, i) => {
              const config = STATUS_CONFIG[step.status];
              const Icon = step.icon;
              const isLast = i === pipelineSteps.length - 1;

              return (
                <motion.div key={step.name}
                  initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06, type: "spring", stiffness: 300, damping: 25 }}
                  className="relative pb-5 last:pb-0">
                  {!isLast && <div className="absolute left-[7px] top-8 bottom-0 w-px bg-gradient-to-b from-zinc-700 to-zinc-800" />}
                  <div className="flex items-start gap-4">
                    <div className={cn("relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border", config.border, config.bg)}>
                      {config.pulse && <span className={cn("absolute inset-0 animate-ping rounded-full opacity-30", step.status === "running" ? "bg-violet-500" : "bg-amber-500")} />}
                      <Icon className={cn("h-4 w-4", config.color)} />
                    </div>
                    <div className="min-w-0 flex-1 pt-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-medium text-zinc-200">{step.name}</h3>
                        <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", config.bg, config.color)}>{config.label}</span>
                      </div>
                      <p className="mt-0.5 text-xs text-zinc-500">{step.message}</p>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Running Jobs with progress */}
        {runningJobs.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-5">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-medium uppercase tracking-wider text-violet-400">
              <Loader2 className="h-4 w-4 animate-spin" /> Active Jobs
            </h2>
            <div className="space-y-3">
              {runningJobs.map((job) => (
                <div key={job.id} className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-sm text-zinc-200">{job.params.ticker as string} / {job.params.strategy as string}</span>
                    <span className="text-xs text-zinc-500">{Math.round(job.progress * 100)}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                    <motion.div className="h-full bg-violet-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${job.progress * 100}%` }} transition={{ duration: 0.5 }} />
                  </div>
                  <p className="mt-1.5 text-[10px] text-zinc-600">{job.progress_message || job.progress_stage}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Recent Completed Jobs */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wider text-zinc-400">Recent Results</h2>
          {loading ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-zinc-500" /></div>
          ) : completedJobs.length === 0 ? (
            <div className="py-8 text-center">
              <Bot className="mx-auto h-8 w-8 text-zinc-700 mb-2" />
              <p className="text-sm text-zinc-500">No completed jobs yet.</p>
              <button onClick={() => router.push("/jobs")} className="mt-3 text-xs text-violet-400 hover:text-violet-300">Submit a backtest →</button>
            </div>
          ) : (
            <div className="space-y-2">
              {completedJobs.slice(0, 10).map((job) => {
                const bt = (job.result as Record<string, unknown>)?.backtest as Record<string, unknown> | undefined;
                const ret = (bt?.total_return as number) || 0;
                const duration = job.completed_at ? `${((new Date(job.completed_at).getTime() - new Date(job.created_at).getTime()) / 1000).toFixed(1)}s` : "";

                return (
                  <button key={job.id} type="button" onClick={() => router.push("/jobs")}
                    className="flex w-full items-center gap-3 rounded-lg border border-zinc-800/50 bg-zinc-900/30 px-3 py-2.5 text-left hover:bg-zinc-800/30 transition-colors">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                    <div className="flex-1 min-w-0">
                      <span className="font-mono text-xs font-medium text-zinc-200">{job.params.ticker as string}</span>
                      <span className="ml-2 rounded bg-zinc-800 px-1.5 py-0.5 text-[9px] text-violet-300">{job.params.strategy as string}</span>
                    </div>
                    <span className={cn("text-xs font-mono", ret > 0 ? "text-emerald-400" : "text-red-400")}>{(ret * 100).toFixed(1)}%</span>
                    {bt && <span className="text-xs text-zinc-600">Sharpe {(bt.sharpe_ratio as number)?.toFixed(2)}</span>}
                    {duration && <span className="text-[10px] text-zinc-600 tabular-nums">{duration}</span>}
                  </button>
                );
              })}
            </div>
          )}
        </motion.div>
      </main>
    </div>
  );
}
