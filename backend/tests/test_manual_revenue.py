import pytest
from fastapi.testclient import TestClient

from app.main import app


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
