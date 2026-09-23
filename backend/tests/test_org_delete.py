import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.rate_limit import reset_for_tests


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "founder_auth_mode", "mock")
    monkeypatch.setattr(settings, "data_source", "mock")
    reset_for_tests()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_delete_org_requires_confirm(client):
    r = client.request(
        "DELETE",
        "/api/founder/v1/customers/1",
        json={"confirm": "no"},
    )
    assert r.status_code == 400


def test_delete_org_mock(client):
    before = client.get("/api/founder/v1/customers", params={"limit": 5})
    total_before = before.json()["total"]
    r = client.request(
        "DELETE",
        "/api/founder/v1/customers/1",
        json={"confirm": "eliminar", "reason": "test org"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert client.get("/api/founder/v1/customers/1").status_code == 404
    after = client.get("/api/founder/v1/customers", params={"limit": 5})
    assert after.json()["total"] == total_before - 1
