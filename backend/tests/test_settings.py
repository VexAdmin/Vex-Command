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


def test_linear_integration_defaults_to_optional(client, monkeypatch):
    monkeypatch.setattr(settings, "linear_workspace_url", "")
    r = client.get("/api/founder/v1/settings")
    assert r.status_code == 200
    assert r.json()["integrations"]["linear"] == "optional"


def test_linear_integration_returns_configured_url(client, monkeypatch):
    monkeypatch.setattr(settings, "linear_workspace_url", "https://linear.app/vexsec/team/COM")
    r = client.get("/api/founder/v1/settings")
    assert r.status_code == 200
    assert r.json()["integrations"]["linear"] == "https://linear.app/vexsec/team/COM"
