"""WebSocket event manager for real-time agent updates to the dashboard.

Provides a singleton EventManager that handles WebSocket connections,
broadcasts agent events to all connected clients, and maintains a
bounded event history for late-joining clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class EventManager:
    """Manages WebSocket connections and broadcasts agent events."""

    def __init__(self, max_history: int = 100) -> None:
        self._connections: list[WebSocket] = []
        self._history: deque[dict] = deque(maxlen=max_history)

    async def connect(self, ws: WebSocket) -> None:
        """Accept a WebSocket connection and replay event history."""
        await ws.accept()
        self._connections.append(ws)
        # Send history on connect so the client catches up
        for event in self._history:
            await ws.send_json(event)

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection from the active list."""
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, event: dict) -> None:
        """Send an event to all connected WebSocket clients.

        Dead connections are automatically cleaned up.
        """
        event["server_timestamp"] = datetime.now(timezone.utc).isoformat()
        self._history.append(event)
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def emit_sync(self, event: dict) -> None:
        """Synchronous emit for use from non-async agent code.

        Appends the event to history but does not push to WebSocket
        clients (they will receive it on next broadcast or reconnect).
        """
        event["server_timestamp"] = datetime.now(timezone.utc).isoformat()
        self._history.append(event)

    def get_history(self) -> list[dict]:
        """Return the full event history as a plain list."""
        return list(self._history)


# Singleton instance used across the application
event_manager = EventManager()
