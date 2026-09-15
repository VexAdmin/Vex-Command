"""Founder session auth — proxy Raptor login, httpOnly cookies on ops."""

from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth import Operator, is_platform_operator, operator_from_access_token, require_operator
from app.config import settings

logger = logging.getLogger("vex.command.auth")

router = APIRouter(prefix="/auth", tags=["founder-auth"])

ACCESS_COOKIE = "founder_access"
REFRESH_COOKIE = "founder_refresh"
ACCESS_MAX_AGE = 2 * 60 * 60
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


async def _raptor_post(path: str, json_body: dict) -> httpx.Response:
    url = f"{settings.raptor_auth_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            return await client.post(url, json=json_body)
    except httpx.HTTPError as exc:
        logger.warning("raptor auth unreachable: %s", exc)
        raise HTTPException(status_code=502, detail="auth upstream unavailable") from exc


def _tokens_from_raptor(data: dict) -> tuple[str, str | None]:
    access = data.get("token")
    if not access:
        raise HTTPException(status_code=502, detail="auth upstream error")
    return access, data.get("refresh_token")


@router.post("/login")
async def login(body: LoginBody, response: Response) -> dict[str, str | None]:
    r = await _raptor_post("/login", {"email": body.email, "password": body.password})
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid email or password")
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
    r = await _raptor_post("/refresh", {"refresh_token": raw})
    if r.status_code == 401:
        _clear_session_cookies(response)
        raise HTTPException(status_code=401, detail="session expired")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="auth upstream error")
    access, refresh = _tokens_from_raptor(r.json())
    op = operator_from_access_token(access)
    _reject_non_operator(op.email, op.role, op.org_id)
    _set_session_cookies(response, access, refresh)
    return {"email": op.email, "role": op.role}


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    _clear_session_cookies(response)
    return {"status": "ok"}


@router.get("/me")
async def me(operator: Annotated[Operator, Depends(require_operator)]) -> dict[str, str | None]:
    return {"email": operator.email, "role": operator.role}
