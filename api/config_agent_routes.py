"""Configuration Agent — natural language config changes.

User types "set commission to 15 bps" and the LLM extracts structured
config changes, validates them, and persists to the database.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_optional_user
from db.models import PlatformConfig, User, UserSetting
from db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config-agent", tags=["config-agent"])

# Schema of all configurable values with types and valid ranges
CONFIG_SCHEMA: dict[str, dict] = {
    "backtest.initial_capital": {"type": "float", "min": 1000, "max": 100_000_000, "unit": "USD"},
    "backtest.commission": {"type": "float", "min": 0, "max": 0.05, "unit": "fraction (e.g. 0.001 = 10 bps)"},
    "backtest.slippage": {"type": "float", "min": 0, "max": 0.05, "unit": "fraction"},
    "backtest.risk_free_rate": {"type": "float", "min": 0, "max": 0.20, "unit": "annual rate"},
    "backtest.benchmark_ticker": {"type": "str"},
    "backtest.train_window": {"type": "int", "min": 20, "max": 1000, "unit": "trading days"},
    "backtest.test_window": {"type": "int", "min": 5, "max": 500, "unit": "trading days"},
    "risk.max_position_pct": {"type": "float", "min": 0.01, "max": 1.0, "unit": "fraction"},
    "risk.max_sector_pct": {"type": "float", "min": 0.05, "max": 1.0, "unit": "fraction"},
    "risk.max_drawdown_pct": {"type": "float", "min": 0.01, "max": 0.50, "unit": "fraction"},
    "risk.var_confidence": {"type": "float", "min": 0.90, "max": 0.999, "unit": "probability"},
    "risk.kelly_fraction": {"type": "float", "min": 0.01, "max": 1.0, "unit": "fraction of full Kelly"},
    "risk.max_correlation": {"type": "float", "min": 0.1, "max": 1.0, "unit": "correlation coefficient"},
    "strategy.mean_reversion.entry_threshold": {"type": "float", "min": 0.5, "max": 5.0, "unit": "z-score"},
    "strategy.mean_reversion.exit_threshold": {"type": "float", "min": -1.0, "max": 2.0, "unit": "z-score"},
    "strategy.mean_reversion.default_window": {"type": "int", "min": 5, "max": 252, "unit": "days"},
    "strategy.momentum.lookback": {"type": "int", "min": 20, "max": 504, "unit": "days"},
    "strategy.momentum.skip_recent": {"type": "int", "min": 0, "max": 63, "unit": "days"},
    "strategy.momentum.top_pct": {"type": "float", "min": 0.05, "max": 0.50, "unit": "fraction"},
    "strategy.momentum.bottom_pct": {"type": "float", "min": 0.05, "max": 0.50, "unit": "fraction"},
    "llm.default_model": {"type": "str"},
    "llm.temperature": {"type": "float", "min": 0.0, "max": 2.0},
    "llm.max_tokens": {"type": "int", "min": 100, "max": 16000},
    "decay.min_signals": {"type": "int", "min": 2, "max": 50},
    "decay.max_horizon": {"type": "int", "min": 5, "max": 252, "unit": "days"},
}

SYSTEM_PROMPT = """You are a configuration assistant for a quantitative research platform.
The user will describe config changes in natural language. Extract structured changes.

Available configuration keys and their constraints:
{schema}

Respond with ONLY a JSON object in this exact format:
{{"changes": [{{"key": "backtest.commission", "value": 0.0015}}, ...]}}

Rules:
- Convert human language to the correct key and numeric value
- "15 bps" = 0.0015, "10 basis points" = 0.001
- "quarter Kelly" = 0.25, "half Kelly" = 0.5
- If the user's request is unclear, return {{"changes": [], "error": "Could not understand: ..."}}
- Only return keys that exist in the schema above
"""


class ConfigAgentRequest(BaseModel):
    message: str


def _validate_change(key: str, value) -> tuple[bool, str]:
    """Validate a config change against the schema."""
    if key not in CONFIG_SCHEMA:
        return False, f"Unknown config key: {key}"

    schema = CONFIG_SCHEMA[key]
    expected_type = schema["type"]

    try:
        if expected_type == "float":
            value = float(value)
        elif expected_type == "int":
            value = int(value)
        elif expected_type == "str":
            value = str(value)
    except (ValueError, TypeError):
        return False, f"Invalid type for {key}: expected {expected_type}"

    if "min" in schema and value < schema["min"]:
        return False, f"{key} must be >= {schema['min']}"
    if "max" in schema and value > schema["max"]:
        return False, f"{key} must be <= {schema['max']}"

    return True, ""


@router.post("")
def config_agent(
    req: ConfigAgentRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """Process a natural language config change request."""
    from core.llm import llm_call_safe

    # Build schema description for the LLM
    schema_desc = "\n".join(
        f"  {k}: {v['type']}, range [{v.get('min', 'any')}, {v.get('max', 'any')}] {v.get('unit', '')}"
        for k, v in CONFIG_SCHEMA.items()
    )

    prompt = SYSTEM_PROMPT.format(schema=schema_desc)
    response = llm_call_safe(
        req.message,
        system_prompt=prompt,
        json_mode=True,
    )

    # Parse LLM response
    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        return {"error": "Failed to parse LLM response", "raw": response.content}

    if "error" in parsed:
        return {"error": parsed["error"]}

    changes = parsed.get("changes", [])
    results = []

    for change in changes:
        key = change.get("key", "")
        value = change.get("value")

        # Validate
        valid, err = _validate_change(key, value)
        if not valid:
            results.append({"key": key, "value": value, "status": "rejected", "reason": err})
            continue

        # Get current value
        current = None
        if user:
            user_setting = db.query(UserSetting).filter_by(user_id=user.id, key=key).first()
            if user_setting:
                current = user_setting.value
        if current is None:
            platform_setting = db.query(PlatformConfig).filter_by(key=key).first()
            if platform_setting:
                current = platform_setting.value

        # Persist
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

        results.append({
            "key": key,
            "previous": current,
            "new": str(value),
            "status": "applied",
        })

    db.commit()

    return {
        "message": req.message,
        "changes": results,
        "applied": sum(1 for r in results if r["status"] == "applied"),
    }


@router.get("/schema")
def get_schema() -> dict:
    """Return the full configuration schema for the frontend."""
    return {"schema": CONFIG_SCHEMA}
