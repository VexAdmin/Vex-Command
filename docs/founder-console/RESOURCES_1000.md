# Founder Console — Recursos técnicos @ 1.000 orgs

Checklist operativo derivado de `FOUNDER_CONSOLE_BLUEPRINT.md`. Usar cuando se pase de plantilla a implementación.

---

## 1. DNS / hosts

| Recurso | Valor | Obligatorio |
|---|---|---|
| Subdominio console | `ops.vexraptor.com` | Sí |
| App cliente (existente) | `app.vexraptor.com` | — |
| Marketing (existente) | `vexraptor.com` | — |
| Grafana (opcional) | `metrics.vexraptor.com` (VPN/SSO) | Fase 1+ |
| TLS | Cloudflare → origen (ideal Full Strict) | Sí |
| SEO | `noindex` + robots disallow en `ops` | Sí |
| WAF / IP allowlist | Cloudflare WAF; allowlist opcional | Recomendado |

---

## 2. Compute & contenedores

| Servicio | Spec guía @1k orgs | Rol |
|---|---|---|
| `vex-raptor` (existente) | 4–8 vCPU / 8–16 GB | API producto |
| `worker` ARQ (existente) | N réplicas | Scans |
| **`vex-founder`** (nuevo) | 1–2 vCPU / 1–2 GB | SPA + `/api/founder/v1` |
| ETL jobs | En worker ARQ o cron dedicado | Refresh `fact_*` cada 5–15 min |

---

## 3. Bases de datos

| DB | Motor | Contenido |
|---|---|---|
| **Postgres primary** (existente) | PG 16 | Producto + schema nuevo `founder` (CRM, goals, alerts, notes) |
| **Postgres replica** | Streaming / managed | Lecturas founder (no saturar primary) |
| **Warehouse** | ClickHouse (o BigQuery) | `dim_org`, `fact_mrr_daily`, `fact_usage_daily`, `fact_cogs_daily`, `fact_billing_event`, `agg_platform_hourly` |
| **Redis** | Redis 7 | Cache overview 30–120s + contadores |
| **Object storage** | DO Spaces / S3 | Exports CSV, snapshots semanales |

### Rol DB dedicado
```
vex_founder_ro  → SELECT solo en vistas agregadas + founder.*
vex_founder_rw  → DML solo en schema founder
```
**Prohibido:** SELECT a tablas de findings/payloads desde el console.

---

## 4. Billing & terceros

| Servicio | Para qué | Fase |
|---|---|---|
| **Stripe** (products/prices por plan) | MRR real, invoices, dunning | F3 (crítico) |
| Stripe webhooks → founder API | `fact_billing_event` | F3 |
| Slack incoming webhook | Alertas founder | F2 |
| Linear / email | Support threads | F2 |
| Gemini | Weekly brief / risk narrative (fail-soft) | F5 opcional |

---

## 5. Auth & seguridad

| Control | Detalle |
|---|---|
| Rol | Solo `platform_operator` (+ opcional `founder_readonly`) |
| MFA | Obligatorio |
| Session TTL | 30–60 min |
| Audit | Toda lectura Account 360 y todo cambio de plan/deal |
| CORS | Solo origen `https://ops.vexraptor.com` |
| Cookies | Host-only en `ops` — no compartir con `app` |
| Rate limit | ~60 req/min/operator |

---

## 6. APIs a construir

Prefijo: `/api/founder/v1/*`  
Auth: `require_platform_operator` + middleware de audit.

Mínimo F1: `GET /overview`, `GET /customers`, `GET /customers/{org_id}`, `GET /ops/platform`  
Ver lista completa en blueprint §5.

---

## 7. Instrumentación previa en Vex (gaps)

| Gap | Ticket / nota | Bloquea |
|---|---|---|
| Coste Gemini por scan | `PRICE-00` | Unit Economics |
| Stripe webhooks | `PRICE-01c` | Revenue real |
| Contador logins / report downloads | Nuevo | Usage fiable |

Sin Stripe: modo **manual_revenue + operating metrics** (honesto en pre-clientes).

---

## 8. Coste infra extra (orden de magnitud)

| Fase | Logos | Extra / mes |
|---|---|---|
| F0 | 0–20 | ~$0–20 (DNS/SPA) |
| F1 | 20–200 | ~$40–120 (replica + alerts) |
| F2 | 200–1.000 | ~$150–400 (warehouse + founder svc) |

Además del coste del producto (scans, Gemini, droplet principal).

---

## 9. Orden de implementación recomendado

1. Prototipo (hecho) → validar UX contigo  
2. `ops` + auth + Command Center + Customers (SQL views en PG)  
3. Pipeline + goals + Slack  
4. Stripe + waterfall  
5. COGS Gemini  
6. ClickHouse + cohorts + NRR + brief IA  

---

## 10. Archivos de esta plantilla

| Archivo | Qué es |
|---|---|
| `FOUNDER_CONSOLE_BLUEPRINT.md` | Producto + arquitectura completa |
| `RESOURCES_1000.md` | Este checklist |
| `prototype/index.html` | UI interactiva multi-módulo |
