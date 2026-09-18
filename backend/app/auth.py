from __future__ import annotations

import logging
from typing import Annotated

import httpx
import jwt
from fastapi import Cookie, Header, HTTPException
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger("vex.command.auth")

ALGORITHM = "HS256"


class Operator(BaseModel):
    email: str
    role: str | None = None
    org_id: int | None = None


def is_platform_operator(email: str, role: str | None, org_id: int | None) -> bool:
    """Same contract as Vex Raptor org_access.is_platform_operator."""
    if email.strip().lower() in settings.operator_emails:
        return True
    return role == "admin" and org_id is None


def operator_from_access_token(token: str) -> Operator:
    """Local, network-free shape check on a JWT: valid signature, not a refresh
    token used as access (S1), and belongs to a platform operator. This is
    cheap and used right after Raptor issues a token (login/refresh) where a
    revocation round-trip is pointless — the token cannot have been revoked
    yet. It does NOT prove the session is still live; see require_operator()
    for the full S1 check against Raptor on every subsequent request."""
    secret = settings.jwt_secret_key
    if not secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY not configured")
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid token")
    # S1: Raptor tags every issued token with type=access|refresh. A refresh
    # token must never be accepted where an access token is expected.
    if payload.get("type") == "refresh":
        raise HTTPException(status_code=401, detail="refresh token cannot be used as access token")
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="invalid token")
    role = payload.get("role")
    org_id = payload.get("org_id")
    if not is_platform_operator(email, role, org_id):
        raise HTTPException(status_code=403, detail="platform operator required")
    return Operator(email=email, role=role, org_id=org_id)


def decode_bearer_token(authorization: str | None) -> Operator:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="operator token required")
    return operator_from_access_token(authorization.split(" ", 1)[1].strip())


async def _raptor_me(token: str) -> httpx.Response:
    url = f"{settings.raptor_auth_url.rstrip('/')}/me"
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.get(url, headers={"Authorization": f"Bearer {token}"})


async def _validate_session_with_raptor(token: str) -> Operator:
    """S1 — last hop of every authenticated Command request: ask Raptor whether
    this access token is still a live session. Raptor's GET /me applies the
    exact checks Command can't replicate on its own (T-32 token_version vs DB,
    JTI blacklist in Redis, users.is_active) — see src/routers/_shared.py
    get_current_user. Fail closed: any transport error or non-200 response
    rejects the request instead of trusting the locally-decoded JWT alone.
    """
    try:
        r = await _raptor_me(token)
    except httpx.HTTPError as exc:
        logger.warning("raptor session check unreachable: %s", exc)
        raise HTTPException(status_code=401, detail="session could not be verified") from exc
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="session expired or revoked")
    try:
        data = r.json()
    except ValueError:
        raise HTTPException(status_code=401, detail="session could not be verified")
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="session could not be verified")
    role = data.get("role")
    org_id = data.get("org_id")
    if not is_platform_operator(email, role, org_id):
        raise HTTPException(status_code=403, detail="platform operator required")
    return Operator(email=email, role=role, org_id=org_id)


def resolve_access_token(
    authorization: str | None,
    founder_access: str | None,
) -> str | None:
    """Same credential resolution as require_operator — keep Raptor proxy in sync."""
    if (
        authorization
        and authorization.lower().startswith("bearer ")
        and settings.app_env not in ("prod", "staging")
    ):
        return authorization.split(" ", 1)[1].strip()
    if founder_access:
        return founder_access
    return None


def session_token_required(
    authorization: str | None,
    founder_access: str | None,
) -> str:
    token = resolve_access_token(authorization, founder_access)
    if not token:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "auth",
                "message": "Sesión expirada o sin permisos. Vuelve a iniciar sesión.",
            },
        )
    return token


async def require_operator(
    authorization: Annotated[str | None, Header()] = None,
    founder_access: Annotated[str | None, Cookie()] = None,
) -> Operator:
    if settings.founder_auth_mode == "mock":
        if settings.app_env in ("prod", "staging"):
            raise HTTPException(status_code=500, detail="FOUNDER_AUTH_MODE=mock forbidden in prod")
        return Operator(email="edu@vexraptor.com", role="admin", org_id=None)
    token = session_token_required(authorization, founder_access)
    operator_from_access_token(token)
    return await _validate_session_with_raptor(token)
