"""Operational checklist fields per org (founder schema, Command-only)."""

from __future__ import annotations

from typing import Any

CHECKLIST_FIELDS: tuple[str, ...] = (
    "dpa_signed",
    "primary_contact_set",
    "kickoff_done",
    "scope_documented",
)

CHECKLIST_LABELS: dict[str, str] = {
    "dpa_signed": "DPA / acuerdo firmado",
    "primary_contact_set": "Contacto principal registrado",
    "kickoff_done": "Kickoff realizado",
    "scope_documented": "Alcance documentado",
}


def checklist_defaults() -> dict[str, bool]:
    return {key: False for key in CHECKLIST_FIELDS}


def checklist_payload(
    values: dict[str, bool],
    *,
    updated_at: str | None = None,
    updated_by: str | None = None,
) -> dict[str, Any]:
    items = [
        {"key": key, "label": CHECKLIST_LABELS[key], "done": bool(values.get(key, False))}
        for key in CHECKLIST_FIELDS
    ]
    done_count = sum(1 for item in items if item["done"])
    return {
        "items": items,
        "done_count": done_count,
        "total": len(CHECKLIST_FIELDS),
        "updated_at": updated_at,
        "updated_by": updated_by,
    }


def merge_checklist_body(body: dict[str, Any], current: dict[str, bool]) -> dict[str, bool]:
    merged = dict(current)
    for key in CHECKLIST_FIELDS:
        if key in body:
            merged[key] = bool(body[key])
    return merged
