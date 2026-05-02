#!/bin/bash
# 매시간 자동 healthcheck — 이슈 발견 시 logging
set -e
LOG="/tmp/healthcheck.log"
TS=$(date '+%Y-%m-%d %H:%M:%S')

# 1. bridge alive
BRIDGE=$(curl -s -m 5 https://callback.investiqs.net/health 2>/dev/null | grep -c "ok")

# 2. n8n container alive
N8N=$(docker ps -q --filter "name=n8n-n8n-1" 2>/dev/null | wc -l)

# 3. Active workflows
ACTIVE=$(docker exec n8n-n8n-1 n8n list:workflow --active=true --onlyId 2>/dev/null | wc -l || echo 0)

# 4. tunnel alive
TUNNEL=$(systemctl is-active cloudflared-investiqs 2>/dev/null)

# 5. disk
DISK=$(df / | tail -1 | awk '{print $5}' | tr -d '%')

echo "[$TS] bridge=$BRIDGE n8n=$N8N active=$ACTIVE/27 tunnel=$TUNNEL disk=$DISK%" >> "$LOG"

# Auto-fix: 비활성 워크플로우 감지 시 활성화
if [ "$N8N" -eq "1" ] && [ "$ACTIVE" -lt "27" ]; then
    echo "[$TS] AUTO-FIX: $((27-ACTIVE)) inactive workflows" >> "$LOG"
    docker exec n8n-n8n-1 sh -c "for f in /home/node/.n8n/workflows/*.json 2>/dev/null; do n8n update:workflow --id=\$(jq -r .id \$f) --active=true; done" 2>/dev/null || true
fi
