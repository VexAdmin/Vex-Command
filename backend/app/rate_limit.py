"""S5 — login rate limiting by real client IP.

Command proxies /auth/login to Raptor, which rate-limits at 5/minute per IP
(src/routers/auth.py). Applied there, that limit sees the *container* IP of
the vex-founder service, not the attacker's — every operator behind Command
shares one bucket, and a brute-force from the internet never trips it. This
module enforces the same budget in Command, keyed by the actual client IP,
before the request ever reaches Raptor.

In-process only (single Command instance for Sprint 1) — a Redis-backed
store (matching Raptor's SCALE-02) is a fine follow-up if Command ever runs
more than one replica.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.config import settings

WINDOW_SECONDS = 60
MAX_ATTEMPTS = 5

_hits: dict[str, list[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    """Real client IP. X-Forwarded-For is only honored when the direct peer is
    a configured reverse proxy — otherwise an internet client could set the
    header itself and dodge the limit entirely."""
    peer = request.client.host if request.client else "unknown"
    if peer in settings.trusted_proxies:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
    return peer


def enforce_login_rate_limit(request: Request) -> None:
    ip = client_ip(request)
    now = time.monotonic()
    hits = _hits[ip]
    hits[:] = [t for t in hits if now - t < WINDOW_SECONDS]
    if len(hits) >= MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="too many login attempts, try again later")
    hits.append(now)


TARGETS_WINDOW_SECONDS = 300
TARGETS_MAX_MUTATIONS = 10

_targets_hits: dict[str, list[float]] = defaultdict(list)


def enforce_targets_rate_limit(operator_email: str, org_id: int) -> None:
    key = f"{operator_email.lower()}:{org_id}"
    now = time.monotonic()
    hits = _targets_hits[key]
    hits[:] = [t for t in hits if now - t < TARGETS_WINDOW_SECONDS]
    if len(hits) >= TARGETS_MAX_MUTATIONS:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": "Demasiados cambios seguidos. Espera unos minutos.",
            },
        )
    hits.append(now)


def reset_for_tests() -> None:
    _hits.clear()
    _targets_hits.clear()
