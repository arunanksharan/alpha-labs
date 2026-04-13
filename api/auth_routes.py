"""Authentication API routes — signup, login, refresh, logout."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.schemas import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from auth.service import login, logout, refresh_access_token, signup
from db.models import User
from db.session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup_route(req: SignupRequest, db: Session = Depends(get_db)) -> dict:
    try:
        user, access, refresh = signup(req.email, req.password, db)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": 3600,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
def login_route(req: LoginRequest, db: Session = Depends(get_db)) -> dict:
    try:
        user, access, refresh = login(req.email, req.password, db)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": 3600,
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
def refresh_route(req: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    try:
        access, refresh = refresh_access_token(req.refresh_token, db)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": 3600,
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
def logout_route(req: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    logout(req.refresh_token, db)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse)
def me_route(user: User = Depends(get_current_user)) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "is_verified": user.is_verified,
    }
