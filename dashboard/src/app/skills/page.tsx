"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BarChart2,
  TrendingUp,
  MessageCircle,
  FileText,
  Globe,
  RotateCcw,
  ArrowLeft,
  Save,
  CheckCircle2,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { cn, API_URL } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Skill {
  agent_name: string;
  display_name: string;
  icon: string;
  description: string;
  skill: string;
  is_custom: boolean;
  updated_at: string;
}

/* ------------------------------------------------------------------ */
/*  Icon map                                                           */
/* ------------------------------------------------------------------ */

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  quant: BarChart2,
  technician: TrendingUp,
  sentiment: MessageCircle,
  fundamentalist: FileText,
  macro: Globe,
  contrarian: RotateCcw,
};

function agentIcon(agentName: string) {
  return ICON_MAP[agentName] ?? FileText;
}

/* ------------------------------------------------------------------ */
/*  Auth header helper                                                 */
/* ------------------------------------------------------------------ */

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/* ------------------------------------------------------------------ */
/*  Card animation variants                                            */
/* ------------------------------------------------------------------ */

const containerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.06 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 25 } },
};

/* ------------------------------------------------------------------ */
/*  Component: Agent Card                                              */
/* ------------------------------------------------------------------ */

function AgentCard({
  skill,
  onClick,
}: {
  skill: Skill;
  onClick: () => void;
}) {
  const Icon = agentIcon(skill.agent_name);

  return (
    <motion.button
      variants={cardVariants}
      whileHover={{ scale: 1.015, y: -2 }}
      whileTap={{ scale: 0.985 }}
      onClick={onClick}
      className={cn(
        "flex flex-col items-start gap-3 rounded-xl border border-zinc-800 bg-zinc-900/60 p-5",
        "text-left transition-colors hover:border-violet-500/40 hover:bg-zinc-900/90",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50"
      )}
    >
      <div className="flex w-full items-center justify-between">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-zinc-700/60 bg-zinc-800/80">
          <Icon className="h-5 w-5 text-violet-400" />
        </div>
        <span
          className={cn(
            "rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
            skill.is_custom
              ? "bg-violet-500/15 text-violet-400 border border-violet-500/30"
              : "bg-zinc-800 text-zinc-500 border border-zinc-700/50"
          )}
        >
          {skill.is_custom ? "Custom" : "Default"}
        </span>
      </div>
      <div>
        <h3 className="text-sm font-semibold text-zinc-100">{skill.display_name}</h3>
        <p className="mt-1 text-xs leading-relaxed text-zinc-500">{skill.description}</p>
      </div>
    </motion.button>
  );
}

/* ------------------------------------------------------------------ */
/*  Component: Editor                                                  */
/* ------------------------------------------------------------------ */

function SkillEditor({
  skill,
  onBack,
  onUpdate,
}: {
  skill: Skill;
  onBack: () => void;
  onUpdate: (updated: Skill) => void;
}) {
  const [content, setContent] = useState(skill.skill);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const Icon = agentIcon(skill.agent_name);
  const isModified = content !== skill.skill;

  // Auto-resize textarea
  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.max(400, el.scrollHeight)}px`;
  }, []);

  useEffect(() => {
    resize();
  }, [content, resize]);

  // Save handler
  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/skills/${skill.agent_name}`, {
        method: "PUT",
        headers: authHeaders(),
        body: JSON.stringify({ skill: content }),
      });
      if (!res.ok) throw new Error(`Save failed (${res.status})`);
      setSaved(true);
      onUpdate({ ...skill, skill: content, is_custom: true });
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  // Reset handler
  async function handleReset() {
    if (!confirmReset) {
      setConfirmReset(true);
      return;
    }
    setResetting(true);
    setError(null);
    setConfirmReset(false);
    try {
      const res = await fetch(`${API_URL}/api/skills/reset/${skill.agent_name}`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(`Reset failed (${res.status})`);
      const data = await res.json();
      setContent(data.skill);
      onUpdate({ ...skill, skill: data.skill, is_custom: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setResetting(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      className="space-y-5"
    >
      {/* Editor header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-700/60 bg-zinc-800/60 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-zinc-700/60 bg-zinc-800/80">
          <Icon className="h-5 w-5 text-violet-400" />
        </div>
        <div className="flex-1">
          <h2 className="text-base font-semibold text-zinc-100">{skill.display_name}</h2>
          <p className="text-xs text-zinc-500">{skill.description}</p>
        </div>
        <span
          className={cn(
            "rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
            (isModified || skill.is_custom)
              ? "bg-violet-500/15 text-violet-400 border border-violet-500/30"
              : "bg-zinc-800 text-zinc-500 border border-zinc-700/50"
          )}
        >
          {isModified || skill.is_custom ? "Custom" : "Default"}
        </span>
      </div>

      {/* Textarea */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-1">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          spellCheck={false}
          className={cn(
            "w-full resize-none rounded-lg bg-zinc-950/80 px-4 py-3",
            "font-mono text-sm leading-relaxed text-zinc-300 placeholder-zinc-600",
            "border border-zinc-800/50 focus:border-violet-500/40 focus:outline-none focus:ring-1 focus:ring-violet-500/20",
            "transition-colors min-h-[400px]"
          )}
        />
      </div>

      {/* Error message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400"
          >
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Saved confirmation */}
      <AnimatePresence>
        {saved && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400"
          >
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
            Saved successfully
          </motion.div>
        )}
      </AnimatePresence>

      {/* Buttons */}
      <div className="flex flex-wrap items-center gap-3">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          onClick={handleSave}
          disabled={saving}
          className={cn(
            "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
            "bg-violet-600 text-white hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {saving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Save className="h-3.5 w-3.5" />
          )}
          Save
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          onClick={handleReset}
          disabled={resetting}
          className={cn(
            "flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
            confirmReset
              ? "border-red-500/60 bg-red-500/15 text-red-400 hover:bg-red-500/25"
              : "border-red-500/30 text-red-400 hover:border-red-500/50 hover:bg-red-500/10",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {resetting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RotateCcw className="h-3.5 w-3.5" />
          )}
          {confirmReset ? "Confirm Reset" : "Reset to Default"}
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          onClick={onBack}
          className="flex items-center gap-2 rounded-lg border border-zinc-700/60 px-4 py-2 text-sm font-medium text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-300 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </motion.button>
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSkills() {
      try {
        const res = await fetch(`${API_URL}/api/skills`, {
          headers: authHeaders(),
        });
        if (!res.ok) throw new Error(`Failed to load skills (${res.status})`);
        const data = await res.json();
        setSkills(data.skills || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load skills");
      } finally {
        setLoading(false);
      }
    }
    fetchSkills();
  }, []);

  const selectedSkill = skills.find((s) => s.agent_name === selectedAgent) ?? null;

  function handleUpdate(updated: Skill) {
    setSkills((prev) =>
      prev.map((s) => (s.agent_name === updated.agent_name ? updated : s))
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-lg">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-5">
          <h1 className="text-lg font-semibold text-zinc-50">Agent Skills</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Define each agent&apos;s expertise, methodology, and personality
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 py-6">
        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-zinc-500" />
          </div>
        )}

        {/* Error state */}
        {!loading && error && !skills.length && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <AlertTriangle className="h-8 w-8 text-zinc-600 mb-3" />
            <p className="text-sm text-zinc-500">{error}</p>
          </div>
        )}

        {/* Grid view */}
        {!loading && !selectedAgent && skills.length > 0 && (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
          >
            {skills.map((skill) => (
              <AgentCard
                key={skill.agent_name}
                skill={skill}
                onClick={() => setSelectedAgent(skill.agent_name)}
              />
            ))}
          </motion.div>
        )}

        {/* Editor view */}
        {!loading && selectedSkill && (
          <SkillEditor
            key={selectedSkill.agent_name}
            skill={selectedSkill}
            onBack={() => {
              setSelectedAgent(null);
              setError(null);
            }}
            onUpdate={handleUpdate}
          />
        )}
      </main>
    </div>
  );
}
