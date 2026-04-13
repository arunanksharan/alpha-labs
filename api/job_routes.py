"""Job management API — submit, track, and cancel async research/backtest jobs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import get_optional_user
from db.models import User
from jobs import BacktestConfig, Job, JobStatus, JobType, get_runner
from jobs.wrapper import run_research_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class BacktestConfigSchema(BaseModel):
    initial_capital: float | None = None
    commission: float | None = None
    slippage: float | None = None
    risk_free_rate: float | None = None
    strategy_params: dict[str, Any] | None = None


class JobSubmitRequest(BaseModel):
    job_type: str = "research"
    ticker: str
    strategy: str = "mean_reversion"
    start_date: str = "2022-01-01"
    end_date: str = "2026-04-13"
    config: BacktestConfigSchema | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/submit")
def submit_job(
    req: JobSubmitRequest,
    user: User | None = Depends(get_optional_user),
) -> dict:
    """Submit a job for async execution. Returns job_id immediately."""
    runner = get_runner()

    config = BacktestConfig(**(req.config.model_dump() if req.config else {}))

    job = Job(
        job_type=JobType(req.job_type),
        params={
            "ticker": req.ticker,
            "strategy": req.strategy,
            "start_date": req.start_date,
            "end_date": req.end_date,
        },
        user_id=user.id if user else None,
    )

    runner.submit(
        job,
        run_research_job,
        ticker=req.ticker,
        strategy_name=req.strategy,
        start_date=req.start_date,
        end_date=req.end_date,
        config=config,
    )

    return {"job_id": job.id, "status": "pending"}


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    """Get job status, progress, and result."""
    runner = get_runner()
    job = runner.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.to_dict()


@router.get("")
def list_jobs(
    limit: int = 50,
    offset: int = 0,
    user: User | None = Depends(get_optional_user),
) -> dict:
    """List jobs, most recent first."""
    runner = get_runner()
    jobs = runner.list_jobs(user_id=user.id if user else None, limit=limit, offset=offset)
    return {
        "jobs": [j.to_dict() for j in jobs],
        "total": len(jobs),
    }


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    """Cancel a running or pending job."""
    runner = get_runner()
    cancelled = runner.cancel(job_id)
    if not cancelled:
        raise HTTPException(400, "Job could not be cancelled (may already be complete)")
    return {"job_id": job_id, "status": "cancelled"}
