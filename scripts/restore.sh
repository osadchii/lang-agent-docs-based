#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

usage() {
  cat <<'EOF'
Usage: restore.sh <path-to-backup> [target-database]

The backup can be a plain *.backup or a *.backup.gz file created by scripts/backup.sh.
Connection parameters are read from ENV_FILE (defaults to ../.env) or existing environment variables.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="${2:-${RESTORE_DB:-${POSTGRES_DB:-lang_agent_restore}}}"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file $BACKUP_FILE does not exist" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_ENV_FILE="$REPO_ROOT/.env"
ENV_FILE="${ENV_FILE:-$DEFAULT_ENV_FILE}"

if [[ -n "${ENV_FILE:-}" && -f "$ENV_FILE" ]]; then
  log "Loading environment from $ENV_FILE"
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
else
  log "ENV_FILE not provided or file missing, relying on exported variables"
fi

PGHOST="${POSTGRES_HOST:-${PGHOST:-localhost}}"
PGPORT="${POSTGRES_PORT:-${PGPORT:-5432}}"
PGUSER="${POSTGRES_USER:-${PGUSER:-postgres}}"
PGPASSWORD_VALUE="${PGPASSWORD:-${POSTGRES_PASSWORD:-}}"

if [[ -z "$PGPASSWORD_VALUE" ]]; then
  echo "PGPASSWORD/POSTGRES_PASSWORD must be set for restore" >&2
  exit 1
fi

export PGPASSWORD="$PGPASSWORD_VALUE"

log "Preparing to restore $BACKUP_FILE into database $TARGET_DB"

ensure_database() {
  local db_name=$1
  local drop_existing=$2
  local escaped="${db_name//\'/\'\'}"
  local exists
  exists="$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -Atqc \
    "SELECT 1 FROM pg_database WHERE datname='${escaped}'" || true)"

  if [[ "$exists" == "1" ]]; then
    if [[ "$drop_existing" == "true" ]]; then
      log "Dropping existing database $db_name"
      dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$db_name"
      log "Recreating database $db_name"
      createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$db_name"
    else
      log "Database $db_name already exists, skipping creation"
      return
    fi
  else
    log "Creating database $db_name"
    createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$db_name"
  fi
}

if [[ "${RESTORE_MANAGE_DATABASE:-true}" == "true" ]]; then
  ensure_database "$TARGET_DB" "${RESTORE_DROP_EXISTING:-false}"
fi

RESTORE_FLAGS=(--no-owner --no-privileges)
if [[ "${RESTORE_CLEAN:-true}" == "true" ]]; then
  RESTORE_FLAGS+=(--clean --if-exists)
fi

if [[ "$BACKUP_FILE" == *.gz ]]; then
  log "Streaming gzip archive"
  gunzip -c "$BACKUP_FILE" | pg_restore \
    -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$TARGET_DB" \
    "${RESTORE_FLAGS[@]}"
else
  log "Restoring from plain custom-format backup"
  pg_restore \
    -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$TARGET_DB" \
    "${RESTORE_FLAGS[@]}" \
    "$BACKUP_FILE"
fi

log "Restore finished for $TARGET_DB"
