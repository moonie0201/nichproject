"""헬스 alerter 회귀 테스트.

요구사항:
1. token 만료 임박 감지 (refresh_expires_at < 7일 → ALERT)
2. publish 정체 감지 (마지막 publish > 24시간 → ALERT)
3. bridge_api 응답 없음 (HTTP timeout/connect error → ALERT)
4. Discord webhook 호출 (DISCORD_WEBHOOK_URL 설정 시)
5. ALERT 없으면 webhook 호출 X (스팸 방지)
6. ENV 토글 (HEALTH_ALERTER_ENABLED)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_check_token_expiry_alerts_when_under_7days(tmp_path):
    """refresh_expires_at 이 7일 이내면 ALERT."""
    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({
        "access_token": "ak", "refresh_token": "rk",
        "expires_at": time.time() + 3600,
        "refresh_expires_at": time.time() + 86400 * 5,  # 5일 후
    }))
    from auto_publisher.health_alerter import check_token_expiry
    alert = check_token_expiry(token_file, threshold_days=7)
    assert alert is not None
    assert "5" in alert or "임박" in alert or "expir" in alert.lower()


def test_check_token_expiry_no_alert_when_far_future(tmp_path):
    """refresh_expires_at 이 30일 후면 ALERT 없음."""
    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({
        "access_token": "ak", "refresh_token": "rk",
        "expires_at": time.time() + 3600,
        "refresh_expires_at": time.time() + 86400 * 30,
    }))
    from auto_publisher.health_alerter import check_token_expiry
    assert check_token_expiry(token_file, threshold_days=7) is None


def test_check_token_expiry_alerts_when_already_expired(tmp_path):
    """이미 만료됐으면 ALERT (음수 days)."""
    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({
        "access_token": "ak", "refresh_token": "rk",
        "expires_at": time.time() - 100,
        "refresh_expires_at": time.time() - 86400 * 3,  # 3일 전 만료
    }))
    from auto_publisher.health_alerter import check_token_expiry
    alert = check_token_expiry(token_file, threshold_days=7)
    assert alert is not None
    assert "만료" in alert or "expired" in alert.lower()


def test_check_token_expiry_no_data_returns_none(tmp_path):
    """token.json 없거나 refresh_expires_at 없으면 None (graceful)."""
    from auto_publisher.health_alerter import check_token_expiry
    # 파일 자체 없음
    assert check_token_expiry(tmp_path / "missing.json") is None
    # refresh_expires_at 키 없음 (legacy)
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"access_token": "ak"}))
    assert check_token_expiry(legacy) is None


def test_check_publish_stagnation_alerts_after_24h(tmp_path):
    """마지막 publish 가 24h 초과면 ALERT."""
    history = tmp_path / "publish_history.json"
    old_ts = (time.time() - 86400 * 2)  # 2일 전
    history.write_text(json.dumps([{
        "slug": "test", "published_at": "2026-05-04T00:00:00",
        "_timestamp": old_ts,
    }]))
    from auto_publisher.health_alerter import check_publish_stagnation
    alert = check_publish_stagnation(history, threshold_hours=24, now=time.time())
    assert alert is not None
    assert "24" in alert or "stagnant" in alert.lower() or "정체" in alert or "발행" in alert


def test_check_publish_stagnation_no_alert_when_recent(tmp_path):
    """마지막 publish 가 1시간 전이면 ALERT 없음."""
    history = tmp_path / "publish_history.json"
    history.write_text(json.dumps([{
        "slug": "test", "_timestamp": time.time() - 3600,
    }]))
    from auto_publisher.health_alerter import check_publish_stagnation
    assert check_publish_stagnation(history, threshold_hours=24, now=time.time()) is None


def test_check_publish_stagnation_empty_history(tmp_path):
    """빈 history 또는 파일 없으면 ALERT (publish 0건)."""
    from auto_publisher.health_alerter import check_publish_stagnation
    alert = check_publish_stagnation(tmp_path / "empty.json", threshold_hours=24,
                                     now=time.time())
    assert alert is not None  # 발행 이력 없음 자체가 문제


def test_send_discord_alert_calls_webhook():
    """Discord webhook URL 설정 시 alert 전송."""
    from auto_publisher.health_alerter import send_discord_alert
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: None
        mock_resp.read.return_value = b'{"ok":true}'
        mock_urlopen.return_value = mock_resp
        result = send_discord_alert(
            webhook_url="https://discord.com/api/webhooks/test",
            alerts=["TikTok 토큰 5일 후 만료", "발행 24h 0건"],
        )
    assert result is True
    assert mock_urlopen.call_count == 1


def test_send_discord_alert_no_webhook_returns_false():
    """webhook URL 빈 값이면 False (no-op)."""
    from auto_publisher.health_alerter import send_discord_alert
    with patch("urllib.request.urlopen") as mock_urlopen:
        result = send_discord_alert(webhook_url="", alerts=["test"])
    assert result is False
    mock_urlopen.assert_not_called()


def test_send_discord_alert_empty_alerts_skips():
    """alerts 비어있으면 webhook 호출 X (스팸 방지)."""
    from auto_publisher.health_alerter import send_discord_alert
    with patch("urllib.request.urlopen") as mock_urlopen:
        result = send_discord_alert(webhook_url="https://x", alerts=[])
    assert result is False
    mock_urlopen.assert_not_called()


def test_run_health_check_aggregates_alerts(tmp_path, monkeypatch):
    """run_health_check() 가 모든 점검 모아서 webhook 1번 호출."""
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test")
    monkeypatch.setenv("HEALTH_ALERTER_ENABLED", "true")

    # token 만료 임박
    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({
        "access_token": "ak",
        "refresh_expires_at": time.time() + 86400 * 3,  # 3일 후
    }))
    # publish 24h 정체
    history = tmp_path / "history.json"
    history.write_text(json.dumps([{"_timestamp": time.time() - 86400 * 2}]))

    from auto_publisher.health_alerter import run_health_check
    with patch("auto_publisher.health_alerter.send_discord_alert", return_value=True) as mock_send:
        result = run_health_check(token_file=token_file, history_file=history)

    assert result["alerts_count"] >= 2
    assert mock_send.call_count == 1
    sent_alerts = mock_send.call_args.kwargs.get("alerts") or mock_send.call_args.args[1]
    assert len(sent_alerts) >= 2


def test_run_health_check_disabled_skips_all(tmp_path, monkeypatch):
    """HEALTH_ALERTER_ENABLED=false 면 알림 스킵."""
    monkeypatch.setenv("HEALTH_ALERTER_ENABLED", "false")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://x")
    from auto_publisher.health_alerter import run_health_check
    with patch("auto_publisher.health_alerter.send_discord_alert") as mock_send:
        result = run_health_check(token_file=tmp_path / "x", history_file=tmp_path / "y")
    assert result["enabled"] is False
    mock_send.assert_not_called()
