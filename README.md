# Vex Command — Founder Console

Producto interno del dueño (`ops.vexraptor.com`). **No** es el Dashboard MSSP.

**Plan:** [`docs/PLAN_MAESTRO.md`](docs/PLAN_MAESTRO.md)

## Modo local (mock — F0)

```bash
cd ~/Documents/Proyectos/Vex-Command
make install
make api    # 8081 · FOUNDER_AUTH_MODE=mock
make web    # 5174
```

## Modo SQL (F1 — datos reales o dev stub)

```bash
make db-up   # Postgres en :5433 (Docker)
export DATABASE_URL=postgresql://vex_founder:vex_founder_dev@127.0.0.1:5433/vex_founder
export DATA_SOURCE=sql
make api
```

Sin Raptor adjunto: `FOUNDER_DEV_STUB=true` crea 3 orgs de prueba en PG.

### Datos reales desde Raptor local (Docker)

Con `vex-raptor-postgres` corriendo en tu Mac:

```bash
cd ~/Documents/Proyectos/Proyecto\ Vex-Raptor && docker compose up -d postgres
cd ~/Documents/Proyectos/Vex-Command
make db-sync-raptor   # copia organizations, users, scan_history → :5433
make api-sql          # terminal A
make web              # terminal B → http://localhost:5174
```

`make api-sql` usa `FOUNDER_DEV_STUB=false` y health de Raptor en `:8000`.
Auth sigue en `mock` en dev — no necesitas JWT para explorar.

### Pipeline (C-10)

En **04 Pipeline**: crea deals y muévelos entre stages (← → / Lost). Con `make api-sql` los deals persisten en `founder.deal` + actividad en `deal_activity`.

Con Raptor prod: apunta `DATABASE_URL` a la **replica** de lectura (rol `vex_founder_ro`).

## Auth JWT (ops.)

```bash
export FOUNDER_AUTH_MODE=jwt
export JWT_SECRET_KEY=<mismo SECRET_KEY que Raptor>
# Token: login en app como platform operator, o create_access_token en Raptor
export VITE_FOUNDER_TOKEN=<jwt>   # frontend dev
```

## Tests

```bash
make test       # mock + auth + pipeline + goals (17 tests)
make test-sql   # F1 integration + pipeline + goals persist (requiere Docker + postgres)
```

## Deploy

```bash
docker build -f deploy/Dockerfile.vex-founder -t vex-founder .
# + nginx deploy/nginx-ops.vexraptor.com.conf.example en droplet
```

Siguiente: **C-01** — DNS `ops.vexraptor.com` (lo haces tú en Cloudflare).
