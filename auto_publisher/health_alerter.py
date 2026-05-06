"""헬스 alerter — 운영 silent fail 감지 + Discord 알림.

배경 (2026-05-02 ~ 05-06 incident):
- TikTok refresh token 60일 만료 → invalid_grant
- n8n cron 등록 실패 → 4일간 발행 0건
- 위 두 이슈 모두 사용자가 직접 발견할 때까지 silent

이 모듈은:
1. token 만료 임박 (default 7일 이내) 감지
2. publish 정체 (default 24h 초과) 감지
3. Discord webhook 으로 즉시 알림
4. ENV 토글 (HEALTH_ALERTER_ENABLED)
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def check_token_expiry(token_file: Path, threshold_days: int = 7) -> Optional[str]:
    """TikTok refresh_expires_at 이 threshold 이내면 ALERT 메시지 반환.

    Returns:
        str: ALERT 메시지 (만료 임박 또는 이미 만료)
        None: 안전 또는 데이터 없음 (graceful)
    """
    if not token_file.exists():
        return None
    try:
        token = json.loads(token_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    refresh_at = token.get("refresh_expires_at")
    if refresh_at is None:
        return None
    delta_sec = refresh_at - time.time()
    delta_days = delta_sec / 86400
    if delta_days < 0:
        return f"⚠️ TikTok refresh token 이미 만료 ({abs(delta_days):.1f}일 경과) — 즉시 재인증 필요"
    if delta_days <= threshold_days:
        return f"⚠️ TikTok refresh token 만료 임박 ({delta_days:.1f}일 후) — 재인증 준비"
    return None


def _read_history_timestamps(history_file: Path) -> list[float]:
    """publish_history.json 에서 timestamp 추출. 다양한 형식 지원."""
    if not history_file.exists():
        return []
    try:
        data = json.loads(history_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = data if isinstance(data, list) else (
        list(data.values()) if isinstance(data, dict) else [])
    timestamps: list[float] = []
    for r in items:
        if not isinstance(r, dict):
            continue
        ts = r.get("_timestamp")
        if isinstance(ts, (int, float)):
            timestamps.append(float(ts))
            continue
        # ISO string fallback
        for key in ("published_at", "date", "timestamp"):
            v = r.get(key)
            if isinstance(v, str) and len(v) >= 10:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                    timestamps.append(dt.timestamp())
                    break
                except ValueError:
                    pass
    return timestamps


def check_publish_stagnation(history_file: Path, threshold_hours: int = 24,
                             now: Optional[float] = None) -> Optional[str]:
    """마지막 publish 가 threshold_hours 초과 정체면 ALERT 반환."""
    if now is None:
        now = time.time()
    timestamps = _read_history_timestamps(history_file)
    if not timestamps:
        return f"⚠️ 발행 이력 비어있음 — n8n cron 또는 bridge_api 점검 필요"
    last = max(timestamps)
    age_hours = (now - last) / 3600
    if age_hours > threshold_hours:
        return f"⚠️ 마지막 발행 후 {age_hours:.1f}시간 경과 (정체) — cron/bridge 점검"
    return None


def send_discord_alert(webhook_url: str, alerts: list[str]) -> bool:
    """Discord webhook 으로 alerts 전송. 빈 alerts 또는 webhook 없으면 no-op."""
    if not webhook_url or not alerts:
        return False
    body = {
        "username": "investiqs.net 헬스 alerter",
        "content": "🚨 **헬스 점검 알림** 🚨\n" + "\n".join(f"- {a}" for a in alerts),
    }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as e:
        logger.warning(f"Discord webhook 호출 실패: {e}")
        return False
    logger.info(f"Discord alert 전송: {len(alerts)}개")
    return True


def run_health_check(token_file: Path, history_file: Path,
                     token_threshold_days: int = 7,
                     publish_threshold_hours: int = 24) -> dict:
    """전체 헬스 점검 + 결과 dict 반환. enabled=false 면 즉시 종료."""
    enabled = os.getenv("HEALTH_ALERTER_ENABLED", "true").lower() not in ("false", "0", "no")
    if not enabled:
        return {"enabled": False, "alerts_count": 0, "alerts": []}

    alerts: list[str] = []
    token_alert = check_token_expiry(token_file, token_threshold_days)
    if token_alert:
        alerts.append(token_alert)
    publish_alert = check_publish_stagnation(history_file, publish_threshold_hours)
    if publish_alert:
        alerts.append(publish_alert)

    sent = False
    if alerts:
        webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
        sent = send_discord_alert(webhook_url=webhook, alerts=alerts)

    return {"enabled": True, "alerts_count": len(alerts), "alerts": alerts, "sent": sent}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    repo = Path("/home/mh/ocstorage/workspace/nichproject")
    result = run_health_check(
        token_file=repo / ".tiktok_secrets" / "token.json",
        history_file=repo / "auto_publisher" / "data" / "published_history.json",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["alerts_count"] == 0 else 1)
