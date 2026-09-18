import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def _pre_revenue_mode(monkeypatch):
    monkeypatch.setattr(settings, "founder_auth_mode", "mock")
    monkeypatch.setattr(settings, "data_source", "mock")
    monkeypatch.setattr(settings, "founder_dataset", "pre_revenue")


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_add_manual_revenue_mock(client):
    r = client.post(
        "/api/founder/v1/revenue/manual",
        json={
            "period_month": "2026-10-01",
            "mrr_usd": 1000,
            "channel": "partner",
            "reason": "Tyndall — Cliente X — neto post 50/50",
        },
    )
    assert r.status_code == 200
    assert r.json()["entry"]["channel"] == "partner"

    listed = client.get("/api/founder/v1/revenue/manual")
    assert any(e["reason"].startswith("Tyndall") for e in listed.json()["items"])


def test_add_manual_revenue_requires_reason(client):
    r = client.post(
        "/api/founder/v1/revenue/manual",
        json={"period_month": "2026-10-01", "mrr_usd": 1000, "reason": "  "},
    )
    assert r.status_code == 400


def test_add_manual_revenue_invalid_channel(client):
    r = client.post(
        "/api/founder/v1/revenue/manual",
        json={"period_month": "2026-10-01", "mrr_usd": 1000, "reason": "x", "channel": "bogus"},
    )
    assert r.status_code == 400


def test_overview_reflects_manual_ledger(client):
    month = date.today().replace(day=1).isoformat()
    post = client.post(
        "/api/founder/v1/revenue/manual",
        json={
            "period_month": month,
            "mrr_usd": 2500,
            "channel": "direct",
            "reason": "Home ledger wiring",
        },
    )
    assert post.status_code == 200
    overview = client.get("/api/founder/v1/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["ledger_month_usd"] == 2500
    assert body["mrr"] == 2500
    assert body["ledger_wired"] is True
