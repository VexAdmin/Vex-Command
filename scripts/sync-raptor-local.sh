#!/usr/bin/env bash
# Copy Raptor OLTP tables from local vex-raptor-postgres into Vex-Command Postgres (:5433).
# Safe for dev: does not touch Raptor primary in prod — only your local Docker stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RAPTOR_CONTAINER="${RAPTOR_PG_CONTAINER:-vex-raptor-postgres}"
RAPTOR_USER="${RAPTOR_PG_USER:-vex_raptor}"
RAPTOR_DB="${RAPTOR_PG_DB:-vex_raptor}"

COMMAND_CONTAINER="${COMMAND_PG_CONTAINER:-vex-command-postgres-1}"
COMMAND_USER="${COMMAND_PG_USER:-vex_founder}"
COMMAND_DB="${COMMAND_PG_DB:-vex_founder}"

WORK="${TMPDIR:-/tmp}/vex-command-raptor-sync"
DUMP_IN_CONTAINER="/tmp/raptor_oltp.dump"
DUMP_LOCAL="$WORK/raptor_oltp.dump"

if ! docker ps --format '{{.Names}}' | grep -qx "$RAPTOR_CONTAINER"; then
  echo "✗ Raptor Postgres not running ($RAPTOR_CONTAINER)."
  echo "  Start it: cd ~/Documents/Proyectos/Proyecto\\ Vex-Raptor && docker compose up -d postgres"
  exit 1
fi

echo "→ Starting Command Postgres (port 5433)..."
docker compose up -d postgres

for i in $(seq 1 30); do
  if docker exec "$COMMAND_CONTAINER" pg_isready -U "$COMMAND_USER" -d "$COMMAND_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

mkdir -p "$WORK"

echo "→ Dumping organizations, users, scan_history from $RAPTOR_CONTAINER..."
docker exec "$RAPTOR_CONTAINER" rm -f "$DUMP_IN_CONTAINER"
docker exec "$RAPTOR_CONTAINER" pg_dump -U "$RAPTOR_USER" -d "$RAPTOR_DB" \
  --format=custom \
  --no-owner --no-acl \
  --table=public.organizations \
  --table=public.users \
  --table=public.scan_history \
  -f "$DUMP_IN_CONTAINER"

docker cp "$RAPTOR_CONTAINER:$DUMP_IN_CONTAINER" "$DUMP_LOCAL"

echo "→ Dropping old public OLTP tables in $COMMAND_DB (if any)..."
docker exec "$COMMAND_CONTAINER" psql -U "$COMMAND_USER" -d "$COMMAND_DB" -v ON_ERROR_STOP=1 <<'SQL'
DROP TABLE IF EXISTS public.scan_history CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.organizations CASCADE;
SQL

echo "→ Restoring into $COMMAND_CONTAINER/$COMMAND_DB..."
docker exec -i "$COMMAND_CONTAINER" pg_restore -U "$COMMAND_USER" -d "$COMMAND_DB" --no-owner --no-acl < "$DUMP_LOCAL"

ORG_COUNT="$(docker exec "$COMMAND_CONTAINER" psql -U "$COMMAND_USER" -d "$COMMAND_DB" -Atc "SELECT COUNT(*) FROM public.organizations")"
SCAN_COUNT="$(docker exec "$COMMAND_CONTAINER" psql -U "$COMMAND_USER" -d "$COMMAND_DB" -Atc "SELECT COUNT(*) FROM public.scan_history")"

echo ""
echo "✓ Sync done: $ORG_COUNT orgs, $SCAN_COUNT scans in $COMMAND_DB"
echo ""
echo "Next:"
echo "  export DATA_SOURCE=sql"
echo "  export FOUNDER_DEV_STUB=false"
echo "  export DATABASE_URL=postgresql://${COMMAND_USER}:vex_founder_dev@127.0.0.1:5433/${COMMAND_DB}"
echo "  export RAPTOR_HEALTH_URL=http://127.0.0.1:8000/health"
echo "  make api    # terminal A"
echo "  make web    # terminal B → http://localhost:5174"
