from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "founder_auth_mode", "mock")
    monkeypatch.setattr(settings, "data_source", "mock")
    monkeypatch.setattr(settings, "founder_dataset", "scale")


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["product"] == "vex-command"


def test_overview_scale(client):
    r = client.get("/api/founder/v1/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["paying_logos"] == 1024
    assert body["mrr"] > 300_000
    assert body["arr"] == body["mrr"] * 12


def test_customers_pagination(client):
    r = client.get("/api/founder/v1/customers", params={"limit": 25})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1024
    assert len(body["items"]) == 25


def test_customer_360_audits_without_findings_payload(client):
    r = client.get("/api/founder/v1/customers/1")
    assert r.status_code == 200
    body = r.json()
    assert "org" in body
    assert "payload" not in body
    assert "evidence" not in str(body).lower()
