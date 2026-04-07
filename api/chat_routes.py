"""Chat API routes for research conversations.

Provides endpoints for sending research questions, retrieving history,
and clearing conversations.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Session-level chat instance (single-user for now; TODO: per-session persistence)
_chat_instance = None


def _get_chat():
    """Lazy singleton for the chat handler."""
    global _chat_instance
    if _chat_instance is None:
        from agents.chat import ResearchChat
        _chat_instance = ResearchChat()
    return _chat_instance


class ChatMessage(BaseModel):
    """Incoming chat message payload."""
    message: str


@router.post("")
def send_message(msg: ChatMessage) -> dict:
    """Send a research question, get a grounded response.

    The response includes the answer, citations from computations,
    suggested follow-up actions, and agent trace data.
    """
    chat = _get_chat()
    return chat.send(msg.message)


@router.get("/history")
def get_history() -> dict:
    """Retrieve the full conversation history."""
    chat = _get_chat()
    return {"history": chat.get_history()}


@router.delete("/history")
def clear_history() -> dict:
    """Clear the conversation history."""
    chat = _get_chat()
    chat.clear()
    return {"status": "cleared"}
