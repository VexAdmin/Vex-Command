import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.rate_limit import reset_for_tests
from app.target_audit import parse_target_audit_row


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "founder_auth_mode", "mock")
    monkeypatch.setattr(settings, "data_source", "mock")
    reset_for_tests()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_parse_target_audit_row_add():
    row = {
        "action": "customers.targets.add",
        "actor_email": "edu@vexraptor.com",
        "path": (
            "/api/founder/v1/customers/12/targets — "
            "add ejemplo.com | harbor.test -> harbor.test\nexemplo.com"
        ),
        "created_at": "2026-09-19T10:00:00Z",
    }
    parsed = parse_target_audit_row(row)
    assert parsed is not None
    assert parsed["kind"] == "add"
    assert parsed["entry"] == "ejemplo.com"


def test_customer_includes_ops_and_timeline(client):
    r = client.get("/api/founder/v1/customers/1")
    assert r.status_code == 200
    body = r.json()
    assert body["ops"]["pilot_stage"] == "pilot"
    assert isinstance(body["target_timeline"], list)
    assert body["checklist"]["total"] == 4


def test_patch_account_ops_mock(client):
    patch = client.patch(
        "/api/founder/v1/customers/1/ops",
        json={"pilot_stage": "production", "next_step": "Renovación Q4"},
    )
    assert patch.status_code == 200
    ops = patch.json()["ops"]
    assert ops["pilot_stage"] == "production"
    assert ops["next_step"] == "Renovación Q4"

    get2 = client.get("/api/founder/v1/customers/1")
    assert get2.json()["ops"]["pilot_stage"] == "production"
