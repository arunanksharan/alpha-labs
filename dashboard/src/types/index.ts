export interface AgentEvent {
  agent_name: string;
  status: "pending" | "running" | "completed" | "failed" | "awaiting_approval" | "approved" | "rejected";
  message: string;
  data: Record<string, unknown>;
  timestamp: string;
  server_timestamp?: string;
}

export interface Signal {
  ticker: string;
  date: string;
  direction: number;
  confidence: number;
  metadata?: Record<string, unknown>;
}

export interface BacktestMetrics {
  strategy_name: string;
  total_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  calmar_ratio: number;
  win_rate: number;
  profit_factor: number;
  var_95?: number;
  cvar_95?: number;
}

export interface EquityCurvePoint {
  date: string;
  equity: number;
}

export interface ICCurvePoint {
  horizon: number;
  ic: number;
  ic_std: number;
  is_significant: boolean;
}

export interface ResearchResult {
  strategy_name: string;
  ticker: string;
  start_date: string;
  end_date: string;
  signals_count: number;
  backtest: BacktestMetrics & { equity_curve: EquityCurvePoint[] };
  risk_assessment: Record<string, unknown>;
  validation: Record<string, unknown>;
  signal_decay: { half_life?: number; ic_at_1d?: number; ic_at_5d?: number };
  metadata: Record<string, unknown>;
}
