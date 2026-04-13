"""Database session management.

Reads DATABASE_URL from environment. Falls back to SQLite automatically
if PostgreSQL is not available (no Docker/server running).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/quant_researcher",
)

SQLITE_PATH = Path("data/quant_researcher.db")


def _create_engine():
    """Create the DB engine, falling back to SQLite if Postgres is unavailable."""
    if DATABASE_URL.startswith("sqlite"):
        logger.info("Using SQLite database: %s", DATABASE_URL)
        return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    # Try Postgres first
    try:
        eng = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connected to PostgreSQL: %s", DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL)
        return eng
    except Exception as exc:
        logger.warning("PostgreSQL unavailable (%s), falling back to SQLite", exc.__class__.__name__)
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        sqlite_url = f"sqlite:///{SQLITE_PATH}"
        logger.info("Using SQLite database: %s", sqlite_url)
        return create_engine(sqlite_url, connect_args={"check_same_thread": False})


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Auto-create tables on import (safe for SQLite, idempotent for Postgres)
try:
    from db.models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")
except Exception as exc:
    logger.warning("Could not create tables: %s", exc)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Non-generator version for use outside FastAPI (CLI, scripts)."""
    return SessionLocal()
