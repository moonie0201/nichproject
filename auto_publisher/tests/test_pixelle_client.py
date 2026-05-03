"""Pixelle-Video REST API 클라이언트 회귀 테스트.

배경: Stage 2 split-screen Shorts 의 B-roll (아래 절반 1080x960) 을
Pixelle FastAPI (~localhost:8866) 에서 받아오는 통합 클라이언트.

핵심 invariant:
1. 캐시 hit 시 네트워크 호출 0
2. 캐시 miss 시 POST /api/video/generate/sync 호출 + mp4 다운로드
3. API 다운/에러 시 None 반환 (graceful fallback → ffmpeg 단독)
4. category_pool 모드: 같은 카테고리 미리 생성된 N개 중 랜덤/라운드로빈 선택
"""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── 1. 캐시 hit 회귀 ──────────────────────────────────────

def test_get_broll_cache_hit_returns_existing_mp4(tmp_path, monkeypatch):
    """카테고리 디렉토리에 mp4 1개 이상 있으면 그걸 반환, 네트워크 호출 X."""
    monkeypatch.setenv("PIXELLE_BROLL_CACHE_DIR", str(tmp_path))
    cache_dir = tmp_path / "etf-analysis"
    cache_dir.mkdir()
    fake_mp4 = cache_dir / "broll-001.mp4"
    fake_mp4.write_bytes(b"\x00" * 1024)  # 더미

    from auto_publisher.pixelle_client import get_broll
    with patch("httpx.post") as mock_post:
        result = get_broll(category="etf-analysis", duration_sec=60)
    assert result == fake_mp4
    mock_post.assert_not_called()


# ── 2. 캐시 miss 시 API 호출 ──────────────────────────────

def test_get_broll_cache_miss_calls_pixelle_api(tmp_path, monkeypatch):
    """캐시 디렉토리 비어있으면 Pixelle API 호출 후 mp4 저장."""
    monkeypatch.setenv("PIXELLE_BROLL_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("PIXELLE_API_URL", "http://localhost:8866")

    from auto_publisher.pixelle_client import get_broll

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "video_url": "http://localhost:8866/api/files/result.mp4",
        "duration_sec": 60.0,
    }
    fake_response.raise_for_status = MagicMock()

    fake_dl = MagicMock()
    fake_dl.status_code = 200
    fake_dl.content = b"\x00" * 2048

    with patch("httpx.post", return_value=fake_response) as mock_post, \
         patch("httpx.get", return_value=fake_dl) as mock_get:
        result = get_broll(category="etf-analysis", duration_sec=60)

    assert mock_post.called, "API POST 호출 필수"
    assert result is not None
    assert result.exists()
    assert result.read_bytes() == b"\x00" * 2048


# ── 3. API 실패 시 graceful fallback ──────────────────────

def test_get_broll_api_failure_returns_none(tmp_path, monkeypatch):
    """Pixelle API 다운/timeout 시 None 반환 (호출자가 ffmpeg 단독으로 fallback)."""
    monkeypatch.setenv("PIXELLE_BROLL_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("PIXELLE_API_URL", "http://localhost:8866")

    from auto_publisher.pixelle_client import get_broll
    import httpx

    with patch("httpx.post", side_effect=httpx.ConnectError("connection refused")):
        result = get_broll(category="etf-analysis", duration_sec=60)

    assert result is None, "API 실패 시 None 반환 (fallback 위해)"


# ── 4. PIXELLE_ENABLED=false 면 즉시 None ─────────────────

def test_get_broll_disabled_returns_none(tmp_path, monkeypatch):
    """PIXELLE_ENABLED=false 환경 변수면 캐시 확인도 안 하고 즉시 None."""
    monkeypatch.setenv("PIXELLE_BROLL_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("PIXELLE_ENABLED", "false")

    from auto_publisher.pixelle_client import get_broll
    with patch("httpx.post") as mock_post:
        result = get_broll(category="etf-analysis", duration_sec=60)
    assert result is None
    mock_post.assert_not_called()


# ── 5. 카테고리 풀 라운드로빈 ─────────────────────────────

def test_get_broll_category_pool_rotates(tmp_path, monkeypatch):
    """카테고리 디렉토리에 mp4 여러 개면 호출마다 다른 파일 반환 (라운드로빈/랜덤)."""
    monkeypatch.setenv("PIXELLE_BROLL_CACHE_DIR", str(tmp_path))
    cache_dir = tmp_path / "etf-analysis"
    cache_dir.mkdir()
    files = [cache_dir / f"broll-{i:03d}.mp4" for i in range(5)]
    for f in files:
        f.write_bytes(b"\x00")

    from auto_publisher.pixelle_client import get_broll
    seen = set()
    for _ in range(10):
        r = get_broll(category="etf-analysis", duration_sec=60)
        if r:
            seen.add(r.name)
    # 5개 중 최소 2개 이상 다른 파일이 선택되어야 함
    assert len(seen) >= 2, f"카테고리 풀 회전 안 됨: {seen}"
