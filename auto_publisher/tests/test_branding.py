"""Tests for auto_publisher.branding (Improvement 4)."""
import shutil
import subprocess
import pytest
from pathlib import Path


def test_branding_import():
    from auto_publisher.branding import (
        make_intro_clip,
        make_outro_clip,
        make_transition_clip,
        make_lower_third_overlay,
    )
    assert callable(make_intro_clip)
    assert callable(make_outro_clip)
    assert callable(make_transition_clip)
    assert callable(make_lower_third_overlay)


def _has_ffmpeg_nvenc() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        capture_output=True, text=True, timeout=10,
    )
    return "h264_nvenc" in result.stdout or "h264_nvenc" in result.stderr


@pytest.mark.skipif(
    not _has_ffmpeg_nvenc(),
    reason="ffmpeg or h264_nvenc not available",
)
def test_intro_clip_renders(tmp_path):
    from auto_publisher.branding import make_intro_clip

    out = tmp_path / "intro.mp4"
    ok = make_intro_clip("테스트", out, 640, 360, 1.0)
    assert ok, "make_intro_clip returned False"
    assert out.exists(), "intro.mp4 not created"
    assert out.stat().st_size > 0, "intro.mp4 is empty"
