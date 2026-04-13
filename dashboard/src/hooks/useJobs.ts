"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { API_URL } from "@/lib/utils";

export interface BacktestConfigInput {
  initial_capital?: number;
  commission?: number;
  slippage?: number;
  risk_free_rate?: number;
  strategy_params?: Record<string, unknown>;
}

export interface JobData {
  id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  params: Record<string, unknown>;
  progress: number;
  progress_stage: string;
  progress_message: string;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export function useJobs() {
  const [jobs, setJobs] = useState<JobData[]>([]);
  const [loading, setLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const getHeaders = useCallback(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
  }, []);

  // Fetch job list
  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/jobs`, { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
      }
    } catch {}
  }, [getHeaders]);

  // Submit a new job
  const submitJob = useCallback(async (
    ticker: string,
    strategy: string,
    startDate: string,
    endDate: string,
    config?: BacktestConfigInput,
  ) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/jobs/submit`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({
          ticker, strategy, start_date: startDate, end_date: endDate,
          config: config || null,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        await fetchJobs();
        return data.job_id as string;
      }
      return null;
    } catch {
      return null;
    } finally {
      setLoading(false);
    }
  }, [getHeaders, fetchJobs]);

  // Poll for updates when there are active jobs
  useEffect(() => {
    fetchJobs();

    pollRef.current = setInterval(() => {
      const hasActive = jobs.some((j) => j.status === "pending" || j.status === "running");
      if (hasActive) {
        fetchJobs();
      }
    }, 2000);

    return () => clearInterval(pollRef.current);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-poll when jobs change and there are active ones
  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === "pending" || j.status === "running");
    if (hasActive) {
      const timer = setTimeout(fetchJobs, 2000);
      return () => clearTimeout(timer);
    }
  }, [jobs, fetchJobs]);

  return { jobs, submitJob, fetchJobs, loading };
}
