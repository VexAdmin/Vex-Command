"""Deterministic synthetic world @ ~1.000 orgs. Same seed always same numbers."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Literal

from app import kpis

Plan = Literal["Essential", "Professional", "Enterprise", "MSSP"]
Risk = Literal["ok", "watch", "risk"]
Stage = Literal["pilot", "paid", "expansion"]
DealStage = Literal["lead", "qualified", "pilot", "negotiation", "won", "lost"]

PREFIXES = [
    "Nova", "Harbor", "Andes", "Meridian", "Atlántica", "Pampa", "Nimbus", "Helix",
    "Cedar", "Orion", "Vela", "Apex", "Lumen", "Forge", "Quanta", "Ridge",
    "Solace", "Vector", "Nadir", "Prism", "Kite", "Boreal", "Cinder", "Ion",
]
SUFFIXES = [
    "Sec", "Labs", "Bank", "Fintech", "MSSP", "Holdings", "Cyber", "Health",
    "Retail", "Energy", "Air", "Capital", "Systems", "Cloud", "Group", "Partners",
]
REGIONS = ["EU", "LATAM", "US", "APAC"]
CHANNELS = ["direct", "inbound", "mssp", "referral"]


class Rng:
    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = (self.state ^ (self.state >> 15)) * (1 | self.state) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    def pick(self, items: list):
        return items[int(self.next() * len(items)) % len(items)]

    def between(self, a: float, b: float) -> float:
        return a + (b - a) * self.next()

    def chance(self, p: float) -> bool:
        return self.next() < p


@dataclass
class Org:
    id: int
    name: str
    slug: str
    plan: Plan
    mrr: float
    health: int
    risk: Risk
    region: str
    channel: str
    stage: Stage
    last_active_days: int
    scans_30d: int
    findings_hc_30d: int
    reports_30d: int
    seats: int
    created_at: str
    owner: str
    payment_ok: bool
    cogs_gemini: float
    cogs_infra: float


@dataclass
class Deal:
    id: int
    name: str
    org_id: int | None
    stage: DealStage
    acv_usd: float
    probability: int
    source: str
    region: str
    close_date: str
    owner_email: str


@dataclass
class Ticket:
    id: int
    org_name: str
    title: str
    priority: str
    status: str
    age_hours: float


@dataclass
class World:
    dataset: str
    generated_at: str
    orgs: list[Org]
    pilots: int
    deals: list[Deal]
    tickets: list[Ticket]
    mrr_trend: list[float]
    waterfall: dict
    cohorts: list[dict]
    usage: dict
    economics: dict
    ops: dict
    goals: dict
    alerts: list[dict]
    notes: dict = field(default_factory=dict)

    def overview(self) -> dict:
        paying = [o for o in self.orgs if o.stage != "pilot"]
        mrr = sum(o.mrr for o in paying)
        gemini = sum(o.cogs_gemini for o in paying)
        infra = sum(o.cogs_infra for o in paying)
        nn = kpis.net_new_mrr(
            self.waterfall["new"],
            self.waterfall["expansion"],
            self.waterfall["contraction"],
            self.waterfall["churn"],
        )
        return {
            "dataset": self.dataset,
            "arr": kpis.arr(mrr),
            "mrr": mrr,
            "net_new_mrr": nn,
            "paying_logos": len(paying),
            "pilots": self.pilots,
            "gross_margin": kpis.gross_margin(mrr, gemini, infra),
            "nrr": self.waterfall["nrr"],
            "logo_churn": self.waterfall["logo_churn"],
            "revenue_churn": self.waterfall["revenue_churn"],
            "platform_uptime": self.ops["uptime_30d"],
            "arq_depth": self.ops["arq_depth"],
            "mrr_trend": self.mrr_trend,
            "goal_net_new": self.goals["net_new"],
            "alerts": self.alerts,
            "billing_mode": "manual" if self.dataset == "pre_revenue" else "stripe_live_demo",
        }


def _slug(name: str, oid: int) -> str:
    raw = hashlib.sha1(f"{name}-{oid}".encode()).hexdigest()[:8]
    return f"{name.lower().replace(' ', '-').replace('á', 'a')[:24]}-{raw}"


def build_world(seed: int = 20260907, dataset: str = "scale") -> World:
    rng = Rng(seed)
    today = date(2026, 9, 7)

    if dataset == "pre_revenue":
        return _pre_revenue(today)

    orgs: list[Org] = []
    plan_quotas: list[tuple[Plan, int, tuple[float, float]]] = [
        ("Essential", 460, (390, 790)),
        ("Professional", 308, (990, 2100)),
        ("Enterprise", 154, (2800, 6200)),
        ("MSSP", 102, (1800, 4200)),
    ]
    oid = 1
    for plan, count, (lo, hi) in plan_quotas:
        for _ in range(count):
            name = f"{rng.pick(PREFIXES)} {rng.pick(SUFFIXES)}"
            last = int(rng.between(0, 40))
            recency = max(0, 100 - last * 3.2)
            payment = 100 if rng.chance(0.97) else 20
            usage = rng.between(25, 100)
            support = rng.between(60, 100)
            health = int(kpis.org_health(recency, payment, usage, support))
            risk: Risk = "ok" if health >= 75 else "watch" if health >= 50 else "risk"
            mrr = round(rng.between(lo, hi), 0)
            scans = int(rng.between(2, 80 if plan != "Enterprise" else 140))
            gemini = round(scans * (0.16 if plan == "Essential" else 0.59 if plan == "Professional" else 1.4), 2)
            infra = round(scans * 0.09, 2)
            stage: Stage = "expansion" if rng.chance(0.18) else "paid"
            orgs.append(
                Org(
                    id=oid,
                    name=name,
                    slug=_slug(name, oid),
                    plan=plan,
                    mrr=mrr,
                    health=health,
                    risk=risk,
                    region=rng.pick(REGIONS),
                    channel=rng.pick(CHANNELS),
                    stage=stage,
                    last_active_days=last,
                    scans_30d=scans,
                    findings_hc_30d=int(scans * rng.between(0.04, 0.22)),
                    reports_30d=int(rng.between(0, 8)),
                    seats=int(rng.between(3, 80)),
                    created_at=(today - timedelta(days=int(rng.between(20, 700)))).isoformat(),
                    owner="edu@vexraptor.com",
                    payment_ok=payment > 50,
                    cogs_gemini=gemini,
                    cogs_infra=infra,
                )
            )
            oid += 1

    pilots = 86
    mrr = sum(o.mrr for o in orgs)
    nn = 18400.0
    start_mrr = mrr - nn
    expansion = round(start_mrr * 0.18, 0)
    contraction = round(start_mrr * 0.02, 0)
    churn = round(start_mrr * 0.04, 0)
    new = round(nn - expansion + contraction + churn, 0)
    # Target design COGS until PRICE-00 is wired: Gemini 14% + infra 8% of MRR.
    raw_g = sum(o.cogs_gemini for o in orgs) or 1
    raw_i = sum(o.cogs_infra for o in orgs) or 1
    fg, fi = (mrr * 0.14) / raw_g, (mrr * 0.08) / raw_i
    for o in orgs:
        o.cogs_gemini = round(o.cogs_gemini * fg, 2)
        o.cogs_infra = round(o.cogs_infra * fi, 2)
    trend = []
    cursor = mrr - nn * 11
    for i in range(12):
        cursor = cursor + nn * (0.72 + 0.05 * (i / 11))
        trend.append(round(cursor, 0))
    # Normalize last point to current MRR
    scale = mrr / trend[-1]
    trend = [round(v * scale, 0) for v in trend]

    deals = _deals(rng, orgs, today)
    tickets = _tickets(rng, orgs)
    alerts = _alerts(orgs, mrr)

    gemini = sum(o.cogs_gemini for o in orgs)
    infra = sum(o.cogs_infra for o in orgs)

    usage = {
        "scans_7d": int(sum(o.scans_30d for o in orgs) * 0.28),
        "findings_hc_7d": int(sum(o.findings_hc_30d for o in orgs) * 0.28),
        "wau_orgs": sum(1 for o in orgs if o.last_active_days <= 7),
        "reports_30d": sum(o.reports_30d for o in orgs),
        "by_engine": {"pentest": 11200, "arsenal": 3100, "asm": 2400, "sense": 48000},
        "funnel": {"signup": 140, "first_scan": 98, "first_high": 71, "converted": 24},
        "adoption": {
            "intelligence": 0.41,
            "triggers": 0.22,
            "branding": 0.18,
            "sense_fleet": 0.09,
        },
    }

    return World(
        dataset="scale",
        generated_at=today.isoformat(),
        orgs=orgs,
        pilots=pilots,
        deals=deals,
        tickets=tickets,
        mrr_trend=trend,
        waterfall={
            "start": round(start_mrr, 0),
            "new": new,
            "expansion": expansion,
            "contraction": contraction,
            "churn": churn,
            "end": round(mrr, 0),
            "nrr": round(kpis.nrr(start_mrr, expansion, contraction, churn), 4),
            "logo_churn": 0.021,
            "revenue_churn": round(kpis.revenue_churn(churn, start_mrr), 4),
            "by_plan": _by_plan(orgs),
            "billing": {"open_invoices": 41, "past_due": 7, "dunning": 3, "refunds_30d": 1200},
        },
        cohorts=[
            {"cohort": "2026-03", "m0": 1, "m1": 0.98, "m2": 1.01, "m3": 1.08, "m6": 1.14},
            {"cohort": "2026-04", "m0": 1, "m1": 0.97, "m2": 0.99, "m3": 1.05, "m6": None},
            {"cohort": "2026-05", "m0": 1, "m1": 0.96, "m2": 1.02, "m3": None, "m6": None},
            {"cohort": "2026-06", "m0": 1, "m1": 0.99, "m2": None, "m3": None, "m6": None},
            {"cohort": "2026-07", "m0": 1, "m1": 0.98, "m2": None, "m3": None, "m6": None},
        ],
        usage=usage,
        economics={
            "gemini": round(gemini, 0),
            "infra": round(infra, 0),
            "gross_margin": kpis.gross_margin(mrr, gemini, infra),
            "gemini_share": gemini / mrr if mrr else 0,
            "infra_share": infra / mrr if mrr else 0,
            "thin_margin_orgs": sum(1 for o in orgs if o.mrr and (o.cogs_gemini + o.cogs_infra) / o.mrr > 0.40),
            "per_scan": [
                {"profile": "Recon", "tokens": 0.12, "infra": 0.04, "total": 0.16, "flag": "ok"},
                {"profile": "Assessment", "tokens": 0.48, "infra": 0.11, "total": 0.59, "flag": "ok"},
                {"profile": "Deep", "tokens": 2.10, "infra": 0.40, "total": 2.50, "flag": "watch"},
            ],
        },
        ops={
            "health": "ok",
            "version": "1.4.1",
            "uptime_30d": 0.994,
            "arq_depth": 12,
            "orphaned_running": 0,
            "errors_5xx_24h": 0.0012,
            "alembic_head": "t146_sense_client_site",
            "playwright": "ok",
            "interactsh": "fail-soft",
            "gemini_24h": 1840,
        },
        goals={
            "quarter": "Q3 2026",
            "okrs": [
                {"title": "ARR → $5.0M", "current": None, "target": 5_000_000, "unit": "usd"},
                {"title": "NRR ≥ 110%", "current": None, "target": 1.10, "unit": "ratio"},
                {"title": "5 MSSP partners", "current": 4, "target": 5, "unit": "count"},
            ],
            "net_new": {"current": nn, "target": 25000},
            "rules": [
                {"name": "Failed payment ≥ 1", "enabled": True},
                {"name": "ARQ depth > 100", "enabled": True},
                {"name": "Gemini 24h > $3k", "enabled": True},
                {"name": "NRR drop > 5pp WoW", "enabled": True},
            ],
        },
        alerts=alerts,
    )


def _pre_revenue(today: date) -> World:
    nn_target = 25000
    return World(
        dataset="pre_revenue",
        generated_at=today.isoformat(),
        orgs=[],
        pilots=0,
        deals=[
            Deal(1, "Financiera del Sur", None, "lead", 18000, 10, "inbound", "LATAM", "2026-10-15", "edu@vexraptor.com"),
            Deal(2, "Retail MX inbound", None, "lead", 8000, 10, "inbound", "LATAM", "2026-10-30", "edu@vexraptor.com"),
            Deal(3, "Gov lab ES", None, "qualified", 24000, 25, "outbound", "EU", "2026-10-20", "edu@vexraptor.com"),
            Deal(4, "MSSP Chile", None, "qualified", 12000, 25, "referral", "LATAM", "2026-11-01", "edu@vexraptor.com"),
            Deal(5, "Harbor Fintech Pilot", None, "pilot", 43000, 40, "inbound", "EU", "2026-09-28", "edu@vexraptor.com"),
        ],
        tickets=[],
        mrr_trend=[0] * 12,
        waterfall={
            "start": 0, "new": 0, "expansion": 0, "contraction": 0, "churn": 0, "end": 0,
            "nrr": 0, "logo_churn": 0, "revenue_churn": 0,
            "by_plan": {p: 0 for p in ("Essential", "Professional", "Enterprise", "MSSP")},
            "billing": {"open_invoices": 0, "past_due": 0, "dunning": 0, "refunds_30d": 0},
        },
        cohorts=[],
        usage={
            "scans_7d": 0, "findings_hc_7d": 0, "wau_orgs": 0, "reports_30d": 0,
            "by_engine": {"pentest": 0, "arsenal": 0, "asm": 0, "sense": 0},
            "funnel": {"signup": 0, "first_scan": 0, "first_high": 0, "converted": 0},
            "adoption": {},
        },
        economics={
            "gemini": 0, "infra": 0, "gross_margin": 0, "gemini_share": 0, "infra_share": 0,
            "thin_margin_orgs": 0, "per_scan": [],
        },
        ops={
            "health": "ok", "version": "1.4.1", "uptime_30d": 0.994, "arq_depth": 12,
            "orphaned_running": 0, "errors_5xx_24h": 0.0012,
            "alembic_head": "t146_sense_client_site", "playwright": "ok",
            "interactsh": "fail-soft", "gemini_24h": 42,
        },
        goals={
            "quarter": "Q3 2026",
            "okrs": [
                {"title": "First 10 paying logos", "current": 0, "target": 10, "unit": "count"},
                {"title": "Close first Enterprise", "current": 0, "target": 1, "unit": "count"},
                {"title": "Stripe live + PRICE-00", "current": 0, "target": 1, "unit": "count"},
            ],
            "net_new": {"current": 0, "target": nn_target},
            "rules": [
                {"name": "Failed payment ≥ 1", "enabled": True},
                {"name": "ARQ depth > 100", "enabled": True},
                {"name": "Gemini 24h > $3k", "enabled": True},
                {"name": "NRR drop > 5pp WoW", "enabled": False},
            ],
        },
        alerts=[
            {"severity": "info", "title": "Pre-revenue mode", "body": "0 paying logos. Pipeline is the source of truth until Stripe is live."},
            {"severity": "warn", "title": "PRICE-01c open", "body": "Sin Stripe el panel de revenue miente. Usa pipeline + operating metrics."},
            {"severity": "warn", "title": "PRICE-00 open", "body": "Sin COGS Gemini por scan no hay unit economics defendible."},
        ],
    )


def _by_plan(orgs: list[Org]) -> dict[str, float]:
    out = {"Essential": 0.0, "Professional": 0.0, "Enterprise": 0.0, "MSSP": 0.0}
    for o in orgs:
        out[o.plan] += o.mrr
    return {k: round(v, 0) for k, v in out.items()}


def _deals(rng: Rng, orgs: list[Org], today: date) -> list[Deal]:
    names = [
        ("Financiera del Sur", "lead", 18000, 10, "inbound"),
        ("Retail MX inbound", "lead", 8000, 10, "inbound"),
        ("Gov lab ES", "qualified", 24000, 25, "outbound"),
        ("MSSP Chile", "qualified", 12000, 25, "referral"),
        ("Clinic Stack", "pilot", 9000, 40, "inbound"),
        ("Harbor Fintech expand", "pilot", 43000, 45, "direct"),
        ("NovaSec expand", "negotiation", 21000, 60, "mssp"),
        ("Sense Partner BR", "won", 33000, 100, "mssp"),
        ("Andes Cyber upsell", "negotiation", 7200, 55, "direct"),
        ("EU Bank RFP", "qualified", 64000, 20, "outbound"),
        ("APAC MSSP overlay", "lead", 28000, 10, "outbound"),
        ("Health group PT", "pilot", 15000, 35, "inbound"),
        ("Old MSSP trial", "lost", 11000, 0, "inbound"),
    ]
    deals = []
    for i, (name, stage, acv, prob, source) in enumerate(names, 1):
        deals.append(
            Deal(
                id=i,
                name=name,
                org_id=orgs[i * 17].id if i * 17 < len(orgs) else None,
                stage=stage,  # type: ignore[arg-type]
                acv_usd=acv,
                probability=prob,
                source=source,
                region=rng.pick(REGIONS),
                close_date=(today + timedelta(days=int(rng.between(5, 70)))).isoformat(),
                owner_email="edu@vexraptor.com",
            )
        )
    return deals


def _tickets(rng: Rng, orgs: list[Org]) -> list[Ticket]:
    titles = [
        ("SSO timeout", "P2"),
        ("White-label logo PDF", "P3"),
        ("Sense offline site", "P1"),
        ("Scan stuck RUNNING", "P2"),
        ("Report variant for board", "P3"),
        ("Seat limit reached", "P2"),
        ("SSO IdP metadata", "P2"),
    ]
    out = []
    for i, (title, pri) in enumerate(titles, 1):
        org = orgs[i * 41 % len(orgs)]
        out.append(Ticket(i, org.name, title, pri, "open", round(rng.between(1, 48), 1)))
    return out


def _alerts(orgs: list[Org], mrr: float) -> list[dict]:
    failed = [o for o in orgs if not o.payment_ok]
    risky = [o for o in orgs if o.risk == "risk"]
    dunning_mrr = sum(o.mrr for o in failed[:3])
    return [
        {"severity": "crit", "title": f"{min(3, len(failed))} failed payments", "body": f"${dunning_mrr:,.0f} MRR in dunning · acción hoy"},
        {"severity": "warn", "title": f"{len(risky)} orgs health < 50", "body": "Sin scan reciente o pago frágil · riesgo de churn"},
        {"severity": "warn", "title": "Gemini spike +38%", "body": "24h · revisar scans Deep en 4 Enterprise"},
        {"severity": "info", "title": "Pipeline coverage 2.1×", "body": f"Meta mes $25,000 net new · MRR actual ${mrr:,.0f}"},
    ]


def org_dict(o: Org) -> dict:
    return asdict(o)


def deal_dict(d: Deal) -> dict:
    return asdict(d)
