"""kinetic subtitles — TikTok/Reels 표준 큰 글씨 + 단어 1-2개 동적 노출.

목적: 시청자 retention ↑ (조용한 환경/이어폰 미사용 시에도 영상 핵심 전달).

흐름:
1. 기존 SRT 파싱 → cues
2. 각 cue 단어 단위 분할 → words_per_chunk(default 2)개씩 묶음
3. ASS 형식으로 출력 (FFmpeg subtitle filter 호환)

ENV:
- KINETIC_SUBTITLES_ENABLED (default true) — kill switch
- KINETIC_FONTSIZE (default 80)
- KINETIC_WORDS_PER_CHUNK (default 2)
"""
from __future__ import annotations

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


_SRT_TS = re.compile(r"(\d+):(\d+):(\d+),(\d+)")


def _srt_ts_to_seconds(ts: str) -> float:
    m = _SRT_TS.match(ts.strip())
    if not m:
        return 0.0
    h, mi, s, ms = (int(x) for x in m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000


def _seconds_to_ass_ts(sec: float) -> str:
    """h:mm:ss.cc (centiseconds, 2자리)."""
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    sec -= h * 3600
    m = int(sec // 60)
    sec -= m * 60
    s = int(sec)
    cs = int(round((sec - s) * 100))
    if cs == 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _parse_srt(srt_text: str) -> list[tuple[float, float, str]]:
    """SRT 텍스트 → [(start, end, text), ...]."""
    cues = []
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        # 첫 줄은 idx, 두 번째는 timestamp, 나머지는 text
        ts_line_idx = 1 if "-->" not in lines[0] else 0
        if ts_line_idx >= len(lines) or "-->" not in lines[ts_line_idx]:
            continue
        ts = lines[ts_line_idx]
        text_lines = lines[ts_line_idx + 1:]
        try:
            start_s, end_s = ts.split("-->")
            start = _srt_ts_to_seconds(start_s)
            end = _srt_ts_to_seconds(end_s)
        except ValueError:
            continue
        text = " ".join(text_lines).strip()
        if text:
            cues.append((start, end, text))
    return cues


def _ass_header(fontsize: int) -> str:
    return (
        "[Script Info]\n"
        "Title: kinetic\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\nPlayResY: 1920\n"
        "WrapStyle: 0\nScaledBorderAndShadow: yes\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,Noto Sans CJK KR,{fontsize},&H00FFFFFF,&H000000FF,"
        "&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,2,2,40,40,200,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )


def srt_to_kinetic_ass(srt_text: str, fontsize: int = 80,
                       words_per_chunk: int = 2) -> str:
    """SRT → ASS (kinetic 큰 글씨 + 단어 N개씩 chunk)."""
    if words_per_chunk < 1:
        words_per_chunk = 1
    header = _ass_header(fontsize)
    cues = _parse_srt(srt_text)
    dialogues: list[str] = []
    for start, end, text in cues:
        words = text.split()
        if not words:
            continue
        chunks = [words[i:i + words_per_chunk]
                  for i in range(0, len(words), words_per_chunk)]
        if not chunks:
            continue
        per_chunk_dur = (end - start) / len(chunks)
        for i, chunk in enumerate(chunks):
            cs = start + i * per_chunk_dur
            ce = cs + per_chunk_dur
            chunk_text = " ".join(chunk).replace(",", "،").replace("\n", " ")
            dialogues.append(
                f"Dialogue: 0,{_seconds_to_ass_ts(cs)},"
                f"{_seconds_to_ass_ts(ce)},Default,,0,0,0,,{chunk_text}"
            )
    return header + "\n".join(dialogues) + ("\n" if dialogues else "")


def build_kinetic_ass_or_skip(srt_text: str) -> Optional[str]:
    """ENV 체크 후 ASS 반환 또는 None.

    Returns:
        str: ASS 텍스트 (KINETIC_SUBTITLES_ENABLED=true)
        None: disabled (호출자가 원본 SRT 사용)
    """
    enabled = os.getenv("KINETIC_SUBTITLES_ENABLED", "true").lower() not in (
        "false", "0", "no")
    if not enabled:
        return None
    fontsize = int(os.getenv("KINETIC_FONTSIZE", "80"))
    wpc = int(os.getenv("KINETIC_WORDS_PER_CHUNK", "2"))
    return srt_to_kinetic_ass(srt_text, fontsize=fontsize, words_per_chunk=wpc)
