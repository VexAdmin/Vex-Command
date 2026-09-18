from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.config import settings
from app.raptor_client import (
    get_org_allowed_targets,
    patch_org_allowed_targets,
    raptor_api_base,
)


@pytest.fixture(autouse=True)
def _reset_raptor_urls(monkeypatch):
    monkeypatch.setattr(settings, "raptor_auth_url", "http://vex-raptor:8000/api/v1/auth")
    monkeypatch.setattr(settings, "raptor_api_url", "")


def test_raptor_api_base_derived_from_auth_url():
    assert raptor_api_base() == "http://vex-raptor:8000/api/v1"


def test_raptor_api_base_normalizes_missing_api_v1(monkeypatch):
    monkeypatch.setattr(settings, "raptor_api_url", "http://vex-raptor:8000")
    assert raptor_api_base() == "http://vex-raptor:8000/api/v1"


def _mock_client(response: httpx.Response) -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock(return_value=response)
    client.patch = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


@pytest.mark.asyncio
async def test_get_maps_raptor_403_to_structured_error():
    response = httpx.Response(
        403,
        json={"detail": "Insufficient Permissions: Administrator role required."},
    )
    with patch("app.raptor_client.httpx.AsyncClient", return_value=_mock_client(response)):
        with pytest.raises(HTTPException) as exc:
            await get_org_allowed_targets(7, "token")
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "raptor_forbidden"
    assert "Administrator" in exc.value.detail["message"]


@pytest.mark.asyncio
async def test_get_maps_raptor_404_to_org_not_found():
    response = httpx.Response(404, json={"detail": "org_not_found"})
    with patch("app.raptor_client.httpx.AsyncClient", return_value=_mock_client(response)):
        with pytest.raises(HTTPException) as exc:
            await get_org_allowed_targets(7, "token")
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "org_not_found"


@pytest.mark.asyncio
async def test_get_returns_allowed_targets_from_config_row():
    response = httpx.Response(
        200,
        json={
            "org_id": 7,
            "allowed_targets": "vehistrack.com\njackontheroad.es",
            "sentinel_enabled": False,
        },
    )
    with patch("app.raptor_client.httpx.AsyncClient", return_value=_mock_client(response)):
        raw = await get_org_allowed_targets(7, "token")
    assert raw == "vehistrack.com\njackontheroad.es"


@pytest.mark.asyncio
async def test_patch_maps_upstream_502_with_body():
    response = httpx.Response(502, text="bad gateway")
    with patch("app.raptor_client.httpx.AsyncClient", return_value=_mock_client(response)):
        with pytest.raises(HTTPException) as exc:
            await patch_org_allowed_targets(7, "lab.test", "token")
    assert exc.value.status_code == 502
    assert exc.value.detail["code"] == "raptor_unavailable"
    assert exc.value.detail["raptor_status"] == 502


@pytest.mark.asyncio
async def test_get_rejects_non_json_body():
    response = httpx.Response(200, text="<html>not json</html>")
    with patch("app.raptor_client.httpx.AsyncClient", return_value=_mock_client(response)):
        with pytest.raises(HTTPException) as exc:
            await get_org_allowed_targets(7, "token")
    assert exc.value.status_code == 502
    assert exc.value.detail["code"] == "raptor_unavailable"
