"""Parse allowlist mutation rows from founder.v_audit_log."""

from __future__ import annotations

import re

_TARGET_ACTIONS = frozenset({"customers.targets.add", "customers.targets.remove"})

_DETAIL_RE = re.compile(
    r"^(add|remove)\s+(.+?)\s+\|\s*(.*?)\s*->\s*(.*)$",
    re.IGNORECASE | re.DOTALL,
)


def parse_target_audit_row(row: dict) -> dict | None:
    action = row.get("action") or ""
    if action not in _TARGET_ACTIONS:
        return None
    kind = "add" if action.endswith(".add") else "remove"
    path = row.get("path") or ""
    detail = path.split(" — ", 1)[-1] if " — " in path else ""
    entry = detail
    before_after = None
    m = _DETAIL_RE.match(detail.strip())
    if m:
        entry = m.group(2).strip()
        before_after = {"before": m.group(3).strip(), "after": m.group(4).strip()}
    created = row.get("created_at")
    return {
        "kind": kind,
        "entry": entry,
        "actor_email": row.get("actor_email"),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
        "before_after": before_after,
    }
