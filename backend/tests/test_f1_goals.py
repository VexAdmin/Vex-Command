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


def test_goal_okr_persists_sql(sql_client):
    get = sql_client.get("/api/founder/v1/goals")
    assert get.status_code == 200
    okr_id = get.json()["okrs"][0]["id"]
    put = sql_client.put(
        "/api/founder/v1/goals",
        json={"kind": "okr", "id": okr_id, "target": 42},
    )
    assert put.status_code == 200

    with TestClient(app) as restarted:
        reget = restarted.get("/api/founder/v1/goals")
        assert reget.status_code == 200
        assert any(o["id"] == okr_id and o["target"] == 42 for o in reget.json()["okrs"])
        audit = restarted.get("/api/founder/v1/audit")
        assert audit.status_code == 200
        assert "goals.update" in {i["action"] for i in audit.json()["items"]}
