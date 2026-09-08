from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Protocol

from app.auth import Operator
from app.config import settings
from app.pipeline import DEFAULT_PROBABILITY, DEAL_STAGES, deals_summary
from app.seed import Deal, World, build_world, deal_dict, org_dict


class FounderProvider(Protocol):
    dataset: str

    async def overview(self) -> dict[str, Any]: ...
    async def waterfall(self) -> dict[str, Any]: ...
    async def cohorts(self) -> dict[str, Any]: ...
    async def customers(
        self, q: str, plan: str, risk: str, sort: str, cursor: int, limit: int
    ) -> dict[str, Any]: ...
    async def customer(self, org_id: int) -> dict[str, Any] | None: ...
    async def add_note(self, org_id: int, body: str, operator: Operator) -> dict[str, Any]: ...
    async def deals(self) -> dict[str, Any]: ...
    async def create_deal(self, body: dict[str, Any], operator: Operator) -> dict[str, Any]: ...
    async def update_deal_stage(self, deal_id: int, stage: str, operator: Operator) -> dict[str, Any]: ...
    async def usage(self) -> dict[str, Any]: ...
    async def economics(self) -> dict[str, Any]: ...
    async def retention(self) -> dict[str, Any]: ...
    async def ops(self) -> dict[str, Any]: ...
    async def goals(self) -> dict[str, Any]: ...
    async def update_okr(self, okr_id: int, target: float, operator: Operator) -> dict[str, Any]: ...
    async def update_net_new_goal(self, target: float, operator: Operator) -> dict[str, Any]: ...
    async def alerts(self) -> dict[str, Any]: ...
    async def support(self) -> dict[str, Any]: ...
    async def settings_view(self) -> dict[str, Any]: ...
    async def weekly_brief(self) -> dict[str, Any]: ...
    async def export_rows(self) -> list[list[Any]]: ...


class MockProvider:
    def __init__(self, world: World) -> None:
        self._world = world
        self.dataset = world.dataset

    async def overview(self) -> dict[str, Any]:
        return self._world.overview()

    async def waterfall(self) -> dict[str, Any]:
        return self._world.waterfall

    async def cohorts(self) -> dict[str, Any]:
        return {"cohorts": self._world.cohorts}

    async def customers(
        self, q: str, plan: str, risk: str, sort: str, cursor: int, limit: int
    ) -> dict[str, Any]:
        rows = self._world.orgs
        if q:
            needle = q.lower()
            rows = [o for o in rows if needle in o.name.lower() or needle in o.slug]
        if plan:
            rows = [o for o in rows if o.plan == plan]
        if risk:
            rows = [o for o in rows if o.risk == risk]
        if sort == "health":
            rows = sorted(rows, key=lambda o: o.health)
        elif sort == "last_active":
            rows = sorted(rows, key=lambda o: o.last_active_days, reverse=True)
        else:
            rows = sorted(rows, key=lambda o: o.mrr, reverse=True)
        slice_ = rows[cursor : cursor + limit]
        return {
            "total": len(rows),
            "cursor": cursor,
            "next_cursor": cursor + limit if cursor + limit < len(rows) else None,
            "items": [org_dict(o) for o in slice_],
        }

    async def customer(self, org_id: int) -> dict[str, Any] | None:
        org = next((o for o in self._world.orgs if o.id == org_id), None)
        if not org:
            return None
        notes = self._world.notes.get(org_id, [])
        return {
            "org": org_dict(org),
            "notes": notes,
            "usage_30d": {
                "scans": org.scans_30d,
                "findings_hc": org.findings_hc_30d,
                "reports": org.reports_30d,
            },
            "margin": {
                "mrr": org.mrr,
                "cogs": org.cogs_gemini + org.cogs_infra,
                "ratio": (org.cogs_gemini + org.cogs_infra) / org.mrr if org.mrr else 0,
            },
            "next_step": "Call + value email" if org.risk == "risk" else "Quarterly review",
        }

    async def add_note(self, org_id: int, body: str, operator: Operator) -> dict[str, Any]:
        org = next((o for o in self._world.orgs if o.id == org_id), None)
        if not org:
            raise ValueError("org not found")
        note = {"body": body, "actor_email": operator.email}
        self._world.notes.setdefault(org_id, []).insert(0, note)
        return note

    async def deals(self) -> dict[str, Any]:
        items = [deal_dict(d) for d in self._world.deals]
        goal = self._world.goals["net_new"]["target"]
        return deals_summary(items, goal)

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
        new_id = max((d.id for d in self._world.deals), default=0) + 1
        deal = Deal(
            id=new_id,
            name=name,
            org_id=int(org_id) if org_id is not None else None,
            stage=stage,  # type: ignore[arg-type]
            acv_usd=acv,
            probability=int(body.get("probability") or DEFAULT_PROBABILITY.get(stage, 10)),
            source=source,
            region=(body.get("region") or "—"),
            close_date=(date.today() + timedelta(days=30)).isoformat(),
            owner_email=operator.email,
        )
        self._world.deals.append(deal)
        return deal_dict(deal)

    async def update_deal_stage(self, deal_id: int, stage: str, operator: Operator) -> dict[str, Any]:
        if stage not in DEAL_STAGES:
            raise ValueError("invalid stage")
        deal = next((d for d in self._world.deals if d.id == deal_id), None)
        if not deal:
            raise ValueError("deal not found")
        deal.stage = stage  # type: ignore[assignment]
        deal.probability = DEFAULT_PROBABILITY.get(stage, deal.probability)
        return deal_dict(deal)

    async def usage(self) -> dict[str, Any]:
        return self._world.usage

    async def economics(self) -> dict[str, Any]:
        return self._world.economics

    async def retention(self) -> dict[str, Any]:
        risks = sorted(
            [o for o in self._world.orgs if o.risk in ("risk", "watch")],
            key=lambda o: o.health,
        )[:20]
        return {
            "logo_churn": self._world.waterfall["logo_churn"],
            "revenue_churn": self._world.waterfall["revenue_churn"],
            "nrr": self._world.waterfall["nrr"],
            "risks": [
                {
                    **org_dict(o),
                    "signal": "No scan 21d+" if o.last_active_days >= 21 else "Payment retry",
                    "next_step": "Call + Pilot value email" if o.health < 50 else "Demo Deep",
                }
                for o in risks
            ],
        }

    async def ops(self) -> dict[str, Any]:
        return self._world.ops

    async def goals(self) -> dict[str, Any]:
        data = dict(self._world.goals)
        data["okrs"] = [{**okr, "id": i + 1} for i, okr in enumerate(self._world.goals["okrs"])]
        return data

    async def update_okr(self, okr_id: int, target: float, operator: Operator) -> dict[str, Any]:
        okrs = self._world.goals["okrs"]
        if not 1 <= okr_id <= len(okrs):
            raise ValueError("okr not found")
        okrs[okr_id - 1]["target"] = target
        return {**okrs[okr_id - 1], "id": okr_id}

    async def update_net_new_goal(self, target: float, operator: Operator) -> dict[str, Any]:
        self._world.goals["net_new"]["target"] = target
        return dict(self._world.goals["net_new"])

    async def alerts(self) -> dict[str, Any]:
        return {"items": self._world.alerts, "rules": self._world.goals["rules"]}

    async def support(self) -> dict[str, Any]:
        open_t = self._world.tickets
        nps = 48 if self._world.dataset == "scale" else None
        return {
            "open": len(open_t),
            "median_first_reply_h": 3.2 if open_t else 0,
            "nps": nps,
            "nps_n": 126 if nps is not None else 0,
            "tickets": [t.__dict__ for t in open_t],
            "themes": [],
        }

    async def settings_view(self) -> dict[str, Any]:
        live = self._world.dataset == "scale"
        return {
            "host": "ops.vexraptor.com",
            "api_prefix": "/api/founder/v1",
            "currency": "USD",
            "fy_start": "January",
            "session_ttl": "45m",
            "mfa": "required",
            "ip_allowlist": False,
            "dataset": self._world.dataset,
            "data_source": "mock",
            "integrations": {
                "stripe": "connected" if live else "manual_ledger",
                "slack": "connected" if live else "optional",
                "linear": settings.linear_workspace_url or "optional",
                "clickhouse": "phase_2",
            },
            "operators": [{"email": "edu@vexraptor.com", "role": "founder"}],
        }

    async def weekly_brief(self) -> dict[str, Any]:
        o = await self.overview()
        lines = [
            f"Net new MRR ${o['net_new_mrr']:,.0f}",
            f"{o['paying_logos']} paying logos",
            f"NRR {o['nrr'] * 100:.0f}%",
        ]
        return {"brief": lines, "model": "fail-soft-template"}

    async def export_rows(self) -> list[list[Any]]:
        return [
            [o.id, o.name, o.plan, o.mrr, o.health, o.region, o.stage]
            for o in self._world.orgs
        ]


def build_mock_provider(seed: int, dataset: str) -> MockProvider:
    return MockProvider(build_world(seed, dataset))
