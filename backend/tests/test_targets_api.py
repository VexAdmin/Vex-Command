import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.audit import _MEMORY
from app.config import settings
from app.main import app
from app.rate_limit import reset_for_tests


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "founder_auth_mode", "mock")
    monkeypatch.setattr(settings, "data_source", "mock")
    monkeypatch.setattr(settings, "founder_dataset", "scale")
    reset_for_tests()
    _MEMORY.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@patch("app.targets_service.patch_org_allowed_targets", new_callable=AsyncMock)
@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_add_bare_domain_jackontheroad(get_mock, patch_mock, client):
    get_mock.return_value = "vehistrack.com\njackontheroad.es"
    patch_mock.return_value = None
    r = client.post(
        "/api/founder/v1/customers/1/targets",
        json={"entry": "jackontheroad.com"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["entry"] == "jackontheroad.com"
    assert body["authorized_targets"] == [
        "vehistrack.com",
        "jackontheroad.es",
        "jackontheroad.com",
    ]
    patch_mock.assert_awaited_once_with(
        1,
        "vehistrack.com\njackontheroad.es\njackontheroad.com",
        "test-token",
    )


@patch("app.targets_service.patch_org_allowed_targets", new_callable=AsyncMock)
@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_add_target_proxies_patch(get_mock, patch_mock, client):
    get_mock.return_value = "harbor.test"
    patch_mock.return_value = None
    r = client.post(
        "/api/founder/v1/customers/1/targets",
        json={"entry": "https://api.harbor.test/"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["entry"] == "api.harbor.test"
    assert "api.harbor.test" in body["authorized_targets"]
    patch_mock.assert_awaited_once()
    args = patch_mock.await_args.args
    assert args[0] == 1
    assert "api.harbor.test" in args[1]
    assert args[2] == "test-token"


@patch("app.targets_service.patch_org_allowed_targets", new_callable=AsyncMock)
@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_remove_target_proxies_patch(get_mock, patch_mock, client):
    get_mock.return_value = "harbor.test\napi.harbor.test"
    patch_mock.return_value = None
    r = client.request(
        "DELETE",
        "/api/founder/v1/customers/1/targets",
        content=json.dumps({"entry": "api.harbor.test"}),
        headers={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["authorized_targets"] == ["harbor.test"]
    patch_mock.assert_awaited_once_with(1, "harbor.test", "test-token")


@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_add_rejects_invalid_entry(get_mock, client):
    get_mock.return_value = None
    r = client.post(
        "/api/founder/v1/customers/1/targets",
        json={"entry": "   "},
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 400


@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_add_rejects_duplicate(get_mock, client):
    get_mock.return_value = "harbor.test"
    r = client.post(
        "/api/founder/v1/customers/1/targets",
        json={"entry": "harbor.test"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "duplicate"


@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_add_rejects_invalid_format(get_mock, client):
    get_mock.return_value = None
    r = client.post(
        "/api/founder/v1/customers/1/targets",
        json={"entry": "not a valid host"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid_format"


@patch("app.targets_service.patch_org_allowed_targets", new_callable=AsyncMock)
@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_wiring_get_then_patch(get_mock, patch_mock, client):
    get_mock.return_value = None
    patch_mock.return_value = None
    r = client.post(
        "/api/founder/v1/customers/2/targets",
        json={"entry": "lab.example"},
        headers={"Authorization": "Bearer wiring-token"},
    )
    assert r.status_code == 200
    get_mock.assert_awaited_once_with(2, "wiring-token")
    patch_mock.assert_awaited_once()
    assert patch_mock.await_args.args[1] == "lab.example"


@patch("app.targets_service.patch_org_allowed_targets", new_callable=AsyncMock)
@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_audit_recorded_on_add(get_mock, patch_mock, client):
    get_mock.return_value = None
    patch_mock.return_value = None
    client.post(
        "/api/founder/v1/customers/1/targets",
        json={"entry": "new.test"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert any(row["action"] == "customers.targets.add" for row in _MEMORY)
    row = next(r for r in _MEMORY if r["action"] == "customers.targets.add")
    assert row["org_id"] == 1
    assert "new.test" in row["path"]


@patch("app.targets_service.patch_org_allowed_targets", new_callable=AsyncMock)
@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_audit_recorded_on_remove(get_mock, patch_mock, client):
    get_mock.return_value = "only.test"
    patch_mock.return_value = None
    client.request(
        "DELETE",
        "/api/founder/v1/customers/1/targets",
        content=json.dumps({"entry": "only.test"}),
        headers={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
    )
    assert any(row["action"] == "customers.targets.remove" for row in _MEMORY)


@patch("app.targets_service.patch_org_allowed_targets", new_callable=AsyncMock)
@patch("app.targets_service.get_org_allowed_targets", new_callable=AsyncMock)
def test_rate_limit_blocks_excess_mutations(get_mock, patch_mock, client):
    get_mock.return_value = None
    patch_mock.return_value = None
    headers = {"Authorization": "Bearer test-token"}
    for i in range(10):
        r = client.post(
            "/api/founder/v1/customers/1/targets",
            json={"entry": f"host{i}.test"},
            headers=headers,
        )
        assert r.status_code == 200
    r = client.post(
        "/api/founder/v1/customers/1/targets",
        json={"entry": "host-final.test"},
        headers=headers,
    )
    assert r.status_code == 429
