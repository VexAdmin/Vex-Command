import httpx
import jwt
import pytest
from fastapi import HTTPException

from app.auth import (
    decode_bearer_token,
    is_platform_operator,
    operator_from_access_token,
    require_operator,
)
from app.config import settings


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-key-at-least-32-chars-long!!")
    monkeypatch.setattr(settings, "founder_auth_mode", "jwt")
    monkeypatch.setattr(settings, "app_env", "dev")


def _token(
    sub: str,
    role: str = "admin",
    org_id: int | None = None,
    token_type: str | None = "access",
) -> str:
    payload = {"sub": sub, "role": role, "jti": "test-jti"}
    if org_id is not None:
        payload["org_id"] = org_id
    if token_type is not None:
        payload["type"] = token_type
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def test_platform_operator_by_email():
    assert is_platform_operator("edu@vexraptor.com", "viewer", 5) is True


def test_platform_operator_admin_unscoped():
    assert is_platform_operator("x@corp.com", "admin", None) is True


def test_tenant_admin_rejected():
    assert is_platform_operator("x@corp.com", "admin", 3) is False


def test_operator_token_accepted():
    op = decode_bearer_token(f"Bearer {_token('edu@vexraptor.com')}")
    assert op.email == "edu@vexraptor.com"


def test_tenant_token_rejected():
    with pytest.raises(HTTPException) as exc:
        decode_bearer_token(f"Bearer {_token('tenant@corp.com', org_id=7)}")
    assert exc.value.status_code == 403


def test_missing_token_rejected():
    with pytest.raises(HTTPException) as exc:
        decode_bearer_token(None)
    assert exc.value.status_code == 401


# --- S1: refresh token used as access must be rejected ----------------------


def test_refresh_token_rejected_as_access():
    token = _token("edu@vexraptor.com", token_type="refresh")
    with pytest.raises(HTTPException) as exc:
        operator_from_access_token(token)
    assert exc.value.status_code == 401


def test_access_token_without_type_claim_still_accepted():
    """Raptor convention: type must be 'access' or absent, never 'refresh'."""
    token = _token("edu@vexraptor.com", token_type=None)
    op = operator_from_access_token(token)
    assert op.email == "edu@vexraptor.com"


async def test_mock_mode_dev(monkeypatch):
    monkeypatch.setattr(settings, "founder_auth_mode", "mock")
    op = await require_operator(None)
    assert op.email == "edu@vexraptor.com"


# --- S1: require_operator's last hop must revalidate the live session ------
# against Raptor (type, JTI blacklist, token_version, is_active — see
# src/routers/_shared.py get_current_user). A locally-decoded-but-revoked JWT
# must never pass.


async def test_require_operator_accepts_live_raptor_session(monkeypatch):
    async def fake_me(token: str) -> httpx.Response:
        return httpx.Response(
            200,
            json={"email": "edu@vexraptor.com", "role": "admin", "org_id": None},
        )

    monkeypatch.setattr("app.auth._raptor_me", fake_me)
    op = await require_operator(None, founder_access=_token("edu@vexraptor.com"))
    assert op.email == "edu@vexraptor.com"


async def test_require_operator_rejects_raptor_revoked_session(monkeypatch):
    async def fake_me(token: str) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Token revocado"})

    monkeypatch.setattr("app.auth._raptor_me", fake_me)
    with pytest.raises(HTTPException) as exc:
        await require_operator(None, founder_access=_token("edu@vexraptor.com"))
    assert exc.value.status_code == 401


async def test_require_operator_fails_closed_on_raptor_unreachable(monkeypatch):
    async def fake_me(token: str) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("app.auth._raptor_me", fake_me)
    with pytest.raises(HTTPException) as exc:
        await require_operator(None, founder_access=_token("edu@vexraptor.com"))
    assert exc.value.status_code == 401


async def test_require_operator_rejects_non_operator_from_raptor(monkeypatch):
    async def fake_me(token: str) -> httpx.Response:
        return httpx.Response(
            200,
            json={"email": "tenant@corp.com", "role": "admin", "org_id": 7},
        )

    monkeypatch.setattr("app.auth._raptor_me", fake_me)
    with pytest.raises(HTTPException) as exc:
        await require_operator(None, founder_access=_token("tenant@corp.com", org_id=7))
    assert exc.value.status_code == 403


# --- S7: Bearer/localStorage path disabled in prod --------------------------


async def test_require_operator_ignores_bearer_in_prod(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")

    async def fake_me(token: str) -> httpx.Response:  # pragma: no cover - must not be called
        raise AssertionError("Raptor should not be reached without a cookie")

    monkeypatch.setattr("app.auth._raptor_me", fake_me)
    with pytest.raises(HTTPException) as exc:
        await require_operator(f"Bearer {_token('edu@vexraptor.com')}", founder_access=None)
    assert exc.value.status_code == 401


async def test_require_operator_accepts_bearer_in_dev(monkeypatch):
    async def fake_me(token: str) -> httpx.Response:
        return httpx.Response(
            200, json={"email": "edu@vexraptor.com", "role": "admin", "org_id": None}
        )

    monkeypatch.setattr("app.auth._raptor_me", fake_me)
    op = await require_operator(f"Bearer {_token('edu@vexraptor.com')}", founder_access=None)
    assert op.email == "edu@vexraptor.com"
