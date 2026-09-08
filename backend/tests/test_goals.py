import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_update_okr_target_mock(client):
    get = client.get("/api/founder/v1/goals")
    okr = get.json()["okrs"][0]
    r = client.put(
        "/api/founder/v1/goals",
        json={"kind": "okr", "id": okr["id"], "target": 20},
    )
    assert r.status_code == 200
    assert r.json()["result"]["target"] == 20
    reget = client.get("/api/founder/v1/goals")
    assert reget.json()["okrs"][0]["target"] == 20


def test_update_okr_not_found_mock(client):
    r = client.put("/api/founder/v1/goals", json={"kind": "okr", "id": 999, "target": 1})
    assert r.status_code == 404


def test_update_net_new_goal_mock(client):
    r = client.put("/api/founder/v1/goals", json={"kind": "net_new", "target": 30000})
    assert r.status_code == 200
    assert r.json()["result"]["target"] == 30000
    reget = client.get("/api/founder/v1/goals")
    assert reget.json()["net_new"]["target"] == 30000
