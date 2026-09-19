"""Proxy to Vex Raptor org config API.

⚠️ RAPTOR TOUCH: changes here affect production Raptor deploy + JWT sessions.
Prefer founder SQL views for reads; use this module only for org config PATCH/GET
when unavoidable. See docs/operations/COMMAND_RAPTOR_BOUNDARY.md.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException

from app.config import settings
from app.target_errors import raptor_http_error

logger = logging.getLogger("vex.command.raptor")


def _normalize_raptor_api_base(base: str) -> str:
    """Ensure org-config proxy hits /api/v1/orgs/... (not bare :8000/orgs/...)."""
    normalized = base.rstrip("/")
    if normalized.endswith("/api/v1"):
        return normalized
    if "/api/v1" not in normalized:
        fixed = f"{normalized}/api/v1"
        logger.warning(
            "RAPTOR API base missing /api/v1 — normalized %s -> %s",
            normalized,
            fixed,
        )
        return fixed
    return normalized


def raptor_api_base() -> str:
    explicit = getattr(settings, "raptor_api_url", "") or ""
    if explicit:
        return _normalize_raptor_api_base(explicit)
    base = settings.raptor_auth_url.rstrip("/")
    if base.endswith("/auth"):
        base = base[: -len("/auth")]
    return _normalize_raptor_api_base(base)


def _org_config_url(org_id: int) -> str:
    return f"{raptor_api_base()}/orgs/{org_id}/config"


def _parse_json_response(response: httpx.Response, *, org_id: int, action: str) -> dict:
    try:
        data = response.json()
    except ValueError as exc:
        logger.warning(
            "raptor org config %s returned non-JSON org_id=%s status=%s body=%s",
            action,
            org_id,
            response.status_code,
            response.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail={
                "code": "raptor_unavailable",
                "message": "Raptor devolvió una respuesta inválida.",
                "raptor_action": action,
                "org_id": org_id,
            },
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=502,
            detail={
                "code": "raptor_unavailable",
                "message": "Raptor devolvió una respuesta inválida.",
                "raptor_action": action,
                "org_id": org_id,
            },
        )
    return data


async def get_org_allowed_targets(org_id: int, access_token: str) -> str | None:
    url = _org_config_url(org_id)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError as exc:
        logger.warning("raptor org config GET failed org_id=%s url=%s: %s", org_id, url, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "code": "raptor_unavailable",
                "message": "Raptor no disponible. Reintenta más tarde.",
            },
        ) from exc
    if r.status_code != 200:
        logger.warning(
            "raptor org config GET failed org_id=%s url=%s status=%s body=%s",
            org_id,
            url,
            r.status_code,
            r.text[:500],
        )
        raise raptor_http_error(
            r.status_code,
            org_id=org_id,
            action="GET org config",
            body=r.text,
        )
    data = _parse_json_response(r, org_id=org_id, action="GET")
    if data.get("config") is None and "allowed_targets" not in data:
        return None
    return data.get("allowed_targets")


async def patch_org_allowed_targets(org_id: int, allowed_targets: str, access_token: str) -> None:
    url = _org_config_url(org_id)
    body = {"allowed_targets": allowed_targets}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.patch(
                url,
                json=body,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        logger.warning("raptor org config PATCH failed org_id=%s url=%s: %s", org_id, url, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "code": "raptor_unavailable",
                "message": "Raptor no disponible. Reintenta más tarde.",
            },
        ) from exc
    if r.status_code != 200:
        logger.warning(
            "raptor org config PATCH failed org_id=%s url=%s status=%s body=%s",
            org_id,
            url,
            r.status_code,
            r.text[:500],
        )
        raise raptor_http_error(
            r.status_code,
            org_id=org_id,
            action="PATCH org config",
            body=r.text,
        )
