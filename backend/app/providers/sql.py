from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

import httpx
from sqlalchemy import text

from app import kpis
from app.auth import Operator
from app.config import settings
from app.db import session_factory
from app.prod_checks import access_max_age_seconds
from app.pipeline import DEFAULT_PROBABILITY, DEAL_STAGES, deals_summary, row_to_deal
from app.seed import build_world
from app.providers.mock import MockProvider
from app.account_checklist import (
    CHECKLIST_FIELDS,
    checklist_defaults,
    checklist_payload,
    merge_checklist_body,
)
from app.account_ops import default_next_step, normalize_pilot_stage, ops_payload
from app.customer_filters import filter_customer_rows, sort_customer_rows
from app.ops_alerts import alerts_empty_allowlist, alerts_from_orgs
from app.target_audit import parse_target_audit_row
from app.target_policy import entry_to_display, parse_allowed_targets

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


def _parse_allowed_targets(raw: str | None) -> list[str]:
    return [entry_to_display(e) for e in parse_allowed_targets(raw)]


def _month_start(day: date | None = None) -> date:
    ref = day or date.today()
    return date(ref.year, ref.month, 1)


async def _ledger_month_usd(session: Any) -> float:
    month_key = _month_start().strftime("%Y-%m")
    r = await session.execute(
        text(
            "SELECT COALESCE(SUM(mrr_usd), 0) "
            "FROM founder.manual_revenue "
            "WHERE to_char(period_month, 'YYYY-MM') = :month_key"
        ),
        {"month_key": month_key},
    )
    return float(r.scalar_one())


async def _open_deals_count(session: Any) -> int:
    r = await session.execute(
        text("SELECT COUNT(*) FROM founder.deal WHERE stage NOT IN ('won', 'lost')")
    )
    return int(r.scalar_one())


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

    async def _fetch_account_checklist_row(self, session: Any, org_id: int) -> Any:
        try:
            r = await session.execute(
                text(
                    "SELECT dpa_signed, primary_contact_set, kickoff_done, scope_documented, "
                    "updated_at, updated_by "
                    "FROM founder.account_checklist WHERE org_id = :org_id"
                ),
                {"org_id": org_id},
            )
            return r.first()
        except Exception as exc:
            logger.warning("account_checklist read failed org_id=%s: %s", org_id, exc)
            return None

    async def _fetch_account_ops_row(self, session: Any, org_id: int) -> Any:
        try:
            result = await session.execute(
                text(
                    "SELECT pilot_stage, next_step, updated_at, updated_by "
                    "FROM founder.account_ops WHERE org_id = :org_id"
                ),
                {"org_id": org_id},
            )
            return result.first()
        except Exception as exc:
            logger.warning("account_ops read failed org_id=%s: %s", org_id, exc)
            return None

    async def _fetch_target_timeline(self, session: Any, org_id: int) -> list[dict[str, Any]]:
        try:
            audit = await session.execute(
                text(
                    "SELECT actor_email, action, path, created_at "
                    "FROM founder.v_audit_log "
                    "WHERE org_id = :org_id AND action LIKE 'customers.targets.%' "
                    "ORDER BY created_at DESC LIMIT 25"
                ),
                {"org_id": org_id},
            )
            return [
                item
                for row in audit.fetchall()
                for item in [parse_target_audit_row(dict(row._mapping))]
                if item
            ]
        except Exception as exc:
            logger.warning("target timeline read failed org_id=%s: %s", org_id, exc)
            return []

    async def _orgs(self) -> list[dict[str, Any]]:
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(text("SELECT * FROM founder.v_org_summary ORDER BY org_id"))
            return [_row_to_org(row) for row in r.fetchall()]

    async def overview(self) -> dict[str, Any]:
        orgs = await self._orgs()
        with_plan = [o for o in orgs if o["stage"] != "pilot"]
        pilots = len([o for o in orgs if o["stage"] == "pilot"])
        factory = session_factory()
        async with factory() as session:
            ops = (await session.execute(text("SELECT * FROM founder.v_platform_scan_ops"))).one()
            usage = (await session.execute(text("SELECT * FROM founder.v_usage_platform"))).one()
            ledger_month = await _ledger_month_usd(session)
            open_deals = await _open_deals_count(session)
        mrr = ledger_month
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
                "href": "/customers?risk=risk",
            })
        alerts.extend(alerts_from_orgs(orgs))
        try:
            async with factory() as session:
                alerts.extend(await alerts_empty_allowlist(session))
        except Exception as exc:
            logger.warning("empty allowlist alerts skipped: %s", exc)
        return {
            "dataset": self.dataset,
            "data_source": "sql",
            "arr": kpis.arr(mrr),
            "mrr": mrr,
            "net_new_mrr": None,
            "paying_logos": len(with_plan),
            "orgs_with_plan": len(with_plan),
            "org_count": len(orgs),
            "pilots": pilots,
            "gross_margin": None,
            "nrr": None,
            "logo_churn": None,
            "revenue_churn": None,
            "platform_uptime": None,
            "arq_depth": ops.running_scans,
            "mrr_trend": None,
            "goal_net_new": {"current": None, "target": 25000.0},
            "alerts": alerts,
            "billing_mode": "manual_ledger",
            "ledger_wired": True,
            "ledger_month_usd": ledger_month,
            "open_deals": open_deals,
            "stripe_wired": False,
            "scans_7d": ops.scans_7d,
            "wau_orgs": usage.wau_orgs,
            "orphaned_running": ops.orphaned_running,
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

    async def _empty_allowlist_org_ids(self, session: Any) -> set[int]:
        r = await session.execute(
            text(
                """
                SELECT org_id FROM founder.v_org_targets
                WHERE allowed_targets IS NULL OR trim(allowed_targets) = ''
                """
            )
        )
        return {int(row.org_id) for row in r.fetchall()}

    async def _pilot_stage_by_org(self, session: Any) -> dict[int, str]:
        try:
            r = await session.execute(
                text("SELECT org_id, pilot_stage FROM founder.account_ops")
            )
            return {int(row.org_id): row.pilot_stage for row in r.fetchall()}
        except Exception as exc:
            logger.warning("account_ops list for filters failed: %s", exc)
            return {}

    async def customers(
        self,
        q: str,
        plan: str,
        risk: str,
        sort: str,
        cursor: int,
        limit: int,
        *,
        view: str = "",
        pilot_stage: str = "",
    ) -> dict[str, Any]:
        rows = await self._orgs()
        empty_ids: set[int] | None = None
        pilot_map: dict[int, str] | None = None
        need_db = view == "empty_allowlist" or bool(pilot_stage)
        if need_db:
            factory = session_factory()
            async with factory() as session:
                if view == "empty_allowlist":
                    empty_ids = await self._empty_allowlist_org_ids(session)
                if pilot_stage:
                    pilot_map = await self._pilot_stage_by_org(session)
        rows = filter_customer_rows(
            rows,
            q=q,
            plan=plan,
            risk=risk,
            view=view,
            pilot_stage=pilot_stage,
            empty_allowlist_ids=empty_ids,
            pilot_stage_by_org=pilot_map,
        )
        rows = sort_customer_rows(rows, sort)
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
            cfg = await session.execute(
                text("SELECT allowed_targets FROM founder.v_org_targets WHERE org_id = :org_id"),
                {"org_id": org_id},
            )
            cfg_row = cfg.first()
            scans = await session.execute(
                text(
                    "SELECT id, target, status, started_at, finding_count "
                    "FROM founder.v_scan_attribution "
                    "WHERE org_id = :org_id "
                    "ORDER BY founder.scan_ts(started_at) DESC NULLS LAST "
                    "LIMIT 25"
                ),
                {"org_id": org_id},
            )
            recent_scans = [
                {
                    "id": row.id,
                    "target": row.target,
                    "status": row.status,
                    "started_at": row.started_at,
                    "finding_count": row.finding_count or 0,
                }
                for row in scans.fetchall()
            ]
            ops_db = await self._fetch_account_ops_row(session, org_id)
            checklist_db = await self._fetch_account_checklist_row(session, org_id)
            target_timeline = await self._fetch_target_timeline(session, org_id)
        fallback_step = default_next_step(org["risk"])
        if ops_db:
            ops = ops_payload(
                pilot_stage=ops_db.pilot_stage,
                next_step=ops_db.next_step or fallback_step,
                updated_at=ops_db.updated_at.isoformat() if ops_db.updated_at else None,
                updated_by=ops_db.updated_by,
            )
        else:
            ops = ops_payload(
                pilot_stage="pilot",
                next_step=fallback_step,
            )
        if checklist_db:
            checklist_values = {
                key: bool(getattr(checklist_db, key)) for key in CHECKLIST_FIELDS
            }
            checklist = checklist_payload(
                checklist_values,
                updated_at=checklist_db.updated_at.isoformat() if checklist_db.updated_at else None,
                updated_by=checklist_db.updated_by,
            )
        else:
            checklist = checklist_payload(checklist_defaults())
        return {
            "org": org,
            "notes": notes,
            "ops": ops,
            "checklist": checklist,
            "target_timeline": target_timeline,
            "authorized_targets": _parse_allowed_targets(
                cfg_row.allowed_targets if cfg_row else None
            ),
            "recent_scans": recent_scans,
            "usage_30d": {
                "scans": org["scans_30d"],
                "findings_hc": org["findings_hc_30d"],
                "reports": org["reports_30d"],
            },
            "margin": {"mrr": 0, "cogs": 0, "ratio": 0},
            "next_step": ops["next_step"],
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

    async def update_account_ops(
        self, org_id: int, body: dict[str, Any], operator: Operator
    ) -> dict[str, Any]:
        orgs = await self._orgs()
        org = next((o for o in orgs if o["id"] == org_id), None)
        if not org:
            raise ValueError("org not found")
        stage = normalize_pilot_stage(body.get("pilot_stage"))
        next_step = (body.get("next_step") or "").strip() or None
        factory = session_factory()
        async with factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO founder.account_ops (org_id, pilot_stage, next_step, updated_by)
                    VALUES (:org_id, :pilot_stage, :next_step, :updated_by)
                    ON CONFLICT (org_id) DO UPDATE SET
                        pilot_stage = EXCLUDED.pilot_stage,
                        next_step = EXCLUDED.next_step,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = now()
                    """
                ),
                {
                    "org_id": org_id,
                    "pilot_stage": stage,
                    "next_step": next_step,
                    "updated_by": operator.email,
                },
            )
            await session.commit()
        refreshed = await self.customer(org_id)
        assert refreshed is not None
        return refreshed["ops"]

    async def update_account_checklist(
        self, org_id: int, body: dict[str, Any], operator: Operator
    ) -> dict[str, Any]:
        orgs = await self._orgs()
        org = next((o for o in orgs if o["id"] == org_id), None)
        if not org:
            raise ValueError("org not found")
        current = checklist_defaults()
        factory = session_factory()
        async with factory() as session:
            row = await self._fetch_account_checklist_row(session, org_id)
            if row:
                current = {key: bool(getattr(row, key)) for key in CHECKLIST_FIELDS}
            merged = merge_checklist_body(body, current)
            await session.execute(
                text(
                    """
                    INSERT INTO founder.account_checklist (
                        org_id, dpa_signed, primary_contact_set, kickoff_done,
                        scope_documented, updated_by
                    )
                    VALUES (
                        :org_id, :dpa_signed, :primary_contact_set, :kickoff_done,
                        :scope_documented, :updated_by
                    )
                    ON CONFLICT (org_id) DO UPDATE SET
                        dpa_signed = EXCLUDED.dpa_signed,
                        primary_contact_set = EXCLUDED.primary_contact_set,
                        kickoff_done = EXCLUDED.kickoff_done,
                        scope_documented = EXCLUDED.scope_documented,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = now()
                    """
                ),
                {
                    "org_id": org_id,
                    "updated_by": operator.email,
                    **merged,
                },
            )
            await session.commit()
        refreshed = await self.customer(org_id)
        assert refreshed is not None
        return refreshed["checklist"]

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

    async def manual_revenue(self) -> dict[str, Any]:
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(
                text(
                    "SELECT id, org_id, period_month, mrr_usd, channel, reason, actor_email, created_at "
                    "FROM founder.manual_revenue ORDER BY created_at DESC"
                )
            )
            items = [
                {
                    "id": row.id,
                    "org_id": row.org_id,
                    "period_month": row.period_month.isoformat(),
                    "mrr_usd": float(row.mrr_usd),
                    "channel": row.channel,
                    "reason": row.reason,
                    "actor_email": row.actor_email,
                }
                for row in r.fetchall()
            ]
        return {"items": items}

    async def add_manual_revenue(self, body: dict[str, Any], operator: Operator) -> dict[str, Any]:
        reason = (body.get("reason") or "").strip()
        if not reason:
            raise ValueError("reason required")
        try:
            mrr_usd = float(body.get("mrr_usd"))
        except (TypeError, ValueError):
            raise ValueError("mrr_usd must be a number")
        period_month = (body.get("period_month") or "").strip()
        if not period_month:
            raise ValueError("period_month required")
        try:
            period_date = date.fromisoformat(period_month)
        except ValueError:
            raise ValueError("period_month must be YYYY-MM-DD")
        channel = body.get("channel") or "direct"
        if channel not in ("direct", "partner"):
            raise ValueError("channel must be 'direct' or 'partner'")
        org_id = body.get("org_id")
        factory = session_factory()
        async with factory() as session:
            r = await session.execute(
                text(
                    "INSERT INTO founder.manual_revenue "
                    "(org_id, period_month, mrr_usd, channel, reason, actor_email) "
                    "VALUES (:org_id, :period_month, :mrr_usd, :channel, :reason, :actor_email) "
                    "RETURNING id, org_id, period_month, mrr_usd, channel, reason, actor_email"
                ),
                {
                    "org_id": int(org_id) if org_id is not None else None,
                    "period_month": period_date,
                    "mrr_usd": mrr_usd,
                    "channel": channel,
                    "reason": reason,
                    "actor_email": operator.email,
                },
            )
            row = r.one()
            await session.commit()
        return {
            "id": row.id,
            "org_id": row.org_id,
            "period_month": row.period_month.isoformat(),
            "mrr_usd": float(row.mrr_usd),
            "channel": row.channel,
            "reason": row.reason,
            "actor_email": row.actor_email,
        }

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
            usage = (await session.execute(text("SELECT * FROM founder.v_usage_platform"))).one()
            alembic = None
            try:
                v = await session.execute(text("SELECT founder.f_alembic_head()"))
                alembic = v.scalar()
            except Exception as exc:
                logger.warning("alembic head read failed: %s", exc)
        health_payload: dict[str, Any] = {"status": "unknown", "version": "—"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(settings.raptor_health_url)
                if r.status_code == 200:
                    health_payload = r.json()
        except Exception as exc:
            logger.info("raptor health unreachable: %s", exc)

        def _health_field(key: str) -> Any:
            val = health_payload.get(key)
            return val if val not in (None, "") else None

        return {
            "health": health_payload.get("status", "unknown"),
            "version": health_payload.get("version", "—"),
            "command_version": None,
            "command_deploy_label": None,
            "command_env": None,
            "arq_depth": row.running_scans,
            "orphaned_running": row.orphaned_running,
            "scans_7d": int(row.scans_7d or 0),
            "findings_hc_7d": int(row.findings_hc_7d or 0),
            "wau_orgs": int(usage.wau_orgs or 0),
            "platform_scans_30d": int(usage.scans_30d or 0),
            "uptime_30d": _health_field("uptime_30d"),
            "errors_5xx_24h": _health_field("errors_5xx_24h"),
            "alembic_head": alembic or "—",
            "playwright": _health_field("playwright"),
            "interactsh": _health_field("interactsh"),
            "gemini_24h": _health_field("gemini_24h"),
            "raptor_health_url": settings.raptor_health_url,
            "telemetry_note": (
                "Uptime, 5xx, Playwright, Interactsh y Gemini 24h requieren telemetría en Raptor "
                "(PRICE-00) o campos extra en /health — aún no expuestos."
            ),
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
            "rules": [],
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
            # S7: real access-cookie lifetime, not a fixed marketing string —
            # see ACCESS_MAX_AGE in founder_auth.py for the actual value/why.
            "session_ttl": f"{access_max_age_seconds() // 60}m",
            # S7: no MFA is implemented on this session (Raptor's own login
            # has none either). Showing "required" was a lie.
            "mfa": "no implementado",
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
