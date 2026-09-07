from __future__ import annotations

from typing import Any

DEAL_STAGES = frozenset({"lead", "qualified", "pilot", "negotiation", "won", "lost"})
STAGE_ORDER = ("lead", "qualified", "pilot", "negotiation", "won")
DEFAULT_PROBABILITY = {
    "lead": 10,
    "qualified": 25,
    "pilot": 40,
    "negotiation": 60,
    "won": 100,
    "lost": 0,
}
NET_NEW_GOAL = 25_000.0


def row_to_deal(row: Any) -> dict[str, Any]:
    close = row.close_date
    return {
        "id": row.id,
        "name": row.name,
        "org_id": row.org_id,
        "stage": row.stage,
        "acv_usd": float(row.acv_usd),
        "probability": int(row.probability),
        "source": row.source,
        "region": row.region or "—",
        "close_date": close.isoformat() if close else None,
        "owner_email": row.owner_email or "—",
    }


def deals_summary(items: list[dict[str, Any]], goal: float = NET_NEW_GOAL) -> dict[str, Any]:
    open_ = [d for d in items if d["stage"] not in ("won", "lost")]
    pipeline = sum(d["acv_usd"] for d in open_)
    weighted = sum(d["acv_usd"] * d["probability"] / 100 for d in open_)
    won = sum(1 for d in items if d["stage"] == "won")
    closed = sum(1 for d in items if d["stage"] in ("won", "lost"))
    return {
        "items": items,
        "pipeline": pipeline,
        "weighted": weighted,
        "coverage": (weighted / goal) if goal else 0,
        "win_rate": (won / closed) if closed else 0,
    }


def next_stage(stage: str) -> str | None:
    if stage not in STAGE_ORDER:
        return None
    idx = STAGE_ORDER.index(stage)
    if idx + 1 >= len(STAGE_ORDER):
        return None
    return STAGE_ORDER[idx + 1]
