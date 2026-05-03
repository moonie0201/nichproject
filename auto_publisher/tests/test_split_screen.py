"""apply_split_screen_broll 회귀 — 1080x1920 입력 + B-roll → 위/아래 분할 mp4."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import shutil
import subprocess

import pytest


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg 없으면 시각 합성 테스트 의미 없음",
)


def _make_dummy_video(out: Path, width: int, height: int, dur: float = 1.0,
                      color: str = "black") -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"color=c={color}:size={width}x{height}:duration={dur}:rate=30",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
         "-pix_fmt", "yuv420p", str(out)],
        capture_output=True, timeout=30,
    )


def test_split_screen_disabled_passthrough(tmp_path, monkeypatch):
    """SHORTS_SPLIT_SCREEN=false 면 input → output 단순 복사."""
    monkeypatch.setenv("SHORTS_SPLIT_SCREEN", "false")
    src = tmp_path / "input.mp4"
    dst = tmp_path / "output.mp4"
    _make_dummy_video(src, 1080, 1920)

    from auto_publisher.video_composer import apply_split_screen_broll
    assert apply_split_screen_broll(src, "etf-analysis", dst)
    assert dst.exists()
    assert dst.stat().st_size > 100


def test_split_screen_enabled_pixelle_disabled_uses_placeholder(tmp_path, monkeypatch):
    """SPLIT_SCREEN=true + PIXELLE_ENABLED=false 면 placeholder bottom 사용."""
    monkeypatch.setenv("SHORTS_SPLIT_SCREEN", "true")
    monkeypatch.setenv("PIXELLE_ENABLED", "false")
    monkeypatch.setenv("PIXELLE_BROLL_CACHE_DIR", str(tmp_path / "cache"))
    src = tmp_path / "input.mp4"
    dst = tmp_path / "output.mp4"
    _make_dummy_video(src, 1080, 1920, dur=2.0)

    from auto_publisher.video_composer import apply_split_screen_broll
    assert apply_split_screen_broll(src, "etf-analysis", dst)
    assert dst.exists()
    # 결과는 1080x1920 유지
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=width,height", "-of", "csv=p=0",
         "-select_streams", "v:0", str(dst)],
        capture_output=True, text=True, timeout=10,
    )
    w, h = map(int, probe.stdout.strip().split(","))
    assert (w, h) == (1080, 1920), f"출력 해상도 오류: {w}x{h}"


def test_split_screen_uses_cached_broll_when_available(tmp_path, monkeypatch):
    """캐시 풀에 broll mp4 있으면 placeholder 대신 그것 사용 (vstack 정상)."""
    monkeypatch.setenv("SHORTS_SPLIT_SCREEN", "true")
    monkeypatch.setenv("PIXELLE_ENABLED", "true")
    cache = tmp_path / "cache"
    monkeypatch.setenv("PIXELLE_BROLL_CACHE_DIR", str(cache))
    cat_dir = cache / "etf-analysis"
    cat_dir.mkdir(parents=True)
    broll = cat_dir / "broll-001.mp4"
    _make_dummy_video(broll, 1080, 960, dur=3.0, color="red")

    src = tmp_path / "input.mp4"
    dst = tmp_path / "output.mp4"
    _make_dummy_video(src, 1080, 1920, dur=2.0, color="blue")

    from auto_publisher.video_composer import apply_split_screen_broll
    assert apply_split_screen_broll(src, "etf-analysis", dst)
    assert dst.exists()
    # 1080x1920 보장
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", "-select_streams", "v:0", str(dst)],
        capture_output=True, text=True, timeout=10,
    )
    w, h = map(int, probe.stdout.strip().split(","))
    assert (w, h) == (1080, 1920)
