#!/usr/bin/env bash
set -euo pipefail

umask 077

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

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
PGDATABASE="${POSTGRES_DB:-${PGDATABASE:-lang_agent}}"
PGUSER="${POSTGRES_USER:-${PGUSER:-postgres}}"
PGPASSWORD_VALUE="${PGPASSWORD:-${POSTGRES_PASSWORD:-}}"

if [[ -z "$PGPASSWORD_VALUE" ]]; then
  echo "PGPASSWORD/POSTGRES_PASSWORD must be set for backups" >&2
  exit 1
fi

export PGPASSWORD="$PGPASSWORD_VALUE"

BACKUP_ROOT="${BACKUP_DIR:-/var/backups/postgres}"
BACKUP_PREFIX="${BACKUP_PREFIX:-lang-agent}"
DAILY_RETENTION="${BACKUP_RETENTION_DAILY_DAYS:-30}"
WEEKLY_RETENTION="${BACKUP_RETENTION_WEEKLY_DAYS:-90}"
MONTHLY_RETENTION="${BACKUP_RETENTION_MONTHLY_DAYS:-365}"
WEEKLY_DAY="${BACKUP_WEEKLY_DAY:-7}"    # 1=Mon .. 7=Sun
MONTHLY_DAY="${BACKUP_MONTHLY_DAY:-01}" # 01..31

DAILY_DIR="$BACKUP_ROOT/daily"
WEEKLY_DIR="$BACKUP_ROOT/weekly"
MONTHLY_DIR="$BACKUP_ROOT/monthly"

mkdir -p "$DAILY_DIR" "$WEEKLY_DIR" "$MONTHLY_DIR"

TIMESTAMP="$(date -u +%Y%m%d_%H%M%SZ)"
BACKUP_NAME="${BACKUP_PREFIX}_${TIMESTAMP}.backup"
DAILY_PATH="$DAILY_DIR/$BACKUP_NAME"

log "Creating backup $BACKUP_NAME"
pg_dump \
  -h "$PGHOST" \
  -p "$PGPORT" \
  -U "$PGUSER" \
  -d "$PGDATABASE" \
  -F c -b -v \
  -f "$DAILY_PATH"

gzip "$DAILY_PATH"
DAILY_PATH="${DAILY_PATH}.gz"

DAY_OF_WEEK="$(date -u +%u)"
DAY_OF_MONTH="$(date -u +%d)"

if [[ "$DAY_OF_WEEK" == "$WEEKLY_DAY" ]]; then
  log "Capturing weekly snapshot"
  cp "$DAILY_PATH" "$WEEKLY_DIR/${BACKUP_PREFIX}_${TIMESTAMP}.backup.gz"
fi

if [[ "$DAY_OF_MONTH" == "$MONTHLY_DAY" ]]; then
  log "Capturing monthly snapshot"
  cp "$DAILY_PATH" "$MONTHLY_DIR/${BACKUP_PREFIX}_${TIMESTAMP}.backup.gz"
fi

cleanup_old() {
  local dir=$1
  local retention_days=$2
  [[ -d "$dir" ]] || return 0

  if [[ "$retention_days" =~ ^[0-9]+$ ]]; then
    find "$dir" -type f -name "*.backup.gz" -mtime +"$retention_days" -print -delete
  fi
}

cleanup_old "$DAILY_DIR" "$DAILY_RETENTION"
cleanup_old "$WEEKLY_DIR" "$WEEKLY_RETENTION"
cleanup_old "$MONTHLY_DIR" "$MONTHLY_RETENTION"

if [[ "${BACKUP_ENABLE_RCLONE:-false}" == "true" ]]; then
  if ! command -v rclone >/dev/null 2>&1; then
    echo "rclone not found but BACKUP_ENABLE_RCLONE=true" >&2
    exit 1
  fi

  REMOTE="${BACKUP_REMOTE:?BACKUP_REMOTE must be set when BACKUP_ENABLE_RCLONE=true}"
  REMOTE_PATH="${BACKUP_REMOTE_PATH:-backups/${BACKUP_PREFIX}/$(date -u +%Y/%m)}"
  log "Uploading $DAILY_PATH to $REMOTE:$REMOTE_PATH"
  rclone copy "$DAILY_PATH" "$REMOTE:$REMOTE_PATH/"
fi

log "Backup complete: $DAILY_PATH"
