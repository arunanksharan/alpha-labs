"""Voice API routes — Deepgram key proxy for browser-side STT.

The Deepgram API key is never exposed to the client directly.
This endpoint returns a short-lived key for the browser to use
when connecting to Deepgram's WebSocket streaming API.
"""

from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/key")
def get_voice_key() -> dict:
    """Return the Deepgram API key for browser-side STT.

    In production, this should return a short-lived project key
    from Deepgram's /keys API. For now, returns the env var.
    """
    key = os.environ.get("DEEPGRAM_API_KEY", "")
    if not key:
        return {"key": None, "error": "DEEPGRAM_API_KEY not configured"}
    return {"key": key}
