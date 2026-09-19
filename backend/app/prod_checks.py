"""Fail-closed validation before serving prod/staging traffic."""

from __future__ import annotations

from app.config import settings

_SESSION_TTL_MIN = 30
_SESSION_TTL_MAX = 120


def access_max_age_seconds() -> int:
    minutes = settings.founder_session_ttl_minutes
    return minutes * 60


def validate_prod_settings() -> None:
    if settings.app_env not in ("prod", "staging"):
        return
    origin = (settings.console_origin or "").strip().rstrip("/")
    if not origin.startswith("https://"):
        raise RuntimeError(
            f"APP_ENV={settings.app_env} requires CONSOLE_ORIGIN to be https — got {origin!r}"
        )
    if settings.founder_auth_mode != "jwt":
        raise RuntimeError(
            f"APP_ENV={settings.app_env} requires FOUNDER_AUTH_MODE=jwt — got {settings.founder_auth_mode!r}"
        )
    minutes = settings.founder_session_ttl_minutes
    if not (_SESSION_TTL_MIN <= minutes <= _SESSION_TTL_MAX):
        raise RuntimeError(
            f"FOUNDER_SESSION_TTL_MINUTES must be between {_SESSION_TTL_MIN} and {_SESSION_TTL_MAX} "
            f"in prod — got {minutes}"
        )
    if settings.resolved_data_source != "sql":
        raise RuntimeError("prod/staging requires DATA_SOURCE=sql and DATABASE_URL set")
