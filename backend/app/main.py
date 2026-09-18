from __future__ import annotations

import csv
import io
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse

from app.audit import list_recent, record
from app.auth import Operator, require_operator
from app.config import settings
from app.founder_auth import router as founder_auth_router
from app.db import close_db, init_db
from app.providers import build_provider
from app.rate_limit import enforce_targets_rate_limit
from app.targets_service import access_token_from_request, add_target, remove_target

OperatorDep = Annotated[Operator, Depends(require_operator)]

APP_VERSION = "0.2.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.provider = build_provider()
    yield
    await close_db()


def _is_prod_like(app_env: str) -> bool:
    return app_env in ("prod", "staging")


def _docs_urls() -> tuple[str | None, str | None, str | None]:
    """S4: Swagger/ReDoc/OpenAPI are unauthenticated admin surface — never
    exposed on ops.vexraptor.com. Dev keeps them for local debugging."""
    if _is_prod_like(settings.app_env):
        return None, None, None
    return "/api/founder/docs", "/redoc", "/openapi.json"


def _cors_origins() -> list[str]:
    """S6: prod/staging only ever talk to the real console origin — the
    127.0.0.1:5174 Vite dev-server origin must never be trusted on
    ops.vexraptor.com, even with allow_credentials=True."""
    if _is_prod_like(settings.app_env):
        return [settings.console_origin]
    return [settings.console_origin, "http://127.0.0.1:5174"]


_docs_url, _redoc_url, _openapi_url = _docs_urls()

app = FastAPI(
    title="Vex Command",
    version=APP_VERSION,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    lifespan=lifespan,
)
app.include_router(founder_auth_router, prefix="/api/founder/v1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
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
async def health():
    # S4: this route has no auth — it must never leak dataset/data_source/
    # auth_mode/product to an unauthenticated caller (that was exactly what
    # let anyone fingerprint the deployment). Status + version only, same
    # shape as Raptor's own /health.
    return {"status": "ok", "version": APP_VERSION}


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


@app.get("/api/founder/v1/revenue/manual")
async def manual_revenue(request: Request, operator: OperatorDep):
    await record(request, operator, "revenue.manual.list")
    return await _provider(request).manual_revenue()


@app.post("/api/founder/v1/revenue/manual")
async def add_manual_revenue(request: Request, operator: OperatorDep):
    await record(request, operator, "revenue.manual.create")
    body = await request.json()
    try:
        entry = await _provider(request).add_manual_revenue(body, operator)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "entry": entry}


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


@app.post("/api/founder/v1/customers/{org_id}/targets")
async def add_customer_target(org_id: int, request: Request, operator: OperatorDep):
    enforce_targets_rate_limit(operator.email, org_id)
    body = await request.json()
    entry = (body.get("entry") or "").strip()
    if not entry:
        raise HTTPException(400, "entry required")
    token = access_token_from_request(request)
    result = await add_target(org_id, entry, token)
    await record(
        request,
        operator,
        "customers.targets.add",
        org_id,
        detail=f"add {result['entry']} | {result['diff']['before']} -> {result['diff']['after']}",
    )
    return result


@app.delete("/api/founder/v1/customers/{org_id}/targets")
async def remove_customer_target(org_id: int, request: Request, operator: OperatorDep):
    enforce_targets_rate_limit(operator.email, org_id)
    body = await request.json()
    entry = (body.get("entry") or "").strip()
    if not entry:
        raise HTTPException(400, "entry required")
    token = access_token_from_request(request)
    result = await remove_target(org_id, entry, token)
    await record(
        request,
        operator,
        "customers.targets.remove",
        org_id,
        detail=f"remove {result['entry']} | {result['diff']['before']} -> {result['diff']['after']}",
    )
    return result


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


@app.put("/api/founder/v1/goals")
async def update_goals(request: Request, operator: OperatorDep):
    await record(request, operator, "goals.update")
    body = await request.json()
    kind = body.get("kind")
    try:
        target = float(body.get("target"))
    except (TypeError, ValueError):
        raise HTTPException(400, "target must be a number")
    try:
        if kind == "okr":
            okr_id = int(body.get("id"))
            result = await _provider(request).update_okr(okr_id, target, operator)
        elif kind == "net_new":
            result = await _provider(request).update_net_new_goal(target, operator)
        else:
            raise HTTPException(400, "kind must be 'okr' or 'net_new'")
    except ValueError as exc:
        msg = str(exc)
        raise HTTPException(404 if "not found" in msg else 400, msg)
    return {"ok": True, "result": result}


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
    _static_root = Path(settings.static_dir)

    def _spa_file_response(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        if path:
            candidate = _static_root / path
            if candidate.is_file():
                return FileResponse(candidate)
        index = _static_root / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404, detail="SPA not built")
        return FileResponse(index)

    @app.get("/", include_in_schema=False)
    async def spa_index() -> FileResponse:
        return _spa_file_response("")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_path(full_path: str) -> FileResponse:
        return _spa_file_response(full_path)
