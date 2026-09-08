#!/usr/bin/env bash
# Apply founder DB role passwords at deploy time (never commit credentials).
# Usage:
#   export DATABASE_URL_ADMIN=postgresql://postgres:...@host:5432/vex_raptor
#   export VEX_FOUNDER_RO_PASSWORD="$(openssl rand -base64 24)"
#   export VEX_FOUNDER_RW_PASSWORD="$(openssl rand -base64 24)"
#   bash deploy/apply-founder-roles.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${DATABASE_URL_ADMIN:?Set DATABASE_URL_ADMIN (superuser connection)}"
: "${VEX_FOUNDER_RO_PASSWORD:?Set VEX_FOUNDER_RO_PASSWORD}"
: "${VEX_FOUNDER_RW_PASSWORD:?Set VEX_FOUNDER_RW_PASSWORD}"

if [[ "$VEX_FOUNDER_RO_PASSWORD" == change_me_* || "$VEX_FOUNDER_RW_PASSWORD" == change_me_* ]]; then
  echo "✗ Refusing default placeholder passwords (change_me_*)" >&2
  exit 1
fi

psql "$DATABASE_URL_ADMIN" -v ON_ERROR_STOP=1 -f "$ROOT/sql/003_roles.sql"

psql "$DATABASE_URL_ADMIN" -v ON_ERROR_STOP=1 \
  -v ro_pass="$VEX_FOUNDER_RO_PASSWORD" \
  -v rw_pass="$VEX_FOUNDER_RW_PASSWORD" <<'SQL'
ALTER ROLE vex_founder_ro WITH LOGIN PASSWORD :'ro_pass';
ALTER ROLE vex_founder_rw WITH LOGIN PASSWORD :'rw_pass';
SQL

echo "✓ founder roles applied (vex_founder_ro / vex_founder_rw)"
