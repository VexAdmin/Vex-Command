import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_create_and_move_deal_mock(client):
    create = client.post(
        "/api/founder/v1/pipeline/deals",
        json={"name": "C-10 test deal", "acv_usd": 15000, "source": "inbound"},
    )
    assert create.status_code == 200
    deal = create.json()["deal"]
    assert deal["name"] == "C-10 test deal"
    assert deal["stage"] == "lead"
    deal_id = deal["id"]

    move = client.patch(
        f"/api/founder/v1/pipeline/deals/{deal_id}",
        json={"stage": "qualified"},
    )
    assert move.status_code == 200
    assert move.json()["deal"]["stage"] == "qualified"

    listed = client.get("/api/founder/v1/pipeline/deals")
    assert listed.status_code == 200
    found = next(d for d in listed.json()["items"] if d["id"] == deal_id)
    assert found["stage"] == "qualified"


def test_create_deal_requires_name(client):
    r = client.post("/api/founder/v1/pipeline/deals", json={"name": "  "})
    assert r.status_code == 400
