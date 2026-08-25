"""BGM 관리자 — 저작권 없는 배경음악을 카테고리별로 다운로드·캐시·선택.

소스 우선순위:
  1. 로컬 캐시 (.omc/bgm_cache/<category>/*.mp3|ogg) — hit 즉시 반환
  2. ffmpeg 앰비언트 자동 생성 — 브라운 노이즈 + 사인파 (CC0, 저작권 없음)
  3. None → 영상은 BGM 없이 정상 생성

수동으로 좋은 음악을 쓰고 싶을 때:
  .omc/bgm_cache/{category}/*.mp3 에 직접 배치 → 1순위로 사용됨
  무료 출처: pixabay.com/music (CC0), YouTube Audio Library (YouTube 전용 안전)

환경변수:
  VIDEO_BGM=1              BGM 활성화 (기본 on)
  BGM_VOLUME=0.08          나레이션 대비 볼륨 (기본 0.08)
  BGM_CACHE_DIR            캐시 루트 (기본 .omc/bgm_cache)
  BGM_AMBIENT_FALLBACK=1   ffmpeg 앰비언트 폴백 사용 (기본 on)

수동 추가:
  .omc/bgm_cache/{category}/*.mp3 에 MP3 직접 배치 → 자동 사용
"""
from __future__ import annotations

import logging
import os
import random
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# 카테고리 → ffmpeg 앰비언트 프로파일
_AMBIENT_PROFILES: dict[str, dict] = {
    "market":  {"noise": "brown", "freq1": 196, "freq2": 246},   # G3 + B3 (밝은 분위기)
    "intraday":{"noise": "pink",  "freq1": 220, "freq2": 277},   # A3 + C#4
    "default": {"noise": "brown", "freq1": 174, "freq2": 220},   # F3 + A3 (차분)
}


def _cache_dir() -> Path:
    base = os.getenv(
        "BGM_CACHE_DIR",
        str(Path(__file__).parent.parent / ".omc" / "bgm_cache"),
    )
    return Path(base)


def _is_enabled() -> bool:
    return os.getenv("VIDEO_BGM", "1").lower() not in ("false", "0", "no")


def _ambient_profile(category: str) -> dict:
    cat = category.lower().strip()
    for key in _AMBIENT_PROFILES:
        if key in cat:
            return _AMBIENT_PROFILES[key]
    return _AMBIENT_PROFILES["default"]


def _select_from_cache(category: str) -> Path | None:
    for subdir in (category, "default"):
        cdir = _cache_dir() / subdir
        if cdir.exists():
            files = sorted(cdir.glob("*.mp3")) + sorted(cdir.glob("*.ogg"))
            if files:
                return random.choice(files)
    return None


def _generate_ambient(category: str, duration_sec: float = 300.0) -> Path | None:
    """ffmpeg으로 앰비언트 배경음 생성. 브라운노이즈 + 낮은 사인파 2개.
    저작권 완전 없음. 240~300초 생성 후 캐시 저장.
    """
    if os.getenv("BGM_AMBIENT_FALLBACK", "1").lower() in ("false", "0", "no"):
        return None

    profile = _ambient_profile(category)
    noise = profile["noise"]
    f1 = profile["freq1"]
    f2 = profile["freq2"]
    dur = max(duration_sec, 120.0)

    cdir = _cache_dir() / "ambient"
    cdir.mkdir(parents=True, exist_ok=True)
    out = cdir / f"ambient-v2-{category}-{f1}.mp3"

    if out.exists():
        return out

    # sine 에는 amplitude 파라미터 없음 → volume 필터로 레벨 조절
    ffmpeg = os.getenv("FFMPEG_BIN", "ffmpeg")
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"anoisesrc=d={dur:.0f}:c={noise}:a=0.012",
        "-f", "lavfi", "-i", f"sine=frequency={f1}:duration={dur:.0f}",
        "-f", "lavfi", "-i", f"sine=frequency={f2}:duration={dur:.0f}",
        "-filter_complex",
        "[1]volume=0.010,tremolo=f=1.5:d=0.4[s1];[2]volume=0.010,tremolo=f=1.5:d=0.4[s2];[0]volume=0.7[n];[n][s1][s2]amix=inputs=3:duration=first,aecho=0.5:0.3:80:0.3[out]",
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "96k",
        str(out),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode == 0:
            logger.info(f"앰비언트 BGM 생성: {out.name} ({dur:.0f}s)")
            return out
        else:
            logger.warning(f"앰비언트 생성 실패: {result.stderr.decode()[-200:]}")
            out.unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"앰비언트 ffmpeg 실패: {e}")

    return None


def get_bgm(category: str, duration_sec: float = 60.0) -> Path | None:
    """카테고리에 맞는 BGM 파일 경로 반환.

    우선순위: 로컬 캐시 → ffmpeg 앰비언트 → None
    """
    if not _is_enabled():
        return None

    cached = _select_from_cache(category)
    if cached:
        return cached

    return _generate_ambient(category, duration_sec=max(duration_sec * 3, 240.0))


def mix_bgm(video_path: Path, out_path: Path, category: str = "default") -> bool:
    """기존 mp4에 BGM을 amix로 얹어 새 mp4 생성. c:v copy로 재인코딩 없음."""
    bgm = get_bgm(category)
    if bgm is None:
        return False

    volume = os.getenv("BGM_VOLUME", "0.08")
    filter_complex = (
        f"[1:a]volume={volume},aloop=loop=-1:size=2000000000[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )

    from auto_publisher.video_composer import _ffmpeg_run
    args = [
        "-i", str(video_path),
        "-i", str(bgm),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-ac", "2",
        "-shortest",
        str(out_path),
    ]
    ok = _ffmpeg_run(args, "bgm_mix")
    if not ok:
        logger.warning(f"BGM mix 실패 — 원본 유지: {video_path}")
    return ok
