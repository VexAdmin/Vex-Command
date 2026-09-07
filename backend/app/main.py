from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.audit import list_recent, record
from app.auth import Operator, require_operator
from app.config import settings
from app.db import close_db, init_db
from app.providers import build_provider

OperatorDep = Annotated[Operator, Depends(require_operator)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.provider = build_provider()
    yield
    await close_db()


app = FastAPI(title="Vex Command", version="0.2.0", docs_url="/api/founder/docs", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.console_origin, "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def noindex(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


def _provider(request: Request):
    return request.app.state.provider


@app.get("/health")
async def health(request: Request):
    p = _provider(request)
    return {
        "status": "ok",
        "product": "vex-command",
        "version": "0.2.0",
        "dataset": p.dataset,
        "data_source": settings.resolved_data_source,
        "auth_mode": settings.founder_auth_mode,
    }


@app.get("/api/founder/v1/overview")
async def overview(request: Request, operator: OperatorDep):
    await record(request, operator, "overview.read")
    return await _provider(request).overview()


@app.get("/api/founder/v1/revenue/waterfall")
async def waterfall(request: Request, operator: OperatorDep):
    await record(request, operator, "revenue.waterfall")
    return await _provider(request).waterfall()


@app.get("/api/founder/v1/revenue/cohorts")
async def cohorts(request: Request, operator: OperatorDep):
    await record(request, operator, "revenue.cohorts")
    return await _provider(request).cohorts()


@app.get("/api/founder/v1/customers")
async def customers(
    request: Request,
    operator: OperatorDep,
    q: str = "",
    plan: str = "",
    risk: str = "",
    sort: str = "mrr",
    cursor: int = 0,
    limit: int = Query(25, le=100),
):
    await record(request, operator, "customers.list")
    return await _provider(request).customers(q, plan, risk, sort, cursor, limit)


@app.get("/api/founder/v1/customers/{org_id}")
async def customer(org_id: int, request: Request, operator: OperatorDep):
    await record(request, operator, "customers.360", org_id)
    data = await _provider(request).customer(org_id)
    if not data:
        raise HTTPException(404, "org not found")
    return data


@app.post("/api/founder/v1/customers/{org_id}/notes")
async def add_note(org_id: int, request: Request, operator: OperatorDep):
    await record(request, operator, "customers.note", org_id)
    body = await request.json()
    text = (body.get("body") or "").strip()
    if not text:
        raise HTTPException(400, "empty note")
    try:
        note = await _provider(request).add_note(org_id, text, operator)
    except ValueError:
        raise HTTPException(404, "org not found")
    return {"ok": True, "note": note}


@app.get("/api/founder/v1/pipeline/deals")
async def deals(request: Request, operator: OperatorDep):
    await record(request, operator, "pipeline.list")
    return await _provider(request).deals()


@app.post("/api/founder/v1/pipeline/deals")
async def create_deal(request: Request, operator: OperatorDep):
    await record(request, operator, "pipeline.create")
    body = await request.json()
    try:
        deal = await _provider(request).create_deal(body, operator)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "deal": deal}


@app.patch("/api/founder/v1/pipeline/deals/{deal_id}")
async def update_deal(deal_id: int, request: Request, operator: OperatorDep):
    await record(request, operator, "pipeline.update", deal_id)
    body = await request.json()
    stage = (body.get("stage") or "").strip()
    if not stage:
        raise HTTPException(400, "stage required")
    try:
        deal = await _provider(request).update_deal_stage(deal_id, stage, operator)
    except ValueError as exc:
        msg = str(exc)
        raise HTTPException(404 if "not found" in msg else 400, msg)
    return {"ok": True, "deal": deal}


@app.get("/api/founder/v1/usage/summary")
async def usage(request: Request, operator: OperatorDep):
    await record(request, operator, "usage.read")
    return await _provider(request).usage()


@app.get("/api/founder/v1/economics/cogs")
async def economics(request: Request, operator: OperatorDep):
    await record(request, operator, "economics.read")
    return await _provider(request).economics()


@app.get("/api/founder/v1/retention/health")
async def retention(request: Request, operator: OperatorDep):
    await record(request, operator, "retention.read")
    return await _provider(request).retention()


@app.get("/api/founder/v1/ops/platform")
async def ops(request: Request, operator: OperatorDep):
    await record(request, operator, "ops.read")
    return await _provider(request).ops()


@app.get("/api/founder/v1/goals")
async def goals(request: Request, operator: OperatorDep):
    await record(request, operator, "goals.read")
    return await _provider(request).goals()


@app.get("/api/founder/v1/alerts")
async def alerts(request: Request, operator: OperatorDep):
    await record(request, operator, "alerts.read")
    return await _provider(request).alerts()


@app.get("/api/founder/v1/support")
async def support(request: Request, operator: OperatorDep):
    await record(request, operator, "support.read")
    return await _provider(request).support()


@app.get("/api/founder/v1/settings")
async def settings_view(request: Request, operator: OperatorDep):
    await record(request, operator, "settings.read")
    return await _provider(request).settings_view()


@app.post("/api/founder/v1/reports/weekly/run")
async def weekly_brief(request: Request, operator: OperatorDep):
    await record(request, operator, "brief.run")
    return await _provider(request).weekly_brief()


@app.get("/api/founder/v1/exports/accounting.csv")
async def export_csv(request: Request, operator: OperatorDep):
    await record(request, operator, "export.accounting")
    rows = await _provider(request).export_rows()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["org_id", "name", "plan", "mrr_usd", "health", "region", "stage"])
    for row in rows:
        writer.writerow(row)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vex-founder-accounting.csv"},
    )


@app.get("/api/founder/v1/audit")
async def audit_log(request: Request, operator: OperatorDep):
    await record(request, operator, "audit.read")
    items = await list_recent(100)
    return {"items": items}


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /\n"


if settings.serve_static:
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="spa")
