import ipaddress

import pytest

from app.target_policy import (
    MAX_ALLOWED_TARGETS_CHARS,
    entry_warnings,
    merge_add,
    merge_remove,
    parse_allowed_targets,
    parse_single_entry,
    serialize_allowed_targets,
)


def test_parse_newline_and_comma():
    raw = "https://harbor.test, https://api.harbor.test\n10.0.0.0/24"
    entries = parse_allowed_targets(raw)
    assert entries == ["harbor.test", "api.harbor.test", ipaddress.ip_network("10.0.0.0/24")]


def test_parse_dedup():
    raw = "harbor.test\nharbor.test, harbor.test"
    assert parse_allowed_targets(raw) == ["harbor.test"]


def test_parse_cidr_invalid_discarded():
    assert parse_allowed_targets("10.0.0.0/999") == []


def test_parse_single_url_normalizes_host():
    assert parse_single_entry("https://Parabank.parasoft.com/") == "parabank.parasoft.com"


def test_parse_single_cidr():
    net = parse_single_entry("10.0.0.0/24")
    assert str(net) == "10.0.0.0/24"


def test_parse_single_rejects_empty():
    with pytest.raises(ValueError, match="entry required"):
        parse_single_entry("   ")


def test_merge_add_appends_and_serializes():
    merged, added = merge_add("harbor.test", "https://api.harbor.test/")
    assert added == "api.harbor.test"
    assert merged == "harbor.test\napi.harbor.test"


def test_merge_add_rejects_duplicate():
    with pytest.raises(ValueError, match="already on allowlist"):
        merge_add("harbor.test\napi.harbor.test", "api.harbor.test")


def test_merge_add_enforces_max_length():
    base = "\n".join([f"host{i}.test" for i in range(200)])
    with pytest.raises(ValueError, match="2000 characters"):
        merge_add(base, "x" * (MAX_ALLOWED_TARGETS_CHARS))


def test_merge_remove_by_hostname():
    merged, removed = merge_remove("harbor.test\napi.harbor.test", "https://api.harbor.test/")
    assert removed == "api.harbor.test"
    assert merged == "harbor.test"


def test_merge_remove_missing_raises():
    with pytest.raises(ValueError, match="not on allowlist"):
        merge_remove("harbor.test", "missing.test")


def test_entry_warnings_metadata_host():
    warnings = entry_warnings("metadata.google.internal")
    assert any("metadata" in w for w in warnings)


def test_entry_warnings_link_local_ip():
    warnings = entry_warnings("169.254.169.254")
    assert warnings


def test_serialize_one_per_line():
    entries = parse_allowed_targets("a.test, b.test")
    assert serialize_allowed_targets(entries) == "a.test\nb.test"
