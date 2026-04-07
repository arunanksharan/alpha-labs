"use client";

import { useRef, useMemo, useCallback, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import dynamic from "next/dynamic";

import type { FC } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface VolSurface3DProps {
  data?: { strike: number; expiry: number; iv: number }[];
  className?: string;
}

// ---------------------------------------------------------------------------
// Three.js scene (loaded only on client)
// ---------------------------------------------------------------------------

const Scene = dynamic(() => import("./vol-surface-scene"), { ssr: false });

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const VolSurface3D: FC<VolSurface3DProps> = ({ data, className }) => {
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
        Implied Volatility Surface
      </h3>

      <div className="relative h-[400px] w-full overflow-hidden rounded-lg">
        {mounted ? (
          <Scene data={data} />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-zinc-600">
            Loading 3D surface...
          </div>
        )}
      </div>
    </div>
  );
};

export default VolSurface3D;
