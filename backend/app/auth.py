from __future__ import annotations

import jwt
from fastapi import Header, HTTPException
from pydantic import BaseModel

from app.config import settings

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


def decode_bearer_token(authorization: str | None) -> Operator:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="operator token required")
    secret = settings.jwt_secret_key
    if not secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY not configured")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid token")
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="invalid token")
    role = payload.get("role")
    org_id = payload.get("org_id")
    if not is_platform_operator(email, role, org_id):
        raise HTTPException(status_code=403, detail="platform operator required")
    return Operator(email=email, role=role, org_id=org_id)


def require_operator(authorization: str | None = Header(default=None)) -> Operator:
    if settings.founder_auth_mode == "mock":
        if settings.app_env in ("prod", "staging"):
            raise HTTPException(status_code=500, detail="FOUNDER_AUTH_MODE=mock forbidden in prod")
        return Operator(email="edu@vexraptor.com", role="admin", org_id=None)
    return decode_bearer_token(authorization)
