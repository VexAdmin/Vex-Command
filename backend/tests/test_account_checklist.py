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


def test_customer_includes_checklist(client):
    r = client.get("/api/founder/v1/customers/1")
    assert r.status_code == 200
    body = r.json()
    assert body["checklist"]["total"] == 4
    assert body["checklist"]["done_count"] == 0
    assert len(body["checklist"]["items"]) == 4


def test_patch_account_checklist_mock(client):
    patch = client.patch(
        "/api/founder/v1/customers/1/checklist",
        json={"dpa_signed": True, "kickoff_done": True},
    )
    assert patch.status_code == 200
    checklist = patch.json()["checklist"]
    assert checklist["done_count"] == 2
    keys = {item["key"]: item["done"] for item in checklist["items"]}
    assert keys["dpa_signed"] is True
    assert keys["kickoff_done"] is True
    assert keys["scope_documented"] is False

    get2 = client.get("/api/founder/v1/customers/1")
    assert get2.json()["checklist"]["done_count"] == 2


def test_ops_includes_aggregate_fields(client):
    r = client.get("/api/founder/v1/ops/platform")
    assert r.status_code == 200
    body = r.json()
    assert "scans_7d" in body
    assert "wau_orgs" in body


def test_ops_includes_command_version(client):
    r = client.get("/api/founder/v1/ops/platform")
    assert r.status_code == 200
    body = r.json()
    assert body["command_version"] == "0.2.0"
    assert body["command_env"] == "dev"
