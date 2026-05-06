"""B-roll pool (다수) 회귀 테스트.

목적: split-screen Shorts 의 아래 절반에 N개 B-roll 17초씩 ladder 전환
시청자 지루함 방지 (현재 88초 동안 같은 영상 1개 → 5개 17초씩).
"""
from __future__ import annotations
from unittest.mock import patch
import pytest


def _make_dummy(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * 1024)


def test_get_broll_pool_returns_up_to_n_from_cache(tmp_path, monkeypatch):
    """캐시에 N개 이상 있으면 정확히 N개 반환."""
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))
    cdir = tmp_path / "etf-analysis"
    for i in range(10):
        _make_dummy(cdir / f"pexels-{i:03d}.mp4")
    from auto_publisher.stock_broll import get_broll_pool
    pool = get_broll_pool(category="etf-analysis", n=5)
    assert isinstance(pool, list)
    assert len(pool) == 5
    assert all(p.exists() for p in pool)


def test_get_broll_pool_returns_all_when_cache_under_n(tmp_path, monkeypatch):
    """캐시에 N개 미만이면 가용한 만큼 (no error)."""
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))
    cdir = tmp_path / "crypto"
    for i in range(2):
        _make_dummy(cdir / f"pexels-{i:03d}.mp4")
    from auto_publisher.stock_broll import get_broll_pool
    pool = get_broll_pool(category="crypto", n=5)
    assert len(pool) == 2
    assert all(p.exists() for p in pool)


def test_get_broll_pool_no_cache_no_keys_returns_empty(tmp_path, monkeypatch):
    """캐시 비어있고 API 키도 없으면 빈 리스트."""
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))
    from auto_publisher.stock_broll import get_broll_pool
    pool = get_broll_pool(category="weekly", n=5)
    assert pool == []


def test_get_broll_pool_distinct_files(tmp_path, monkeypatch):
    """반환된 N개는 중복 없음 (같은 파일 2번 X)."""
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))
    cdir = tmp_path / "default"
    for i in range(8):
        _make_dummy(cdir / f"pexels-{i:03d}.mp4")
    from auto_publisher.stock_broll import get_broll_pool
    pool = get_broll_pool(category="default", n=5)
    assert len(set(p.name for p in pool)) == 5


def test_get_broll_pool_n_zero_returns_empty(tmp_path, monkeypatch):
    """n=0 이면 빈 리스트."""
    monkeypatch.setenv("STOCK_BROLL_CACHE_DIR", str(tmp_path))
    cdir = tmp_path / "tax"
    for i in range(3):
        _make_dummy(cdir / f"pexels-{i:03d}.mp4")
    from auto_publisher.stock_broll import get_broll_pool
    pool = get_broll_pool(category="tax", n=0)
    assert pool == []
