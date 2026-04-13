"""Cron scheduler API — configure and control the daily research cycle."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from jobs.cron import get_scheduler

router = APIRouter(prefix="/api/cron", tags=["cron"])


class CronConfigUpdate(BaseModel):
    enabled: bool | None = None
    schedule_hour: int | None = None
    schedule_minute: int | None = None
    timezone_offset: int | None = None
    strategy: str | None = None
    refresh_data: bool | None = None
    auto_run_signals: bool | None = None


@router.get("/status")
def get_cron_status() -> dict:
    """Get current cron scheduler status and config."""
    scheduler = get_scheduler()
    return {
        "config": scheduler.config.to_dict(),
        "status": {
            "running": scheduler.status.running,
            "last_run": scheduler.status.last_run,
            "last_result": scheduler.status.last_result,
            "next_run": scheduler.status.next_run,
            "tickers_processed": scheduler.status.tickers_processed,
            "errors": scheduler.status.errors,
        },
    }


@router.post("/config")
def update_cron_config(req: CronConfigUpdate) -> dict:
    """Update cron schedule configuration."""
    scheduler = get_scheduler()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    config = scheduler.update_config(updates)
    return {"config": config.to_dict()}


@router.post("/start")
def start_cron() -> dict:
    """Start the cron scheduler."""
    scheduler = get_scheduler()
    scheduler.start()
    return {"status": "started", "config": scheduler.config.to_dict()}


@router.post("/stop")
def stop_cron() -> dict:
    """Stop the cron scheduler."""
    scheduler = get_scheduler()
    scheduler.stop()
    return {"status": "stopped"}


@router.post("/run-now")
def run_now() -> dict:
    """Trigger an immediate research cycle (manual trigger)."""
    scheduler = get_scheduler()
    result = scheduler.run_now()
    return result
