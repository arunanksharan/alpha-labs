"""Cycle API routes for triggering research cycles.

Provides endpoints for manually triggering daily/weekly cycles and
checking scheduler status.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/cycles", tags=["cycles"])

# Shared scheduler instance (lazy)
_scheduler_instance = None


def _get_scheduler():
    """Lazy singleton for the cycle scheduler."""
    global _scheduler_instance
    if _scheduler_instance is None:
        from agents.scheduler import CycleScheduler
        _scheduler_instance = CycleScheduler()
    return _scheduler_instance


@router.post("/run-daily")
def run_daily() -> dict:
    """Trigger the daily research cycle manually.

    Runs full multi-agent research on all tracked tickers and returns
    the morning brief.
    """
    scheduler = _get_scheduler()
    brief = scheduler.run_daily_cycle()
    return brief


@router.post("/run-weekly")
def run_weekly() -> dict:
    """Trigger the weekly review cycle manually.

    Runs performance review, signal decay checks, and generates
    rebalancing suggestions.
    """
    scheduler = _get_scheduler()
    return scheduler.run_weekly_cycle()


@router.get("/status")
def cycle_status() -> dict:
    """Get the current scheduler status."""
    scheduler = _get_scheduler()
    return {
        "daily_last_run": scheduler.last_daily.isoformat() if scheduler.last_daily else None,
        "weekly_last_run": scheduler.last_weekly.isoformat() if scheduler.last_weekly else None,
        "tickers": scheduler._tickers,
    }
