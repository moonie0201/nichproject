"""stock B-roll 캐시 LRU 회전 회귀 테스트.

정책:
- 카테고리당 최대 STOCK_BROLL_MAX_PER_CATEGORY 개 (default 10)
- 새 다운로드 후 한도 초과 시 가장 오래 안 쓴 (atime 기준) mp4 삭제
- 캐시 hit 시 선택된 파일의 atime 갱신 → LRU 보호
- 한도 무시: STOCK_BROLL_MAX_PER_CATEGORY=999 (사실상 무제한)
"""
from __future__ import annotations
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def _make_mp4(path: Path, atime_offset_sec: float = 0):
    """더미 mp4 생성. atime/mtime 을 현재시간 - offset 으로 설정."""
    path.write_bytes(b"\x00" * 1024)
    t = time.time() - atime_offset_sec
    os.utime(path, (t, t))


def test_evict_oldest_when_over_limit(tmp_path, monkeypatch):
    """max=3 인데 4번째 다운로드되면 가장 오래된 1개 삭제."""
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("STOCK_BROLL_MAX_PER_CATEGORY", "3")

    cdir = tmp_path / "etf-analysis"
    cdir.mkdir()
    # 기존 3개 (각 다른 atime)
    _make_mp4(cdir / "old.mp4", atime_offset_sec=86400 * 30)  # 30일 전
    _make_mp4(cdir / "mid.mp4", atime_offset_sec=86400 * 7)   # 7일 전
    _make_mp4(cdir / "new.mp4", atime_offset_sec=3600)        # 1시간 전

    from auto_publisher.stock_broll import get_stock_broll
    search_resp = MagicMock(status_code=200)
    search_resp.raise_for_status = MagicMock()
    search_resp.json.return_value = {
        "videos": [{"id": 7777, "video_files": [
            {"link": "https://pexels.com/v.mp4", "width": 1080, "height": 1920, "quality": "hd"}
        ]}]
    }
    dl_resp = MagicMock(status_code=200, content=b"\xff" * 4096)
    dl_resp.raise_for_status = MagicMock()

    with patch("httpx.get", side_effect=[search_resp, dl_resp]):
        # 캐시 hit 막기 위해 mock select to return None
        with patch("auto_publisher.stock_broll._select_from_pool", return_value=None):
            result = get_stock_broll(category="etf-analysis", duration_sec=60)

    assert result is not None
    files = sorted(cdir.glob("*.mp4"))
    # 새 파일 추가됐고, 가장 오래된 'old.mp4' 가 삭제되어야 함
    names = [f.name for f in files]
    assert "old.mp4" not in names, f"oldest 파일이 삭제 안 됨: {names}"
    assert "mid.mp4" in names
    assert "new.mp4" in names
    assert "pexels-7777.mp4" in names
    assert len(files) == 3, f"max=3 인데 {len(files)}개 남음"


def test_no_eviction_when_under_limit(tmp_path, monkeypatch):
    """max=10 이고 현재 2개면 새 다운로드 후 3개 모두 보존."""
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("STOCK_BROLL_MAX_PER_CATEGORY", "10")

    cdir = tmp_path / "crypto"
    cdir.mkdir()
    _make_mp4(cdir / "a.mp4", atime_offset_sec=86400 * 30)
    _make_mp4(cdir / "b.mp4", atime_offset_sec=86400)

    from auto_publisher.stock_broll import get_stock_broll
    search_resp = MagicMock(status_code=200)
    search_resp.raise_for_status = MagicMock()
    search_resp.json.return_value = {
        "videos": [{"id": 5555, "video_files": [
            {"link": "https://pexels.com/v.mp4", "width": 1080, "height": 1920, "quality": "hd"}
        ]}]
    }
    dl_resp = MagicMock(status_code=200, content=b"\xff" * 4096)
    dl_resp.raise_for_status = MagicMock()

    with patch("httpx.get", side_effect=[search_resp, dl_resp]):
        with patch("auto_publisher.stock_broll._select_from_pool", return_value=None):
            get_stock_broll(category="crypto", duration_sec=60)

    files = sorted(cdir.glob("*.mp4"))
    assert len(files) == 3, f"한도 미달인데 삭제됨: {[f.name for f in files]}"


def test_unlimited_when_max_is_zero_or_negative(tmp_path, monkeypatch):
    """STOCK_BROLL_MAX_PER_CATEGORY=0 이면 사실상 무제한 (삭제 안 함)."""
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("STOCK_BROLL_MAX_PER_CATEGORY", "0")

    cdir = tmp_path / "dividend"
    cdir.mkdir()
    for i in range(15):
        _make_mp4(cdir / f"file_{i:02d}.mp4", atime_offset_sec=86400 * (i + 1))

    from auto_publisher.stock_broll import get_stock_broll
    search_resp = MagicMock(status_code=200)
    search_resp.raise_for_status = MagicMock()
    search_resp.json.return_value = {
        "videos": [{"id": 1111, "video_files": [
            {"link": "https://pexels.com/v.mp4", "width": 1080, "height": 1920, "quality": "hd"}
        ]}]
    }
    dl_resp = MagicMock(status_code=200, content=b"\xff" * 4096)
    dl_resp.raise_for_status = MagicMock()

    with patch("httpx.get", side_effect=[search_resp, dl_resp]):
        with patch("auto_publisher.stock_broll._select_from_pool", return_value=None):
            get_stock_broll(category="dividend", duration_sec=60)

    files = sorted(cdir.glob("*.mp4"))
    assert len(files) == 16, f"무제한인데 정리됨: {len(files)}개"


def test_cache_hit_updates_atime(tmp_path, monkeypatch):
    """캐시 hit 시 선택된 파일의 atime 이 갱신되어 LRU 보호받아야 함."""
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))

    cdir = tmp_path / "tax"
    cdir.mkdir()
    target = cdir / "tax-001.mp4"
    _make_mp4(target, atime_offset_sec=86400 * 30)  # 30일 전
    old_atime = target.stat().st_atime

    from auto_publisher.stock_broll import get_stock_broll
    with patch("httpx.get") as mock_get:
        result = get_stock_broll(category="tax", duration_sec=60)

    assert result == target
    mock_get.assert_not_called()  # 네트워크 안 탐
    new_atime = target.stat().st_atime
    assert new_atime > old_atime, f"atime 갱신 안 됨 (old={old_atime}, new={new_atime})"
