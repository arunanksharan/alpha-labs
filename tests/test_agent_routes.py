"""Tests for agent API routes and the WebSocket event manager."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.events import EventManager, event_manager
from api.server import app


@pytest.fixture(autouse=True)
def _clear_state():
    """Reset module-level run state and event history between tests."""
    import api.agent_routes as routes

    routes._runs.clear()
    routes._approval_events.clear()
    routes._approval_decisions.clear()
    # Reset singleton event history
    event_manager._history.clear()
    event_manager._connections.clear()
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/agents/run
# ---------------------------------------------------------------------------


def test_run_endpoint_returns_run_id(client: TestClient) -> None:
    """POST /api/agents/run should return a run_id and pending status."""
    with patch("api.agent_routes._run_pipeline", new_callable=AsyncMock) as mock_pipeline:
        response = client.post(
            "/api/agents/run",
            json={"ticker": "AAPL"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "run_id" in body
    assert body["status"] == "pending"
    assert len(body["run_id"]) == 12


def test_run_endpoint_custom_params(client: TestClient) -> None:
    """Custom parameters should be accepted."""
    with patch("api.agent_routes._run_pipeline", new_callable=AsyncMock):
        response = client.post(
            "/api/agents/run",
            json={
                "ticker": "MSFT",
                "strategy": "momentum",
                "start_date": "2021-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 50_000.0,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert "run_id" in body


# ---------------------------------------------------------------------------
# GET /api/agents/status
# ---------------------------------------------------------------------------


def test_status_endpoint(client: TestClient) -> None:
    """GET /api/agents/status should return runs, pending approvals, and events."""
    response = client.get("/api/agents/status")
    assert response.status_code == 200
    body = response.json()
    assert "runs" in body
    assert "pending_approvals" in body
    assert "latest_events" in body
    assert isinstance(body["runs"], dict)
    assert isinstance(body["pending_approvals"], list)
    assert isinstance(body["latest_events"], list)


def test_status_after_run(client: TestClient) -> None:
    """Status should reflect a started run."""
    import api.agent_routes as routes

    routes._runs["abc123"] = {
        "run_id": "abc123",
        "status": "running",
        "request": {"ticker": "AAPL"},
        "result": None,
        "error": None,
    }

    response = client.get("/api/agents/status")
    body = response.json()
    assert "abc123" in body["runs"]
    assert body["runs"]["abc123"]["status"] == "running"


# ---------------------------------------------------------------------------
# GET /api/agents/events
# ---------------------------------------------------------------------------


def test_events_endpoint_returns_history(client: TestClient) -> None:
    """GET /api/agents/events should return the event history."""
    # Seed some events
    event_manager.emit_sync({"type": "test_event", "data": "hello"})
    event_manager.emit_sync({"type": "test_event", "data": "world"})

    response = client.get("/api/agents/events")
    assert response.status_code == 200
    body = response.json()
    assert "events" in body
    assert len(body["events"]) == 2
    assert body["events"][0]["data"] == "hello"
    assert body["events"][1]["data"] == "world"


def test_events_endpoint_empty_history(client: TestClient) -> None:
    """Events endpoint should return empty list when no events exist."""
    response = client.get("/api/agents/events")
    assert response.status_code == 200
    assert response.json()["events"] == []


# ---------------------------------------------------------------------------
# POST /api/agents/approve
# ---------------------------------------------------------------------------


def test_approve_no_pending(client: TestClient) -> None:
    """Approve should return 404 when there are no pending approvals."""
    response = client.post("/api/agents/approve", json={"approved": True})
    assert response.status_code == 404


def test_approve_with_pending(client: TestClient) -> None:
    """Approve should resolve a pending approval."""
    import api.agent_routes as routes

    routes._approval_events["run_abc"] = asyncio.Event()

    response = client.post("/api/agents/approve", json={"approved": True, "run_id": "run_abc"})
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run_abc"
    assert body["decision"] == "approved"
    # Event is set (signaling the background task to resume)
    assert routes._approval_events["run_abc"].is_set()


def test_reject_with_pending(client: TestClient) -> None:
    """Reject should resolve a pending approval with rejected status."""
    import api.agent_routes as routes

    routes._approval_events["run_xyz"] = asyncio.Event()

    response = client.post("/api/agents/approve", json={"approved": False})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "rejected"


# ---------------------------------------------------------------------------
# EventManager unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_manager_broadcast() -> None:
    """Broadcast should add events to history with server_timestamp."""
    mgr = EventManager(max_history=10)

    await mgr.broadcast({"type": "test", "value": 42})

    history = mgr.get_history()
    assert len(history) == 1
    assert history[0]["type"] == "test"
    assert history[0]["value"] == 42
    assert "server_timestamp" in history[0]


@pytest.mark.asyncio
async def test_event_manager_broadcast_respects_max_history() -> None:
    """History should be bounded by max_history."""
    mgr = EventManager(max_history=3)

    for i in range(5):
        await mgr.broadcast({"type": "test", "index": i})

    history = mgr.get_history()
    assert len(history) == 3
    assert history[0]["index"] == 2
    assert history[2]["index"] == 4


def test_event_manager_emit_sync() -> None:
    """emit_sync should add events to history synchronously."""
    mgr = EventManager(max_history=50)

    mgr.emit_sync({"type": "sync_test", "value": "abc"})
    mgr.emit_sync({"type": "sync_test", "value": "def"})

    history = mgr.get_history()
    assert len(history) == 2
    assert history[0]["value"] == "abc"
    assert history[1]["value"] == "def"
    assert "server_timestamp" in history[0]
    assert "server_timestamp" in history[1]


def test_event_manager_emit_sync_respects_max_history() -> None:
    """Synchronous emit should also respect max_history."""
    mgr = EventManager(max_history=2)

    for i in range(5):
        mgr.emit_sync({"index": i})

    history = mgr.get_history()
    assert len(history) == 2
    assert history[0]["index"] == 3


@pytest.mark.asyncio
async def test_event_manager_disconnect_cleanup() -> None:
    """Disconnect should remove a connection from the list."""
    mgr = EventManager()
    ws = MagicMock(spec=["accept", "send_json", "receive_text"])
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()

    await mgr.connect(ws)
    assert len(mgr._connections) == 1

    mgr.disconnect(ws)
    assert len(mgr._connections) == 0


@pytest.mark.asyncio
async def test_event_manager_broadcast_removes_dead_connections() -> None:
    """Dead WebSocket connections should be cleaned up on broadcast."""
    mgr = EventManager()

    good_ws = MagicMock()
    good_ws.accept = AsyncMock()
    good_ws.send_json = AsyncMock()

    bad_ws = MagicMock()
    bad_ws.accept = AsyncMock()
    bad_ws.send_json = AsyncMock(side_effect=RuntimeError("connection closed"))

    await mgr.connect(good_ws)
    await mgr.connect(bad_ws)
    assert len(mgr._connections) == 2

    await mgr.broadcast({"type": "test"})

    # Dead connection should have been removed
    assert len(mgr._connections) == 1
    assert mgr._connections[0] is good_ws


# ---------------------------------------------------------------------------
# WebSocket endpoint (smoke test)
# ---------------------------------------------------------------------------


def test_websocket_connect(client: TestClient) -> None:
    """WebSocket at /ws should accept connections and receive history."""
    event_manager.emit_sync({"type": "preload", "val": 1})

    with client.websocket_connect("/ws") as ws:
        # Should receive the pre-loaded history event
        data = ws.receive_json()
        assert data["type"] == "preload"
        assert data["val"] == 1


def test_agent_websocket_connect(client: TestClient) -> None:
    """WebSocket at /api/agents/ws should accept connections."""
    with client.websocket_connect("/api/agents/ws") as ws:
        # Connection accepted -- no errors
        pass
