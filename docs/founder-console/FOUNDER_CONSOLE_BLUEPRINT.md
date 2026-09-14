# Vex Founder Console — Blueprint de plataforma founder profesional

> **Estado:** plantilla de producto + arquitectura (no cableado a prod).  
> **Audiencia:** solo dueño / platform operators (nunca tenants MSSP).  
> **Hipótesis de escala:** diseñada para **1.000 organizaciones** activas mañana.  
> **Fecha:** 2026-09-06 · Producto: Vex Raptor

---

## 0. Qué es (y qué no es)

| | Dashboard cliente (`app.vexraptor.com`) | **Founder Console** (`ops.vexraptor.com`) |
|---|---|---|
| Quién | MSSP, SOC, compliance | Tú + 0–3 operadores internos |
| Pregunta | ¿Estamos seguros? | ¿Cómo va el negocio y la máquina? |
| Datos | Findings, scans, Sense, reportes | Dinero, clientes, margen, pipeline, COGS, salud |
| Tenancy | Aislado por `org_id` | Cross-tenant **agregado** (nunca PII de findings en UI) |

**Regla de oro:** el Founder Console **no** vive dentro del SPA del cliente. Es un producto interno separado, misma marca Vex, distinto job.

---

## 1. Módulos de la plataforma (feature set completo)

### 1.1 Command Center (home)
- ARR / MRR / Net New MRR / Logo count
- Burn rate estimado + runway (si hay gasto registrado)
- Health score de plataforma (scans OK %, cola, errores 5xx)
- Alertas founder: churn risk, pago fallido, spike de coste Gemini, incidentes
- Goals del mes vs actual (editable)

### 1.2 Revenue & Billing
- MRR waterfall (new / expansion / contraction / churn)
- Ingresos por plan (Essential / Professional / Enterprise / MSSP Partner)
- Cohort revenue retention (N‑month)
- Facturas, failed payments, dunning status
- Forecast 3/6/12 meses (escenarios base / upside / downside)
- Integración Stripe (fuente de verdad de dinero) + manual overrides para deals offline

### 1.3 Customers (Account 360°)
- Lista de 1.000 orgs: plan, MRR, last active, health score, owner CSM (tú al inicio)
- Ficha cuenta: contrato, seats/targets, uso 30d, tickets, NPS, risk flags
- Segmentación: ICP, región, canal (directo / MSSP), stage (Pilot → Paid → Expansion)
- Acciones: upgrade plan (platform operator), notas internas, next step

### 1.4 Pipeline & GTM
- Board Kanban: Lead → Qualified → Pilot → Negotiation → Closed Won/Lost
- Deal value, close date, source (inbound web, referral, outbound)
- Win/loss reasons
- MSSP partner pipeline (orgs-cliente bajo un partner)
- Actividad: demos, propuestas enviadas, follow-ups

### 1.5 Product Usage (leading indicators)
- Scans / día / semana (por motor: pentest, arsenal, ASM, Sense)
- Findings High/Critical entregados (valor percibido)
- Reportes PDF generados / variantes usadas
- DAU/WAU orgs (login + scan)
- Feature adoption (Intelligence, Triggers, Branding, Sense Fleet…)
- Funnel Pilot: signup → first scan → first High finding → convert

### 1.6 Unit Economics & COGS
- Coste Gemini (tokens × tarifa) por scan / por org / por plan
- Coste infra prorrateado (DO droplet, Redis, Postgres, Playwright, egress)
- Gross margin por plan y por cohort
- Contribución marginal por logo
- Alerta: org con COGS > 40% de su MRR

### 1.7 Retention, Churn & Health
- Logo churn / revenue churn / net revenue retention (NRR)
- Health score compuesto: recency de scan + pago OK + soporte + uso features
- Churn risk list (top 20) con razón probable
- Expansion opportunities (uso cerca del límite de targets)

### 1.8 Support & Voice of Customer
- Inbox ligero o sync con email/Linear/Intercom
- NPS / CSAT (encuesta post-reporte o post-Pilot)
- Themes de feedback → backlog link
- SLA interno (aunque seas solo tú: tiempo a primera respuesta)

### 1.9 Platform Ops (puente a ingeniería)
- Uptime `/health`, versión desplegada, Alembic head
- Cola ARQ: depth, failed jobs, orphaned RUNNING scans
- Error budget 7d / 30d
- Coste Gemini rolling 24h
- Enlaces a Grafana/Prometheus (no reimplementar APM aquí)

### 1.10 Goals, Alerts & Reports
- OKRs trimestrales + KPIs semanales
- Alertas: Slack/email (pago fallido, NRR drop, cola > N, Gemini spike)
- Reportes PDF/CSV semanales al dueño (lunes 08:00 UTC)
- Export contable (CSV para asesor)

### 1.11 Access, Audit & Compliance interna
- Solo roles `platform_operator` (+ opcional `founder_readonly` para mentor/asesor)
- MFA obligatorio
- Audit log de cada acción cross-tenant (quién miró qué org, quién cambió plan)
- Session timeout corto (30–60 min)
- IP allowlist opcional

### 1.12 Settings
- Conexiones: Stripe, Slack, email SMTP, Linear, analytics warehouse
- Umbrales de alerta
- Moneda (USD/EUR), FY start
- Feature flags del console (no confundir con `feature_flags.py` del producto)

---

## 2. IA (capa founder, no motor ofensivo)

Opcional y **fail-soft** — no bloquea el panel:

| Capacidad | Input | Output |
|---|---|---|
| Weekly brief | KPIs + churn list + pipeline | Resumen 8 líneas “qué pasó / qué hacer” |
| Account risk | health + usage + tickets | “Por qué esta org puede churnear” |
| Pricing sanity | COGS vs MRR | Flags de margen negativo |
| Forecast narrative | waterfall + pipeline | Texto para board/mentor |

Modelo: Gemini (ya en stack) con prompt aislado, **sin** findings de clientes en el contexto (solo agregados y metadatos de cuenta).

---

## 3. Información arquitectura (vista lógica)

```
                    ┌─────────────────────────────┐
                    │  ops.vexraptor.com (SPA)    │
                    │  Founder Console Vue/React  │
                    └──────────────┬──────────────┘
                                   │ JWT platform_operator
                    ┌──────────────▼──────────────┐
                    │  founder-api (FastAPI)       │
                    │  /api/founder/v1/*          │
                    │  rate-limit + audit         │
                    └──────┬───────────┬──────────┘
           read aggregates │           │ write CRM/notes
                           │           │
         ┌─────────────────▼──┐   ┌────▼────────────────┐
         │ Analytics warehouse│   │ Founder OLTP (PG)   │
         │ (ClickHouse / PG   │   │ deals, notes, goals │
         │  replica + views)  │   │ alert_rules, okrs   │
         └─────────┬──────────┘   └─────────────────────┘
                   │ ETL cada 5–15 min
         ┌─────────▼──────────┐   ┌─────────────────────┐
         │ Prod Postgres      │   │ Stripe webhooks     │
         │ (orgs, scans,      │──▶│ + billing mirror    │
         │  plans, audit)     │   └─────────────────────┘
         └────────────────────┘
                   │
         ┌─────────▼──────────┐
         │ Redis + Prometheus │  (live ops counters)
         └────────────────────┘
```

**Por qué warehouse separado a 1.000 orgs:**  
Las queries de cohort/waterfall/NRR matan el OLTP de scans si corren en prod. Con 1.000 orgs y ~10–50 scans/día/org peores casos, el histórico de findings/scans es grande; el Founder Console **solo lee agregados**.

---

## 4. Modelo de datos (mínimo viable → escala)

### 4.1 En Founder OLTP (nuevo schema `founder`)

| Tabla | Propósito |
|---|---|
| `founder.deal` | Pipeline CRM |
| `founder.deal_activity` | Notas, demos, emails logueados |
| `founder.account_note` | Notas internas por `org_id` |
| `founder.goal` / `founder.okr` | Metas |
| `founder.alert_rule` / `founder.alert_event` | Alertas |
| `founder.manual_revenue` | Deals offline / ajustes |
| `founder.cogs_daily` | Snapshot coste Gemini+infra |
| `founder.nps_response` | Encuestas |
| `founder.audit_log` | Quién hizo qué en el console |
| `founder.operator` | Usuarios internos (link a `users` platform) |

### 4.2 En warehouse (materialized / ETL)

| Vista / tabla | Grain | Uso |
|---|---|---|
| `dim_org` | org | plan, created_at, region, partner_id |
| `fact_mrr_daily` | org × day | MRR snapshot |
| `fact_usage_daily` | org × day | scans, findings_hc, logins, reports |
| `fact_cogs_daily` | org × day | tokens_usd, infra_usd |
| `fact_billing_event` | event | invoice, payment_failed, refund |
| `agg_platform_hourly` | hour | cola, errors, active_scans |

IDs: `org_id` entero (ya en Vex). Nunca copiar payloads de findings al warehouse founder — solo conteos y severidades agregadas.

### 4.3 Stripe como fuente de verdad de dinero

- Webhook → `fact_billing_event` + actualización `fact_mrr_daily`
- Plan interno Vex (`orgs.plan`) **sincronizado** desde Stripe product/price IDs
- Hasta que haya Stripe: `founder.manual_revenue` + plan en DB (modo “pre-revenue honest”)

---

## 5. APIs (`/api/founder/v1`)

Todas con `Depends(require_platform_operator)` + audit middleware.

| Método | Ruta | Notas |
|---|---|---|
| GET | `/overview` | KPIs del Command Center |
| GET | `/revenue/waterfall?from=&to=` | |
| GET | `/revenue/cohorts` | |
| GET | `/customers` | paginado, filtros, sort |
| GET | `/customers/{org_id}` | 360° (sin findings crudos) |
| PATCH | `/customers/{org_id}/notes` | |
| GET/POST | `/pipeline/deals` | |
| PATCH | `/pipeline/deals/{id}` | |
| GET | `/usage/summary` | |
| GET | `/economics/cogs` | |
| GET | `/retention/health` | |
| GET | `/ops/platform` | health + queue |
| GET/PUT | `/goals` | |
| GET/PUT | `/alerts/rules` | |
| POST | `/reports/weekly/run` | |
| GET | `/exports/accounting.csv` | |
| GET | `/audit` | |

**Rate limit:** 60 req/min por operator.  
**Paginación:** cursor-based en customers (1.000+ filas ok).  
**Cache:** Redis 30–120s en overview/waterfall (invalidar en webhook Stripe).

---

## 6. Frontend

| Decisión | Elección | Motivo |
|---|---|---|
| App | SPA propia (Vue 3 + TS, mismo stack que consola) o React | Separar deploy del SPA cliente |
| Hosting | Contenedor `vex-founder` o stage en Nginx | No mezclar bundles con `frontend_dist` del cliente |
| Charts | Apache ECharts o Observable Plot | Waterfalls y cohorts serios |
| Auth | Mismo JWT issuer, claim `platform_operator` + MFA | Reusar auth Vex |
| i18n | ES + EN | Alineado a producto |

Rutas UI (prototipo en `prototype/index.html`):

```
/               Command Center
/revenue        Revenue
/customers      Customers
/customers/:id  Account 360
/pipeline       Pipeline
/usage          Product Usage
/economics      Unit Economics
/retention      Retention
/support        Support / VoC
/ops            Platform Ops
/goals          Goals & Alerts
/settings       Settings
```

---

## 7. Subdominios, DNS, TLS (producción)

| Host | Rol |
|---|---|
| `vexraptor.com` | Marketing (Next.js, ya existe) |
| `app.vexraptor.com` | Consola cliente (Vue, ya existe) |
| **`ops.vexraptor.com`** | **Founder Console** (nuevo) |
| `api.vexraptor.com` *(opc.)* | API pública unificada; o seguir `/api/v1` en app |
| `metrics.vexraptor.com` *(opc. interno)* | Grafana detrás de VPN/SSO |
| `status.vexraptor.com` *(futuro)* | Status page clientes |

**Cloudflare:**
- `ops` → mismo droplet o servicio separado, SSL Full (strict) preferible a Flexible a medio plazo
- WAF + IP allowlist opcional en `ops`
- **No** indexar: `X-Robots-Tag: noindex`, robots disallow, Basic Auth de emergencia además de JWT en fase 0

**Cookies / CORS:**
- Cookie de sesión founder **no** compartida con `app` (host-only en `ops`)
- Si JWT en `Authorization` header: CORS allowlist solo `https://ops.vexraptor.com`

---

## 8. Infra dimensionada a 1.000 orgs

### 8.1 Hipótesis de carga

| Variable | Valor de diseño |
|---|---|
| Orgs | 1.000 |
| Usuarios founder | ≤ 5 |
| Scans concurrentes pico | 50–100 (ya limitado por worker) |
| Eventos usage/día | ~50k–500k filas warehouse |
| Queries founder concurrentes | < 10 (humano) |
| Retención warehouse | 25 meses (NRR + FY) |
| Retención findings prod | según plan (ya existe retention) |

El cuello de botella **no** es el Founder UI (pocos humanos). Es **no degradar prod** con agregaciones.

### 8.2 Stack recomendado (faseado)

#### Fase 0 — Pre-revenue / 0–20 logos (ahora)
| Recurso | Spec | Notas |
|---|---|---|
| Mismo droplet DO | App + worker actuales | Sin máquina nueva |
| Schema `founder` en Postgres prod | Tablas CRM/goals | Escrituras ligeras |
| Vistas SQL / materialized views | MRR/usage diarios | Refresh cron ARQ cada 15 min |
| SPA Founder | Contenedor o path interno | `ops.` DNS |
| Stripe test mode | Webhooks a staging | |
| **Coste extra** | ~$0–20/mes | Dominio/DNS ya pagado |

#### Fase 1 — 20–200 logos
| Recurso | Spec |
|---|---|
| Read replica Postgres | 1× DO managed PG replica o streaming replica |
| Redis DB lógica aparte | Contadores founder cache |
| Contenedor `vex-founder` | CPU share baja |
| Grafana + Prometheus | Ya parcialmente `/metrics` |
| Slack alerts | Incoming webhook |
| **Coste extra** | ~$40–120/mes |

#### Fase 2 — 200–1.000 logos (diseño objetivo)
| Recurso | Spec | Para qué |
|---|---|---|
| **Analytics DB** | ClickHouse Cloud o CH en droplet 4 vCPU / 8 GB, o BigQuery | Cohorts, waterfall, series |
| **ETL** | ARQ jobs + (opc.) dbt | `fact_*` refresh 5–15 min |
| **Object storage** | DO Spaces / S3 | Exports CSV, snapshots semanales |
| **Founder API** | Proceso separado o router montado con pool read-only | Aísla carga |
| **Secrets** | Ya en env; Stripe live keys solo en prod | |
| **Backups** | pg_dump founder + CH backup diario | |
| **Observabilidad** | Grafana dashboards “Founder ETL lag” | |
| **Coste extra** | ~$150–400/mes típico | Depende CH managed vs self-host |

### 8.3 Droplet / servicios (foto a 1.000 orgs)

Asumiendo SaaS multi-tenant (no 1.000 self-hosts):

| Servicio | Capacidad guía |
|---|---|
| `vex-raptor` API | 4–8 vCPU, 8–16 GB (prod app) |
| `worker` ARQ × N | Escala horizontal por cola de scans |
| Postgres 16 primary | 4–8 vCPU, 16–32 GB RAM, SSD; connection pooler (PgBouncer) |
| Postgres replica | Solo lecturas founder + reporting |
| Redis 7 | 2–4 GB |
| ClickHouse (o equivalente) | 4 vCPU / 8–16 GB |
| `vex-founder` | 1–2 vCPU / 1–2 GB (UI+API ligeros) |
| Cloudflare | DNS + WAF + cache estático founder assets |

Self-hosted customers (si vendes appliance): el Founder Console **solo ve** telemetría opt-in / billing — nunca asumas acceso a su Postgres.

### 8.4 Seguridad a escala

1. Separación de red: founder API no puede `SELECT` findings text — rol DB `vex_founder_ro` con grants solo a vistas agregadas + `founder.*`
2. Row-level: no aplica cross-tenant UI; el peligro es **exfiltración masiva** → audit + deny export findings
3. MFA + hardware key recomendada para founder
4. Break-glass: cuenta offline documentada
5. Pen-test del console como superficie privilegiada (prioridad alta cuando exista)

---

## 9. Instrumentación que hay que cablear en Vex (prerrequisitos)

Hoy el producto ya tiene piezas; el Founder Console las **consume**:

| Señal | Fuente actual / gap |
|---|---|
| Orgs + plan | `orgs` ✅ |
| Scans / estado | `scan_store` / ASM ✅ |
| `/metrics` Prometheus | `metrics_service.py` ✅ |
| Coste Gemini por scan | **GAP** (`PRICE-00`) — obligatorio para economics |
| Stripe webhooks | **GAP** (`PRICE-01c`) — obligatorio para revenue real |
| Login events | Audit / JWT issue — instrumentar `fact_usage_daily.logins` |
| Report downloads | `reports` router — contador |
| Platform operator | `is_platform_operator` ✅ |

Sin Stripe + sin COGS, el panel puede existir en modo **“operating metrics only”** (uso + ops + pipeline manual). Eso es honesto en pre-revenue.

---

## 10. Fases de construcción (producto)

| Fase | Entrega | Valor |
|---|---|---|
| **F0** | Prototipo HTML (este repo) + blueprint | Alinear visión |
| **F1** | `ops.` + auth operator + Command Center + Customers list (SQL views) | Ver el negocio real |
| **F2** | Pipeline + notes + goals + Slack alerts | Operar GTM |
| **F3** | Stripe sync + Revenue waterfall | Dinero de verdad |
| **F4** | COGS Gemini + Unit Economics | Margen defendible |
| **F5** | Warehouse + cohorts + NRR + weekly brief IA | Escala 200–1.000 |

No construir F5 antes de F3: cohorts sin billing son teatro.

---

## 11. KPIs canónicos (definir una sola fórmula)

| KPI | Fórmula (canónica) |
|---|---|
| MRR | Suma de suscripciones activas normalizadas a mes |
| ARR | MRR × 12 |
| Net New MRR | New + Expansion − Contraction − Churn |
| Logo churn | Orgs lost / orgs start-of-month |
| Revenue churn | MRR lost / MRR start-of-month |
| NRR | (MRR_start + expand − contract − churn) / MRR_start |
| Gross margin | (Revenue − Gemini − infra alloc) / Revenue |
| Org health | 0–100 ponderado: recency 40%, payment 30%, usage 20%, support 10% |

Documentar fórmulas en código (`founder/kpis.py`) — una sola fuente; UI solo formatea.

---

## 12. Qué NO incluir (para no hinchar)

- Ticketing enterprise completo (usar Linear/email)
- BI genérico tipo Metabase para todo el mundo (el console es opinionated)
- Findings del cliente en pantallas founder
- Multi-founder marketplace / investors portal (fase posterior: `readonly`)

---

## 13. Prototipo

Archivo interactivo: [`prototype/index.html`](./prototype/index.html)

Abre en navegador local. Incluye navegación de todos los módulos §1 con datos sintéticos a escala ~1.000 orgs (demo).

---

## 14. Checklist de go-live (cuando haya código real)

- [ ] DNS `ops.vexraptor.com` + TLS
- [ ] Contenedor/SPA no expuesto en nav del cliente
- [ ] Solo `platform_operator` + MFA
- [ ] Rol DB read-only a agregados
- [ ] Audit log de accesos a Account 360
- [ ] Stripe webhook firmado (o modo manual documentado)
- [ ] Cron ETL + alerta si lag > 30 min
- [ ] Backup founder schema
- [ ] `noindex` + WAF
- [ ] Runbook: “qué hacer si MRR no cuadra con Stripe”

---

## 15. Resumen ejecutivo de recursos (foto “mañana 1.000”)

| Capa | Qué necesitas |
|---|---|
| DNS | `ops.vexraptor.com` (+ opcional Grafana) |
| Compute | App founder pequeña + workers de ETL |
| DB OLTP | Schema `founder` en Postgres (+ replica lectura) |
| DB analítica | ClickHouse o warehouse SQL |
| Cache | Redis |
| Billing | Stripe (products por plan Vex) |
| Observabilidad | Prometheus (`/metrics`) + Grafana |
| Alertas | Slack/email |
| Storage | Spaces/S3 para exports |
| Auth | JWT + MFA + audit |
| Coste infra extra guía | ~$150–400/mes en fase 1.000 orgs (además del stack de producto) |

**Decisión de producto:** el Founder Console es tan crítico como el Dashboard MSSP para ti, pero **invisible** para el cliente. Construirlo bien es disciplina de SaaS; construirlo dentro del dashboard del tenant es un error de posicionamiento.
