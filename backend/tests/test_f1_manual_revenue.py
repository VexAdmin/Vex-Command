import os

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def db_url():
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://vex_founder:vex_founder_dev@127.0.0.1:5433/vex_founder",
    )


@pytest.fixture
def sql_client(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)
    monkeypatch.setattr(settings, "data_source", "sql")
    monkeypatch.setattr(settings, "founder_dev_stub", True)
    monkeypatch.setattr(settings, "founder_auth_mode", "mock")
    try:
        with TestClient(app) as client:
            yield client
    except Exception as exc:
        pytest.skip(f"Postgres not available: {exc}")


def test_manual_revenue_persists_sql(sql_client):
    post = sql_client.post(
        "/api/founder/v1/revenue/manual",
        json={
            "period_month": "2026-10-01",
            "mrr_usd": 1500,
            "channel": "partner",
            "reason": "SQL persist test",
        },
    )
    assert post.status_code == 200
    with TestClient(app) as restarted:
        listed = restarted.get("/api/founder/v1/revenue/manual")
        assert any(e["reason"] == "SQL persist test" for e in listed.json()["items"])
        audit = restarted.get("/api/founder/v1/audit")
        assert "revenue.manual.create" in {i["action"] for i in audit.json()["items"]}
