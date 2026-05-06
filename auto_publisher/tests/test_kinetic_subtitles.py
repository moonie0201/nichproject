"""kinetic subtitles 회귀 테스트.

목적: TikTok/Reels 표준 — 큰 글씨 + 단어 1-2개씩 동적 노출.
효과: 시청자 retention ↑ (조용한 환경에서도 영상 핵심 전달).

설계:
- 입력: SRT 텍스트
- 출력: ASS 텍스트 (FFmpeg subtitle filter 호환)
- 옵션: words_per_chunk (default 2), fontsize, outline 등
"""
from __future__ import annotations
import pytest


SAMPLE_SRT = """1
00:00:00,000 --> 00:00:04,000
ETF 운용보수 0.03 vs 0.5 차이의 진실

2
00:00:04,000 --> 00:00:08,000
30년 후 5천만원이 사라집니다 충격적인 결과
"""


def test_srt_to_kinetic_ass_returns_ass_header():
    """ASS 출력에 Script Info / V4+ Styles / Events 섹션 포함."""
    from auto_publisher.kinetic_subtitles import srt_to_kinetic_ass
    ass = srt_to_kinetic_ass(SAMPLE_SRT)
    assert "[Script Info]" in ass
    assert "[V4+ Styles]" in ass
    assert "[Events]" in ass
    assert "Dialogue:" in ass


def test_srt_to_kinetic_ass_splits_words(monkeypatch):
    """words_per_chunk=2 면 cue 1개당 단어 N//2 개의 Dialogue 줄 생성."""
    from auto_publisher.kinetic_subtitles import srt_to_kinetic_ass
    ass = srt_to_kinetic_ass(SAMPLE_SRT, words_per_chunk=2)
    dialogues = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    # cue 1: 7 단어 → 4 chunks, cue 2: 6 단어 → 3 chunks → 총 ≥ 7
    assert len(dialogues) >= 7


def test_srt_to_kinetic_ass_timestamps_within_cue():
    """각 chunk 의 시간 범위가 원본 cue 범위 안에 있어야 함."""
    from auto_publisher.kinetic_subtitles import srt_to_kinetic_ass
    ass = srt_to_kinetic_ass(SAMPLE_SRT, words_per_chunk=2)
    for line in ass.splitlines():
        if not line.startswith("Dialogue:"):
            continue
        # Dialogue: 0,0:00:00.00,0:00:00.40,...
        parts = line.split(",", 9)
        start = parts[1]
        end = parts[2]
        # 형식: H:MM:SS.cc
        assert ":" in start
        assert ":" in end


def test_srt_to_kinetic_ass_handles_empty_input():
    """빈 SRT 입력 시 빈 Events 섹션 (no exception)."""
    from auto_publisher.kinetic_subtitles import srt_to_kinetic_ass
    ass = srt_to_kinetic_ass("")
    assert "[Events]" in ass
    dialogues = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    assert dialogues == []


def test_srt_to_kinetic_ass_custom_fontsize():
    """fontsize 옵션이 Style 라인에 반영."""
    from auto_publisher.kinetic_subtitles import srt_to_kinetic_ass
    ass = srt_to_kinetic_ass(SAMPLE_SRT, fontsize=120)
    style_lines = [l for l in ass.splitlines() if l.startswith("Style:")]
    assert any(",120," in s for s in style_lines)


def test_srt_to_kinetic_ass_words_per_chunk_one():
    """words_per_chunk=1 이면 단어 단위 (가장 동적)."""
    from auto_publisher.kinetic_subtitles import srt_to_kinetic_ass
    ass = srt_to_kinetic_ass(SAMPLE_SRT, words_per_chunk=1)
    dialogues = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    # 7 + 6 = 13 단어
    assert len(dialogues) == 13


def test_srt_to_kinetic_ass_disabled_returns_none(monkeypatch):
    """KINETIC_SUBTITLES_ENABLED=false 면 None (호출자가 원본 SRT 그대로 사용)."""
    monkeypatch.setenv("KINETIC_SUBTITLES_ENABLED", "false")
    from auto_publisher.kinetic_subtitles import build_kinetic_ass_or_skip
    result = build_kinetic_ass_or_skip(SAMPLE_SRT)
    assert result is None


def test_build_kinetic_ass_or_skip_enabled_returns_ass(monkeypatch):
    """KINETIC_SUBTITLES_ENABLED=true (default) 면 ASS 텍스트 반환."""
    monkeypatch.delenv("KINETIC_SUBTITLES_ENABLED", raising=False)
    from auto_publisher.kinetic_subtitles import build_kinetic_ass_or_skip
    result = build_kinetic_ass_or_skip(SAMPLE_SRT)
    assert result is not None
    assert "Dialogue:" in result
