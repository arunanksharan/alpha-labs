"""Settings API routes — API keys, model selection, agent prompts, platform config.

DB-backed persistence with in-memory fallbacks for environments without Postgres.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, get_optional_user
from db.models import AgentPrompt, PlatformConfig, User, UserSetting
from db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

# ---------------------------------------------------------------------------
# Default agent prompts (fallback if DB is empty)
# ---------------------------------------------------------------------------

def _load_default_prompts() -> dict[str, str]:
    """Load default prompts from the skills system."""
    try:
        from api.skill_routes import DEFAULT_SKILLS
        return {k: v["skill"] for k, v in DEFAULT_SKILLS.items()}
    except ImportError:
        return {}

DEFAULT_PROMPTS: dict[str, str] = _load_default_prompts() or {
    "research_director": "You are a senior research director at a quantitative hedge fund.",
    "the_quant": "You are a quantitative analyst focusing on statistical signals.",
    "the_technician": "You are a technical analyst analyzing price action.",
    "sentiment_analyst": "You are a sentiment analyst.",
    "the_fundamentalist": "You are a fundamental analyst.",
    "the_macro_strategist": "You are a macro strategist.",
}

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class KeysRequest(BaseModel):
    openai: str = ""
    anthropic: str = ""
    gemini: str = ""
    groq: str = ""
    deepseek: str = ""


class ModelRequest(BaseModel):
    model: str


class PromptsRequest(BaseModel):
    prompts: dict[str, str]


class ConfigUpdateRequest(BaseModel):
    settings: dict[str, str]


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

_KEY_ENV_MAP = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def _encrypt(value: str) -> str:
    """Encrypt a value with Fernet. Returns plaintext if no key configured."""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        return value
    try:
        from cryptography.fernet import Fernet
        f = Fernet(key.encode())
        return f.encrypt(value.encode()).decode()
    except Exception:
        return value


def _decrypt(value: str) -> str:
    """Decrypt a Fernet-encrypted value. Returns as-is if not encrypted."""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        return value
    try:
        from cryptography.fernet import Fernet
        f = Fernet(key.encode())
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value


@router.get("/keys")
def get_keys(user: User | None = Depends(get_optional_user)) -> dict:
    from core.llm import check_api_keys
    return {"keys": check_api_keys()}


@router.post("/keys")
def set_keys(
    req: KeysRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    updated = []
    for provider, env_var in _KEY_ENV_MAP.items():
        value = getattr(req, provider, "")
        if value and value.strip():
            os.environ[env_var] = value.strip()
            updated.append(provider)

            # Persist encrypted key to DB if user is authenticated
            if user:
                from db.models import ApiKey
                existing = db.query(ApiKey).filter_by(user_id=user.id, provider=provider).first()
                encrypted = _encrypt(value.strip())
                if existing:
                    existing.encrypted_key = encrypted
                else:
                    db.add(ApiKey(user_id=user.id, provider=provider, encrypted_key=encrypted))

    if user:
        db.commit()

    from core.llm import check_api_keys
    return {"updated": updated, "keys": check_api_keys()}


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------


@router.get("/model")
def get_model(user: User | None = Depends(get_optional_user)) -> dict:
    import core.llm as llm_mod
    return {"model": llm_mod.DEFAULT_MODEL}


@router.post("/model")
def set_model(req: ModelRequest, user: User | None = Depends(get_optional_user)) -> dict:
    import core.llm as llm_mod

    alias = req.model.strip()
    if alias not in llm_mod.MODEL_ALIASES:
        return {"error": f"Unknown model alias: {alias}", "available": list(llm_mod.MODEL_ALIASES.keys())}

    llm_mod.DEFAULT_MODEL = alias
    os.environ["QR_DEFAULT_MODEL"] = alias
    return {"model": alias}


# ---------------------------------------------------------------------------
# Agent prompts (DB-backed with fallback)
# ---------------------------------------------------------------------------


@router.get("/prompts")
def get_prompts(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    prompts = dict(DEFAULT_PROMPTS)

    if user:
        db_prompts = db.query(AgentPrompt).filter_by(user_id=user.id).all()
        for p in db_prompts:
            prompts[p.agent_name] = p.prompt

    return {"prompts": prompts}


@router.post("/prompts")
def set_prompts(
    req: PromptsRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    updated = []

    for agent, prompt in req.prompts.items():
        if not prompt.strip():
            continue

        if user:
            existing = db.query(AgentPrompt).filter_by(
                user_id=user.id, agent_name=agent
            ).first()
            if existing:
                existing.prompt = prompt.strip()
            else:
                db.add(AgentPrompt(user_id=user.id, agent_name=agent, prompt=prompt.strip()))
            updated.append(agent)
        else:
            DEFAULT_PROMPTS[agent] = prompt.strip()
            updated.append(agent)

    if user:
        db.commit()

    prompts = dict(DEFAULT_PROMPTS)
    if user:
        db_prompts = db.query(AgentPrompt).filter_by(user_id=user.id).all()
        for p in db_prompts:
            prompts[p.agent_name] = p.prompt

    return {"updated": updated, "prompts": prompts}


# ---------------------------------------------------------------------------
# Platform config (DB-backed)
# ---------------------------------------------------------------------------


@router.get("/config")
def get_config_all(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return all platform config values, with user overrides applied."""
    config: dict[str, dict] = {}

    # Global defaults from DB
    for row in db.query(PlatformConfig).all():
        config[row.key] = {
            "value": row.value,
            "category": row.category,
            "description": row.description,
            "source": "default",
        }

    # User overrides
    if user:
        for row in db.query(UserSetting).filter_by(user_id=user.id).all():
            if row.key in config:
                config[row.key]["value"] = row.value
                config[row.key]["source"] = "user"
            else:
                config[row.key] = {
                    "value": row.value,
                    "category": "custom",
                    "description": "",
                    "source": "user",
                }

    return {"config": config}


@router.post("/config")
def update_config(
    req: ConfigUpdateRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """Update config values. Saves as user overrides if authenticated, otherwise global."""
    updated = []

    for key, value in req.settings.items():
        if user:
            existing = db.query(UserSetting).filter_by(user_id=user.id, key=key).first()
            if existing:
                existing.value = str(value)
            else:
                db.add(UserSetting(user_id=user.id, key=key, value=str(value)))
        else:
            existing = db.query(PlatformConfig).filter_by(key=key).first()
            if existing:
                existing.value = str(value)

        updated.append(key)

    db.commit()
    return {"updated": updated}
