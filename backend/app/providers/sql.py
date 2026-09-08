from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import text

from app import kpis
from app.auth import Operator
from app.config import settings
from app.db import session_factory
from app.pipeline import DEFAULT_PROBABILITY, DEAL_STAGES, deals_summary, row_to_deal
from app.seed import build_world
from app.providers.mock import MockProvider

logger = logging.getLogger("vex.command.sql")

PLAN_LABEL = {
    "free": "Essential",
    "pilot": "Essential",
    "eval": "Essential",
    "essential": "Essential",
    "professional": "Professional",
    "enterprise": "Enterprise",
    "pro": "Professional",
}


def _days_ago(dt: datetime | None) -> int:
    if dt is None:
        return 999
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return max(0, int((datetime.now(UTC) - dt).total_seconds() // 86400))


def _health_score(last_active_days: int, is_active: bool, scans_30d: int, seats: int) -> int:
    recency = max(0.0, 100.0 - last_active_days * 3.2)
    payment = 100.0 if is_active else 20.0
    usage = min(100.0, scans_30d * 8.0)
    support = 70.0 if seats else 40.0
    return int(kpis.org_health(recency, payment, usage, support))


def _risk(health: int) -> str:
    if health >= 75:
        return "ok"
    if health >= 50:
        return "watch"
    return "risk"


def _row_to_org(row: Any) -> dict[str, Any]:
    last_active = row.last_active_at
    last_active_days = _days_ago(last_active)
    health = _health_score(last_active_days, row.is_active, row.scans_30d, row.seats)
    plan = PLAN_LABEL.get((row.plan or "").lower(), row.plan or "Essential")
    if isinstance(plan, str) and plan.lower() == "mssp":
        plan = "MSSP"
    elif isinstance(plan, str):
        plan = plan.title() if plan.lower() not in PLAN_LABEL else PLAN_LABEL[plan.lower()]
    slug = row.name.lower().replace(" ", "-")[:32]
    return {
        "id": row.org_id,
        "name": row.name,
        "slug": slug,
        "plan": plan,
        "mrr": 0.0,
        "health": health,
        "risk": _risk(health),
        "region": "—",
        "channel": "direct",
        "stage": "pilot" if (row.plan or "").lower() == "pilot" else "paid",
        "last_active_days": last_active_days,
        "scans_30d": row.scans_30d,
        "findings_hc_30d": row.findings_hc_30d,
        "reports_30d": row.reports_30d,
        "seats": row.seats,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "owner": "—",
        "payment_ok": True,
        "cogs_gemini": 0.0,
        "cogs_infra": 0.0,
    }


class SqlProvider:
    dataset = "pre_revenue"

    def __init__(self) -> None:
        self._fallback = MockProvider(build_world(settings.founder_seed, "pre_revenue"))

    async def _orgs(self) -> list[dict[str, Any]]:
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(text("SELECT * FROM founder.v_org_summary ORDER BY org_id"))
            return [_row_to_org(row) for row in r.fetchall()]

    async def overview(self) -> dict[str, Any]:
        orgs = await self._orgs()
        paying = [o for o in orgs if o["stage"] != "pilot"]
        pilots = len([o for o in orgs if o["stage"] == "pilot"])
        mrr = 0.0
        factory = session_factory()
        async with factory() as session:
            ops = (await session.execute(text("SELECT * FROM founder.v_platform_scan_ops"))).one()
            usage = (await session.execute(text("SELECT * FROM founder.v_usage_platform"))).one()
        alerts = []
        if ops.orphaned_running:
            alerts.append({
                "severity": "warn",
                "title": f"{ops.orphaned_running} orphaned RUNNING",
                "body": "Revisar reconcile en Raptor",
            })
        risky = [o for o in orgs if o["risk"] == "risk"]
        if risky:
            alerts.append({
                "severity": "warn",
                "title": f"{len(risky)} orgs en riesgo",
                "body": "Sin scan reciente o uso bajo",
            })
        alerts.append({
            "severity": "info",
            "title": "Pre-revenue mode",
            "body": "MRR=0 hasta Stripe (F3). Datos de uso/ops son reales.",
        })
        return {
            "dataset": self.dataset,
            "data_source": "sql",
            "arr": 0.0,
            "mrr": mrr,
            "net_new_mrr": 0.0,
            "paying_logos": len(paying),
            "pilots": pilots,
            "gross_margin": 0.0,
            "nrr": 0.0,
            "logo_churn": 0.0,
            "revenue_churn": 0.0,
            "platform_uptime": 0.994,
            "arq_depth": ops.running_scans,
            "mrr_trend": [0.0] * 12,
            "goal_net_new": {"current": 0.0, "target": 25000.0},
            "alerts": alerts,
            "billing_mode": "manual_ledger",
            "scans_7d": ops.scans_7d,
            "wau_orgs": usage.wau_orgs,
        }

    async def waterfall(self) -> dict[str, Any]:
        return {
            "start": 0,
            "new": 0,
            "expansion": 0,
            "contraction": 0,
            "churn": 0,
            "end": 0,
            "nrr": 0,
            "logo_churn": 0,
            "revenue_churn": 0,
            "by_plan": {p: 0 for p in ("Essential", "Professional", "Enterprise", "MSSP")},
            "billing": {"open_invoices": 0, "past_due": 0, "dunning": 0, "refunds_30d": 0},
        }

    async def cohorts(self) -> dict[str, Any]:
        return {"cohorts": []}

    async def customers(
        self, q: str, plan: str, risk: str, sort: str, cursor: int, limit: int
    ) -> dict[str, Any]:
        rows = await self._orgs()
        if q:
            needle = q.lower()
            rows = [o for o in rows if needle in o["name"].lower() or needle in o["slug"]]
        if plan:
            rows = [o for o in rows if o["plan"] == plan]
        if risk:
            rows = [o for o in rows if o["risk"] == risk]
        if sort == "health":
            rows = sorted(rows, key=lambda o: o["health"])
        elif sort == "last_active":
            rows = sorted(rows, key=lambda o: o["last_active_days"], reverse=True)
        else:
            rows = sorted(rows, key=lambda o: o["mrr"], reverse=True)
        slice_ = rows[cursor : cursor + limit]
        return {
            "total": len(rows),
            "cursor": cursor,
            "next_cursor": cursor + limit if cursor + limit < len(rows) else None,
            "items": slice_,
        }

    async def customer(self, org_id: int) -> dict[str, Any] | None:
        orgs = await self._orgs()
        org = next((o for o in orgs if o["id"] == org_id), None)
        if not org:
            return None
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(
                text(
                    "SELECT body, actor_email, created_at FROM founder.account_note "
                    "WHERE org_id = :org_id ORDER BY created_at DESC LIMIT 50"
                ),
                {"org_id": org_id},
            )
            notes = [
                {"body": row.body, "actor_email": row.actor_email}
                for row in r.fetchall()
            ]
        return {
            "org": org,
            "notes": notes,
            "usage_30d": {
                "scans": org["scans_30d"],
                "findings_hc": org["findings_hc_30d"],
                "reports": org["reports_30d"],
            },
            "margin": {"mrr": 0, "cogs": 0, "ratio": 0},
            "next_step": "Call + value email" if org["risk"] == "risk" else "Quarterly review",
        }

    async def add_note(self, org_id: int, body: str, operator: Operator) -> dict[str, Any]:
        if not await self.customer(org_id):
            raise ValueError("org not found")
        factory = session_factory()
        async with factory() as session:
            await session.execute(
                text(
                    "INSERT INTO founder.account_note (org_id, body, actor_email) "
                    "VALUES (:org_id, :body, :actor_email)"
                ),
                {"org_id": org_id, "body": body, "actor_email": operator.email},
            )
            await session.commit()
        return {"body": body, "actor_email": operator.email}

    async def deals(self) -> dict[str, Any]:
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(
                text(
                    "SELECT id, name, org_id, stage, acv_usd, probability, source, region, "
                    "close_date, owner_email FROM founder.deal ORDER BY updated_at DESC, id DESC"
                )
            )
            items = [row_to_deal(row) for row in r.fetchall()]
        return deals_summary(items)

    async def create_deal(self, body: dict[str, Any], operator: Operator) -> dict[str, Any]:
        name = (body.get("name") or "").strip()
        if not name:
            raise ValueError("name required")
        stage = body.get("stage") or "lead"
        if stage not in DEAL_STAGES:
            raise ValueError("invalid stage")
        acv = float(body.get("acv_usd") or 0)
        source = (body.get("source") or "inbound").strip() or "inbound"
        org_id = body.get("org_id")
        probability = int(body.get("probability") or DEFAULT_PROBABILITY.get(stage, 10))
        region = body.get("region")
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(
                text(
                    "INSERT INTO founder.deal "
                    "(name, org_id, stage, acv_usd, probability, source, region, owner_email) "
                    "VALUES (:name, :org_id, :stage, :acv_usd, :probability, :source, :region, :owner_email) "
                    "RETURNING id, name, org_id, stage, acv_usd, probability, source, region, close_date, owner_email"
                ),
                {
                    "name": name,
                    "org_id": int(org_id) if org_id is not None else None,
                    "stage": stage,
                    "acv_usd": acv,
                    "probability": probability,
                    "source": source,
                    "region": region,
                    "owner_email": operator.email,
                },
            )
            row = r.one()
            await session.execute(
                text(
                    "INSERT INTO founder.deal_activity (deal_id, kind, body, actor_email) "
                    "VALUES (:deal_id, 'note', :body, :actor_email)"
                ),
                {
                    "deal_id": row.id,
                    "body": f"Deal created in {stage}",
                    "actor_email": operator.email,
                },
            )
            await session.commit()
        return row_to_deal(row)

    async def update_deal_stage(self, deal_id: int, stage: str, operator: Operator) -> dict[str, Any]:
        if stage not in DEAL_STAGES:
            raise ValueError("invalid stage")
        probability = DEFAULT_PROBABILITY.get(stage, 10)
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(
                text(
                    "UPDATE founder.deal SET stage = :stage, probability = :probability, updated_at = now() "
                    "WHERE id = :deal_id "
                    "RETURNING id, name, org_id, stage, acv_usd, probability, source, region, close_date, owner_email"
                ),
                {"deal_id": deal_id, "stage": stage, "probability": probability},
            )
            row = r.one_or_none()
            if row is None:
                raise ValueError("deal not found")
            await session.execute(
                text(
                    "INSERT INTO founder.deal_activity (deal_id, kind, body, actor_email) "
                    "VALUES (:deal_id, 'followup', :body, :actor_email)"
                ),
                {
                    "deal_id": deal_id,
                    "body": f"Stage → {stage}",
                    "actor_email": operator.email,
                },
            )
            await session.commit()
        return row_to_deal(row)

    async def usage(self) -> dict[str, Any]:
        factory = session_factory()
        async with factory() as session:
            ops = (await session.execute(text("SELECT * FROM founder.v_platform_scan_ops"))).one()
            usage = (await session.execute(text("SELECT * FROM founder.v_usage_platform"))).one()
        orgs = await self._orgs()
        return {
            "scans_7d": ops.scans_7d,
            "findings_hc_7d": ops.findings_hc_7d,
            "wau_orgs": usage.wau_orgs,
            "reports_30d": 0,
            "by_engine": {"pentest": ops.scans_7d, "arsenal": 0, "asm": 0, "sense": 0},
            "funnel": {"signup": len(orgs), "first_scan": usage.wau_orgs, "first_high": 0, "converted": 0},
            "adoption": {},
        }

    async def economics(self) -> dict[str, Any]:
        return {
            "gemini": 0,
            "infra": 0,
            "gross_margin": 0,
            "gemini_share": 0,
            "infra_share": 0,
            "thin_margin_orgs": 0,
            "per_scan": [],
            "note": "PRICE-00 pendiente en Raptor",
        }

    async def retention(self) -> dict[str, Any]:
        orgs = await self._orgs()
        risks = sorted([o for o in orgs if o["risk"] in ("risk", "watch")], key=lambda o: o["health"])[:20]
        return {
            "logo_churn": 0,
            "revenue_churn": 0,
            "nrr": 0,
            "risks": [
                {
                    **o,
                    "signal": "No scan 21d+" if o["last_active_days"] >= 21 else "Low usage",
                    "next_step": "Call + Pilot value email" if o["health"] < 50 else "Quarterly review",
                }
                for o in risks
            ],
        }

    async def ops(self) -> dict[str, Any]:
        factory = session_factory()
        async with factory() as session:
            row = (await session.execute(text("SELECT * FROM founder.v_platform_scan_ops"))).one()
            alembic = None
            try:
                v = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                alembic = v.scalar()
            except Exception:
                pass
        health_payload: dict[str, Any] = {"status": "unknown", "version": "—"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(settings.raptor_health_url)
                if r.status_code == 200:
                    health_payload = r.json()
        except Exception as exc:
            logger.info("raptor health unreachable: %s", exc)
        return {
            "health": health_payload.get("status", "unknown"),
            "version": health_payload.get("version", "—"),
            "uptime_30d": 0.994,
            "arq_depth": row.running_scans,
            "orphaned_running": row.orphaned_running,
            "errors_5xx_24h": 0,
            "alembic_head": alembic or "—",
            "playwright": "—",
            "interactsh": "—",
            "gemini_24h": 0,
            "raptor_health_url": settings.raptor_health_url,
        }

    async def goals(self) -> dict[str, Any]:
        factory = session_factory()
        async with factory() as session:
            okr_rows = (
                await session.execute(
                    text(
                        "SELECT id, quarter, title, target, current, unit FROM founder.okr ORDER BY id"
                    )
                )
            ).fetchall()
            goal_row = (
                await session.execute(
                    text(
                        "SELECT target, current FROM founder.goal WHERE kpi = 'net_new_mrr' "
                        "ORDER BY id LIMIT 1"
                    )
                )
            ).one_or_none()
        okrs = [
            {
                "id": r.id,
                "title": r.title,
                "target": float(r.target),
                "current": float(r.current),
                "unit": r.unit,
            }
            for r in okr_rows
        ]
        net_new = (
            {"current": float(goal_row.current), "target": float(goal_row.target)}
            if goal_row
            else {"current": 0.0, "target": 25000.0}
        )
        return {
            "quarter": okr_rows[0].quarter if okr_rows else "Q3 2026",
            "okrs": okrs,
            "net_new": net_new,
            "rules": self._fallback._world.goals["rules"],
        }

    async def update_okr(self, okr_id: int, target: float, operator: Operator) -> dict[str, Any]:
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(
                text(
                    "UPDATE founder.okr SET target = :target WHERE id = :id "
                    "RETURNING id, title, target, current, unit"
                ),
                {"id": okr_id, "target": target},
            )
            row = r.one_or_none()
            if row is None:
                raise ValueError("okr not found")
            await session.commit()
        return {
            "id": row.id,
            "title": row.title,
            "target": float(row.target),
            "current": float(row.current),
            "unit": row.unit,
        }

    async def update_net_new_goal(self, target: float, operator: Operator) -> dict[str, Any]:
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(
                text(
                    "UPDATE founder.goal SET target = :target, updated_at = now() "
                    "WHERE kpi = 'net_new_mrr' RETURNING target, current"
                ),
                {"target": target},
            )
            row = r.one_or_none()
            if row is None:
                raise ValueError("goal not found")
            await session.commit()
        return {"current": float(row.current), "target": float(row.target)}

    async def alerts(self) -> dict[str, Any]:
        o = await self.overview()
        return {"items": o["alerts"], "rules": (await self.goals())["rules"]}

    async def support(self) -> dict[str, Any]:
        return {
            "open": 0,
            "median_first_reply_h": 0,
            "nps": None,
            "nps_n": 0,
            "tickets": [],
            "themes": [],
        }

    async def settings_view(self) -> dict[str, Any]:
        return {
            "host": "ops.vexraptor.com",
            "api_prefix": "/api/founder/v1",
            "currency": "USD",
            "fy_start": "January",
            "session_ttl": "45m",
            "mfa": "required",
            "ip_allowlist": False,
            "dataset": self.dataset,
            "data_source": "sql",
            "integrations": {
                "stripe": "manual_ledger",
                "slack": "optional",
                "linear": settings.linear_workspace_url or "optional",
                "clickhouse": "phase_2",
            },
            "operators": [{"email": e, "role": "founder"} for e in sorted(settings.operator_emails)],
        }

    async def weekly_brief(self) -> dict[str, Any]:
        o = await self.overview()
        lines = [
            f"{o['paying_logos']} orgs activas · {o['pilots']} pilots",
            f"Scans 7d: {o.get('scans_7d', 0)} · WAU: {o.get('wau_orgs', 0)}",
            "MRR=0 (pre-revenue). Pipeline en F2.",
            o["alerts"][0]["body"] if o["alerts"] else "Sin alertas",
            "Acción: cerrar 2 pilots esta semana",
        ]
        return {"brief": lines, "model": "fail-soft-template"}

    async def export_rows(self) -> list[list[Any]]:
        orgs = await self._orgs()
        return [[o["id"], o["name"], o["plan"], 0, o["health"], o["region"], o["stage"]] for o in orgs]
