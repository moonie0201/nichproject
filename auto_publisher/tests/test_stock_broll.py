"""Pexels API stock B-roll 클라이언트 회귀 테스트.

Pexels Videos API: https://api.pexels.com/videos/search?query=...
- 무료 + 상업 사용 OK (attribution 권장)
- 200 req/h, API key 필요
- Response: videos[].video_files[].link (mp4 URL)

핵심 invariant:
1. 캐시 hit 시 네트워크 호출 0 (pixelle_client 와 동일 패턴)
2. 캐시 miss 시 Pexels API 호출 + mp4 다운로드 + 카테고리 디렉토리 저장
3. PEXELS_API_KEY 미설정 시 즉시 None
4. API 에러 시 None 반환 (graceful fallback)
5. 카테고리 → 검색어 매핑
"""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_get_stock_broll_no_api_key_returns_none(tmp_path, monkeypatch):
    """PEXELS_API_KEY 미설정 시 즉시 None (네트워크 호출 X)."""
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))

    from auto_publisher.stock_broll import get_stock_broll
    with patch("httpx.get") as mock_get:
        result = get_stock_broll(category="etf-analysis", duration_sec=60)
    assert result is None
    mock_get.assert_not_called()


def test_get_stock_broll_cache_hit(tmp_path, monkeypatch):
    """카테고리 캐시 디렉토리에 mp4 있으면 네트워크 없이 반환."""
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))
    cdir = tmp_path / "etf-analysis"
    cdir.mkdir()
    cached = cdir / "pexels-12345.mp4"
    cached.write_bytes(b"\x00" * 1024)

    from auto_publisher.stock_broll import get_stock_broll
    with patch("httpx.get") as mock_get:
        result = get_stock_broll(category="etf-analysis", duration_sec=60)
    assert result == cached
    mock_get.assert_not_called()


def test_get_stock_broll_api_call_downloads_mp4(tmp_path, monkeypatch):
    """캐시 miss 시 Pexels search + 첫 결과 mp4 다운로드 + 캐시 저장."""
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))

    from auto_publisher.stock_broll import get_stock_broll

    # /videos/search 응답
    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.raise_for_status = MagicMock()
    search_resp.json.return_value = {
        "videos": [
            {
                "id": 99999,
                "video_files": [
                    {"link": "https://videos.pexels.com/video-files/99999/test.mp4",
                     "width": 1080, "height": 1920, "quality": "hd"}
                ],
            }
        ]
    }
    # mp4 다운로드 응답
    dl_resp = MagicMock()
    dl_resp.status_code = 200
    dl_resp.raise_for_status = MagicMock()
    dl_resp.content = b"\xff" * 4096

    with patch("httpx.get", side_effect=[search_resp, dl_resp]) as mock_get:
        result = get_stock_broll(category="etf-analysis", duration_sec=60)

    assert result is not None
    assert result.exists()
    assert result.read_bytes() == b"\xff" * 4096
    # 첫 호출은 Pexels API search
    assert "api.pexels.com" in str(mock_get.call_args_list[0])


def test_get_stock_broll_api_failure_returns_none(tmp_path, monkeypatch):
    """API 에러 시 None (호출자 fallback)."""
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))

    from auto_publisher.stock_broll import get_stock_broll
    import httpx
    with patch("httpx.get", side_effect=httpx.ConnectError("timeout")):
        result = get_stock_broll(category="etf-analysis", duration_sec=60)
    assert result is None


def test_category_to_query_mapping():
    """카테고리 → Pexels 검색 키워드 매핑."""
    from auto_publisher.stock_broll import category_to_query
    assert "finance" in category_to_query("etf-analysis").lower() or \
           "stock" in category_to_query("etf-analysis").lower() or \
           "money" in category_to_query("etf-analysis").lower()
    assert category_to_query("market-wrap") != category_to_query("etf-analysis")
    # 알 수 없는 카테고리도 generic finance 키워드 반환
    assert category_to_query("unknown-xyz") is not None
