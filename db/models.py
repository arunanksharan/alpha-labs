"""SQLAlchemy ORM models for the Agentic Alpha Lab.

9 tables covering users, auth, configuration, research state, and history.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import JSON

# Portable types
JSONB = JSON
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Users & Auth
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSetting", back_populates="user", cascade="all, delete-orphan")
    prompts = relationship("AgentPrompt", back_populates="user", cascade="all, delete-orphan")
    universe = relationship("ResearchUniverse", back_populates="user", cascade="all, delete-orphan")
    api_keys_rel = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    research_history = relationship("ResearchHistory", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token = Column(String(512), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class PlatformConfig(Base):
    """Global platform defaults — seeded from config/settings.py."""

    __tablename__ = "platform_config"

    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    description = Column(Text, default="")


class UserSetting(Base):
    """Per-user configuration overrides."""

    __tablename__ = "user_settings"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="settings")


class AgentPrompt(Base):
    """Per-user agent system prompts."""

    __tablename__ = "agent_prompts"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    agent_name = Column(String(100), primary_key=True)
    prompt = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="prompts")


# ---------------------------------------------------------------------------
# Research Universe
# ---------------------------------------------------------------------------


class ResearchUniverse(Base):
    """Per-user ticker universe."""

    __tablename__ = "research_universe"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ticker = Column(String(20), primary_key=True)
    start_date = Column(String(10), default="2022-01-01")
    strategies = Column(JSONB, default=["mean_reversion", "momentum"])
    added_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="universe")


# ---------------------------------------------------------------------------
# Encrypted API Keys
# ---------------------------------------------------------------------------


class ApiKey(Base):
    """Per-user encrypted API keys for LLM providers."""

    __tablename__ = "api_keys"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    provider = Column(String(50), primary_key=True)
    encrypted_key = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="api_keys_rel")


# ---------------------------------------------------------------------------
# History & Tracking
# ---------------------------------------------------------------------------


class ResearchHistory(Base):
    """Saved research run results."""

    __tablename__ = "research_history"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False)
    strategy = Column(String(50), nullable=False)
    result_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="research_history")


class ChatMessage(Base):
    """Persistent chat history."""

    __tablename__ = "chat_history"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="chat_history")
