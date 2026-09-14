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
2. **Postgres** — `sql/001`, `002`, `003` + passwords `vex_founder_ro/rw` vía `deploy/apply-founder-roles.sh`.
3. **Grants extra** (una vez, porque las tablas las creó `vex_raptor` y el contenedor migra como `vex_founder_rw`):

```sql
GRANT CREATE ON DATABASE vex_raptor TO vex_founder_rw;
ALTER SCHEMA founder OWNER TO vex_founder_rw;
GRANT USAGE ON SCHEMA public TO vex_founder_rw;
GRANT SELECT ON public.organizations, public.users, public.scan_history TO vex_founder_rw;
-- + REASSIGN OWNER de tablas/vistas/sequences en schema founder a vex_founder_rw
```

4. **Imagen** — `docker build -f deploy/Dockerfile.vex-founder -t vex-founder .`
5. **Contenedor** — ver `deploy/run-vex-founder.sh` + `~/vex-founder.env` (no commitear).
6. **nginx** — vhost `ops-vexraptor` (headers `noindex`, proxy a `127.0.0.1:8081`).

**Verificación:**

```bash
curl -s http://127.0.0.1:8081/health
curl -s https://ops.vexraptor.com/health
```

---

## Auth hoy (workaround hasta C-01b)

- API: `FOUNDER_AUTH_MODE=jwt` · `JWT_SECRET_KEY` = `SECRET_KEY` de Raptor.
- **No hay pantalla de login** en Command.
- Flujo manual (~2 h por access token):
  1. Login en `https://app.vexraptor.com`
  2. En consola de `app`: `fetch('/api/v1/auth/refresh', {method:'POST', credentials:'include'}).then(r=>r.json()).then(d=>prompt('token', d.token))`
  3. En consola de `ops`: `localStorage.setItem('founder_token', TOKEN)` + reload

**Próximo paso (C-01b):** login propio en `ops` (usuario/contraseña) + sesión httpOnly + auto-refresh — sustituye este ritual.

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
# editar JWT_SECRET_KEY + VEX_FOUNDER_RW_PASSWORD
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

## Seguridad pendiente (go-live)

- [ ] **C-01b** — Login UI en `ops` (prioridad)
- [ ] Cloudflare Access o IP allowlist (capa extra opcional)
- [ ] WAF rules
- [ ] Backup `pg_dump` schema `founder`

---

## Handoff

Sprint cerrado: **C-01 deploy ops.vexraptor.com** — live 2026-09-14.  
Siguiente: **C-01b** — pantalla login Command (usuario/contraseña, sesión httpOnly).  
Modelo sugerido: **Claude Sonnet (thinking)** — auth cross-subdomain + sesión.
