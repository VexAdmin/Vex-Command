"""Proxy to Vex Raptor org config API."""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger("vex.command.raptor")


def raptor_api_base() -> str:
    explicit = getattr(settings, "raptor_api_url", "") or ""
    if explicit:
        return explicit.rstrip("/")
    base = settings.raptor_auth_url.rstrip("/")
    if base.endswith("/auth"):
        return base[: -len("/auth")]
    return base


async def get_org_allowed_targets(org_id: int, access_token: str) -> str | None:
    url = f"{raptor_api_base()}/orgs/{org_id}/config"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError as exc:
        logger.warning("raptor org config GET failed org_id=%s: %s", org_id, exc)
        raise HTTPException(status_code=502, detail="raptor upstream unavailable") from exc
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="org not found")
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="session expired or revoked")
    if r.status_code == 403:
        raise HTTPException(status_code=403, detail="not authorized for org config")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="raptor upstream error")
    data = r.json()
    if data.get("config") is None and "allowed_targets" not in data:
        return None
    return data.get("allowed_targets")


async def patch_org_allowed_targets(org_id: int, allowed_targets: str, access_token: str) -> None:
    url = f"{raptor_api_base()}/orgs/{org_id}/config"
    body = {"allowed_targets": allowed_targets}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.patch(
                url,
                json=body,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        logger.warning("raptor org config PATCH failed org_id=%s: %s", org_id, exc)
        raise HTTPException(status_code=502, detail="raptor upstream unavailable") from exc
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="org not found")
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="session expired or revoked")
    if r.status_code == 403:
        raise HTTPException(status_code=403, detail="not authorized for org config")
    if r.status_code == 422:
        raise HTTPException(status_code=422, detail="invalid allowlist payload")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="raptor upstream error")
