"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

/* ── Types ── */

interface Thought {
  timestamp: string;
  agent: string;
  message: string;
  type?: "info" | "analysis" | "decision" | "warning";
}

export interface ThoughtStreamProps {
  thoughts: Thought[];
  isLive: boolean;
  className?: string;
}

/* ── Agent badge config ── */

const AGENT_CONFIG: Record<
  string,
  { icon: string; label: string; dotColor: string; badgeBg: string; badgeText: string }
> = {
  quant: {
    icon: "\uD83D\uDD2C",
    label: "Quant",
    dotColor: "bg-violet-400",
    badgeBg: "bg-violet-500/15",
    badgeText: "text-violet-400",
  },
  technician: {
    icon: "\uD83D\uDCCA",
    label: "Technician",
    dotColor: "bg-cyan-400",
    badgeBg: "bg-cyan-500/15",
    badgeText: "text-cyan-400",
  },
  contrarian: {
    icon: "\uD83D\uDE08",
    label: "Contrarian",
    dotColor: "bg-red-400",
    badgeBg: "bg-red-500/15",
    badgeText: "text-red-400",
  },
  sentiment: {
    icon: "\uD83D\uDCAC",
    label: "Sentiment",
    dotColor: "bg-amber-400",
    badgeBg: "bg-amber-500/15",
    badgeText: "text-amber-400",
  },
  fundamentalist: {
    icon: "\uD83D\uDCCB",
    label: "Fundamentalist",
    dotColor: "bg-emerald-400",
    badgeBg: "bg-emerald-500/15",
    badgeText: "text-emerald-400",
  },
  macro: {
    icon: "\uD83C\uDF10",
    label: "Macro",
    dotColor: "bg-blue-400",
    badgeBg: "bg-blue-500/15",
    badgeText: "text-blue-400",
  },
  risk: {
    icon: "\uD83D\uDEE1\uFE0F",
    label: "Risk",
    dotColor: "bg-orange-400",
    badgeBg: "bg-orange-500/15",
    badgeText: "text-orange-400",
  },
  director: {
    icon: "\uD83D\uDC64",
    label: "Director",
    dotColor: "bg-zinc-200",
    badgeBg: "bg-zinc-500/15",
    badgeText: "text-zinc-200",
  },
  research: {
    icon: "\uD83D\uDD2C",
    label: "Research",
    dotColor: "bg-violet-400",
    badgeBg: "bg-violet-500/15",
    badgeText: "text-violet-400",
  },
};

function getAgentConfig(agent: string) {
  const key = agent.toLowerCase().replace(/^the\s+/, "");
  for (const [k, v] of Object.entries(AGENT_CONFIG)) {
    if (key.includes(k)) return v;
  }
  return {
    icon: "\uD83E\uDD16",
    label: agent,
    dotColor: "bg-zinc-500",
    badgeBg: "bg-zinc-500/15",
    badgeText: "text-zinc-400",
  };
}

/* ── Spring animation ── */

const spring = { type: "spring" as const, stiffness: 500, damping: 32, mass: 0.8 };

/* ── Component ── */

export function ThoughtStream({ thoughts, isLive, className }: ThoughtStreamProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isHovering, setIsHovering] = useState(false);
  const prevLengthRef = useRef(thoughts.length);

  // Auto-scroll to bottom when new thoughts arrive, unless user is hovering
  useEffect(() => {
    if (thoughts.length > prevLengthRef.current && !isHovering && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
    prevLengthRef.current = thoughts.length;
  }, [thoughts.length, isHovering]);

  const handleMouseEnter = useCallback(() => setIsHovering(true), []);
  const handleMouseLeave = useCallback(() => {
    setIsHovering(false);
    // Catch up to bottom on leave
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, []);

  return (
    <div
      className={cn(
        "flex flex-col rounded-xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-sm overflow-hidden",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/60">
        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
          Thought Stream
        </h3>
        {isLive && (
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
            <span className="text-[10px] font-medium uppercase tracking-wider text-emerald-400">
              Live
            </span>
          </div>
        )}
      </div>

      {/* Timeline feed */}
      <div
        ref={scrollRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className="flex-1 overflow-y-auto px-5 py-3"
        style={{ maxHeight: "calc(100vh - 160px)" }}
      >
        {thoughts.length === 0 && (
          <div className="flex items-center justify-center h-32">
            <p className="text-sm text-zinc-600">
              Waiting for agent activity...
            </p>
          </div>
        )}

        <div className="relative">
          {/* Vertical timeline line */}
          {thoughts.length > 0 && (
            <div className="absolute left-[5px] top-2 bottom-2 w-px bg-gradient-to-b from-violet-500/40 via-violet-500/20 to-transparent" />
          )}

          <AnimatePresence initial={false}>
            {thoughts.map((thought, i) => {
              const config = getAgentConfig(thought.agent);
              const isDecision = thought.type === "decision";
              const isWarning = thought.type === "warning";

              const time = (() => {
                try {
                  return new Date(thought.timestamp).toLocaleTimeString("en-GB", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: false,
                  });
                } catch {
                  return thought.timestamp;
                }
              })();

              return (
                <motion.div
                  key={`${thought.timestamp}-${i}`}
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  transition={spring}
                  layout
                  className={cn(
                    "relative flex items-start gap-3 pl-5 py-2",
                    isDecision && "rounded-lg bg-violet-500/[0.06] -mx-2 px-7",
                    isWarning && "rounded-lg bg-amber-500/[0.06] -mx-2 px-7"
                  )}
                >
                  {/* Dot on the timeline */}
                  <span
                    className={cn(
                      "absolute left-0 top-3.5 h-[10px] w-[10px] rounded-full ring-2 ring-zinc-950 shrink-0",
                      config.dotColor
                    )}
                  />

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold",
                          config.badgeBg,
                          config.badgeText
                        )}
                      >
                        <span className="text-xs leading-none">{config.icon}</span>
                        {config.label}
                      </span>
                      <span
                        className="text-[10px] text-zinc-600 font-mono tabular-nums"
                        suppressHydrationWarning
                      >
                        {time}
                      </span>
                    </div>
                    <p
                      className={cn(
                        "mt-1 text-[13px] leading-snug",
                        isDecision ? "text-violet-300" : isWarning ? "text-amber-300" : "text-zinc-400"
                      )}
                    >
                      {thought.message}
                    </p>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
