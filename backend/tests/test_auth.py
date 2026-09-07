import jwt
import pytest
from fastapi import HTTPException

from app.auth import decode_bearer_token, is_platform_operator, require_operator
from app.config import settings


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-key-at-least-32-chars-long!!")
    monkeypatch.setattr(settings, "founder_auth_mode", "jwt")
    monkeypatch.setattr(settings, "app_env", "dev")


def _token(sub: str, role: str = "admin", org_id: int | None = None) -> str:
    payload = {"sub": sub, "role": role, "jti": "test-jti"}
    if org_id is not None:
        payload["org_id"] = org_id
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


def test_mock_mode_dev():
    settings.founder_auth_mode = "mock"
    op = require_operator(None)
    assert op.email == "edu@vexraptor.com"
