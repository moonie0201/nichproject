#!/bin/bash
# n8n 워크플로우 백업 — JSON으로 export, 일자별 디렉토리 저장
set -e
BACKUP_DIR="/home/mh/ocstorage/workspace/nichproject/n8n/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 워크플로우 일괄 export
docker exec n8n-n8n-1 n8n export:workflow --all --separate --output=/tmp/wf_export 2>&1 | tail -5
docker cp n8n-n8n-1:/tmp/wf_export/. "$BACKUP_DIR/"
docker exec n8n-n8n-1 rm -rf /tmp/wf_export

# DB 스냅샷
docker cp n8n-n8n-1:/home/node/.n8n/database.sqlite "$BACKUP_DIR/database.sqlite"

# 30일 이상 된 백업 자동 삭제
find /home/mh/ocstorage/workspace/nichproject/n8n/backups -type d -mtime +30 -exec rm -rf {} + 2>/dev/null

echo "Backup saved to $BACKUP_DIR"
ls "$BACKUP_DIR" | head -5
