"""Per-org operational fields stored in founder schema (Command-only)."""

from __future__ import annotations

PILOT_STAGES = frozenset({"discovery", "pilot", "production", "paused"})

PILOT_STAGE_LABELS = {
    "discovery": "Discovery",
    "pilot": "Piloto",
    "production": "Producción",
    "paused": "Pausado",
}


def default_next_step(risk: str) -> str:
    return "Call + value email" if risk == "risk" else "Quarterly review"


def normalize_pilot_stage(value: str | None) -> str:
    cleaned = (value or "").strip().lower()
    if cleaned not in PILOT_STAGES:
        raise ValueError("invalid pilot_stage")
    return cleaned


def ops_payload(
    *,
    pilot_stage: str,
    next_step: str | None,
    updated_at: str | None = None,
    updated_by: str | None = None,
) -> dict:
    return {
        "pilot_stage": pilot_stage,
        "pilot_stage_label": PILOT_STAGE_LABELS.get(pilot_stage, pilot_stage),
        "next_step": (next_step or "").strip() or None,
        "updated_at": updated_at,
        "updated_by": updated_by,
    }
