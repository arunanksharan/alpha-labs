"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Shield,
  UserCheck,
  CheckCircle2,
  Clock,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ---------- Agent pipeline steps ---------- */

type StepStatus = "completed" | "running" | "awaiting" | "pending" | "failed";

interface PipelineStep {
  name: string;
  icon: React.ElementType;
  status: StepStatus;
  message: string;
}

const PIPELINE_STEPS: PipelineStep[] = [
  {
    name: "Research Agent",
    icon: Search,
    status: "completed",
    message: "Fetched 500 days OHLCV, computed features, generated 6 signals",
  },
  {
    name: "Risk Agent",
    icon: Shield,
    status: "completed",
    message: "5 signals approved, 1 rejected (TSLA: exposure limit)",
  },
  {
    name: "Approval Gate",
    icon: UserCheck,
    status: "awaiting",
    message: "Awaiting human review for 5 signals",
  },
  {
    name: "Validation Agent",
    icon: CheckCircle2,
    status: "pending",
    message: "Pending approval gate",
  },
  {
    name: "Signal Decay",
    icon: Clock,
    status: "pending",
    message: "Waiting for validation",
  },
  {
    name: "Report Generator",
    icon: FileText,
    status: "pending",
    message: "Queued",
  },
];

const STATUS_CONFIG: Record<
  StepStatus,
  { color: string; bg: string; border: string; label: string; pulse: boolean }
> = {
  running: {
    color: "text-violet-400",
    bg: "bg-violet-500/15",
    border: "border-violet-500/40",
    label: "Running",
    pulse: true,
  },
  completed: {
    color: "text-emerald-400",
    bg: "bg-emerald-500/15",
    border: "border-emerald-500/40",
    label: "Completed",
    pulse: false,
  },
  failed: {
    color: "text-red-400",
    bg: "bg-red-500/15",
    border: "border-red-500/40",
    label: "Failed",
    pulse: false,
  },
  awaiting: {
    color: "text-amber-400",
    bg: "bg-amber-500/15",
    border: "border-amber-500/40",
    label: "Awaiting",
    pulse: true,
  },
  pending: {
    color: "text-zinc-500",
    bg: "bg-zinc-500/10",
    border: "border-zinc-700",
    label: "Pending",
    pulse: false,
  },
};

/* ---------- Page ---------- */

export default function AgentsPage() {
  const [visibleSteps, setVisibleSteps] = useState(0);

  useEffect(() => {
    if (visibleSteps < PIPELINE_STEPS.length) {
      const timer = setTimeout(
        () => setVisibleSteps((v) => v + 1),
        400 + visibleSteps * 200
      );
      return () => clearTimeout(timer);
    }
  }, [visibleSteps]);

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
            Agent Pipeline
          </motion.h1>
          <p className="mt-1 text-sm text-zinc-500">
            Monitor the agentic research pipeline in real time
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-8 px-6 py-8">
        {/* Agent Timeline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
        >
          <h2 className="mb-6 text-sm font-medium uppercase tracking-wider text-zinc-400">
            Agent Timeline
          </h2>

          <div className="relative ml-4">
            {/* Vertical connector line */}
            <div className="absolute left-5 top-2 bottom-2 w-px bg-zinc-800" />

            <div className="space-y-1">
              {PIPELINE_STEPS.map((step, i) => {
                const config = STATUS_CONFIG[step.status];
                const Icon = step.icon;
                const isVisible = i < visibleSteps;

                return (
                  <motion.div
                    key={step.name}
                    initial={{ opacity: 0, x: -20 }}
                    animate={
                      isVisible
                        ? { opacity: 1, x: 0 }
                        : { opacity: 0, x: -20 }
                    }
                    transition={{
                      duration: 0.35,
                      ease: [0, 0, 0.2, 1],
                    }}
                    className="relative flex items-start gap-4 py-3"
                  >
                    {/* Icon circle */}
                    <div
                      className={cn(
                        "relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border",
                        config.bg,
                        config.border
                      )}
                    >
                      {config.pulse && (
                        <span
                          className={cn(
                            "absolute inset-0 animate-ping rounded-full opacity-20",
                            step.status === "running"
                              ? "bg-violet-500"
                              : "bg-amber-500"
                          )}
                        />
                      )}
                      <Icon className={cn("h-4 w-4", config.color)} />
                    </div>

                    {/* Content */}
                    <div className="min-w-0 flex-1 pt-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-zinc-200">
                          {step.name}
                        </span>
                        <span
                          className={cn(
                            "rounded-full border px-2 py-0.5 text-[10px] font-medium",
                            config.bg,
                            config.border,
                            config.color
                          )}
                        >
                          {config.label}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-zinc-500">
                        {step.message}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </motion.div>

        {/* 3D Visualization Placeholders */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Vol Surface */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
                3D Vol Surface
              </h3>
              <span className="rounded-full border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-500">
                Three.js
              </span>
            </div>
            <div className="relative flex h-64 items-center justify-center overflow-hidden rounded-lg">
              {/* CSS gradient mesh placeholder */}
              <div
                className="absolute inset-0"
                style={{
                  background: `
                    radial-gradient(ellipse at 20% 50%, rgba(139, 92, 246, 0.25) 0%, transparent 50%),
                    radial-gradient(ellipse at 80% 20%, rgba(6, 182, 212, 0.2) 0%, transparent 50%),
                    radial-gradient(ellipse at 60% 80%, rgba(245, 158, 11, 0.15) 0%, transparent 50%),
                    radial-gradient(ellipse at 40% 30%, rgba(139, 92, 246, 0.1) 0%, transparent 40%),
                    linear-gradient(180deg, rgba(24, 24, 27, 0.8) 0%, rgba(24, 24, 27, 1) 100%)
                  `,
                }}
              />
              {/* Grid lines overlay */}
              <div
                className="absolute inset-0 opacity-20"
                style={{
                  backgroundImage: `
                    linear-gradient(rgba(139, 92, 246, 0.3) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(139, 92, 246, 0.3) 1px, transparent 1px)
                  `,
                  backgroundSize: "30px 30px",
                  transform: "perspective(400px) rotateX(30deg)",
                  transformOrigin: "center bottom",
                }}
              />
              <div className="shimmer-container relative z-10 text-center">
                <AlertTriangle className="mx-auto mb-2 h-5 w-5 text-zinc-600" />
                <p className="text-sm text-zinc-500 shimmer-text">
                  Loading 3D...
                </p>
                <p className="mt-1 text-[10px] text-zinc-700">
                  Three.js integration pending
                </p>
              </div>
            </div>
          </motion.div>

          {/* Correlation */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-medium uppercase tracking-wider text-zinc-400">
                3D Correlation
              </h3>
              <span className="rounded-full border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-500">
                Three.js
              </span>
            </div>
            <div className="relative flex h-64 items-center justify-center overflow-hidden rounded-lg">
              {/* CSS gradient mesh placeholder */}
              <div
                className="absolute inset-0"
                style={{
                  background: `
                    radial-gradient(ellipse at 30% 60%, rgba(16, 185, 129, 0.2) 0%, transparent 50%),
                    radial-gradient(ellipse at 70% 30%, rgba(59, 130, 246, 0.2) 0%, transparent 50%),
                    radial-gradient(ellipse at 50% 50%, rgba(239, 68, 68, 0.1) 0%, transparent 40%),
                    linear-gradient(180deg, rgba(24, 24, 27, 0.8) 0%, rgba(24, 24, 27, 1) 100%)
                  `,
                }}
              />
              {/* Scatter dots overlay */}
              <div className="absolute inset-0 opacity-30">
                {Array.from({ length: 30 }).map((_, i) => (
                  <div
                    key={i}
                    className="absolute h-1.5 w-1.5 rounded-full bg-cyan-400"
                    style={{
                      left: `${15 + Math.random() * 70}%`,
                      top: `${15 + Math.random() * 70}%`,
                      opacity: 0.3 + Math.random() * 0.5,
                    }}
                  />
                ))}
              </div>
              <div className="shimmer-container relative z-10 text-center">
                <AlertTriangle className="mx-auto mb-2 h-5 w-5 text-zinc-600" />
                <p className="text-sm text-zinc-500 shimmer-text">
                  Loading 3D...
                </p>
                <p className="mt-1 text-[10px] text-zinc-700">
                  Three.js integration pending
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </main>

      {/* Shimmer animation */}
      <style jsx>{`
        .shimmer-text {
          background: linear-gradient(
            90deg,
            #71717a 0%,
            #a1a1aa 50%,
            #71717a 100%
          );
          background-size: 200% 100%;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          animation: shimmer 2s ease-in-out infinite;
        }
        @keyframes shimmer {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }
      `}</style>
    </div>
  );
}
