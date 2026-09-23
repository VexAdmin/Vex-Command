"""Delete organization — Raptor (tenant) + founder purge (Command)."""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.auth import Operator
from app.db import session_factory
from app.raptor_client import delete_organization as raptor_delete_organization

logger = logging.getLogger("vex.command.org_delete")

CONFIRM_WORD = "eliminar"


async def purge_founder_org_data(org_id: int) -> None:
    factory = session_factory()
    async with factory() as session:
        try:
            await session.execute(
                text("SELECT founder.f_purge_org_command_data(:org_id)"),
                {"org_id": org_id},
            )
            await session.commit()
        except Exception as exc:
            logger.warning("founder purge failed org_id=%s: %s", org_id, exc)
            raise


async def delete_customer_organization(
    org_id: int,
    access_token: str,
    operator: Operator,
    *,
    confirm: str,
    reason: str | None,
) -> dict:
    if (confirm or "").strip().lower() != CONFIRM_WORD:
        raise ValueError("confirmation must be 'eliminar'")
    await raptor_delete_organization(org_id, access_token, reason=reason)
    await purge_founder_org_data(org_id)
    return {
        "ok": True,
        "org_id": org_id,
        "deleted_by": operator.email,
        "reason": (reason or "").strip() or None,
    }
