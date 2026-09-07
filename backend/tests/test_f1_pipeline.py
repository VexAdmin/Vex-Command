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


def test_pipeline_persists_sql(sql_client):
    create = sql_client.post(
        "/api/founder/v1/pipeline/deals",
        json={"name": "SQL persist deal", "acv_usd": 22000, "source": "outbound"},
    )
    assert create.status_code == 200
    deal_id = create.json()["deal"]["id"]

    move = sql_client.patch(
        f"/api/founder/v1/pipeline/deals/{deal_id}",
        json={"stage": "pilot"},
    )
    assert move.status_code == 200
    assert move.json()["deal"]["stage"] == "pilot"

    # New client simulates API restart — deal must still exist in Postgres
    with TestClient(app) as restarted:
        listed = restarted.get("/api/founder/v1/pipeline/deals")
        assert listed.status_code == 200
        found = next(d for d in listed.json()["items"] if d["id"] == deal_id)
        assert found["name"] == "SQL persist deal"
        assert found["stage"] == "pilot"

        activity = restarted.get("/api/founder/v1/audit")
        assert activity.status_code == 200
        actions = {i["action"] for i in activity.json()["items"]}
        assert "pipeline.create" in actions
        assert "pipeline.update" in actions
