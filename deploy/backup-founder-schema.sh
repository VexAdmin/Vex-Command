#!/usr/bin/env bash
# Dump schema founder from Raptor Postgres (Command ops data only).
# Usage on droplet:
#   bash deploy/backup-founder-schema.sh
#   bash deploy/backup-founder-schema.sh /var/backups/vex-command
#
# Cron example (daily 03:15 UTC):
#   15 3 * * * deploy bash $HOME/Vex-Command/deploy/backup-founder-schema.sh $HOME/founder-backups >> $HOME/founder-backups/backup.log 2>&1
set -euo pipefail

OUT_DIR="${1:-$HOME/founder-backups}"
CONTAINER="${PG_CONTAINER:-vex-raptor-postgres}"
DB="${PG_DB:-vex_raptor}"
USER="${PG_USER:-vex_raptor}"

mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%d-%H%M%SZ)"
FILE="$OUT_DIR/founder-schema-$STAMP.sql.gz"

docker exec "$CONTAINER" pg_dump -U "$USER" -d "$DB" -n founder --no-owner --no-acl \
  | gzip -c > "$FILE"

echo "✓ backup written: $FILE ($(du -h "$FILE" | awk '{print $1}'))"
