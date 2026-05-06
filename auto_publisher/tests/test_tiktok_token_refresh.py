"""TikTok 토큰 refresh_expires_at 추적 회귀 테스트.

배경 (2026-05-02 incident):
- TikTok OAuth 응답엔 `refresh_expires_in` (보통 60일) 포함
- 우리 코드가 이걸 무시 → token.json 에 refresh_expires_at None
- 60일 후 갑자기 invalid_grant 에러 → 발행 chain 정지 4일

이 테스트는:
1. 신규 OAuth 발급 시 refresh_expires_at 저장
2. refresh 시 refresh_expires_at 갱신
3. 응답에 refresh_expires_in 없을 때도 graceful 처리 (None 유지)
"""
from __future__ import annotations

import json
import time
from unittest.mock import patch, MagicMock

import pytest


def _mock_token_response(expires_in: int = 86400, refresh_expires_in: int | None = 5184000,
                         access_token: str = "ak_test", refresh_token: str = "rk_test",
                         open_id: str = "open_test") -> bytes:
    """TikTok OAuth 응답 mock (JSON)."""
    body = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "open_id": open_id,
        "scope": "user.info.basic,video.upload,video.publish",
        "token_type": "Bearer",
    }
    if refresh_expires_in is not None:
        body["refresh_expires_in"] = refresh_expires_in
    return json.dumps(body).encode()


def test_oauth_setup_saves_refresh_expires_at(tmp_path, monkeypatch):
    """tiktok_auth_setup(code=...) 호출 시 refresh_expires_at 도 저장돼야 함."""
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    token_file = tmp_path / "token.json"
    monkeypatch.setattr("auto_publisher.video_uploader.TIKTOK_SECRETS_DIR", tmp_path)
    monkeypatch.setattr("auto_publisher.video_uploader.TIKTOK_TOKEN_FILE", token_file)

    from auto_publisher import video_uploader

    fake_resp = MagicMock()
    fake_resp.read.return_value = _mock_token_response(refresh_expires_in=5184000)
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = lambda *a: None

    with patch("urllib.request.urlopen", return_value=fake_resp):
        before = time.time()
        video_uploader.tiktok_auth_setup(code="auth_code_123")
        after = time.time()

    saved = json.loads(token_file.read_text())
    assert "refresh_expires_at" in saved, f"refresh_expires_at 키 누락: {saved}"
    assert before + 5184000 - 1 <= saved["refresh_expires_at"] <= after + 5184000 + 1


def test_refresh_updates_refresh_expires_at(tmp_path, monkeypatch):
    """tiktok_get_access_token() refresh 흐름에서 refresh_expires_at 갱신돼야 함."""
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    token_file = tmp_path / "token.json"
    monkeypatch.setattr("auto_publisher.video_uploader.TIKTOK_SECRETS_DIR", tmp_path)
    monkeypatch.setattr("auto_publisher.video_uploader.TIKTOK_TOKEN_FILE", token_file)

    # 만료 임박한 기존 token 저장 (refresh_expires_at 없음 = 옛날 결함 케이스)
    token_file.write_text(json.dumps({
        "access_token": "old_ak",
        "refresh_token": "old_rk",
        "expires_at": time.time() - 100,  # 만료
        "open_id": "open_x",
    }))

    from auto_publisher import video_uploader

    fake_resp = MagicMock()
    fake_resp.read.return_value = _mock_token_response(
        refresh_expires_in=5184000, access_token="new_ak", refresh_token="new_rk")
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = lambda *a: None

    with patch("urllib.request.urlopen", return_value=fake_resp):
        before = time.time()
        video_uploader._load_tiktok_credentials()
        after = time.time()

    saved = json.loads(token_file.read_text())
    assert saved["access_token"] == "new_ak"
    assert "refresh_expires_at" in saved
    assert before + 5184000 - 1 <= saved["refresh_expires_at"] <= after + 5184000 + 1


def test_refresh_omits_field_when_response_missing(tmp_path, monkeypatch):
    """응답에 refresh_expires_in 없으면 refresh_expires_at 안 저장 (None 또는 키 없음)."""
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    token_file = tmp_path / "token.json"
    monkeypatch.setattr("auto_publisher.video_uploader.TIKTOK_SECRETS_DIR", tmp_path)
    monkeypatch.setattr("auto_publisher.video_uploader.TIKTOK_TOKEN_FILE", token_file)

    from auto_publisher import video_uploader

    fake_resp = MagicMock()
    fake_resp.read.return_value = _mock_token_response(refresh_expires_in=None)
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = lambda *a: None

    with patch("urllib.request.urlopen", return_value=fake_resp):
        video_uploader.tiktok_auth_setup(code="auth_code_xyz")

    saved = json.loads(token_file.read_text())
    # 응답에 없으면 키 자체가 없거나 None 이어야 함 (가짜 값 만들지 않음)
    assert saved.get("refresh_expires_at") is None
