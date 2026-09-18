"""Server-side merge + Raptor proxy for org allowlist mutations."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.raptor_client import get_org_allowed_targets, patch_org_allowed_targets
from app.target_errors import policy_http_error
from app.target_policy import (
    entry_to_display,
    entry_warnings,
    merge_add,
    merge_remove,
    parse_allowed_targets,
    parse_single_entry,
)


def access_token_from_request(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    cookie = request.cookies.get("founder_access")
    if cookie:
        return cookie
    raise HTTPException(status_code=401, detail="operator token required")


def preview_entry(entry: str) -> dict:
    parsed = parse_single_entry(entry)
    return {
        "parsed": entry_to_display(parsed),
        "warnings": entry_warnings(entry),
    }


async def add_target(org_id: int, entry: str, access_token: str) -> dict:
    current_raw = await get_org_allowed_targets(org_id, access_token)
    before = [entry_to_display(e) for e in parse_allowed_targets(current_raw)]
    try:
        merged, added = merge_add(current_raw, entry)
    except ValueError as exc:
        raise policy_http_error(exc)
    await patch_org_allowed_targets(org_id, merged, access_token)
    after = [entry_to_display(e) for e in parse_allowed_targets(merged)]
    return {
        "ok": True,
        "entry": entry_to_display(added),
        "authorized_targets": after,
        "diff": {"before": before, "after": after},
        "warnings": entry_warnings(entry),
    }


async def remove_target(org_id: int, entry: str, access_token: str) -> dict:
    current_raw = await get_org_allowed_targets(org_id, access_token)
    before = [entry_to_display(e) for e in parse_allowed_targets(current_raw)]
    try:
        merged, removed = merge_remove(current_raw, entry)
    except ValueError as exc:
        raise policy_http_error(exc)
    await patch_org_allowed_targets(org_id, merged, access_token)
    after = [entry_to_display(e) for e in parse_allowed_targets(merged)]
    return {
        "ok": True,
        "entry": entry_to_display(removed) if removed else entry,
        "authorized_targets": after,
        "diff": {"before": before, "after": after},
    }
