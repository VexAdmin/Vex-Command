# Vex Command — Auditoría independiente
**Fecha:** 2026-09-08 · **Alcance:** repo completo, estado F2 (C-10 hecho, C-11 en curso) · **Método:** verificación directa contra código, no contra docs.

---

## 1. Veredicto ejecutivo

Lo que está bien construido: el core de F0/F1 (auth JWT, schema `founder`, SQL parametrizado, pipeline persistido) es sólido y **coincide con lo que el plan y el README afirman** — corrí los 14 tests de `make test` en un entorno limpio (Python 3.12) y pasan los 14, incluidos los 7 de `test_auth.py`. Las queries SQL están parametrizadas de punta a punta (nada de f-strings dentro de `text()`), las vistas agregadas solo exponen `finding_count` (nunca el payload de findings), y todos los endpoints pasan por `OperatorDep`. Esto es higiene real, no teatro.

Los 3 problemas reales:

1. **El export CSV está roto en modo JWT (auth real).** El frontend manda el token como query param (`?token=...`) porque `window.location.href` no puede setear headers — pero el backend **nunca lee ese query param**, solo `Authorization` header. En prod (`FOUNDER_AUTH_MODE=jwt`), el botón de exportar da 401/403 silencioso. Nadie lo notó porque en dev (`mock`) el auth se bypassea entero.
2. **Credenciales por defecto commiteadas en `sql/003_roles.sql`** (`change_me_ro` / `change_me_rw`). El nombre grita "cámbiame" pero no hay ningún check que impida arrancar en prod con esas passwords — es el mismo patrón de riesgo que un secret hardcodeado, aunque el archivo es un template para correr manualmente.
3. **`docker-compose.yml` (servicio `vex-founder`) fuerza `FOUNDER_AUTH_MODE: mock` y no setea `APP_ENV`** (default `dev`) — es decir, el único gate que bloquea mock-auth en prod (`app_env in (prod, staging)`, en `auth.py`) queda inerte en ese compose. El Dockerfile real (`deploy/Dockerfile.vex-founder`) sí hardcodea `APP_ENV=prod` + `FOUNDER_AUTH_MODE=jwt` y es la ruta de deploy real — pero si alguien corre `docker compose up vex-founder` pensando que es "como prod", expone acceso sin token.

Ninguno es existencial hoy porque el producto es interno y no está en `ops.` todavía (C-01 pendiente, correctamente marcado `[ ]`). Pero el #1 es un bug funcional real esperando a C-01, y el #2/#3 son el tipo de cosa que sobrevive silenciosa hasta el día que sí importa.

---

## 2. Declarado vs. verificado

| Afirmación (README / PLAN_MAESTRO) | Verificado | Evidencia |
|---|---|---|
| `make test` → 14 tests (mock + auth + pipeline) | ✅ | Corridos en Python 3.12 limpio: `14 passed, 1 warning in 0.65s` |
| `test_auth.py` (7 tests) | ✅ | `grep -c "def test_"` → 7 |
| C-02 Auth JWT operativo, rechaza tenant/token inválido | ✅ | `auth.py` decodifica HS256, valida `is_platform_operator`, bloquea mock en prod/staging |
| C-04 "Vistas agregadas sin findings" | ✅ | `002_aggregate_views.sql` solo expone `finding_count`/`findings_hc_*` agregados, nunca el payload |
| Deps "pineadas" | ✅ | `requirements.txt` 100% `==`; `frontend/package-lock.json` presente |
| C-08 Audit en `founder.audit_log` | ⚠️ parcial | Solo persiste si hay `DATABASE_URL` (modo SQL). En modo `mock` cae a lista en memoria, capada a 500, se pierde al reiniciar — coherente para F0 pero no lo dice el README |
| SQL parametrizado (sin injection) | ✅ | Revisé `sql.py` completo: cero interpolación de input de usuario en `text()`, todo bind param |
| Export CSV funcional | ❌ | Backend nunca lee `?token=`; roto en modo JWT (ver H1) |
| Git limpio, sin secretos trackeados | ✅ | `git status` limpio, `git ls-files` sin `.env`/DBs/secrets |
| Working tree en `main` | ⚠️ | Está en `main`, no `dev` — dato para vos, no un hallazgo técnico (regla tuya, no del código) |

---

## 3. Hallazgos

### H1 — MEDIA · Export CSV roto en auth real (bug funcional, no solo higiene)
`frontend/src/api/client.ts::exportAccounting()` construye la URL con `?token=<jwt>` y navega con `window.location.href` (no puede mandar `Authorization` header en una navegación GET). `backend/app/main.py::export_csv` depende de `OperatorDep` → `require_operator` → `decode_bearer_token`, que **solo lee el header `Authorization`**, nunca `request.query_params`. Resultado: en `FOUNDER_AUTH_MODE=jwt` el request pega el 401 antes de llegar al handler. Nadie lo vio porque en dev `mock` bypassea todo el auth.

**Fix:** o bien el backend acepta `?token=` como fallback (aceptando el riesgo de que quede en logs de nginx/browser history — necesitaría loggear con cuidado y expirar tokens cortos), o el frontend cambia a `fetch()` + blob + `URL.createObjectURL` para poder mandar el header. La segunda opción es la correcta si te importa no filtrar el JWT en logs.

### H2 — MEDIA · Credenciales por defecto en `sql/003_roles.sql`
```sql
CREATE ROLE vex_founder_ro LOGIN PASSWORD 'change_me_ro';
CREATE ROLE vex_founder_rw LOGIN PASSWORD 'change_me_rw';
```
Es un script "correr una vez como superuser", pero no hay ningún mecanismo (env var, prompt, check en `db.py`) que fuerce a que se cambien antes de ir a prod. Si en algún momento se corre tal cual contra una instancia expuesta, son credenciales públicas en el historial de git.

**Fix:** generar la password en el momento del deploy (script bash que la pida o la genere random y la guarde solo en el secret manager), o al menos un comentario + check en `Makefile`/`deploy` que falle si detecta el default en `DATABASE_URL` de prod.

### H3 — BAJA/MEDIA · `docker-compose.yml` no replica las env vars seguras del Dockerfile real
El servicio `vex-founder` en `docker-compose.yml` define `FOUNDER_AUTH_MODE: mock` y **no define `APP_ENV`**, así que cae al default `"dev"` de `config.py` — el check `if settings.app_env in ("prod","staging")` en `auth.py::require_operator` nunca dispara ahí. El Dockerfile real (usado por el build de C-01) sí es seguro (`APP_ENV=prod`, `FOUNDER_AUTH_MODE=jwt` hardcodeados como `ENV`). El riesgo es de confusión operativa, no de la ruta de deploy documentada — pero vale la pena que el compose no deje una superficie "prod-like" con auth abierto.

**Fix:** o sacar el servicio `vex-founder` de `docker-compose.yml` (dejar el compose solo para Postgres/Redis/dev), o setear `APP_ENV: dev` explícito ahí y agregar un comentario de que ese servicio nunca debe exponerse a internet.

### H4 — BAJA · Auditoría no persistente en modo mock
Ya cubierto en la tabla — es esperado en F0/F1 local, pero si algún día corrés `mock` contra algo semi-real (staging manual, demo a alguien), el audit trail no sobrevive un restart. No bloquea nada hoy.

### Lo que busqué y NO encontré (negativo, para que confíes en el resto)
- Sin f-strings ni `%`/`.format()` dentro de queries SQL (`sql.py` completo revisado).
- Sin `v-html`/`innerHTML`/`dangerouslySetInnerHTML` en el frontend.
- Sin `.env`, `*.db`, `*.sqlite` ni claves trackeadas en git (`git ls-files` limpio, `.gitignore` cubre los patrones correctos).
- Sin endpoints del API sin `OperatorDep` (revisé los 20 endpoints de `main.py` uno por uno).
- Sin god-files: el archivo más grande es `sql.py` con 465 líneas — razonable para un provider con 15+ queries.
- CORS acotado a `console_origin` + `127.0.0.1:5174`, no `allow_origins=["*"]`.

---

## 4. Funcionalidad: sólido / incompleto / ausente

| Área | Estado |
|---|---|
| Auth + audit (F1) | Sólido — verificado con tests reales |
| Pipeline/deals (C-10) | Sólido — persistencia confirmada por `test_pipeline` + `test_f1_pipeline` (este último no lo pude correr sin Postgres, pero el código coincide 1:1 con el patrón ya validado de `test_pipeline`) |
| Export CSV | Incompleto — roto en auth real (H1) |
| Goals/OKRs (C-11) | Ausente — próximo ítem del plan, correctamente marcado `[ ]` |
| Billing/Stripe (F3) | Ausente por diseño — el plan es explícito en no inventar MRR, esto es correcto y poco común (la mayoría de founders inventan el dashboard de revenue antes de tener Stripe) |
| Warehouse/cohorts (F5) | Ausente, gateado correctamente detrás de F3 |

---

## 5. Contexto de mercado

Vex Command no es un producto que se vende — es tooling interno, así que "competencia" en sentido estricto no aplica. El framing correcto es **build vs. buy**:

- **Retool / Internal.io** — generic admin-builder. Te ahorrarían el frontend Vue a cambio de acoplarte a su runtime y pagar por seat; no te dan auth compartido con el `org_access.is_platform_operator` de Raptor ni el schema `founder` a medida. Para un founder solo, construir esto a mano (como hiciste) es razonable mientras el scope sea chico — el punto de quiebre suele ser cuando hay 2+ operadores no-técnicos que necesitan modificar vistas sin tocar código.
- **ChartMogul / Baremetrics** — analítica de suscripción sobre Stripe. Relevante recién en F3 (C-20 Stripe). Hoy no compite con nada de lo que hay en el repo porque no hay billing.
- **Riesgo de over-building**: el patrón más común en herramientas founder-only es invertir demasiado en un dashboard interno antes de tener revenue real que mostrar — el plan ya lo previene explícitamente ("MRR=0", "no saltar a F5 antes de F3"), así que el roadmap está alineado con el riesgo, no lo ignora.

Fuentes: [Baremetrics vs ChartMogul](https://baremetrics.com/blog/baremetrics-vs-chartmogul-which-is-right-for-your-business), [ChartMogul vs Baremetrics](https://chartmogul.com/blog/chartmogul-baremetrics-everything-you-need-to-know/), [10 Best SaaS Metrics Dashboards 2026](https://fungies.io/best-saas-metrics-dashboard-tools-2026/)

---

## 6. Plan de fases sugerido

**Fase 0 — Higiene barata, antes de C-01 (DNS/deploy)**
- H1: arreglar export CSV (fetch+blob, no query param) — 30 min.
- H2: sacar passwords default de `003_roles.sql`, mover a generación en deploy.
- H3: separar el servicio `vex-founder` del `docker-compose.yml` de dev, o forzar `APP_ENV=dev` explícito ahí con comentario de "nunca exponer".
- **No hacer:** no tocar auth.py ni el modelo de roles — está bien como está, el problema es de configuración/despliegue, no de lógica.

**Fase 1 — Credibilidad funcional (converge con tu plan, C-11/C-12/C-13)**
- Seguir el plan tal cual está: Goals editables → alertas Slack → support link. No hay nada en la auditoría que sugiera reordenar esto.

**Fase 2 — C-01 deploy**
- Una vez apliques DNS: correr `test-sql` contra Postgres real antes de exponer, para validar C-06/C-10 con datos reales (no lo pude correr yo por falta de Postgres en este entorno).

**Fase 3+ — Dinero y escala**
- Tal cual el plan: no hay razón para adelantar Stripe ni warehouse. El gate "F3 antes de F5" es correcto y ya está en el doc.

---

## 7. Respecto al roadmap interno

**Converge.** El `PLAN_MAESTRO.md` es honesto consigo mismo — no exagera estados (C-11 en curso está bien marcado, no hay `[x]` sin evidencia que yo haya podido invalidar). Lo único que agregaría al plan es una línea explícita en Fase 0/C-01: "verificar que el export CSV funciona con JWT real antes de exponer en `ops.`" — porque hoy ese bug es invisible en dev y solo aparece el día que alguien lo prueba en prod.
