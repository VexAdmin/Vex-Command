from __future__ import annotations

import logging

from fastapi import Request
from sqlalchemy import text

from app.auth import Operator
from app.db import session_factory

logger = logging.getLogger("vex.command.audit")

_MEMORY: list[dict] = []


async def record(
    request: Request,
    operator: Operator,
    action: str,
    org_id: int | None = None,
) -> None:
    row = {
        "actor_email": operator.email,
        "action": action,
        "org_id": org_id,
        "path": str(request.url.path),
        "ip": request.client.host if request.client else None,
    }
    _MEMORY.insert(0, row)
    _MEMORY[:] = _MEMORY[:500]

    try:
        factory = session_factory()
    except RuntimeError:
        return

    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO founder.audit_log (actor_email, action, org_id, path, ip) "
                "VALUES (:actor_email, :action, :org_id, :path, :ip)"
            ),
            row,
        )
        await session.commit()


async def list_recent(limit: int = 100) -> list[dict]:
    try:
        factory = session_factory()
    except RuntimeError:
        return _MEMORY[:limit]

    async with factory() as session:
        r = await session.execute(
            text(
                "SELECT actor_email, action, org_id, path, ip, created_at "
                "FROM founder.audit_log ORDER BY created_at DESC LIMIT :limit"
            ),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in r.fetchall()]
