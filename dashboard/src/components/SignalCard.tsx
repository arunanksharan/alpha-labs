"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import type { Signal } from "@/types";

interface SignalCardProps {
  signal: Signal;
  index?: number;
}

export function SignalCard({ signal, index = 0 }: SignalCardProps) {
  const isLong = signal.direction > 0;
  const isShort = signal.direction < 0;
  const isFlat = signal.direction === 0;

  const Icon = isLong ? ArrowUpRight : isShort ? ArrowDownRight : Minus;
  const directionLabel = isLong ? "LONG" : isShort ? "SHORT" : "FLAT";
  const directionColor = isLong
    ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20"
    : isShort
    ? "text-red-400 bg-red-400/10 border-red-400/20"
    : "text-zinc-400 bg-zinc-400/10 border-zinc-400/20";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: index * 0.05, ease: [0.34, 1.56, 0.64, 1] }}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold text-zinc-50">{signal.ticker}</span>
          <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", directionColor)}>
            {directionLabel}
          </span>
        </div>
        <Icon className={cn("h-5 w-5", isLong ? "text-emerald-400" : isShort ? "text-red-400" : "text-zinc-400")} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <p className="text-[10px] uppercase text-zinc-500">Confidence</p>
          <div className="mt-1 h-1.5 rounded-full bg-zinc-800">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${signal.confidence * 100}%` }}
              transition={{ duration: 0.6, delay: index * 0.05 + 0.2 }}
              className="h-full rounded-full bg-violet-500"
            />
          </div>
          <p className="mt-0.5 text-xs text-zinc-400">{(signal.confidence * 100).toFixed(0)}%</p>
        </div>
        <div>
          <p className="text-[10px] uppercase text-zinc-500">Date</p>
          <p className="mt-1 text-xs text-zinc-400">{signal.date}</p>
        </div>
      </div>
    </motion.div>
  );
}
