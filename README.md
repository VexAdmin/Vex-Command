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

Con Raptor prod: apunta `DATABASE_URL` a la **replica** de lectura (mismo host, rol `vex_founder_ro`).

## Auth JWT (ops.)

```bash
export FOUNDER_AUTH_MODE=jwt
export JWT_SECRET_KEY=<mismo SECRET_KEY que Raptor>
# Token: login en app como platform operator, o create_access_token en Raptor
export VITE_FOUNDER_TOKEN=<jwt>   # frontend dev
```

## Tests

```bash
make test       # mock + auth (12 tests)
make test-sql   # F1 integration (requiere Docker + postgres)
```

## Deploy

```bash
docker build -f deploy/Dockerfile.vex-founder -t vex-founder .
# + nginx deploy/nginx-ops.vexraptor.com.conf.example en droplet
```

Siguiente: **C-01** — DNS `ops.vexraptor.com` (lo haces tú en Cloudflare).
