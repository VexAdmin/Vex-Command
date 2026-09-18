#!/usr/bin/env bash
# Start or recreate vex-founder on the Raptor droplet (vex-raptor-net).
# Usage:
#   cp deploy/vex-founder.env.example ~/vex-founder.env
#   # edit ~/vex-founder.env — chmod 600
#   bash deploy/run-vex-founder.sh ~/vex-founder.env
set -euo pipefail

ENV_FILE="${1:-$HOME/vex-founder.env}"
IMAGE="${VEX_FOUNDER_IMAGE:-vex-founder:latest}"
NAME="${VEX_FOUNDER_CONTAINER:-vex-founder}"
NETWORK="${VEX_DOCKER_NETWORK:-vex-raptor-net}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "✗ Missing env file: $ENV_FILE" >&2
  echo "  cp deploy/vex-founder.env.example ~/vex-founder.env && chmod 600 ~/vex-founder.env" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a && source "$ENV_FILE" && set +a

: "${JWT_SECRET_KEY:?Set JWT_SECRET_KEY in $ENV_FILE (same as Raptor SECRET_KEY)}"
: "${DATABASE_URL:?Set DATABASE_URL in $ENV_FILE — must be the vex_founder_ro connection string}"
: "${MIGRATION_DATABASE_URL:?Set MIGRATION_DATABASE_URL in $ENV_FILE (vex_raptor owner, migrations only — S3)}"

# S3: runtime must never connect as vex_founder_rw (full DML incl. DELETE on
# founder.*, including audit_log — see sql/003_roles.sql). This script used to
# silently force that role by overwriting DATABASE_URL below; now it just
# fails loud if the env file itself still points at rw instead of quietly
# "fixing" it for you.
if [[ "$DATABASE_URL" == *vex_founder_rw* ]]; then
  echo "✗ DATABASE_URL uses vex_founder_rw — runtime must use vex_founder_ro (S3)." >&2
  echo "  See deploy/vex-founder.env.example." >&2
  exit 1
fi

docker rm -f "$NAME" 2>/dev/null || true

# S3: DATABASE_URL/MIGRATION_DATABASE_URL come straight from --env-file — this
# script no longer overwrites DATABASE_URL to vex_founder_rw.
docker run -d \
  --name "$NAME" \
  --network "$NETWORK" \
  --restart unless-stopped \
  --memory 256m \
  -p 127.0.0.1:8081:8081 \
  --env-file "$ENV_FILE" \
  -e JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  "$IMAGE"

echo "✓ $NAME started — curl -s http://127.0.0.1:8081/health"
