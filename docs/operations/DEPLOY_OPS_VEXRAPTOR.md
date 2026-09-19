# Deploy — `ops.vexraptor.com` (Vex Command)

> Runbook de producción en el droplet Raptor (`deploy@vex-raptor-prod`).
> Host: **https://ops.vexraptor.com** · contenedor: `vex-founder` · puerto local: `127.0.0.1:8081`.

**Estado:** live desde **2026-09-14** (DNS Cloudflare + Postgres `founder` + Docker + nginx).

---

## Arquitectura en el droplet

| Pieza | Dónde |
|---|---|
| Postgres Raptor | `vex-raptor-postgres` · DB `vex_raptor` |
| Schema Command | `founder` (tablas + vistas agregadas) |
| API + SPA | `vex-founder` en red `vex-raptor-net` |
| Proxy público | nginx `/etc/nginx/sites-available/ops-vexraptor` → `:8081` |
| Repo en servidor | `~/Vex-Command` (pull + rebuild) |

Raptor **no** se modifica en código; solo se comparte `SECRET_KEY` (JWT) y Postgres.

---

## Deploy inicial (hecho 2026-09-14)

1. **DNS** — registro `A` `ops` → IP droplet, proxied (Cloudflare).
2. **Postgres, migraciones (owner)** — `sql/001`, `002`, `003` corren como `vex_raptor`
   (owner/superuser), vía `MIGRATION_DATABASE_URL` — nunca con `vex_founder_rw`.
   Passwords de `vex_founder_ro/rw` vía `deploy/apply-founder-roles.sh`.
3. **Runtime = un solo rol acotado, sin ownership ni acceso directo a `public.*`.**
   Desde S3 (2026-09-18) `vex_founder_ro` es el **único** rol runtime: `SELECT`
   sobre las vistas agregadas + DML acotado a `deal`, `deal_activity`,
   `account_note`, `goal`, `okr`, `manual_revenue` (incluye escrituras como
   C-23 manual revenue), e `INSERT`-only sobre `audit_log` (lectura vía
   `founder.v_audit_log`). `vex_founder_rw` queda **deprecado** — no tiene
   ningún grant y nunca debe ser el `DATABASE_URL` de runtime;
   `deploy/run-vex-founder.sh` rechaza arrancar si lo es. Ninguno de los dos
   roles tiene `GRANT` sobre tablas de `public` de Raptor más allá de lo ya
   documentado, ni ownership del schema `founder`. Ver `sql/003_roles.sql` y
   `deploy/bootstrap-founder-db-grants.sql` (versión mínima, solo migración) —
   el `GRANT CREATE`/`ALTER SCHEMA OWNER`/`GRANT SELECT` amplio que este
   archivo tenía antes del 2026-09-15 quedó revertido.

**RLS (Raptor T-22):** `org_configs`, `scan_history` y `scan_metrics` tienen Row
Level Security forzado. En vez de un bypass global de sesión (`app.bypass_rls`,
removido el 2026-09-15 por ser demasiado amplio — se saltaba RLS para cualquier
tabla, no solo las que Command necesita), Command usa funciones `SECURITY DEFINER`
acotadas en el schema `founder`, cada una exponiendo solo las columnas necesarias
(nunca `scan_history.findings`, el payload crudo de pentest):

- `founder.f_org_targets()` → `founder.v_org_targets` (org_id, allowed_targets)
- `founder.f_scan_history()` — usada dentro de `founder.v_scan_attribution`
- `founder.f_scan_metrics()` — ídem, tolera la tabla ausente (columna opcional
  según el entorno)

Estas funciones son dueñas del schema `founder` (corren como `vex_raptor` al
definirse) y por tanto se saltan RLS de forma controlada — `vex_founder_ro/rw`
solo tienen `GRANT EXECUTE` sobre ellas, nunca `SELECT` directo sobre las tablas
de `public` con RLS. Ver `sql/002_aggregate_views.sql` y `sql/003_roles.sql`.

Verificar tras aplicar: `psql -U vex_founder_ro -c "SELECT * FROM founder.v_org_targets;"`
debe devolver filas reales (no vacío, no error de permisos).

4. **Imagen** — `docker build -f deploy/Dockerfile.vex-founder -t vex-founder .`
5. **Contenedor** — dos URLs de conexión separadas en `~/vex-founder.env` (no
   commitear): `DATABASE_URL` (runtime, `vex_founder_ro`) y `MIGRATION_DATABASE_URL`
   (solo migraciones on-startup, `vex_raptor` owner). Ver
   `deploy/run-vex-founder.sh` + `deploy/.env.production.example`.
6. **nginx** — vhost `ops-vexraptor` (headers `noindex`, proxy a `127.0.0.1:8081`).

**Verificación:**

```bash
curl -s http://127.0.0.1:8081/health
curl -s https://ops.vexraptor.com/health
```

---

## Auth (C-01b)

- Pantalla **`/login`** en `ops` — mismas credenciales que Raptor (platform operator).
- Command proxy → `RAPTOR_AUTH_URL` (`http://vex-raptor:8000/api/v1/auth`) en red Docker.
- Sesión en cookies httpOnly `founder_access` / `founder_refresh` (dominio `ops` only).
- Auto-refresh vía `POST /api/founder/v1/auth/refresh` — **no** pegar JWT en consola.
- Env prod: `RAPTOR_AUTH_URL=http://vex-raptor:8000/api/v1/auth`

---

## Higiene del droplet (mantenimiento)

Ejecutar en el droplet cuando convenga (no borra datos de producción).

```bash
# 1. Solo un contenedor founder
docker ps --filter name=vex-founder

# 2. Imágenes huérfanas (libera disco tras rebuilds)
docker image prune -f

# 3. Secretos fuera del historial bash — usar archivo env
cp ~/Vex-Command/deploy/vex-founder.env.example ~/vex-founder.env
chmod 600 ~/vex-founder.env
# editar JWT_SECRET_KEY + DATABASE_URL (vex_founder_ro) + MIGRATION_DATABASE_URL (vex_raptor)
bash ~/Vex-Command/deploy/run-vex-founder.sh ~/vex-founder.env

# 4. (Opcional) limpiar historial si pegaste passwords en la terminal
# history -c && history -w

# 5. Comprobar salud
curl -s http://127.0.0.1:8081/health
docker logs vex-founder --tail 30
```

**No eliminar:** schema `founder`, roles DB, vhost nginx `ops-vexraptor`, red `vex-raptor-net`, volumen `pg-data` de Raptor.

---

## Rebuild tras `git pull`

```bash
cd ~/Vex-Command && git pull
docker build -f deploy/Dockerfile.vex-founder -t vex-founder .
bash deploy/run-vex-founder.sh ~/vex-founder.env
```

Fixes en imagen: `ENV SQL_DIR=/app/sql` · fallback SPA en rutas Vue (`backend/app/main.py`).

---

## Go-live (Command)

| Ítem | Estado | Notas |
|------|--------|--------|
| CORS solo `CONSOLE_ORIGIN` | Hecho (S6) | `APP_ENV=prod` → sin `localhost:5174` |
| Sesión 30–60 min | Hecho (S7) | Cookie access default **45m** · `FOUNDER_SESSION_TTL_MINUTES` |
| Auth JWT en prod | Hecho | `FOUNDER_AUTH_MODE=jwt` · arranque falla si mock en prod |
| Backup schema `founder` | Script | `deploy/backup-founder-schema.sh` |
| Runbook MRR ≠ Stripe | Doc | `docs/operations/RUNBOOK_MRR_STRIPE.md` (F3 pendiente) |
| Cloudflare Access / IP allowlist | Opcional | Capa extra |
| WAF rules | Opcional | Cloudflare |

### Backup `founder` (droplet)

```bash
bash ~/Vex-Command/deploy/backup-founder-schema.sh ~/founder-backups
ls -lt ~/founder-backups | head
```

Restaurar (solo en emergencia, revisar SQL antes de aplicar):

```bash
gunzip -c ~/founder-backups/founder-schema-YYYYMMDD-HHMMSSZ.sql.gz \
  | docker exec -i vex-raptor-postgres psql -U vex_raptor -d vex_raptor
```

### Verificar CORS + sesión tras deploy

```bash
curl -sI -X OPTIONS https://ops.vexraptor.com/api/founder/v1/overview \
  -H "Origin: https://ops.vexraptor.com" \
  -H "Access-Control-Request-Method: GET" | grep -i access-control
```

En **Ajustes** (Settings API): `session_ttl` debe mostrar `45m` (o el valor configurado).

---

## Handoff

Sprint cerrado: **C-01 deploy ops.vexraptor.com** — live 2026-09-14.  
Siguiente: **C-01b** — pantalla login Command (usuario/contraseña, sesión httpOnly).  
Modelo sugerido: **Claude Sonnet (thinking)** — auth cross-subdomain + sesión.
