"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  subtext?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export function MetricCard({ label, value, subtext, trend, className }: MetricCardProps) {
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor = trend === "up" ? "text-emerald-400" : trend === "down" ? "text-red-400" : "text-zinc-400";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0, 0, 0.2, 1] }}
      className={cn(
        "rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-sm",
        className
      )}
    >
      <p className="text-xs font-medium uppercase tracking-wider text-zinc-400">{label}</p>
      <div className="mt-2 flex items-baseline gap-2">
        <p className="text-2xl font-semibold text-zinc-50">{value}</p>
        {trend && <TrendIcon className={cn("h-4 w-4", trendColor)} />}
      </div>
      {subtext && <p className="mt-1 text-xs text-zinc-500">{subtext}</p>}
    </motion.div>
  );
}
