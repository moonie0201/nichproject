"""
TTS + 자막 생성 — edge-tts 기반
- Microsoft Edge Neural 음성, 무한 무료, API 키 불필요
- 한국어 음성 품질 우수 (ko-KR-SunHiNeural / ko-KR-InJoonNeural)
- 단어 boundary 타임스탬프 함께 반환 → SRT 자막 자동 생성
"""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 언어별 기본 음성 (Neural)
DEFAULT_VOICES = {
    "ko": "ko-KR-InJoonNeural",      # 남성, 차분한 톤 (분석 콘텐츠 적합)
    "en": "en-US-GuyNeural",          # 남성, 명확한 발음
    "ja": "ja-JP-KeitaNeural",
    "vi": "vi-VN-NamMinhNeural",
    "id": "id-ID-ArdiNeural",
}


def _format_srt_time(seconds: float) -> str:
    """초 → SRT 타임스탬프 (HH:MM:SS,mmm)"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _preprocess_text(text: str) -> str:
    """대사 전처리:
    - [강조]...[/강조] → 텍스트 유지 (edge-tts는 SSML emphasis 무시하므로 단순 유지)
    - | (수직 바) → 짧은 일시정지 (마침표로 변환해 자연스러운 break)
    - "...." 같은 말줄임 → 정상 포맷
    """
    import re as _re
    text = _re.sub(r"\[/?강조\]", "", text)
    text = _re.sub(r"\s*\|\s*", ", ", text)  # | → ", " (짧은 pause, 중복 마침표 방지)
    text = _re.sub(r"\.{3,}", "…", text)
    text = _re.sub(r"\s{2,}", " ", text)
    text = _re.sub(r"\.\.", ".", text)  # 중복 마침표 제거
    return text.strip()


async def _tts_with_subs(text: str, voice: str, mp3_path: Path) -> list[dict]:
    """edge-tts로 mp3 + sentence/word boundary 생성"""
    import edge_tts
    text = _preprocess_text(text)
    # rate 약간 감속 (-5%) → 너무 빠르지 않아 더 자연스러움
    communicate = edge_tts.Communicate(text, voice, rate="-5%", volume="+0%")
    boundaries = []
    with open(mp3_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
                boundaries.append({
                    "offset_sec": chunk["offset"] / 10_000_000,
                    "duration_sec": chunk["duration"] / 10_000_000,
                    "text": chunk["text"],
                })
    return boundaries


def _boundaries_to_srt(boundaries: list[dict], chars_per_subtitle: int = 50) -> str:
    """boundary → SRT. SentenceBoundary는 그대로, 너무 길면 분할"""
    if not boundaries:
        return ""
    lines = []
    idx = 1
    for b in boundaries:
        text = b["text"].strip()
        if not text:
            continue
        start = b["offset_sec"]
        end = start + b["duration_sec"]
        # 너무 길면 줄바꿈 (가독성)
        if len(text) > chars_per_subtitle:
            # 중간 공백 또는 . , 기준 분할
            mid = len(text) // 2
            split_pos = text.rfind(" ", 0, mid + 10)
            if split_pos > 0:
                text = text[:split_pos] + "\n" + text[split_pos+1:]
        lines.append(f"{idx}\n{_format_srt_time(start)} --> {_format_srt_time(end)}\n{text}\n")
        idx += 1
    return "\n".join(lines)


def synthesize_tts_with_srt(
    text: str, lang: str, mp3_path: Path, srt_path: Path, voice: str = None
) -> dict:
    """텍스트 → mp3 + srt 동시 생성. 반환: {duration_sec, voice, segments}"""
    voice = voice or DEFAULT_VOICES.get(lang, "en-US-GuyNeural")
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            boundaries = pool.submit(asyncio.run, _tts_with_subs(text, voice, mp3_path)).result()
    except RuntimeError:
        boundaries = asyncio.run(_tts_with_subs(text, voice, mp3_path))
    srt_content = _boundaries_to_srt(boundaries)
    srt_path.write_text(srt_content, encoding="utf-8")

    duration_sec = (boundaries[-1]["offset_sec"] + boundaries[-1]["duration_sec"]) if boundaries else 0
    logger.info(f"TTS 완료: {mp3_path.name}, {duration_sec:.1f}초, voice={voice}")
    return {
        "duration_sec": duration_sec,
        "voice": voice,
        "segments_count": len(boundaries),
        "mp3_path": str(mp3_path),
        "srt_path": str(srt_path),
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    text = sys.argv[1] if len(sys.argv) > 1 else "안녕하세요. 오늘은 VOO 분석을 해보겠습니다. 현재가 650달러 44센트, 1년 수익률 36퍼센트입니다."
    out_dir = Path("/tmp/tts_test")
    result = synthesize_tts_with_srt(text, "ko", out_dir / "test.mp3", out_dir / "test.srt")
    print(result)
    print(Path(result["srt_path"]).read_text(encoding="utf-8"))
