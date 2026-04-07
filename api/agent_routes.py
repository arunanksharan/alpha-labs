"""Agent-specific API routes for the multi-agent research pipeline.

Provides endpoints to start agent runs, check status, approve/reject
pending signals, retrieve event history, and stream real-time events
over WebSocket.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from api.events import event_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AgentRunRequest(BaseModel):
    ticker: str
    strategy: str = "mean_reversion"
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 100_000.0


class ApprovalRequest(BaseModel):
    approved: bool


# ---------------------------------------------------------------------------
# In-memory run state (production would use a persistent store)
# ---------------------------------------------------------------------------

_runs: dict[str, dict[str, Any]] = {}
_pending_approval: dict[str, asyncio.Event] = {}
_approval_results: dict[str, bool] = {}


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------


async def _run_pipeline(run_id: str, req: AgentRunRequest) -> None:
    """Execute the multi-agent pipeline in the background."""
    _runs[run_id]["status"] = "running"
    await event_manager.broadcast(
        {"type": "run_started", "run_id": run_id, "ticker": req.ticker}
    )

    try:
        from agents.graph import AgentRunner  # type: ignore[import-untyped]

        runner = AgentRunner()
        result = await runner.run(
            ticker=req.ticker,
            strategy=req.strategy,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            event_callback=lambda evt: asyncio.ensure_future(
                event_manager.broadcast({"type": "agent_event", "run_id": run_id, **evt})
            ),
        )
        _runs[run_id]["status"] = "completed"
        _runs[run_id]["result"] = result
        await event_manager.broadcast(
            {"type": "run_completed", "run_id": run_id}
        )
    except ImportError:
        # AgentRunner not yet implemented -- mark as failed gracefully
        _runs[run_id]["status"] = "failed"
        _runs[run_id]["error"] = "AgentRunner not available (agents.graph module missing)"
        await event_manager.broadcast(
            {
                "type": "run_failed",
                "run_id": run_id,
                "error": _runs[run_id]["error"],
            }
        )
    except Exception as exc:
        logger.exception("Pipeline run %s failed", run_id)
        _runs[run_id]["status"] = "failed"
        _runs[run_id]["error"] = str(exc)
        await event_manager.broadcast(
            {"type": "run_failed", "run_id": run_id, "error": str(exc)}
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/run")
async def start_run(req: AgentRunRequest) -> dict:
    """Start the multi-agent pipeline.

    Returns immediately with a ``run_id``.  The pipeline executes in a
    background task and emits events to the WebSocket stream.
    """
    run_id = uuid.uuid4().hex[:12]
    _runs[run_id] = {
        "run_id": run_id,
        "status": "pending",
        "request": req.model_dump(),
        "result": None,
        "error": None,
    }
    asyncio.create_task(_run_pipeline(run_id, req))
    return {"run_id": run_id, "status": "pending"}


@router.get("/status")
async def get_status() -> dict:
    """Return current agent system status.

    Includes all tracked runs, pending approvals, and the latest events.
    """
    return {
        "runs": _runs,
        "pending_approvals": list(_pending_approval.keys()),
        "latest_events": event_manager.get_history()[-10:],
    }


@router.post("/approve")
async def approve_signals(req: ApprovalRequest) -> dict:
    """Approve or reject pending signals.

    This unblocks any paused pipeline waiting for human approval.
    """
    if not _pending_approval:
        raise HTTPException(status_code=404, detail="No pending approvals")

    # Resolve the most recent pending approval
    run_id = next(iter(_pending_approval))
    _approval_results[run_id] = req.approved
    _pending_approval[run_id].set()
    del _pending_approval[run_id]

    action = "approved" if req.approved else "rejected"
    await event_manager.broadcast(
        {"type": "approval_decision", "run_id": run_id, "decision": action}
    )
    return {"run_id": run_id, "decision": action}


@router.get("/events")
async def get_events() -> dict:
    """Return the full event history for non-WebSocket clients."""
    return {"events": event_manager.get_history()}


@router.websocket("/ws")
async def agent_websocket(websocket: WebSocket) -> None:
    """Real-time event stream.  Dashboard connects here for live updates."""
    await event_manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive; ignore incoming messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_manager.disconnect(websocket)
