#!/bin/bash
# Rotate logs larger than 50MB — gzip + archive, truncate original (preserves file handle)
set -e

ARCHIVE_DIR="/home/mh/ocstorage/workspace/nichproject/.omc/log_archive/$(date +%Y%m)"
mkdir -p "$ARCHIVE_DIR"

LOGS=(
  /tmp/bridge.log
  /tmp/n8n_backup.log
  /home/mh/ocstorage/workspace/nichproject/n8n/bridge.log
  /home/mh/ocstorage/workspace/nichproject/auto_publisher/auto_publisher.log
)

ROTATED=0

for log in "${LOGS[@]}"; do
  [ -f "$log" ] || continue
  SIZE=$(stat -c%s "$log" 2>/dev/null || echo 0)
  if [ "$SIZE" -gt 52428800 ]; then  # 50MB
    DEST="$ARCHIVE_DIR/$(basename "$log")-$(date +%Y%m%d-%H%M%S).gz"
    gzip -c "$log" > "$DEST"
    : > "$log"  # truncate — preserves open file handles held by running processes
    echo "Rotated: $log -> $DEST"
    ROTATED=$((ROTATED + 1))
  fi
done

# Remove archives older than 30 days
find /home/mh/ocstorage/workspace/nichproject/.omc/log_archive -type f -mtime +30 -delete 2>/dev/null

echo "Done. Files rotated: $ROTATED"
