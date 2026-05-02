"""인코더 호환성 회귀 테스트 — fallback_card / static_card 경로.

배경:
- video_composer._make_text_card_clip 가 `-tune stillimage` 옵션을 모든 코덱에
  무조건 전달했음. 이 옵션은 libx264 전용이라 .env 의 FFMPEG_VIDEO_CODEC=h264_nvenc
  와 결합하면 ffmpeg 가 옵션 파싱 실패로 종료.
- 차트가 0개인 인트라데이/주간 슬러그에서만 fallback 경로가 발동하므로
  메인 경로 회귀 테스트로는 잡히지 않음.

이 테스트는 두 가지 핵심 invariant 를 잠근다:
1. fallback_card 빌더는 NVENC 환경변수에서도 valid mp4 를 생성한다.
2. 빌더가 만들어내는 ffmpeg args 는 codec-tune 호환 매트릭스를 지킨다.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg 가 PATH 에 없으면 인코더 호환성 테스트 의미 없음",
)


def _ffmpeg_supports(encoder: str) -> bool:
    out = subprocess.run(
        ["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=10
    ).stdout
    return f" {encoder} " in out


# ── 1. ffmpeg args 빌더 호환성 (가벼운 단위 테스트) ──────────────

def test_codec_tune_pair_always_compatible(monkeypatch):
    """모든 프로파일에서 (-c:v, -tune) 쌍이 호환 매트릭스를 지킨다.

    원래 버그: nvenc 코덱에 stillimage tune 이 동시에 전달되어 ffmpeg 파싱 실패.
    이제: 어떤 프로파일이든 코덱과 tune 이 같은 인코더 패밀리에 속해야 함."""
    monkeypatch.setenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    monkeypatch.setenv("FFMPEG_PRESET", "p1")

    from auto_publisher.video_encoder import build_ffmpeg_args
    LIBX264_TUNES = {"film", "animation", "grain", "stillimage",
                     "fastdecode", "zerolatency", "psnr", "ssim"}
    NVENC_TUNES = {"hq", "ll", "ull", "lossless"}

    for profile in ("static_card", "chart_motion", "short_form", "long_form"):
        args = build_ffmpeg_args(
            profile_name=profile,
            input_args=["-f", "lavfi", "-i", "color=c=black:s=128x128:d=0.04"],
            out_path=Path("/tmp/_unused.mp4"),
        )
        codec = args[args.index("-c:v") + 1]
        if "-tune" in args:
            tune = args[args.index("-tune") + 1]
            if codec == "libx264":
                assert tune in LIBX264_TUNES, (
                    f"{profile}: libx264 + 호환 안되는 tune={tune!r}"
                )
            elif "nvenc" in codec:
                assert tune in NVENC_TUNES, (
                    f"{profile}: {codec} + 호환 안되는 tune={tune!r} "
                    f"(허용: {NVENC_TUNES})"
                )


def test_static_card_uses_libx264_for_quality(monkeypatch):
    """static_card 는 정지 이미지이므로 GPU 강제 환경에서도 libx264 로 인코딩한다.

    이유: NVENC 은 motion estimation 최적화라 정지 영상에서 블록 노이즈가 더 잘 보임.
    libx264 + stillimage 가 정지 콘텐츠 기본기."""
    monkeypatch.setenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    from auto_publisher.video_encoder import build_ffmpeg_args
    args = build_ffmpeg_args(
        profile_name="static_card",
        input_args=["-f", "lavfi", "-i", "color=c=black:s=2x2:d=0.04"],
        out_path=Path("/tmp/_unused.mp4"),
    )
    # -c:v 다음 값이 libx264 여야 함
    cv_idx = args.index("-c:v")
    assert args[cv_idx + 1] == "libx264", (
        f"static_card 는 libx264 사용해야 함 (정지 영상 품질). 실제: {args[cv_idx+1]}"
    )


def test_chart_motion_uses_env_codec(monkeypatch):
    """차트 모션 (Ken Burns) 은 GPU 활용해야 하므로 env 코덱 따라간다."""
    monkeypatch.setenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    from auto_publisher.video_encoder import build_ffmpeg_args
    args = build_ffmpeg_args(
        profile_name="chart_motion",
        input_args=["-f", "lavfi", "-i", "color=c=black:s=2x2:d=0.04"],
        out_path=Path("/tmp/_unused.mp4"),
    )
    cv_idx = args.index("-c:v")
    assert args[cv_idx + 1] == "h264_nvenc"
    # tune 는 nvenc 호환 값이어야 함
    if "-tune" in args:
        tune_idx = args.index("-tune")
        assert args[tune_idx + 1] in {"hq", "ll", "ull", "lossless"}, (
            f"NVENC 호환 tune 값이 아님: {args[tune_idx+1]}"
        )


# ── 2. 실제 인코딩 골든 테스트 ────────────────────────────────

@pytest.mark.skipif(
    not _ffmpeg_supports("libx264"), reason="libx264 미지원 환경"
)
def test_static_card_renders_with_libx264(tmp_path, monkeypatch):
    """static_card 프로파일이 실제 mp4 파일을 생성한다 (1프레임 dry-run)."""
    monkeypatch.setenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")  # 강제로 NVENC
    from auto_publisher.video_encoder import build_ffmpeg_args

    out = tmp_path / "static.mp4"
    args = build_ffmpeg_args(
        profile_name="static_card",
        input_args=["-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.5"],
        out_path=out,
    )
    result = subprocess.run(
        ["ffmpeg", "-y", *args], capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0, (
        f"ffmpeg 실패 (returncode={result.returncode}):\n"
        f"args={args}\nstderr={result.stderr[-500:]}"
    )
    assert out.exists() and out.stat().st_size > 200, (
        f"mp4 산출물 없음 또는 비정상 크기: {out.stat().st_size if out.exists() else 'missing'}"
    )


@pytest.mark.skipif(
    not _ffmpeg_supports("h264_nvenc"), reason="GPU NVENC 미지원 환경"
)
def test_chart_motion_renders_with_nvenc(tmp_path, monkeypatch):
    """chart_motion 프로파일이 실제 NVENC 으로 mp4 생성."""
    monkeypatch.setenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    monkeypatch.setenv("FFMPEG_PRESET", "p1")
    from auto_publisher.video_encoder import build_ffmpeg_args

    out = tmp_path / "motion.mp4"
    # NVENC 최소 프레임 크기: 145x49 → 안전하게 256x256
    args = build_ffmpeg_args(
        profile_name="chart_motion",
        input_args=["-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.5"],
        out_path=out,
    )
    result = subprocess.run(
        ["ffmpeg", "-y", *args], capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0, (
        f"NVENC chart_motion 실패:\nargs={args}\nstderr={result.stderr[-500:]}"
    )
    assert out.exists() and out.stat().st_size > 200


# ── 3. 통합: video_composer._make_text_card_clip 회귀 ──────────

def test_make_text_card_clip_with_nvenc_env(tmp_path, monkeypatch):
    """video_composer._make_text_card_clip 이 NVENC 환경에서도 성공한다.

    이게 원래 깨진 버그의 직접 회귀 테스트.
    cycle 21 이전: AssertionError (returncode != 0)
    cycle 21 이후: pass
    """
    monkeypatch.setenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    monkeypatch.setenv("FFMPEG_PRESET", "p1")
    from auto_publisher.video_composer import _make_text_card_clip

    out = tmp_path / "card.mp4"
    card = {"card_type": "default", "headline": "Test", "subhead": "Sub", "accent": "ACC"}
    ok = _make_text_card_clip(card, duration_sec=0.5, out_path=out,
                               width=128, height=72, color="#000000")
    assert ok, "fallback card 합성 실패 (NVENC env 와 옵션 충돌 가능성)"
    assert out.exists() and out.stat().st_size > 200
