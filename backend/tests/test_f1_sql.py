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


def test_sql_overview_pre_revenue(sql_client):
    r = sql_client.get("/api/founder/v1/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["dataset"] == "pre_revenue"
    assert body["mrr"] == 0
    assert body["data_source"] == "sql"
    assert body["paying_logos"] >= 1


def test_sql_customers_no_findings_payload(sql_client):
    r = sql_client.get("/api/founder/v1/customers?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 3
    assert "findings" not in str(body).lower() or "findings_hc" in str(body)


def test_sql_note_persists(sql_client):
    post = sql_client.post("/api/founder/v1/customers/1/notes", json={"body": "F1 test note"})
    assert post.status_code == 200
    get = sql_client.get("/api/founder/v1/customers/1")
    assert any(n["body"] == "F1 test note" for n in get.json()["notes"])


def test_audit_persisted(sql_client):
    sql_client.get("/api/founder/v1/customers/1")
    audit = sql_client.get("/api/founder/v1/audit")
    assert audit.status_code == 200
    assert any(i["action"] == "customers.360" for i in audit.json()["items"])
