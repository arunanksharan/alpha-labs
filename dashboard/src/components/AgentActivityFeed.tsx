"use client";

import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { AgentEvent } from "@/types";
import {
  Search,
  ShieldCheck,
  BarChart3,
  TrendingDown,
  FileText,
  UserCheck,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Clock,
} from "lucide-react";

const AGENT_ICONS: Record<string, typeof Search> = {
  research: Search,
  risk: ShieldCheck,
  validation: BarChart3,
  decay: TrendingDown,
  report: FileText,
  human: UserCheck,
};

const STATUS_STYLES: Record<string, { icon: typeof CheckCircle; color: string }> = {
  completed: { icon: CheckCircle, color: "text-emerald-400" },
  running: { icon: Loader2, color: "text-violet-400 animate-spin" },
  pending: { icon: Clock, color: "text-zinc-500" },
  failed: { icon: XCircle, color: "text-red-400" },
  awaiting_approval: { icon: AlertTriangle, color: "text-amber-400" },
  approved: { icon: CheckCircle, color: "text-emerald-400" },
  rejected: { icon: XCircle, color: "text-red-400" },
};

interface AgentActivityFeedProps {
  events: AgentEvent[];
  className?: string;
}

export function AgentActivityFeed({ events, className }: AgentActivityFeedProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.15 }}
      className={cn(
        "rounded-xl border border-zinc-800 bg-zinc-900/50 p-5",
        className
      )}
    >
      <h3 className="mb-4 text-sm font-medium uppercase tracking-wider text-zinc-400">
        Agent Activity
      </h3>
      <div className="max-h-96 space-y-2 overflow-y-auto">
        <AnimatePresence mode="popLayout">
          {events.length === 0 && (
            <p className="py-8 text-center text-sm text-zinc-600">
              No agent activity yet. Start a research run.
            </p>
          )}
          {[...events].reverse().map((event, i) => {
            const AgentIcon = AGENT_ICONS[event.agent_name] || Search;
            const statusConfig = STATUS_STYLES[event.status] || STATUS_STYLES.pending;
            const StatusIcon = statusConfig.icon;

            return (
              <motion.div
                key={`${event.timestamp}-${i}`}
                initial={{ opacity: 0, x: -20, height: 0 }}
                animate={{ opacity: 1, x: 0, height: "auto" }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.2, ease: [0, 0, 0.2, 1] }}
                className="flex items-start gap-3 rounded-lg border border-zinc-800/50 bg-zinc-950/50 px-3 py-2.5"
              >
                <div className="mt-0.5 rounded-md bg-zinc-800 p-1.5">
                  <AgentIcon className="h-3.5 w-3.5 text-violet-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase text-zinc-300">
                      {event.agent_name}
                    </span>
                    <StatusIcon className={cn("h-3 w-3", statusConfig.color)} />
                  </div>
                  <p className="mt-0.5 text-sm text-zinc-400 truncate">{event.message}</p>
                </div>
                <span className="shrink-0 text-[10px] text-zinc-600" suppressHydrationWarning>
                  {event.timestamp
                    ? new Date(event.timestamp).toLocaleTimeString("en-GB", { hour12: false })
                    : ""}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
