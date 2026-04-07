"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";

interface ApprovalPanelProps {
  signalsCount: number;
  rejectedCount: number;
  warnings: string[];
  onApprove: () => void;
  onReject: () => void;
  isPending: boolean;
}

export function ApprovalPanel({
  signalsCount,
  rejectedCount,
  warnings,
  onApprove,
  onReject,
  isPending,
}: ApprovalPanelProps) {
  if (!isPending) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
      className="rounded-xl border-2 border-amber-400/30 bg-amber-400/5 p-6"
    >
      <div className="flex items-center gap-3 mb-4">
        <AlertTriangle className="h-5 w-5 text-amber-400" />
        <h3 className="text-lg font-semibold text-zinc-50">Human Approval Required</h3>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="rounded-lg bg-zinc-900/50 p-3">
          <p className="text-xs text-zinc-500">Approved Signals</p>
          <p className="text-xl font-bold text-emerald-400">{signalsCount}</p>
        </div>
        <div className="rounded-lg bg-zinc-900/50 p-3">
          <p className="text-xs text-zinc-500">Risk Rejected</p>
          <p className="text-xl font-bold text-red-400">{rejectedCount}</p>
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="mb-4 space-y-1">
          {warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-300/70">
              {w}
            </p>
          ))}
        </div>
      )}

      <div className="flex gap-3">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onApprove}
          className={cn(
            "flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-3",
            "bg-emerald-500 text-white font-medium",
            "hover:bg-emerald-400 transition-colors"
          )}
        >
          <CheckCircle className="h-4 w-4" />
          Approve & Execute
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onReject}
          className={cn(
            "flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-3",
            "border border-red-500/30 text-red-400 font-medium",
            "hover:bg-red-500/10 transition-colors"
          )}
        >
          <XCircle className="h-4 w-4" />
          Reject
        </motion.button>
      </div>
    </motion.div>
  );
}
