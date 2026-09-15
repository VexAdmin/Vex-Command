# Vex Command — Plan maestro

> **Único documento de ejecución.** No hay blueprint, architecture ni resources aparte.
> Repo: `~/Documents/Proyectos/Vex-Command` · producto: Founder Console (`ops.vexraptor.com`).
> **No** es el Dashboard MSSP (`app.vexraptor.com`). Nunca en el nav del tenant.

**Estado:** F2 solo falta C-12 (Slack, bloqueado — sin workspace todavía) · F3 arrancado con C-23 (manual revenue) hecho, resto **en pausa** — precios de planes (Essential/Professional/Enterprise/MSSP) todavía sin definir, C-20 no puede arrancar sin eso · **C-01/C-01b/C-14 live y verificado end-to-end en `ops.vexraptor.com`** (2026-09-15, cliente 13 Elaborando Futuro con 6 targets + 2 scans reales) — el enfoque de `GRANT org_configs` directo quedó reemplazado por funciones `SECURITY DEFINER` acotadas, ver "Reglas permanentes" abajo  
**Regla:** un ID por chat. No saltar a F5 antes de F3 (cohorts sin billing son teatro).  
**HECHO:** checkbox `[x]` + 1 línea de evidencia (URL, test o comando). Si falta, sigue `EN CURSO`.

---

## Reglas permanentes para prompts a Cursor (aprendidas 2026-09-15)

Incidente: Cursor desplegó C-01/C-01b/C-14 directo a producción y con push directo a
`dev` (sin PR) mientras la sesión de Claude trabajaba en paralelo, sin que quedara
registrado aquí. El código funcionaba pero violaba el diseño de permisos acotados
acordado (bypass RLS global vía `app.bypass_rls` en cada sesión, `vex_founder_rw` con
ownership completo del schema `founder` + `SELECT` directo sobre tablas de `public` de
Raptor con RLS). Corregido en PR #5. Reglas para que no se repita:

1. **Nunca commit ni push directo a `dev` sin rama+PR**, ni siquiera para "solo
   arreglar un bug chico" — cada prompt a Cursor debe decir explícitamente "rama
   feature nueva, PR contra `dev`, nunca commit directo".
2. **RLS de Raptor (`org_configs`, `scan_history`, `scan_metrics` tienen RLS
   forzado)**: Command NUNCA se salta RLS con un bypass de sesión global
   (`app.bypass_rls`). El patrón correcto es una función `SECURITY DEFINER` en el
   schema `founder`, acotada a las columnas exactas que se necesitan (nunca
   `scan_history.findings`), con `GRANT EXECUTE` solo a `vex_founder_ro/rw`. Ver
   `sql/002_aggregate_views.sql` (`f_org_targets`, `f_scan_history`,
   `f_scan_metrics`) como plantilla para cualquier tabla nueva de Raptor con RLS.
3. **`vex_founder_rw` nunca es owner del schema `founder`** ni tiene `SELECT`
   directo sobre tablas de `public` de Raptor. Las migraciones DDL (`sql/001-003`)
   corren con `MIGRATION_DATABASE_URL` (usuario owner `vex_raptor`), separado de
   `DATABASE_URL` (runtime, `vex_founder_ro`). Ver `backend/app/db.py`.
3b. **Funciones `LANGUAGE sql` se validan al crearse, no solo al ejecutarse** —
   si la tabla referenciada puede no existir en algún entorno (dev-stub local vs.
   producción real), usar `LANGUAGE plpgsql` con `EXECUTE` dinámico y un chequeo
   previo en `information_schema.tables`, como hace `f_org_targets`/`f_scan_metrics`.
4. **Verificación real antes de aceptar "tests en verde"**: correr `make test` Y
   `make test-sql` (este último necesita Postgres local con el dev-stub poblado —
   si da "skipped" en vez de "passed", el entorno está vacío, no confirma nada).
   Nunca aceptar el reporte de Cursor sin pedir el output real pegado.
5. **Cualquier cambio de permisos/roles de base de datos en producción** se
   verifica primero en local con el mismo patrón exacto antes de aplicarlo en el
   droplet — nunca improvisar SQL de permisos directo en producción sin haberlo
   probado antes.
6. **`JWT_SECRET_KEY` de Command y `SECRET_KEY` de Raptor son el mismo secreto
   compartido, no dos secretos independientes.** Command no valida contraseñas —
   hace proxy del login a Raptor y verifica el JWT que Raptor ya firmó
   (`operator_from_access_token` en `backend/app/auth.py`, usa
   `settings.jwt_secret_key`). Si se regenera uno sin copiar el mismo valor al
   otro, el login falla con `"invalid token"` (401) — un error que se ve idéntico
   a contraseña incorrecta pero no lo es. Nunca rotar `JWT_SECRET_KEY` en
   Command sin copiar el `SECRET_KEY` real de Raptor (`~/vex-raptor/.env` en el
   droplet) al mismo tiempo. Incidente real: 2026-09-15, tras reconstruir
   `~/vex-founder.env` con un secreto nuevo aleatorio, el login quedó roto en
   Command (pero seguía funcionando en Raptor directo) hasta copiar el valor real.
7. **`GRANT INSERT` sobre una tabla con columna `SERIAL`/`IDENTITY` no alcanza —
   también hace falta `GRANT USAGE ON SEQUENCE <tabla>_id_seq`.** Sin esto,
   Postgres rechaza el `INSERT` con `permission denied for sequence ..._id_seq`
   aunque el `INSERT` sobre la tabla ya esté concedido. Aplica a cualquier grant
   nuevo de escritura, no solo `audit_log`. Ver `sql/003_roles.sql` (PR #10).
8. **Un rol de runtime 100% solo-lectura (`vex_founder_ro`) puede necesitar una
   excepción angosta de escritura si la app tiene su propia bitácora de
   auditoría** (`founder.audit_log`) — el patrón correcto es `GRANT INSERT`
   (nunca `UPDATE`/`DELETE`) solo en esa tabla puntual, más el `USAGE` de su
   secuencia (regla 7), sin ampliar el resto de sus permisos. Ver PR #9/#10.

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
| C-01 | DNS `ops.vexraptor.com` + TLS + `noindex` + vhost | [x] 2026-09-14 · `https://ops.vexraptor.com/health` · runbook `docs/operations/DEPLOY_OPS_VEXRAPTOR.md` |
| C-01b | Login UI en `ops` (usuario/contraseña, sesión httpOnly, auto-refresh) | [x] | `LoginView` + `/auth/login|refresh|logout|me` · proxy Raptor · cookies `founder_*` · `test_founder_auth` |
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
| C-14 | Account 360: authorized targets + recent scans (metadatos) | [x] `org_configs.allowed_targets` + `v_scan_attribution` (legacy `org_id` NULL por email) · `AccountView` · `test_f1_sql` |

---

## F3 — Dinero (bloquea F5)

Gap en Raptor: **PRICE-01c** (bloquea C-21). **En pausa desde 8-sep-2026: pricing de planes
(Essential/Professional/Enterprise/MSSP) todavía no definido — bloquea C-20 y por extensión C-22.**
C-23 no dependía de precios ni de Stripe, por eso pudo avanzar solo.

| ID | Tarea | Gate de cierre |
|---|---|---|
| C-20 | Stripe products/prices por plan Essential / Pro / Enterprise / MSSP | Prices IDs documentados en Settings |
| C-21 | Webhooks firmados → `fact_billing_event` | Evento test en Stripe aparece en API |
| C-22 | Revenue waterfall + MRR/ARR canónicos (`backend/app/kpis.py`) | MRR Command = MRR Stripe ± overrides |
| C-23 | `founder.manual_revenue` para deals offline | [x] Override auditado + `channel` · `test_manual_revenue` + `test_f1_manual_revenue` |
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

- [x] DNS + contenedor + nginx (`ops.vexraptor.com` live 2026-09-14)
- [x] C-01b login UI (sesión founder httpOnly — redeploy ops para activar)
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
