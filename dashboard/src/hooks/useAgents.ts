"use client";

import { useState, useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { API_URL } from "@/lib/utils";

export function useAgents() {
  const { setCurrentRunId, setApprovalPending } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startRun = useCallback(
    async (ticker: string, strategy: string) => {
      setLoading(true);
      setError(null);

      try {
        const res = await fetch(`${API_URL}/api/agents/run`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker, strategy }),
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Agent run failed (${res.status})`);
        }

        const data: { run_id: string } = await res.json();
        setCurrentRunId(data.run_id);
        return data.run_id;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [setCurrentRunId],
  );

  const approve = useCallback(async () => {
    const runId = useAppStore.getState().currentRunId;
    if (!runId) return;

    try {
      const res = await fetch(`${API_URL}/api/agents/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId, approved: true }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Approval failed (${res.status})`);
      }

      setApprovalPending(false);
      return await res.json();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      return null;
    }
  }, [setApprovalPending]);

  const reject = useCallback(async () => {
    const runId = useAppStore.getState().currentRunId;
    if (!runId) return;

    try {
      const res = await fetch(`${API_URL}/api/agents/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId, approved: false }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Rejection failed (${res.status})`);
      }

      setApprovalPending(false);
      setCurrentRunId(null);
      return await res.json();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      return null;
    }
  }, [setApprovalPending, setCurrentRunId]);

  return { startRun, approve, reject, loading, error };
}
