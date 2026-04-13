"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  MessageSquare,
  Target,
  TrendingUp,
  Bot,
  Settings,
  Zap,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { ModelSelector } from "@/components/ModelSelector";

const NAV_ITEMS = [
  { href: "/", label: "Monitor", icon: Activity },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/signals", label: "Signals", icon: Target },
  { href: "/performance", label: "Performance", icon: TrendingUp },
  { href: "/jobs", label: "Jobs", icon: Layers },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export default function Sidebar({ onNavigate }: { onNavigate?: () => void } = {}) {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(true);
  const { mode, setMode, connected } = useAppStore();

  return (
    <motion.aside
      animate={{ width: expanded ? 240 : 64 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="relative flex h-screen flex-col border-r border-zinc-800 bg-zinc-900"
    >
      {/* Header */}
      <div className="flex h-14 items-center gap-2 border-b border-zinc-800 px-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-violet-500/20">
          <Zap className="h-4 w-4 text-violet-400" />
        </div>
        <AnimatePresence>
          {expanded && (
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: "auto" }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden whitespace-nowrap text-sm font-semibold text-zinc-50"
            >
              Agentic Alpha Lab
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-3">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-violet-500 text-white"
                  : "text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <AnimatePresence>
                {expanded && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: "auto" }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ duration: 0.15 }}
                    className="overflow-hidden whitespace-nowrap"
                  >
                    {label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="space-y-3 border-t border-zinc-800 px-3 py-3">
        {/* Demo / Live toggle */}
        <button
          type="button"
          onClick={() => setMode(mode === "demo" ? "live" : "demo")}
          className="flex w-full items-center gap-3"
        >
          <div
            className={cn(
              "relative h-5 w-9 shrink-0 rounded-full transition-colors",
              mode === "live" ? "bg-violet-500" : "bg-zinc-600",
            )}
          >
            <motion.div
              className="absolute top-0.5 h-4 w-4 rounded-full bg-white"
              animate={{ left: mode === "live" ? 18 : 2 }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            />
          </div>
          <AnimatePresence>
            {expanded && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden whitespace-nowrap text-xs font-medium text-zinc-400"
              >
                {mode === "demo" ? "Demo" : "Live"}
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Model selector */}
        <ModelSelector expanded={expanded} />

        {/* Connection status */}
        <div className="flex items-center gap-3 px-0.5">
          <span
            className={cn(
              "h-2 w-2 shrink-0 rounded-full",
              connected ? "bg-emerald-400" : "bg-red-400",
            )}
          />
          <AnimatePresence>
            {expanded && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden whitespace-nowrap text-xs text-zinc-500"
              >
                {connected ? "Connected" : "Disconnected"}
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Logout */}
        <button
          type="button"
          onClick={() => {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            window.location.href = "/login";
          }}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-xs text-zinc-500 hover:bg-zinc-700 hover:text-red-400 transition-colors"
        >
          <LogOut className="h-3.5 w-3.5 shrink-0" />
          <AnimatePresence>
            {expanded && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden whitespace-nowrap"
              >
                Sign Out
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>

      {/* Collapse toggle */}
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="absolute -right-3 top-16 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800 text-zinc-400 hover:text-zinc-200"
      >
        {expanded ? (
          <ChevronLeft className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
      </button>
    </motion.aside>
  );
}
