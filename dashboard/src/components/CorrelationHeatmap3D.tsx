"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import dynamic from "next/dynamic";

import type { FC } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CorrelationHeatmap3DProps {
  tickers?: string[];
  correlations?: number[][]; // NxN matrix, values -1 to 1
  className?: string;
}

// ---------------------------------------------------------------------------
// Three.js scene (loaded only on client)
// ---------------------------------------------------------------------------

const Scene = dynamic(() => import("./correlation-heatmap-scene"), { ssr: false });

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const CorrelationHeatmap3D: FC<CorrelationHeatmap3DProps> = ({
  tickers,
  correlations,
  className,
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div
      className={cn(
        "rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-sm",
        className
      )}
    >
      <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-zinc-400">
        Correlation Heatmap
      </h3>

      <div className="relative h-[400px] w-full overflow-hidden rounded-lg">
        {mounted ? (
          <Scene tickers={tickers} correlations={correlations} />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-zinc-600">
            Loading 3D heatmap...
          </div>
        )}
      </div>
    </div>
  );
};

export default CorrelationHeatmap3D;
