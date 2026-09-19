import os

import pytest
from datetime import date
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
    assert body["ledger_wired"] is True
    assert isinstance(body["ledger_month_usd"], (int, float))
    assert body["mrr"] == body["ledger_month_usd"]
    assert body["data_source"] == "sql"
    assert body["paying_logos"] >= 1
    assert body["gross_margin"] is None
    assert body["nrr"] is None
    assert body["stripe_wired"] is False
    assert body["open_deals"] >= 0


def test_sql_overview_ledger_month(sql_client):
    month = date.today().replace(day=1).isoformat()
    before = sql_client.get("/api/founder/v1/overview").json()["ledger_month_usd"]
    post = sql_client.post(
        "/api/founder/v1/revenue/manual",
        json={
            "period_month": month,
            "mrr_usd": 1500,
            "channel": "direct",
            "reason": "Overview ledger test",
        },
    )
    assert post.status_code == 200
    overview = sql_client.get("/api/founder/v1/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["ledger_month_usd"] == before + 1500
    assert body["mrr"] == before + 1500
    assert body["arr"] == (before + 1500) * 12


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


def test_sql_customer_scans_and_targets(sql_client):
    r = sql_client.get("/api/founder/v1/customers/1")
    assert r.status_code == 200
    body = r.json()
    assert body["usage_30d"]["scans"] >= 2
    assert "harbor.test" in body["authorized_targets"]
    assert "api.harbor.test" in body["authorized_targets"]
    assert len(body["recent_scans"]) >= 2
    assert "findings" not in str(body["recent_scans"]).lower()


def test_sql_customer_scan_metrics_fallback(sql_client):
    r = sql_client.get("/api/founder/v1/customers/3")
    assert r.status_code == 200
    body = r.json()
    assert body["usage_30d"]["scans"] >= 1
    assert len(body["recent_scans"]) >= 1


def test_sql_ops_aggregate_metrics(sql_client):
    r = sql_client.get("/api/founder/v1/ops/platform")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["arq_depth"], int)
    assert isinstance(body["scans_7d"], int)
    assert isinstance(body["wau_orgs"], int)
    assert body["alembic_head"] not in (None, "")
    assert body["health"] in {"ok", "unknown"}
    # Raptor /health does not expose these yet in most envs:
    assert body.get("playwright") in (None, "ok", "fail-soft")


def test_sql_goals_no_mock_alert_rules(sql_client):
    r = sql_client.get("/api/founder/v1/goals")
    assert r.status_code == 200
    body = r.json()
    assert body["rules"] == []
