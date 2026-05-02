"""인코더 프로파일 SSOT — use case 별 ffmpeg 옵션 묶음.

배경: video_composer 의 ffmpeg 호출들이 코덱·preset·tune 을 따로따로 처리하다가
NVENC 환경에서 `-tune stillimage` (libx264 전용) 가 충돌하는 회귀가 발생.

설계 원칙 (장기 안정성):
1. 사용처는 use case 이름만 알면 됨 ("static_card", "chart_motion", ...)
2. 코덱 호환성은 이 모듈이 책임지고 자동 매핑
3. 정지 영상은 libx264 강제 (NVENC motion estimation 오버킬, 정지 화질 ↓)
4. 모션 영상은 환경 코덱 따라감 (GPU 가용 시 NVENC, 없으면 libx264 graceful fallback)
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable


# ── 코덱별 호환 tune 값 ──────────────────────────────────────
_TUNE_BY_CODEC = {
    "libx264": "stillimage",  # static 콘텐츠 default — 정지 영상 압축 최적
    "libx265": None,           # x265 는 stillimage 미지원
    "h264_nvenc": "hq",        # NVENC 호환: hq | ll | ull | lossless
    "hevc_nvenc": "hq",
}


def _is_nvenc(codec: str) -> bool:
    return "nvenc" in codec


def _resolve_tune(codec: str, preferred: str | None = None) -> str | None:
    """preferred 가 코덱과 호환되면 그대로, 아니면 코덱별 안전 default."""
    if preferred is None:
        return _TUNE_BY_CODEC.get(codec)
    # libx264 stillimage 같은 case — preferred 가 코덱 호환 여부 검증
    if codec == "libx264" and preferred in {
        "film", "animation", "grain", "stillimage", "fastdecode", "zerolatency",
    }:
        return preferred
    if _is_nvenc(codec) and preferred in {"hq", "ll", "ull", "lossless"}:
        return preferred
    # 호환 안 되면 안전 default 로 fallback
    return _TUNE_BY_CODEC.get(codec)


def _env_codec(default: str = "h264_nvenc") -> str:
    return os.getenv("FFMPEG_VIDEO_CODEC", default)


def _env_preset(default: str = "p1") -> str:
    return os.getenv("FFMPEG_PRESET", default)


# ── 인코더 프로파일 ──────────────────────────────────────────
# 각 프로파일은 lazy 평가 (env 변경 가능하도록 함수로 정의)

def _profile_static_card() -> dict:
    """정지 이미지 + 텍스트 오버레이 (fallback_card, intro/outro).

    품질 우선: NVENC 환경에서도 libx264 강제 — 정지 영상은 CPU 가 더 깨끗함."""
    return {
        "codec": "libx264",
        "preset": "veryfast",
        "tune": "stillimage",
        "pix_fmt": "yuv420p",
        "extra": ["-crf", "20"],
    }


def _profile_chart_motion() -> dict:
    """차트 슬라이드쇼 (Ken Burns 모션, 메인 본편).

    GPU 우선: env 코덱 따라감 (보통 h264_nvenc)."""
    codec = _env_codec()
    return {
        "codec": codec,
        "preset": _env_preset(),
        "tune": _resolve_tune(codec),
        "pix_fmt": "yuv420p",
        "extra": (
            ["-rc", "vbr", "-cq", "23"] if _is_nvenc(codec) else ["-crf", "23"]
        ),
    }


def _profile_short_form() -> dict:
    """쇼츠 합성 (TTS+오버레이, ~60s) — YouTube Shorts 알고리즘 권장 비트레이트.

    Codex 자문: 8-12 Mbps VBR/CQ 권장 (현재 703 kbps 는 너무 낮음).
    Audio: EBU R128 loudnorm (-16 LUFS) 정규화로 플랫폼 라우드니스 매칭."""
    codec = _env_codec()
    base_extra = (
        ["-rc", "vbr", "-cq", "19", "-b:v", "8M", "-maxrate", "12M", "-bufsize", "16M"]
        if _is_nvenc(codec) else
        ["-crf", "19", "-maxrate", "10M", "-bufsize", "16M"]
    )
    return {
        "codec": codec,
        "preset": _env_preset(),
        "tune": _resolve_tune(codec),
        "pix_fmt": "yuv420p",
        "extra": base_extra,
        "audio_codec": "aac",
        "audio_bitrate": "192k",
        "audio_filter": "loudnorm=I=-16:TP=-1.5:LRA=11",
    }


def _profile_long_form() -> dict:
    """롱폼 (10분+, 모션 풍부) — GPU 필수, 약간 더 높은 품질."""
    codec = _env_codec()
    return {
        "codec": codec,
        "preset": _env_preset(),
        "tune": _resolve_tune(codec),
        "pix_fmt": "yuv420p",
        "extra": (
            ["-rc", "vbr", "-cq", "21"] if _is_nvenc(codec) else ["-crf", "21"]
        ),
    }


_PROFILES = {
    "static_card": _profile_static_card,
    "chart_motion": _profile_chart_motion,
    "short_form": _profile_short_form,
    "long_form": _profile_long_form,
}


def get_profile(name: str) -> dict:
    """프로파일 조회 (lazy 평가, env 반영)."""
    if name not in _PROFILES:
        raise KeyError(f"Unknown encoder profile: {name}. Known: {list(_PROFILES)}")
    return _PROFILES[name]()


def build_ffmpeg_args(
    profile_name: str,
    input_args: Iterable[str],
    out_path: Path,
) -> list[str]:
    """프로파일 기반 ffmpeg 인자 빌드.

    호출 예:
        args = build_ffmpeg_args("static_card",
            ["-f", "lavfi", "-i", filter_expr], out_path)
        subprocess.run(["ffmpeg", "-y", *args])
    """
    p = get_profile(profile_name)
    args: list[str] = list(input_args)
    args += ["-c:v", p["codec"], "-preset", p["preset"]]
    if p.get("tune"):
        args += ["-tune", p["tune"]]
    args += ["-pix_fmt", p["pix_fmt"]]
    args += list(p.get("extra", []))
    args += [str(out_path)]
    return args


# ── 부팅 시 capability 검증 (옵션) ──────────────────────────

def validate_encoders() -> dict[str, bool]:
    """프로파일별 ffmpeg dry-run 으로 호환성 점검.

    bridge_api 부팅 시 1회 호출 권장. 깨진 프로파일 즉시 알람."""
    if shutil.which("ffmpeg") is None:
        return {name: False for name in _PROFILES}

    results: dict[str, bool] = {}
    for name in _PROFILES:
        try:
            tmp_out = Path(f"/tmp/_encoder_check_{name}.mp4")
            args = build_ffmpeg_args(
                name, ["-f", "lavfi", "-i", "color=c=black:s=2x2:d=0.04"], tmp_out
            )
            r = subprocess.run(
                ["ffmpeg", "-y", *args, "-frames:v", "1"],
                capture_output=True, text=True, timeout=10,
            )
            results[name] = (r.returncode == 0)
            tmp_out.unlink(missing_ok=True)
        except Exception:
            results[name] = False
    return results
