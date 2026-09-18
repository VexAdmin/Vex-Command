"""Read org allowlists from founder SQL views (RLS-safe, same source as Account 360)."""

from __future__ import annotations

from sqlalchemy import text

from app.db import session_factory


async def fetch_org_allowed_targets(org_id: int) -> str | None:
    """Return raw allowed_targets for org_id from founder.v_org_targets."""
    factory = session_factory()
    async with factory() as session:
        result = await session.execute(
            text("SELECT allowed_targets FROM founder.v_org_targets WHERE org_id = :org_id"),
            {"org_id": org_id},
        )
        row = result.first()
        return row.allowed_targets if row else None
