"""Authentication service — password hashing, JWT tokens, user CRUD."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from db.models import SessionModel, User

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production-please")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------


def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "exp": expire, "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------


def signup(email: str, password: str, db: Session) -> tuple[User, str, str]:
    """Create a new user and return (user, access_token, refresh_token).

    Raises ValueError if email already exists.
    """
    existing = db.query(User).filter_by(email=email.lower()).first()
    if existing:
        raise ValueError("Email already registered")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        is_verified=True,  # Default true for now
    )
    db.add(user)
    db.flush()

    access = create_access_token(user.id, user.email)
    refresh = create_refresh_token(user.id)

    # Store refresh token in sessions table
    session = SessionModel(
        user_id=user.id,
        refresh_token=refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    db.commit()

    logger.info("User signed up: %s", email)
    return user, access, refresh


def login(email: str, password: str, db: Session) -> tuple[User, str, str]:
    """Authenticate and return (user, access_token, refresh_token).

    Raises ValueError if credentials are invalid.
    """
    user = db.query(User).filter_by(email=email.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Invalid email or password")

    # Cleanup expired sessions for this user
    db.query(SessionModel).filter(
        SessionModel.user_id == user.id,
        SessionModel.expires_at < datetime.now(timezone.utc),
    ).delete()

    access = create_access_token(user.id, user.email)
    refresh = create_refresh_token(user.id)

    session = SessionModel(
        user_id=user.id,
        refresh_token=refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    db.commit()

    return user, access, refresh


def refresh_access_token(refresh_token: str, db: Session) -> tuple[str, str]:
    """Validate refresh token and issue new tokens.

    Raises ValueError if token is invalid or expired.
    """
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise ValueError("Invalid refresh token")

    session = db.query(SessionModel).filter_by(refresh_token=refresh_token).first()
    if not session:
        raise ValueError("Refresh token not found")

    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise ValueError("Refresh token expired")

    user = db.query(User).filter_by(id=session.user_id).first()
    if not user:
        raise ValueError("User not found")

    # Rotate: delete old, create new
    db.delete(session)

    new_access = create_access_token(user.id, user.email)
    new_refresh = create_refresh_token(user.id)

    new_session = SessionModel(
        user_id=user.id,
        refresh_token=new_refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_session)
    db.commit()

    return new_access, new_refresh


def logout(refresh_token: str, db: Session) -> None:
    """Invalidate a refresh token."""
    session = db.query(SessionModel).filter_by(refresh_token=refresh_token).first()
    if session:
        db.delete(session)
        db.commit()
