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
: "${VEX_FOUNDER_RW_PASSWORD:?Set VEX_FOUNDER_RW_PASSWORD in $ENV_FILE}"
: "${DATABASE_URL:?Set DATABASE_URL in $ENV_FILE}"

docker rm -f "$NAME" 2>/dev/null || true

docker run -d \
  --name "$NAME" \
  --network "$NETWORK" \
  --restart unless-stopped \
  --memory 256m \
  -p 127.0.0.1:8081:8081 \
  --env-file "$ENV_FILE" \
  -e JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  -e DATABASE_URL="postgresql://vex_founder_rw:${VEX_FOUNDER_RW_PASSWORD}@postgres:5432/vex_raptor" \
  "$IMAGE"

echo "✓ $NAME started — curl -s http://127.0.0.1:8081/health"
