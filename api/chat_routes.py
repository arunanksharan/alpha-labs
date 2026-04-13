"""Chat API routes — DB-backed conversation history.

Provides endpoints for sending research questions, retrieving history,
and clearing conversations. History persists across server restarts.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_optional_user
from db.models import ChatMessage as ChatMessageModel, User
from db.session import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Fallback in-memory chat for unauthenticated users
_anon_chat = None


def _get_anon_chat():
    global _anon_chat
    if _anon_chat is None:
        from agents.chat import ResearchChat
        _anon_chat = ResearchChat()
    return _anon_chat


class ChatMessageRequest(BaseModel):
    message: str


@router.post("")
def send_message(
    msg: ChatMessageRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """Send a research question, get a grounded response."""
    from agents.chat import ResearchChat

    # Build history context from DB if authenticated
    history = []
    if user:
        db_messages = (
            db.query(ChatMessageModel)
            .filter_by(user_id=user.id)
            .order_by(ChatMessageModel.created_at)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in db_messages]

    # Use a fresh chat instance with history context
    chat = ResearchChat()
    chat._history = history

    response = chat.send(msg.message)

    # Persist to DB if authenticated
    if user:
        db.add(ChatMessageModel(user_id=user.id, role="user", content=msg.message))
        db.add(ChatMessageModel(
            user_id=user.id,
            role="assistant",
            content=response.get("answer", ""),
            metadata_={"citations": response.get("citations", []), "actions": response.get("actions", [])},
        ))
        db.commit()
    else:
        # Fallback for unauthenticated
        anon = _get_anon_chat()
        # Already processed via chat above, just track in anon singleton
        anon._history.append({"role": "user", "content": msg.message})
        anon._history.append({"role": "assistant", "content": response.get("answer", "")})

    return response


@router.get("/history")
def get_history(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieve the full conversation history."""
    if user:
        messages = (
            db.query(ChatMessageModel)
            .filter_by(user_id=user.id)
            .order_by(ChatMessageModel.created_at)
            .all()
        )
        return {"history": [{"role": m.role, "content": m.content} for m in messages]}

    anon = _get_anon_chat()
    return {"history": anon.get_history()}


@router.delete("/history")
def clear_history(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """Clear the conversation history."""
    if user:
        db.query(ChatMessageModel).filter_by(user_id=user.id).delete()
        db.commit()
    else:
        anon = _get_anon_chat()
        anon.clear()

    return {"status": "cleared"}
