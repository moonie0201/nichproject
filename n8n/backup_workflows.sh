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

# Active 상태 검증 + 비활성 시 자동 복구
ACTIVE_COUNT=$(docker exec n8n-n8n-1 n8n list:workflow --active=true --onlyId 2>/dev/null | grep -c . || echo "0")
TOTAL_COUNT=$(docker exec n8n-n8n-1 n8n list:workflow --onlyId 2>/dev/null | grep -c . || echo "0")

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup: $TOTAL_COUNT total, $ACTIVE_COUNT active" >> "$BACKUP_DIR/backup.log"

if [ "$ACTIVE_COUNT" -lt "$TOTAL_COUNT" ] && [ "$TOTAL_COUNT" -gt "0" ]; then
    echo "[WARNING] Inactive workflows detected — auto-reactivating via import" >> "$BACKUP_DIR/backup.log"
    # 백업된 JSON을 active=true로 재임포트하여 활성화
    for wf in "$BACKUP_DIR"/*.json; do
        [ -f "$wf" ] || continue
        fname=$(basename "$wf")
        docker cp "$wf" n8n-n8n-1:/tmp/"$fname"
        docker exec n8n-n8n-1 n8n import:workflow --input=/tmp/"$fname" >> "$BACKUP_DIR/backup.log" 2>&1
        docker exec n8n-n8n-1 rm -f /tmp/"$fname"
    done
    docker restart n8n-n8n-1 >> "$BACKUP_DIR/backup.log" 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Reactivated + restarted" >> "$BACKUP_DIR/backup.log"
fi

# 30일 이상 된 백업 자동 삭제
find /home/mh/ocstorage/workspace/nichproject/n8n/backups -type d -mtime +30 -exec rm -rf {} + 2>/dev/null

echo "Backup saved to $BACKUP_DIR (active: $ACTIVE_COUNT/$TOTAL_COUNT)"
