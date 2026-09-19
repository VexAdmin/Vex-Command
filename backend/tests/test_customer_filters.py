from app.customer_filters import filter_customer_rows, sort_customer_rows
from app.ops_alerts import INACTIVE_DAYS


def _row(**kwargs):
    base = {
        "id": 1,
        "name": "Acme",
        "slug": "acme",
        "plan": "Essential",
        "risk": "ok",
        "mrr": 100.0,
        "health": 80,
        "last_active_days": 5,
        "scans_30d": 3,
    }
    base.update(kwargs)
    return base


def test_filter_inactive_14d():
    rows = [_row(last_active_days=INACTIVE_DAYS), _row(id=2, last_active_days=INACTIVE_DAYS - 1)]
    out = filter_customer_rows(rows, view="inactive_14d")
    assert len(out) == 1
    assert out[0]["id"] == 1


def test_filter_no_scans_30d():
    rows = [
        _row(id=1, scans_30d=0, last_active_days=INACTIVE_DAYS),
        _row(id=2, scans_30d=0, last_active_days=3),
        _row(id=3, scans_30d=1, last_active_days=3),
    ]
    out = filter_customer_rows(rows, view="no_scans_30d")
    assert [o["id"] for o in out] == [2]


def test_filter_empty_allowlist():
    rows = [_row(id=1), _row(id=2)]
    out = filter_customer_rows(rows, view="empty_allowlist", empty_allowlist_ids={2})
    assert [o["id"] for o in out] == [2]


def test_filter_pilot_stage_defaults_to_pilot():
    rows = [_row(id=1), _row(id=2)]
    out = filter_customer_rows(rows, pilot_stage="pilot", pilot_stage_by_org={2: "production"})
    assert [o["id"] for o in out] == [1]

