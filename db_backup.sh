#!/bin/sh
set -eu

SOURCE_DB="${SOURCE_DB:-/home/lst1/lst-onsite-availability/db_data_prod/db.sqlite3}"
DEST_DIR="${DEST_DIR:-/home/lst1/database/onsite-calendar/db}"
DEST_DB="$DEST_DIR/db.sqlite3"

if [ ! -f "$SOURCE_DB" ]; then
    printf 'Database source not found: %s\n' "$SOURCE_DB" >&2
    exit 1
fi

mkdir -p "$DEST_DIR"
python3 - "$SOURCE_DB" "$DEST_DB" <<'PY'
import os
import sqlite3
import sys
import tempfile

source_path, destination_path = sys.argv[1:]
destination_dir = os.path.dirname(destination_path)
fd, temporary_path = tempfile.mkstemp(prefix=".db.sqlite3.", suffix=".tmp", dir=destination_dir)
os.close(fd)
try:
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    destination = sqlite3.connect(temporary_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    os.replace(temporary_path, destination_path)
except Exception:
    try:
        os.unlink(temporary_path)
    except FileNotFoundError:
        pass
    raise
PY
