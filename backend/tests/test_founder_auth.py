import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-key-at-least-32-chars-long!!")
    monkeypatch.setattr(settings, "founder_auth_mode", "jwt")
    monkeypatch.setattr(settings, "app_env", "dev")
    return TestClient(app)


def _token(sub: str, role: str = "admin", org_id: int | None = None) -> str:
    payload = {"sub": sub, "role": role, "jti": "test-jti"}
    if org_id is not None:
        payload["org_id"] = org_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


@pytest.fixture
def raptor_login_ok(monkeypatch):
    access = _token("sysadmin@vexraptor.com")
    refresh = _token("sysadmin@vexraptor.com", role="admin")

    async def fake_post(path: str, json_body: dict):
        from httpx import Response

        if path == "/login":
            if json_body.get("password") == "bad":
                return Response(401, json={"detail": "Invalid email or password"})
            return Response(200, json={"token": access, "refresh_token": refresh})
        if path == "/refresh":
            return Response(200, json={"token": access, "refresh_token": refresh})
        return Response(404)

    monkeypatch.setattr("app.founder_auth._raptor_post", fake_post)
    return access


def test_login_sets_session_cookie(client, raptor_login_ok):
    r = client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "ok"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "sysadmin@vexraptor.com"
    me = client.get("/api/founder/v1/auth/me")
    assert me.status_code == 200


def test_login_rejects_tenant(client, monkeypatch):
    access = _token("tenant@corp.com", org_id=7)

    async def fake_post(path: str, json_body: dict):
        from httpx import Response

        return Response(200, json={"token": access, "refresh_token": "r"})

    monkeypatch.setattr("app.founder_auth._raptor_post", fake_post)
    r = client.post(
        "/api/founder/v1/auth/login",
        json={"email": "tenant@corp.com", "password": "ok"},
    )
    assert r.status_code == 403


def test_refresh_rotates_cookie(client, raptor_login_ok):
    client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "ok"},
    )
    r = client.post("/api/founder/v1/auth/refresh")
    assert r.status_code == 200
    assert client.get("/api/founder/v1/auth/me").status_code == 200


def test_logout_clears_session(client, raptor_login_ok):
    client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "ok"},
    )
    assert client.post("/api/founder/v1/auth/logout").status_code == 200
    assert client.get("/api/founder/v1/auth/me").status_code == 401
