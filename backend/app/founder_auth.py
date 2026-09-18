"""Founder session auth — proxy Raptor login, httpOnly cookies on ops."""

from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth import Operator, is_platform_operator, operator_from_access_token, require_operator
from app.config import settings
from app.rate_limit import client_ip, enforce_login_rate_limit

logger = logging.getLogger("vex.command.auth")

router = APIRouter(prefix="/auth", tags=["founder-auth"])

ACCESS_COOKIE = "founder_access"
REFRESH_COOKIE = "founder_refresh"
# S7: cookie lifetime shorter than Raptor's underlying 2h JWT expiry (which
# Command doesn't control — never edit Raptor). This doesn't shrink the
# token's real exp, but it makes the browser drop the cookie sooner, forcing
# a /refresh round-trip — and a fresh Raptor session revalidation — every
# 45 minutes instead of letting one session coast for the full 2h window.
ACCESS_MAX_AGE = 45 * 60
REFRESH_MAX_AGE = 7 * 24 * 60 * 60


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class RefreshBody(BaseModel):
    refresh_token: str | None = None


def _secure_cookies() -> bool:
    return settings.app_env in ("prod", "staging")


def _set_session_cookies(response: Response, access: str, refresh: str | None) -> None:
    common = {"httponly": True, "secure": _secure_cookies(), "samesite": "lax", "path": "/"}
    response.set_cookie(ACCESS_COOKIE, access, max_age=ACCESS_MAX_AGE, **common)
    if refresh:
        response.set_cookie(REFRESH_COOKIE, refresh, max_age=REFRESH_MAX_AGE, **common)


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")


def _reject_non_operator(email: str, role: str | None, org_id: int | None) -> None:
    if not is_platform_operator(email, role, org_id):
        raise HTTPException(status_code=403, detail="platform operator required")


async def _raptor_post(
    path: str, json_body: dict, headers: dict[str, str] | None = None
) -> httpx.Response:
    url = f"{settings.raptor_auth_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            return await client.post(url, json=json_body, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("raptor auth unreachable: %s", exc)
        raise HTTPException(status_code=502, detail="auth upstream unavailable") from exc


def _tokens_from_raptor(data: dict) -> tuple[str, str | None]:
    access = data.get("token")
    if not access:
        raise HTTPException(status_code=502, detail="auth upstream error")
    return access, data.get("refresh_token")


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response) -> dict[str, str | None]:
    # S5: enforce Command's own per-client-IP budget before ever touching
    # Raptor — Raptor's 5/min limiter would otherwise see the container IP.
    enforce_login_rate_limit(request)
    r = await _raptor_post(
        "/login",
        {"email": body.email, "password": body.password},
        headers={"X-Forwarded-For": client_ip(request)},
    )
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if r.status_code == 429:
        raise HTTPException(status_code=429, detail="too many login attempts, try again later")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="auth upstream error")
    access, refresh = _tokens_from_raptor(r.json())
    op = operator_from_access_token(access)
    _reject_non_operator(op.email, op.role, op.org_id)
    _set_session_cookies(response, access, refresh)
    return {"email": op.email, "role": op.role}


@router.post("/refresh")
async def refresh_session(
    request: Request,
    response: Response,
    body: RefreshBody | None = None,
) -> dict[str, str | None]:
    raw = (body.refresh_token if body else None) or request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="refresh required")
    r = await _raptor_post(
        "/refresh",
        {"refresh_token": raw},
        headers={"X-Forwarded-For": client_ip(request)},
    )
    if r.status_code == 401:
        _clear_session_cookies(response)
        raise HTTPException(status_code=401, detail="session expired")
    if r.status_code == 429:
        raise HTTPException(status_code=429, detail="too many refresh attempts, try again later")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="auth upstream error")
    access, refresh = _tokens_from_raptor(r.json())
    op = operator_from_access_token(access)
    _reject_non_operator(op.email, op.role, op.org_id)
    _set_session_cookies(response, access, refresh)
    return {"email": op.email, "role": op.role}


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict[str, str]:
    # S1: Command's cookies are only a local view of the session — the JWT
    # itself stays valid until Raptor revokes its JTI. Clearing cookies alone
    # leaves a stolen/copied token usable until exp. Best-effort: Command's
    # cookies are always cleared for the browser even if Raptor is
    # unreachable, but we always attempt the real revocation first.
    access = request.cookies.get(ACCESS_COOKIE)
    refresh = request.cookies.get(REFRESH_COOKIE)
    if access:
        try:
            await _raptor_post(
                "/logout",
                {"refresh_token": refresh} if refresh else {},
                headers={"Authorization": f"Bearer {access}"},
            )
        except HTTPException as exc:
            logger.warning("raptor logout failed, clearing local cookies anyway: %s", exc.detail)
    _clear_session_cookies(response)
    return {"status": "ok"}


@router.get("/me")
async def me(operator: Annotated[Operator, Depends(require_operator)]) -> dict[str, str | None]:
    return {"email": operator.email, "role": operator.role}
