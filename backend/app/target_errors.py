"""Structured target mutation errors for API + UI mapping."""

from __future__ import annotations

import json

from fastapi import HTTPException


def policy_http_error(exc: ValueError) -> HTTPException:
    msg = str(exc)
    if "already on allowlist" in msg:
        return HTTPException(
            status_code=422,
            detail={
                "code": "duplicate",
                "message": "Ese target ya está en la lista autorizada.",
            },
        )
    if "2000 characters" in msg:
        return HTTPException(
            status_code=422,
            detail={
                "code": "allowlist_too_long",
                "message": "La lista supera el límite de 2000 caracteres.",
            },
        )
    if "not on allowlist" in msg:
        return HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": "Ese target no está en la lista autorizada.",
            },
        )
    if msg in {"entry required", "invalid target entry", "invalid CIDR notation"}:
        return HTTPException(
            status_code=422,
            detail={
                "code": "invalid_format",
                "message": "Formato inválido. Usa un dominio (ej. ejemplo.com), URL https://… o CIDR.",
            },
        )
    return HTTPException(
        status_code=422,
        detail={"code": "invalid_format", "message": msg},
    )


def _raptor_detail_message(body: str) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except ValueError:
        return body.strip()[:200] or None
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, dict):
            return detail.get("message") or detail.get("code")
    return None


def raptor_http_error(
    status: int,
    *,
    org_id: int,
    action: str,
    body: str = "",
) -> HTTPException:
    upstream = _raptor_detail_message(body)
    if status == 401:
        return HTTPException(
            status_code=401,
            detail={
                "code": "auth",
                "message": "Sesión expirada o revocada.",
            },
        )
    if status == 403:
        return HTTPException(
            status_code=403,
            detail={
                "code": "raptor_forbidden",
                "message": upstream
                or "Sin permisos para editar la configuración de la organización en Raptor.",
            },
        )
    if status == 404:
        return HTTPException(
            status_code=404,
            detail={
                "code": "org_not_found",
                "message": upstream or "Organización no encontrada en Raptor.",
            },
        )
    if status == 422:
        return HTTPException(
            status_code=422,
            detail={
                "code": "raptor_rejected",
                "message": upstream or "Raptor rechazó el formato de la lista autorizada.",
            },
        )
    return HTTPException(
        status_code=502,
        detail={
            "code": "raptor_unavailable",
            "message": upstream or "Raptor no disponible. Reintenta más tarde.",
            "raptor_status": status,
            "raptor_action": action,
            "org_id": org_id,
            "raptor_body": body[:200] if body else "",
        },
    )
