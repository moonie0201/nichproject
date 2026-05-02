"""영상 품질 10/10 강화 회귀 테스트.

배경 (Codex 자문 후 적용된 개선):
- 비트레이트 703 kbps → 8 Mbps (YT 권장)
- 오디오 loudnorm 정규화 (-16 LUFS, EBU R128)
- short_form 인코더 프로파일에 고품질 NVENC 파라미터

이 테스트는 video_encoder.short_form / mux 단계가 위 invariant 를
유지하는지 확인. ffprobe 없는 단위 테스트라 빠름 (<1s).
"""
from __future__ import annotations
import pytest


# ── 1. short_form encoder profile 강화 ──────────────────────

def test_short_form_profile_has_high_bitrate(monkeypatch):
    """NVENC short_form 프로파일이 8M 이상 비트레이트 또는 cq≤22 강제."""
    monkeypatch.setenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    monkeypatch.setenv("FFMPEG_PRESET", "p1")
    from auto_publisher.video_encoder import get_profile
    p = get_profile("short_form")
    extra = p.get("extra", [])
    extra_str = " ".join(extra)
    # NVENC: -cq 19 또는 -b:v 8M 등 고품질 설정
    has_high_quality = (
        ("-cq" in extra and any(int(extra[i+1]) <= 22 for i in range(len(extra)-1) if extra[i] == "-cq" and extra[i+1].isdigit())) or
        ("-b:v" in extra and any("M" in extra[i+1] and int(extra[i+1].rstrip("M")) >= 6 for i in range(len(extra)-1) if extra[i] == "-b:v"))
    )
    assert has_high_quality, (
        f"short_form 프로파일이 고품질 설정 부족: extra={extra_str}"
    )


def test_short_form_profile_has_audio_loudnorm_hint():
    """short_form 프로파일이 audio_filter 에 loudnorm 힌트 포함."""
    from auto_publisher.video_encoder import get_profile
    p = get_profile("short_form")
    af = p.get("audio_filter", "")
    assert "loudnorm" in af, (
        f"short_form audio_filter 에 loudnorm 누락: {af!r}"
    )


# ── 2. mux 단계에 loudnorm 적용 ────────────────────────────

def test_mux_audio_filter_includes_loudnorm(tmp_path, monkeypatch):
    """_mux_audio_subtitle 가 audio 에 loudnorm 정규화를 적용한다."""
    monkeypatch.setenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    from auto_publisher import video_composer

    # 가짜 입력 — 실제 ffmpeg 호출 차단하고 args 만 캡처
    captured_args = []
    def fake_run(args, desc):
        captured_args.extend(args)
        return True
    monkeypatch.setattr(video_composer, "_ffmpeg_run", fake_run)

    fake_video = tmp_path / "v.mp4"; fake_video.write_bytes(b"")
    fake_audio = tmp_path / "a.mp3"; fake_audio.write_bytes(b"")
    fake_srt = tmp_path / "s.srt"; fake_srt.write_text("")
    fake_out = tmp_path / "o.mp4"

    video_composer._mux_audio_subtitle(
        fake_video, fake_audio, fake_srt, fake_out,
        video_duration=30.0, audio_duration=30.0, is_shorts=True,
    )
    args_str = " ".join(captured_args)
    # filter_complex 안에 loudnorm 또는 별도 -af 로 loudnorm 가 있어야
    assert "loudnorm" in args_str, (
        f"mux 단계에 loudnorm 정규화 누락: {args_str[:300]}"
    )
