# Mapa del ecosistema VexSec

> Fuente de verdad de qué vive en qué repo y qué contrato existe entre ellos. Se lee desde
> cualquiera de los 4 chats de producto cuando hace falta contexto cruzado — no se conectan las 4
> carpetas en un mismo chat. Si trabajás algo de Sense, Guard o Command que toca Raptor (o
> viceversa), avisá explícitamente en el chat correspondiente antes de asumir que se puede tratar
> como un solo proyecto.
>
> Última actualización: 2026-09-08.

---

## 1. Los 4 repos

| Repo | Qué es | Producto de cara al mercado | Estado (8-sep-2026) |
|---|---|---|---|
| **Vex Raptor** | Consola + motor ofensivo. El core del negocio. | Vex Raptor — pentest autónomo web/API para empresas grandes, self-hosted Docker + SaaS en `app.vexraptor.com`. Incluye el módulo "Internal Exposure" (gated a plan enterprise, self-hosted por el cliente). | En producción / vendiendo. |
| **Vex Sense** | Línea de producto Raspberry Pi. Reusa el motor de exposición de Raptor, runtime independiente. | Sensor plug-and-play para pymes sin IT propio — visibilidad de exposición en LAN de cliente. Vendido vía partners (Tyndall Telecom, 50/50 revenue-share). | Piloto técnico validado en hardware real (Pi 5); sin cliente real de Tyndall todavía, solo TestOrg. |
| **Vex Guard** | Extensión Chromium. Proyecto nuevo. | Dual-Gate — evita exposición de PII vía IA (bloquea/avisa antes de que el usuario pegue datos sensibles en un prompt). | Arrancando. |
| **Vex Command** (este repo) | "Del negocio" — conecta a los tres anteriores. No es producto de cliente. | Founder Console (`ops.vexraptor.com`), interno, nunca en el nav del tenant. | F2 en curso — ver `docs/PLAN_MAESTRO.md`. |

---

## 2. Contratos entre repos

**Vex Sense → Vex Raptor**
Sense reusa la identidad de Organization/OrgApiKey/billing de Raptor en vez de tener su propio
sistema de cuentas. El runtime de escaneo de Sense es independiente (funciona standalone, sin
conectividad); Raptor solo entra en juego para fleet management, licensing y billing cuando hay
conexión. Decisión tomada explícitamente para no duplicar auth/billing.

**Vex Raptor → Vex Command**
Command lee de Raptor vía:
- `RAPTOR_HEALTH_URL` (Platform Ops module, `backend/app/providers/sql.py`) — health check HTTP.
- Vistas agregadas SQL sobre el mismo Postgres de Raptor (`sql/002_aggregate_views.sql`), **nunca
  acceso directo a la tabla de findings** — regla dura, ver `docs/PLAN_MAESTRO.md` cabecera de F1.
- Gaps pendientes documentados en Raptor pero consumidos por Command: `PRICE-00` (coste Gemini por
  scan, bloquea F4/Unit Economics) y `PRICE-01c` (webhooks Stripe firmados, bloquea F3).

**Vex Guard → el resto**
Sin contrato definido todavía — proyecto recién arrancando. Cuando exista, documentar acá antes de
que se vuelva implícito.

**Regla general de todos los contratos:** ningún repo consumidor lee payloads de findings de
clientes directo. Todo lo que cruza a Command son agregados/metadatos — mismo principio que aplica
a la capa de IA founder (ver §4).

---

## 3. Identidad de marca (pendiente)

- Empresa: **VexSec** (el "SL" es solo forma societaria española). Marca principal: **VEX**.
  Productos: Vex Raptor, Vex Sense (Vex Guard pendiente de nombre final).
- 4-sep-2026: puede que no se puedan registrar las marcas Vex/Vex Raptor/Vex Sense. Se evalúa un
  rebrand completo (empresa + productos) con un nombre global libre para registrar, que cubra
  pentesting hoy y auditoría/ciberseguridad a futuro. Estilo preferido: latín/evocador, compuesto
  inglés, o corto y neutro.
- **El nombre del rebrand todavía NO está decidido.** No usar ningún nombre candidato como si
  fuera definitivo en ningún documento — cuando Edu lo confirme, se actualiza esta sección.
- **Alcance ya definido para cuando se elija:** solo nombre + logo/identidad visual, en repos y
  branding. El eslogan ("The autonomous pentester that never leaves your perimeter"), el titular
  ("Prove what is exploitable. Keep the evidence in your perimeter."), la propuesta de valor y
  toda decisión de producto/negocio ya tomada NO cambian.
- **Estado real: los 4 repos, el código y esta misma carpeta siguen nombrados "Vex".** No
  renombrar nada por iniciativa propia sin que Edu lo pida explícitamente para ese repo puntual.

---

## 4. Decisiones de arquitectura ecosistema-wide

**IA agnóstica de proveedor (8-sep-2026, decidido).** No dejar la IA hardcodeada a un solo
proveedor (hoy: Gemini). El motor debe soportar que tanto VexSec como los clientes elijan qué IA
usar — aplica tanto al motor ofensivo de Raptor como a la capa de IA founder de Command (weekly
brief, account risk, etc. — ver `docs/founder-console/FOUNDER_CONSOLE_BLUEPRINT.md` §2). Pendiente
de diseño: interfaz de proveedor, storage seguro de API keys de terceros (BYOK para
Enterprise/MSSP a evaluar), y el ajuste de las fórmulas de COGS (`PRICE-00`, `gross_margin` en
Command) para que dejen de asumir un único proveedor fijo. No hay ticket abierto todavía en ningún
repo — es una decisión de dirección, no una tarea en curso.

---

## 5. Gaps abiertos que cruzan repos

| Gap | Vive en | Bloquea | Estado |
|---|---|---|---|
| `PRICE-00` — coste Gemini por scan | Vex Raptor | Command F4 (Unit Economics) | Abierto |
| `PRICE-01c` — webhooks Stripe firmados | Vex Raptor | Command F3 (Revenue real) | Abierto |
| IA agnóstica de proveedor | Raptor + Command | Nada bloqueado hoy, es decisión de dirección | Sin ticket |
| Contrato Vex Guard ↔ resto | Vex Guard | — | No definido, proyecto recién arrancando |

---

## Cómo mantener este doc

Actualizar cuando: se cierra un contrato nuevo entre repos, cambia el estado de un gap de la
tabla §5, o se toma una decisión que afecta a más de un repo (como §4). No repetir acá el detalle
de ejecución de cada repo — eso vive en el plan maestro de cada uno (`PLAN_MAESTRO.md` en Command,
el equivalente en Raptor/Sense/Guard si existe).
