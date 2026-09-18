import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.rate_limit import reset_for_tests


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    reset_for_tests()
    yield
    reset_for_tests()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-key-at-least-32-chars-long!!")
    monkeypatch.setattr(settings, "founder_auth_mode", "jwt")
    monkeypatch.setattr(settings, "app_env", "dev")
    return TestClient(app)


def _token(sub: str, role: str = "admin", org_id: int | None = None) -> str:
    payload = {"sub": sub, "role": role, "jti": "test-jti", "type": "access"}
    if org_id is not None:
        payload["org_id"] = org_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


@pytest.fixture
def raptor_login_ok(monkeypatch):
    access = _token("sysadmin@vexraptor.com")
    refresh = _token("sysadmin@vexraptor.com", role="admin")

    async def fake_post(path: str, json_body: dict, headers: dict | None = None):
        from httpx import Response

        if path == "/login":
            if json_body.get("password") == "bad":
                return Response(401, json={"detail": "Invalid email or password"})
            return Response(200, json={"token": access, "refresh_token": refresh})
        if path == "/refresh":
            return Response(200, json={"token": access, "refresh_token": refresh})
        if path == "/logout":
            return Response(200, json={"status": "success"})
        return Response(404)

    monkeypatch.setattr("app.founder_auth._raptor_post", fake_post)
    return access


@pytest.fixture
def raptor_me_ok(monkeypatch):
    """S1: /auth/me and every other Command endpoint call Raptor's GET /me as
    the last-hop session check. Echo back the token's own claims so cookie
    flows set up by raptor_login_ok keep working end to end."""

    async def fake_me(token: str):
        from httpx import Response

        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        return Response(
            200,
            json={
                "email": payload.get("sub"),
                "role": payload.get("role"),
                "org_id": payload.get("org_id"),
            },
        )

    monkeypatch.setattr("app.auth._raptor_me", fake_me)


def test_login_sets_session_cookie(client, raptor_login_ok, raptor_me_ok):
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

    async def fake_post(path: str, json_body: dict, headers: dict | None = None):
        from httpx import Response

        return Response(200, json={"token": access, "refresh_token": "r"})

    monkeypatch.setattr("app.founder_auth._raptor_post", fake_post)
    r = client.post(
        "/api/founder/v1/auth/login",
        json={"email": "tenant@corp.com", "password": "ok"},
    )
    assert r.status_code == 403


def test_refresh_rotates_cookie(client, raptor_login_ok, raptor_me_ok):
    client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "ok"},
    )
    r = client.post("/api/founder/v1/auth/refresh")
    assert r.status_code == 200
    assert client.get("/api/founder/v1/auth/me").status_code == 200


def test_logout_clears_session(client, raptor_login_ok, raptor_me_ok):
    client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "ok"},
    )
    assert client.post("/api/founder/v1/auth/logout").status_code == 200
    assert client.get("/api/founder/v1/auth/me").status_code == 401


# --- S1: logout must revoke the JTI at Raptor, not just clear cookies -------


def test_logout_calls_raptor_logout_with_access_token(client, monkeypatch):
    access = _token("sysadmin@vexraptor.com")
    refresh = _token("sysadmin@vexraptor.com")
    calls: list[tuple[str, dict, dict | None]] = []

    async def fake_post(path: str, json_body: dict, headers: dict | None = None):
        from httpx import Response

        calls.append((path, json_body, headers))
        if path == "/login":
            return Response(200, json={"token": access, "refresh_token": refresh})
        if path == "/logout":
            return Response(200, json={"status": "success"})
        return Response(404)

    monkeypatch.setattr("app.founder_auth._raptor_post", fake_post)
    client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "ok"},
    )
    client.post("/api/founder/v1/auth/logout")

    logout_calls = [c for c in calls if c[0] == "/logout"]
    assert len(logout_calls) == 1
    _, body, headers = logout_calls[0]
    assert headers is not None
    assert headers["Authorization"] == f"Bearer {access}"
    assert body.get("refresh_token") == refresh


def test_logout_still_clears_cookies_when_raptor_unreachable(client, monkeypatch):
    access = _token("sysadmin@vexraptor.com")
    refresh = _token("sysadmin@vexraptor.com")

    async def fake_post(path: str, json_body: dict, headers: dict | None = None):
        from httpx import Response

        if path == "/login":
            return Response(200, json={"token": access, "refresh_token": refresh})
        if path == "/logout":
            from fastapi import HTTPException

            raise HTTPException(status_code=502, detail="auth upstream unavailable")
        return Response(404)

    monkeypatch.setattr("app.founder_auth._raptor_post", fake_post)
    client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "ok"},
    )
    r = client.post("/api/founder/v1/auth/logout")
    assert r.status_code == 200
    assert "founder_access" not in client.cookies


# --- S5: login rate limiting by client IP -----------------------------------


def test_login_rate_limited_after_five_attempts(client, raptor_login_ok):
    for _ in range(5):
        r = client.post(
            "/api/founder/v1/auth/login",
            json={"email": "sysadmin@vexraptor.com", "password": "bad"},
        )
        assert r.status_code == 401
    r = client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "bad"},
    )
    assert r.status_code == 429


def test_raptor_429_mapped_to_429_not_502(client, monkeypatch):
    async def fake_post(path: str, json_body: dict, headers: dict | None = None):
        from httpx import Response

        return Response(429, json={"detail": "rate limited"})

    monkeypatch.setattr("app.founder_auth._raptor_post", fake_post)
    r = client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "ok"},
    )
    assert r.status_code == 429


def test_login_forwards_x_forwarded_for_to_raptor(client, monkeypatch):
    captured: dict = {}

    async def fake_post(path: str, json_body: dict, headers: dict | None = None):
        from httpx import Response

        if path == "/login":
            captured["headers"] = headers
            return Response(401, json={"detail": "Invalid email or password"})
        return Response(404)

    monkeypatch.setattr("app.founder_auth._raptor_post", fake_post)
    client.post(
        "/api/founder/v1/auth/login",
        json={"email": "sysadmin@vexraptor.com", "password": "bad"},
    )
    assert "X-Forwarded-For" in captured["headers"]
