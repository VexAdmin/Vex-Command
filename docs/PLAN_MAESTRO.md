# Vex Command — Plan maestro

> **Único documento de ejecución.** No hay blueprint, architecture ni resources aparte.
> Repo: `~/Documents/Proyectos/Vex-Command` · producto: Founder Console (`ops.vexraptor.com`).
> **No** es el Dashboard MSSP (`app.vexraptor.com`). Nunca en el nav del tenant.

**Estado:** F2 en curso (C-10, C-11, C-13 hechos) · **siguiente:** C-12 alertas Slack (bloqueado — sin workspace de Slack todavía) · deploy C-01 espera dominio Syvrax  
**Regla:** un ID por chat. No saltar a F5 antes de F3 (cohorts sin billing son teatro).  
**HECHO:** checkbox `[x]` + 1 línea de evidencia (URL, test o comando). Si falta, sigue `EN CURSO`.

---

## F0 — Plantilla (local)

| ID | Tarea | Estado |
|---|---|---|
| C-00 | App Vue + API FastAPI + seed 1.024 orgs + 11 módulos + schema SQL | [x] 2026-09-07 · `http://localhost:5174` |
| H1 | Export CSV vía fetch+blob con header `Authorization` (antes: token en query param, URL/logs) | [x] 2026-09-08 · `client.ts` + `client.export.test.ts` (regresión) |
| H2 | Sin passwords hardcodeadas en `sql/003_roles.sql` — roles `NOLOGIN`, password real en deploy | [x] 2026-09-08 · `deploy/apply-founder-roles.sh` |
| H3 | `docker-compose.yml` sin servicio prod-like implícito — `APP_ENV: dev` explícito | [x] 2026-09-08 |

---

## F1 — Superficie real (ops + auth + métricas de operación)

Sin Stripe. El panel muestra orgs/scans/ops reales o vacío honesto, no MRR inventado.

| ID | Tarea | Estado | Gate |
|---|---|---|---|
| C-01 | DNS `ops.vexraptor.com` + TLS + `noindex` + vhost | [ ] | `deploy/nginx-ops.vexraptor.com.conf.example` + `deploy/Dockerfile.vex-founder` listos — **tú** aplicas DNS/Cloudflare |
| C-02 | Auth `platform_operator` + JWT (`FOUNDER_AUTH_MODE=jwt`) | [x] | `backend/app/auth.py` · tests `test_auth.py` (7) |
| C-03 | Schema `founder` + roles `vex_founder_ro/rw` | [x] | `sql/001` + `sql/003` · migrate on startup |
| C-04 | Vistas agregadas sin findings | [x] | `sql/002_aggregate_views.sql` · solo conteos |
| C-05 | Command Center SQL · MRR=0 | [x] | `SqlProvider.overview()` · `dataset=pre_revenue` |
| C-06 | Customers + Account 360 + notas persistidas | [x] | `founder.account_note` · test `test_f1_sql` (con Postgres) |
| C-07 | Platform Ops (health Raptor + scans running) | [x] | `RAPTOR_HEALTH_URL` + `v_platform_scan_ops` |
| C-08 | Audit en `founder.audit_log` | [x] | `backend/app/audit.py` |
| C-09 | Contenedor `vex-founder` separado | [x] | `deploy/Dockerfile.vex-founder` · `docker compose` service |

---

## F2 — Operar GTM

| ID | Tarea | Gate de cierre |
|---|---|---|
| C-10 | Pipeline persistido (`founder.deal` + activity) | [x] Crear/mover deal sobrevive restart · `test_pipeline` + `test_f1_pipeline` |
| C-11 | Goals / OKRs editables (`founder.goal` / `okr`) | [x] PUT `/goals` persiste mock + SQL · `test_goals` + `test_f1_goals` |
| C-12 | Alertas Slack (pago n/a aún; cola ARQ, health, Gemini 24h si existe) | Mensaje real en canal privado |
| C-13 | Support ligero o enlace Linear — no inventar ticketing enterprise | [x] Deep-link Linear via `LINEAR_WORKSPACE_URL` · `test_settings` |

---

## F3 — Dinero (bloquea F5)

Gap en Raptor: **PRICE-01c**.

| ID | Tarea | Gate de cierre |
|---|---|---|
| C-20 | Stripe products/prices por plan Essential / Pro / Enterprise / MSSP | Prices IDs documentados en Settings |
| C-21 | Webhooks firmados → `fact_billing_event` | Evento test en Stripe aparece en API |
| C-22 | Revenue waterfall + MRR/ARR canónicos (`backend/app/kpis.py`) | MRR Command = MRR Stripe ± overrides |
| C-23 | `founder.manual_revenue` para deals offline | Override auditado; no pisa Stripe |
| C-24 | Export CSV contable | GET `/exports/accounting.csv` + fila audit |

---

## F4 — Margen

Gap en Raptor: **PRICE-00**.

| ID | Tarea | Gate de cierre |
|---|---|---|
| C-30 | Coste Gemini por scan en Raptor | Campo/tabla usable por Command |
| C-31 | `fact_cogs_daily` + pantalla Unit Economics | Gross margin = fórmula de `kpis.py` |
| C-32 | Alerta orgs con COGS > 40% del MRR | Slack o lista Retention |

---

## F5 — Escala 200–1.000 orgs

Solo con F3 cerrado.

| ID | Tarea | Gate de cierre |
|---|---|---|
| C-40 | Replica PG de lectura + Redis cache overview 30–120s | Command no pega al primary de scans |
| C-41 | Warehouse (ClickHouse o BigQuery) + ETL 5–15 min + alerta lag > 30 min | `fact_*` frescos; Slack si lag |
| C-42 | Cohorts + NRR | Números desde warehouse, no OLTP |
| C-43 | Weekly brief IA fail-soft (agregados, **sin** findings) | POST `/reports/weekly/run` no tumba el panel si Gemini falla |

---

## Go-live (cuando F1+ esté en `ops.`)

- [ ] WAF / IP allowlist opcional
- [ ] Session TTL 30–60 min
- [ ] Backup `pg_dump` schema `founder`
- [ ] CORS solo `https://ops.vexraptor.com`
- [ ] Runbook: “MRR no cuadra con Stripe”

---

## Recursos (foto @ 1.000 orgs)

| Capa | Qué | Cuándo |
|---|---|---|
| DNS | `ops.vexraptor.com` | C-01 |
| Compute | `vex-founder` 1–2 vCPU / 1–2 GB | C-09 · extra ~$0–20/mes ahora |
| PG | schema `founder` + replica lectura | C-03 / C-40 |
| Warehouse | ClickHouse/BigQuery `fact_*` | C-41 · extra ~$150–400/mes @ 1k |
| Redis | cache KPIs | C-40 |
| Spaces/S3 | exports | C-24 |
| Stripe / Slack / Gemini | dinero / alertas / brief | C-20 / C-12 / C-43 |

KPIs (una fórmula, en `backend/app/kpis.py`): ARR = MRR×12 · Net New = new+exp−con−churn · NRR = (start+exp−con−churn)/start · health = recency 40% + payment 30% + usage 20% + support 10%.

---

## Handoff al cerrar un ID

Sprint: `C-NN` — [1 línea]  
Siguiente: primera fila sin `[x]`  
Modelo sugerido: Composer Fast (slice UI/API) · Sonnet thinking (C-02 auth / C-04 tenancy)
