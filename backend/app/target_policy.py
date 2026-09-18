"""Allowlist validation — mirrors Vex Raptor org_target_policy semantics."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

MAX_ALLOWED_TARGETS_CHARS = 2000

_CIDR_CANDIDATE_RE = re.compile(r"^[0-9a-fA-F:.]+/\d{1,3}$")

AllowlistEntry = str | ipaddress.IPv4Network | ipaddress.IPv6Network

_METADATA_WARNING_HOSTS = frozenset(
    {
        "metadata.google.internal",
        "metadata.goog",
    }
)


def host_of(target: str) -> str:
    t = target if "://" in target else f"http://{target}"
    return (urlparse(t).hostname or target).lower()


def normalize_host(entry: str) -> str:
    host = (host_of(entry) or entry).lower().strip(".")
    if host.startswith("*."):
        host = host[2:]
    return host


def entry_key(entry: AllowlistEntry) -> str:
    return str(entry)


def entry_to_display(entry: AllowlistEntry) -> str:
    return str(entry)


def parse_allowed_targets(raw: str | None) -> list[AllowlistEntry]:
    if not raw or not str(raw).strip():
        return []
    entries: list[AllowlistEntry] = []
    seen: set[str] = set()
    for chunk in str(raw).replace(",", "\n").splitlines():
        entry = chunk.strip()
        if not entry:
            continue
        if _CIDR_CANDIDATE_RE.match(entry):
            try:
                network = ipaddress.ip_network(entry, strict=False)
            except ValueError:
                continue
            key = str(network)
            if key not in seen:
                seen.add(key)
                entries.append(network)
            continue
        host = normalize_host(entry)
        if host and host not in seen:
            seen.add(host)
            entries.append(host)
    return entries


def parse_single_entry(entry: str) -> AllowlistEntry:
    cleaned = (entry or "").strip()
    if not cleaned:
        raise ValueError("entry required")
    if _CIDR_CANDIDATE_RE.match(cleaned):
        try:
            return ipaddress.ip_network(cleaned, strict=False)
        except ValueError:
            raise ValueError("invalid CIDR notation")
    host = normalize_host(cleaned)
    if not host:
        raise ValueError("invalid target entry")
    if " " in host or "/" in host:
        raise ValueError("invalid target entry")
    return host


def serialize_allowed_targets(entries: list[AllowlistEntry]) -> str:
    return "\n".join(str(e) for e in entries)


def entry_warnings(entry: str) -> list[str]:
    warnings: list[str] = []
    cleaned = (entry or "").strip()
    if not cleaned:
        return warnings
    if _CIDR_CANDIDATE_RE.match(cleaned):
        try:
            net = ipaddress.ip_network(cleaned, strict=False)
            if net.is_link_local or net.is_loopback or net.is_private:
                warnings.append("Rango de red privada o local — verifica que sea intencional.")
        except ValueError:
            pass
        return warnings
    host = normalize_host(cleaned)
    if host in _METADATA_WARNING_HOSTS or "metadata" in host:
        warnings.append("Hostname de metadata cloud — revisa antes de autorizar.")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_link_local:
            warnings.append("IP link-local (169.254.x.x) — típica de metadata cloud.")
        elif ip.is_loopback:
            warnings.append("IP loopback — solo válida en labs controlados.")
        elif ip.is_private:
            warnings.append("IP privada — verifica que sea intencional.")
    except ValueError:
        pass
    return warnings


def merge_add(raw: str | None, entry: str) -> tuple[str, AllowlistEntry]:
    new_entry = parse_single_entry(entry)
    current = parse_allowed_targets(raw)
    key = entry_key(new_entry)
    if any(entry_key(e) == key for e in current):
        raise ValueError("target already on allowlist")
    merged = current + [new_entry]
    serialized = serialize_allowed_targets(merged)
    if len(serialized) > MAX_ALLOWED_TARGETS_CHARS:
        raise ValueError("allowlist exceeds 2000 characters")
    return serialized, new_entry


def merge_remove(raw: str | None, entry: str) -> tuple[str, AllowlistEntry | None]:
    cleaned = (entry or "").strip()
    if not cleaned:
        raise ValueError("entry required")
    current = parse_allowed_targets(raw)
    if not current:
        raise ValueError("target not on allowlist")
    remove_key = entry_key(parse_single_entry(cleaned))
    remaining: list[AllowlistEntry] = []
    removed: AllowlistEntry | None = None
    for item in current:
        if entry_key(item) == remove_key and removed is None:
            removed = item
            continue
        remaining.append(item)
    if removed is None:
        raise ValueError("target not on allowlist")
    return serialize_allowed_targets(remaining), removed
