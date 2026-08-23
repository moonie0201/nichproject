"""Tests for auto_publisher.motion_cards."""
import shutil
import tempfile
from pathlib import Path

import pytest


def test_motion_cards_import():
    from auto_publisher.motion_cards import (
        detect_chapter_animation_type,
        make_animated_number_clip,
        make_typewriter_card_clip,
    )
    assert callable(detect_chapter_animation_type)
    assert callable(make_animated_number_clip)
    assert callable(make_typewriter_card_clip)


def test_detect_routing():
    from auto_publisher.motion_cards import detect_chapter_animation_type

    ch1 = {"title": "데이터 근거", "text": "수익률 7.85% 기록"}
    ch2 = {"title": "Hook", "text": "끝까지 보면"}
    ch3 = {"title": "포트폴리오", "text": "분산 투자 전략"}

    assert detect_chapter_animation_type(ch1) == "animated_number", ch1
    assert detect_chapter_animation_type(ch2) == "typewriter", ch2
    assert detect_chapter_animation_type(ch3) == "static", ch3


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not available")
def test_animated_number_clip_renders():
    from auto_publisher.motion_cards import make_animated_number_clip

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test_clip.mp4"
        ok = make_animated_number_clip(
            value="7.85%",
            label="수익률",
            unit="%",
            duration_sec=1.0,
            out_path=out,
            width=320,
            height=180,
        )
        assert ok, "make_animated_number_clip returned False"
        assert out.exists(), "output file not created"
        assert out.stat().st_size > 1000, f"file too small: {out.stat().st_size} bytes"
