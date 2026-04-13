"use client";

import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import type { ICCurvePoint } from "@/types";

interface SignalDecayChartProps {
  data: ICCurvePoint[];
  halfLife?: number;
  title?: string;
}

export function SignalDecayChart({
  data,
  halfLife,
  title = "Signal Decay — IC Curve",
}: SignalDecayChartProps) {
  if (!data.length) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900/50">
        <p className="text-sm text-zinc-500">No decay data</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium uppercase tracking-wider text-zinc-400">{title}</h3>
        {halfLife !== undefined && (
          <span className="rounded-full bg-violet-500/10 px-3 py-1 text-xs font-medium text-violet-400">
            Half-life: {halfLife.toFixed(1)} days
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="horizon"
            tick={{ fill: "#71717a", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "#27272a" }}
            label={{ value: "Forward Days", position: "insideBottom", fill: "#71717a", offset: -5 }}
          />
          <YAxis
            tick={{ fill: "#71717a", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "#27272a" }}
            label={{ value: "IC", angle: -90, position: "insideLeft", fill: "#71717a" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#18181b",
              border: "1px solid #3f3f46",
              borderRadius: "8px",
              color: "#f4f4f5",
            }}
            formatter={(value) => [Number(value).toFixed(4), "IC"]}
          />
          <ReferenceLine y={0} stroke="#3f3f46" strokeDasharray="3 3" />
          {halfLife !== undefined && (
            <ReferenceLine
              x={Math.round(halfLife)}
              stroke="#8b5cf6"
              strokeDasharray="5 5"
              label={{ value: "½", fill: "#8b5cf6", position: "top" }}
            />
          )}
          <Line
            type="monotone"
            dataKey="ic"
            stroke="#06b6d4"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#06b6d4" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  );
}
