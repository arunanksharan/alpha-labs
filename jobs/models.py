"""Job data models — status, types, config, and the Job dataclass."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    RESEARCH = "research"
    BACKTEST = "backtest"
    DATA_REFRESH = "data_refresh"
    DAILY_CYCLE = "daily_cycle"


@dataclass
class BacktestConfig:
    """Per-request backtest configuration overrides."""

    initial_capital: float | None = None
    commission: float | None = None
    slippage: float | None = None
    risk_free_rate: float | None = None
    strategy_params: dict[str, Any] | None = None


@dataclass
class Job:
    """A unit of async work with progress tracking."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    job_type: JobType = JobType.RESEARCH
    status: JobStatus = JobStatus.PENDING
    params: dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    progress_stage: str = "queued"
    progress_message: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    user_id: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["job_type"] = self.job_type.value
        for k in ("created_at", "started_at", "completed_at"):
            if d[k]:
                d[k] = d[k].isoformat()
        return d
