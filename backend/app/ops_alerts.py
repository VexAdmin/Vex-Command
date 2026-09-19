"""Operational alerts for Command overview — aggregates only, no Raptor API."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

INACTIVE_DAYS = 14
_MAX_NAMES_IN_BODY = 4


def _name_list(orgs: list[dict[str, Any]], limit: int = _MAX_NAMES_IN_BODY) -> str:
    names = [o["name"] for o in orgs[:limit]]
    extra = len(orgs) - limit
    body = ", ".join(names)
    if extra > 0:
        body += f" (+{extra} más)"
    return body


def alerts_from_orgs(orgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pure-Python alerts from org summary rows (mock + sql)."""
    out: list[dict[str, Any]] = []
    inactive = [o for o in orgs if o.get("last_active_days", 0) >= INACTIVE_DAYS]
    if inactive:
        out.append(
            {
                "severity": "warn",
                "title": f"{len(inactive)} cuenta(s) sin actividad {INACTIVE_DAYS}d+",
                "body": _name_list(inactive),
                "href": "/customers?sort=last_active",
            }
        )
    cold_usage = [o for o in orgs if o.get("scans_30d", 0) == 0 and o.get("last_active_days", 0) < INACTIVE_DAYS]
    if cold_usage:
        out.append(
            {
                "severity": "info",
                "title": f"{len(cold_usage)} cuenta(s) sin scans en 30d",
                "body": _name_list(cold_usage),
                "href": "/customers",
            }
        )
    return out


async def alerts_empty_allowlist(session: AsyncSession) -> list[dict[str, Any]]:
    """Orgs with an org_configs row but empty allowed_targets (via founder view)."""
    r = await session.execute(
        text(
            """
            SELECT t.org_id, o.name
            FROM founder.v_org_targets t
            JOIN public.organizations o ON o.id = t.org_id
            WHERE t.allowed_targets IS NULL
               OR trim(t.allowed_targets) = ''
            ORDER BY o.name
            LIMIT 20
            """
        )
    )
    rows = r.fetchall()
    if not rows:
        return []
    names = ", ".join(row.name for row in rows[:_MAX_NAMES_IN_BODY])
    extra = len(rows) - _MAX_NAMES_IN_BODY
    if extra > 0:
        names += f" (+{extra} más)"
    first_id = rows[0].org_id
    return [
        {
            "severity": "crit",
            "title": f"{len(rows)} cuenta(s) con allowlist vacía",
            "body": names,
            "href": f"/customers/{first_id}",
        }
    ]
