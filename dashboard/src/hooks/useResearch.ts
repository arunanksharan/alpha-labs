"use client";

import { useState, useCallback } from "react";
import { useAppStore } from "@/lib/store";
import { API_URL } from "@/lib/utils";
import type { ResearchResult, BacktestMetrics, EquityCurvePoint } from "@/types";

const DEMO_RESULT: ResearchResult = {
  strategy_name: "momentum_rsi",
  ticker: "AAPL",
  start_date: "2023-01-01",
  end_date: "2024-01-01",
  signals_count: 47,
  backtest: {
    strategy_name: "momentum_rsi",
    total_return: 0.342,
    annualized_return: 0.298,
    sharpe_ratio: 1.87,
    sortino_ratio: 2.45,
    max_drawdown: -0.112,
    calmar_ratio: 2.66,
    win_rate: 0.58,
    profit_factor: 1.72,
    var_95: -0.021,
    cvar_95: -0.034,
    equity_curve: Array.from({ length: 252 }, (_, i) => ({
      date: new Date(2023, 0, 1 + i).toISOString().slice(0, 10),
      equity: 10000 * (1 + 0.342 * (i / 251) + Math.sin(i / 20) * 0.03),
    })) as EquityCurvePoint[],
  },
  risk_assessment: {
    risk_level: "moderate",
    tail_risk: "low",
    correlation_to_spy: 0.62,
  },
  validation: {
    walk_forward_sharpe: 1.54,
    out_of_sample_return: 0.18,
    overfitting_score: 0.23,
  },
  signal_decay: {
    half_life: 4.2,
    ic_at_1d: 0.08,
    ic_at_5d: 0.045,
  },
  metadata: {
    run_duration_seconds: 12.4,
    model: "gpt-4o",
  },
};

export function useResearch() {
  const { mode, setResult, setMetrics } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runResearch = useCallback(
    async (ticker: string, strategy: string, startDate: string, endDate: string) => {
      setLoading(true);
      setError(null);

      try {
        if (mode === "demo") {
          // Simulate network delay
          await new Promise((r) => setTimeout(r, 1500));
          const result: ResearchResult = {
            ...DEMO_RESULT,
            ticker,
            strategy_name: strategy,
            start_date: startDate,
            end_date: endDate,
          };
          setResult(result);
          setMetrics(result.backtest);
          return result;
        }

        const res = await fetch(`${API_URL}/api/research`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker, strategy, start_date: startDate, end_date: endDate }),
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Request failed (${res.status})`);
        }

        const result: ResearchResult = await res.json();
        setResult(result);
        setMetrics(result.backtest);
        return result;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [mode, setResult, setMetrics],
  );

  const runBacktest = useCallback(
    async (ticker: string, strategy: string, startDate: string, endDate: string) => {
      setLoading(true);
      setError(null);

      try {
        const res = await fetch(`${API_URL}/api/research`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ticker,
            strategy,
            start_date: startDate,
            end_date: endDate,
            backtest_only: true,
          }),
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Backtest failed (${res.status})`);
        }

        const data = await res.json();
        const metrics: BacktestMetrics = data.backtest ?? data;
        setMetrics(metrics);
        return metrics;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [setMetrics],
  );

  const analyzeSentiment = useCallback(async (text: string) => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/sentiment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Sentiment analysis failed (${res.status})`);
      }

      return await res.json();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { runResearch, runBacktest, analyzeSentiment, loading, error };
}
