#!/usr/bin/env bash
set -Eeuo pipefail

# Daily SQLite backup for the production Onsite Calendar.
# Layout:
#   /home/lst1/database/OnsiteCalendar/db.sqlite3          latest copy
#   /home/lst1/database/OnsiteCalendar.YYYYMMDD/db.sqlite3 dated copies

PROD_DB_DIR="${PROD_DB_DIR:-/home/lst1/lst-onsite-availability/db_data_prod}"
SOURCE_DB="${SOURCE_DB:-${PROD_DB_DIR}/db.sqlite3}"
BACKUP_ROOT="${BACKUP_ROOT:-/home/lst1/database}"
LATEST_DIR="${BACKUP_ROOT}/OnsiteCalendar"
LATEST_DB="${LATEST_DIR}/db.sqlite3"
DATE_TODAY="$(date +%Y%m%d)"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

if [[ ! -f "$SOURCE_DB" ]]; then
    log "ERROR: production database not found: $SOURCE_DB" >&2
    exit 1
fi

mkdir -p "$BACKUP_ROOT" "$LATEST_DIR"

# Preserve the previous latest snapshot under the date it represents. The
# marker makes reruns during the same day safe and avoids archiving today's
# snapshot as yesterday's.
if [[ -f "$LATEST_DB" ]]; then
    if [[ -f "${LATEST_DIR}/.backup-date" ]]; then
        PREVIOUS_DATE="$(<"${LATEST_DIR}/.backup-date")"
    else
        PREVIOUS_DATE="$(date -r "$LATEST_DB" +%Y%m%d)"
    fi

    if [[ "$PREVIOUS_DATE" =~ ^[0-9]{8}$ && "$PREVIOUS_DATE" < "$DATE_TODAY" ]]; then
        DATED_PATH="${BACKUP_ROOT}/OnsiteCalendar.${PREVIOUS_DATE}"
        if [[ ! -e "$DATED_PATH" ]]; then
            DATED_TMP="$(mktemp -d "${BACKUP_ROOT}/.OnsiteCalendar.${PREVIOUS_DATE}.XXXXXX")"
            cp -p "$LATEST_DB" "${DATED_TMP}/db.sqlite3"
            printf '%s\n' "$PREVIOUS_DATE" > "${DATED_TMP}/.backup-date"
            mv "$DATED_TMP" "$DATED_PATH"
            log "Archived previous snapshot: ${DATED_PATH}/db.sqlite3"
        else
            log "Dated snapshot already exists; keeping it: $DATED_PATH"
        fi
    fi
fi

# SQLite's online backup API takes a consistent snapshot even if the app is
# writing to the database while this script runs.
TEMP_DB="$(mktemp "${LATEST_DIR}/.db.sqlite3.XXXXXX")"
cleanup() {
    [[ -z "${TEMP_DB:-}" || ! -e "$TEMP_DB" ]] || rm -f -- "$TEMP_DB"
}
trap cleanup EXIT
python3 - "$SOURCE_DB" "$TEMP_DB" <<'PY'
import sqlite3
import sys

source_path, destination_path = sys.argv[1:]
source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
destination = sqlite3.connect(destination_path)
try:
    source.backup(destination)
    result = destination.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise RuntimeError(f"SQLite integrity_check failed: {result}")
finally:
    destination.close()
    source.close()
PY
mv -f -- "$TEMP_DB" "$LATEST_DB"
TEMP_DB=""
MARKER_TMP="${LATEST_DIR}/.backup-date.tmp"
printf '%s\n' "$DATE_TODAY" > "$MARKER_TMP"
mv -f -- "$MARKER_TMP" "${LATEST_DIR}/.backup-date"
log "Latest database backup refreshed: $LATEST_DB"

# Keep the latest copy and dated snapshots from the last seven days. Removing
# a dated directory also removes its db.sqlite3; matching dated files are
# cleaned up too in case an older script created that layout.
CUTOFF_DATE="$(date -d '7 days ago' +%Y%m%d)"
shopt -s nullglob
for PATH_TO_REMOVE in "${BACKUP_ROOT}"/OnsiteCalendar.????????; do
    DATE_SUFFIX="${PATH_TO_REMOVE##*.}"
    [[ "$DATE_SUFFIX" =~ ^[0-9]{8}$ ]] || continue
    if [[ "$DATE_SUFFIX" < "$CUTOFF_DATE" ]]; then
        rm -rf -- "$PATH_TO_REMOVE"
        log "Removed backup older than seven days: $PATH_TO_REMOVE"
    fi
done
log "Backup completed successfully; dated retention starts at ${CUTOFF_DATE}."
