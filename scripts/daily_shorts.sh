#!/usr/bin/env bash
# 매일 쇼츠 1편 — bridge /shorts/auto-latest 호출.
#
# n8n 을 쓰지 않는 이유: 재시작 시 워크플로 활성 상태가 리셋되는 문제가
# 재발해 활성 0개 상태였다 (2026-08-28 확인). 호스트 cron 이 더 단순하고
# 상태가 눈에 보인다.
#
# 심사 모드(.adsense_review)여도 영상 경로는 channel="youtube" 예외로
# 통과한다 — 사이트는 안 바뀌고 기존 라이브 글만 소재로 쓴다.
# 소재(미영상화 blog/study 글)가 떨어지면 bridge 가 skip 을 돌려주고
# 이 스크립트는 그 사실만 로그에 남긴다 — 자연스러운 정지 장치다.
set -u
BRIDGE="${NICHPROJECT_BRIDGE_URL:-http://172.17.0.1:8765}"
LOG=/tmp/daily_shorts.log

{
  echo "=== $(date '+%F %T') 시작 ==="
  resp=$(curl -s --max-time 3000 -X POST "$BRIDGE/shorts/auto-latest" \
    -H "Content-Type: application/json" \
    -d '{"lang":"ko","privacy":"public"}')
  echo "$resp"
  echo "=== $(date '+%F %T') 종료 ==="
} >> "$LOG" 2>&1
