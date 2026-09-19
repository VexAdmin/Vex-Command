"""Shared customer list filters (oleada 2) — mock + SQL providers."""

from __future__ import annotations

from typing import Any

from app.ops_alerts import INACTIVE_DAYS

CUSTOMER_VIEWS = frozenset({"inactive_14d", "no_scans_30d", "empty_allowlist"})

PILOT_STAGE_CHOICES = frozenset({"discovery", "pilot", "production", "paused"})

_DEFAULT_PILOT_STAGE = "pilot"


def effective_pilot_stage(org_id: int, pilot_stage_by_org: dict[int, str] | None) -> str:
    if pilot_stage_by_org and org_id in pilot_stage_by_org:
        raw = (pilot_stage_by_org[org_id] or "").strip().lower()
        if raw in PILOT_STAGE_CHOICES:
            return raw
    return _DEFAULT_PILOT_STAGE


def filter_customer_rows(
    rows: list[dict[str, Any]],
    *,
    q: str = "",
    plan: str = "",
    risk: str = "",
    view: str = "",
    pilot_stage: str = "",
    empty_allowlist_ids: set[int] | None = None,
    pilot_stage_by_org: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    out = list(rows)
    if q:
        needle = q.lower()
        out = [o for o in out if needle in o["name"].lower() or needle in o.get("slug", "").lower()]
    if plan:
        out = [o for o in out if o["plan"] == plan]
    if risk:
        out = [o for o in out if o["risk"] == risk]
    if view in CUSTOMER_VIEWS:
        if view == "inactive_14d":
            out = [o for o in out if o.get("last_active_days", 0) >= INACTIVE_DAYS]
        elif view == "no_scans_30d":
            out = [
                o
                for o in out
                if o.get("scans_30d", 0) == 0 and o.get("last_active_days", 0) < INACTIVE_DAYS
            ]
        elif view == "empty_allowlist":
            ids = empty_allowlist_ids or set()
            out = [o for o in out if o["id"] in ids]
    stage_filter = (pilot_stage or "").strip().lower()
    if stage_filter in PILOT_STAGE_CHOICES:
        out = [
            o
            for o in out
            if effective_pilot_stage(o["id"], pilot_stage_by_org) == stage_filter
        ]
    return out


def sort_customer_rows(rows: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    if sort == "health":
        return sorted(rows, key=lambda o: o["health"])
    if sort == "last_active":
        return sorted(rows, key=lambda o: o.get("last_active_days", 0), reverse=True)
    return sorted(rows, key=lambda o: o.get("mrr", 0), reverse=True)
