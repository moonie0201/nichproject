"""
영상 합성 — ffmpeg 기반
- 차트 PNG 슬라이드쇼 + Ken Burns 효과
- TTS 음성 오버레이
- SRT 자막 burned-in (가독성 고대비)
- 롱폼 (16:9, 1920x1080) / 쇼츠 (9:16, 1080x1920) 자동 분기
"""

import logging
import math
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

logger = logging.getLogger(__name__)

_DESIGN_TOKENS: dict = {}


def _load_design_tokens() -> dict:
    global _DESIGN_TOKENS
    if _DESIGN_TOKENS:
        return _DESIGN_TOKENS
    design_path = Path(__file__).parent.parent / "DESIGN.md"
    if not design_path.exists():
        return {}
    import re as _re
    text = design_path.read_text(encoding="utf-8")
    m = _re.match(r"^---\n(.*?)\n---", text, _re.DOTALL)
    if not m:
        return {}
    try:
        import yaml as _yaml
        _DESIGN_TOKENS = _yaml.safe_load(m.group(1)) or {}
    except Exception:
        pass
    return _DESIGN_TOKENS


def _c(token: str, fallback: str) -> str:
    """Color token → ffmpeg 0xRRGGBB (drawbox/drawtext)"""
    tokens = _load_design_tokens()
    val = tokens.get("colors", {}).get(token, fallback)
    return "0x" + val.lstrip("#")


def _cbg(token: str, fallback: str) -> str:
    """Color token → #RRGGBB (ffmpeg color=c= background)"""
    tokens = _load_design_tokens()
    val = tokens.get("colors", {}).get(token, fallback)
    if not val.startswith("#"):
        val = "#" + val.lstrip("0x")
    return val

WEB_STATIC = Path(os.getenv("WEB_STATIC_DIR", str(Path(__file__).parent.parent / "web" / "static")))
_FONT_FILE = None


def _resolve_chart_path(chart_url: str) -> Path | None:
    """블로그 본문의 /images/.../chart.png URL을 실제 디스크 경로로 변환"""
    if not chart_url:
        return None
    if chart_url.startswith("/images/"):
        return WEB_STATIC / chart_url.lstrip("/")
    p = Path(chart_url)
    return p if p.exists() else None


def _ffmpeg_run(args: list[str], description: str = "ffmpeg") -> bool:
    """ffmpeg 실행 헬퍼"""
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + args
    logger.debug(f"{description}: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        logger.error(f"{description} 실패: {result.stderr[:300]}")
        return False
    return True


def _resolve_font_file() -> str:
    global _FONT_FILE
    if _FONT_FILE:
        return _FONT_FILE

    candidates = [
        ["fc-match", "-f", "%{file}\n", "Noto Sans CJK KR"],
        ["fc-match", "-f", "%{file}\n", "Noto Sans CJK"],
        ["fc-match", "-f", "%{file}\n", "DejaVu Sans"],
    ]
    for cmd in candidates:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except OSError:
            continue
        if result.returncode == 0:
            path = result.stdout.strip().splitlines()[0]
            if path:
                _FONT_FILE = path
                return path
    return ""


def _escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace(",", "\\,")
    )


def _make_text_card_clip(
    card: dict,
    duration_sec: float,
    out_path: Path,
    width: int,
    height: int,
    color: str = "#0f172a",
) -> bool:
    font_file = _resolve_font_file()
    card_type = card.get("card_type", "default")
    headline = _escape_drawtext(textwrap.fill(card.get("headline", ""), width=14))
    subhead = _escape_drawtext(textwrap.fill(card.get("subhead", ""), width=22))
    accent = _escape_drawtext(card.get("accent", "InvestIQs"))
    font_arg = f":fontfile='{font_file}'" if font_file else ""
    base = f"color=c={color}:s={width}x{height}:d={duration_sec:.2f}:r=30"
    if card_type in {"thesis", "thesis_board"}:
        filter_expr = (
            f"{base},"
            f"drawbox=x=64:y=64:w={width-128}:h={height-128}:color={_c('bg-panel', '#020617')}@0.72:t=fill,"
            f"drawbox=x=64:y=64:w={width-128}:h=8:color={_c('primary', '#38BDF8')}:t=fill,"
            f"drawtext=text='INVESTIQS RESEARCH'{font_arg}:fontsize=28:fontcolor={_c('primary', '#38BDF8')}:x=96:y=104,"
            f"drawtext=text='{headline}'{font_arg}:fontsize=56:fontcolor=white:x=96:y=(h*0.25):line_spacing=14,"
            f"drawtext=text='{subhead}'{font_arg}:fontsize=30:fontcolor={_c('text-sub', '#CBD5E1')}:x=96:y=(h*0.56):line_spacing=10,"
            f"drawtext=text='{accent}'{font_arg}:fontsize=34:fontcolor={_c('accent', '#FACC15')}:x=96:y=(h*0.82)"
        )
    elif card_type == "market_dashboard":
        filter_expr = (
            f"{base},"
            f"drawbox=x=72:y=78:w={width-144}:h={height-156}:color={_c('bg-panel', '#020617')}@0.64:t=fill,"
            f"drawbox=x=112:y=138:w={(width-264)//2}:h=180:color=0x0F766E@0.35:t=fill,"
            f"drawbox=x={width//2+20}:y=138:w={(width-264)//2}:h=180:color=0x1D4ED8@0.35:t=fill,"
            f"drawbox=x=112:y=370:w={width-224}:h=4:color={_c('primary', '#38BDF8')}:t=fill,"
            f"drawbox=x=112:y=520:w={width-224}:h=4:color={_c('accent', '#FACC15')}:t=fill,"
            f"drawbox=x=112:y=670:w={width-224}:h=4:color={_c('success', '#22C55E')}:t=fill,"
            f"drawtext=text='MARKET DASHBOARD'{font_arg}:fontsize=30:fontcolor={_c('primary', '#38BDF8')}:x=112:y=104,"
            f"drawtext=text='{accent}'{font_arg}:fontsize=54:fontcolor={_c('accent', '#FACC15')}:x=132:y=190,"
            f"drawtext=text='{headline}'{font_arg}:fontsize=46:fontcolor=white:x=112:y=410:line_spacing=14,"
            f"drawtext=text='{subhead}'{font_arg}:fontsize=28:fontcolor={_c('text-sub', '#CBD5E1')}:x=112:y=710:line_spacing=10"
        )
    elif card_type == "timeline":
        filter_expr = (
            f"{base},"
            f"drawbox=x=92:y=120:w=6:h={height-240}:color={_c('primary', '#38BDF8')}:t=fill,"
            f"drawbox=x=78:y=180:w=34:h=34:color={_c('accent', '#FACC15')}:t=fill,"
            f"drawbox=x=78:y=420:w=34:h=34:color={_c('primary', '#38BDF8')}:t=fill,"
            f"drawbox=x=78:y=660:w=34:h=34:color={_c('success', '#22C55E')}:t=fill,"
            f"drawtext=text='RESEARCH TIMELINE'{font_arg}:fontsize=30:fontcolor={_c('primary', '#38BDF8')}:x=132:y=122,"
            f"drawtext=text='{headline}'{font_arg}:fontsize=52:fontcolor=white:x=132:y=220:line_spacing=14,"
            f"drawtext=text='{subhead}'{font_arg}:fontsize=30:fontcolor={_c('text-sub', '#CBD5E1')}:x=132:y=540:line_spacing=10,"
            f"drawtext=text='{accent}'{font_arg}:fontsize=32:fontcolor={_c('accent', '#FACC15')}:x=132:y=(h*0.82)"
        )
    elif card_type == "number":
        filter_expr = (
            f"{base},"
            f"drawbox=x=80:y=90:w={width-160}:h={height-180}:color=0xFFFFFF@0.05:t=fill,"
            f"drawtext=text='{accent}'{font_arg}:fontsize=72:fontcolor={_c('warning', '#FFD54F')}:x=(w-text_w)/2:y=(h*0.20),"
            f"drawtext=text='{headline}'{font_arg}:fontsize=46:fontcolor=white:x=90:y=(h*0.44):line_spacing=14,"
            f"drawtext=text='{subhead}'{font_arg}:fontsize=28:fontcolor={_c('text-muted', '#D7E3F4')}:x=90:y=(h*0.68):line_spacing=10"
        )
    elif card_type in {"risk", "risk_matrix"}:
        filter_expr = (
            f"{base},"
            f"drawbox=x=72:y=72:w={width-144}:h={height-144}:color={_c('bg-risk', '#7f1d1d')}@0.25:t=fill,"
            f"drawbox=x=72:y=72:w=18:h={height-144}:color={_c('warning', '#FFD54F')}:t=fill,"
            f"drawtext=text='{accent}'{font_arg}:fontsize=34:fontcolor={_c('warning', '#FFD54F')}:x=108:y=110,"
            f"drawtext=text='{headline}'{font_arg}:fontsize=52:fontcolor=white:x=108:y=(h*0.28):line_spacing=14,"
            f"drawtext=text='{subhead}'{font_arg}:fontsize=30:fontcolor={_c('text-risk', '#FDE68A')}:x=108:y=(h*0.58):line_spacing=10"
        )
    elif card_type == "cta":
        filter_expr = (
            f"{base},"
            f"drawbox=x=90:y=(h*0.22):w={width-180}:h={height*0.46}:color=0xFFFFFF@0.05:t=fill,"
            f"drawtext=text='{headline}'{font_arg}:fontsize=56:fontcolor=white:x=(w-text_w)/2:y=(h*0.28):line_spacing=12,"
            f"drawtext=text='{subhead}'{font_arg}:fontsize=28:fontcolor={_c('text-muted', '#D7E3F4')}:x=(w-text_w)/2:y=(h*0.50):line_spacing=10,"
            f"drawtext=text='{accent}'{font_arg}:fontsize=32:fontcolor={_c('warning', '#FFD54F')}:x=(w-text_w)/2:y=(h*0.72)"
        )
    elif card_type == "comparison":
        filter_expr = (
            f"{base},"
            f"drawbox=x=72:y=80:w={width-144}:h=160:color=0xFFFFFF@0.05:t=fill,"
            f"drawbox=x=72:y=300:w={width-144}:h={height-420}:color=0x0b1220@0.45:t=fill,"
            f"drawtext=text='{accent}'{font_arg}:fontsize=40:fontcolor={_c('warning', '#FFD54F')}:x=100:y=128,"
            f"drawtext=text='{headline}'{font_arg}:fontsize=48:fontcolor=white:x=100:y=340:line_spacing=14,"
            f"drawtext=text='{subhead}'{font_arg}:fontsize=28:fontcolor={_c('text-muted', '#D7E3F4')}:x=100:y=620:line_spacing=10"
        )
    else:
        filter_expr = (
            f"{base},"
            f"drawbox=x=72:y=72:w={width-144}:h={height-144}:color=white@0.06:t=fill,"
            f"drawtext=text='{accent}'{font_arg}:fontsize=28:fontcolor={_c('warning', '#FFD54F')}:x=72:y=72,"
            f"drawtext=text='{headline}'{font_arg}:fontsize=54:fontcolor=white:"
            f"x=72:y=(h*0.24):line_spacing=14,"
            f"drawtext=text='{subhead}'{font_arg}:fontsize=30:fontcolor={_c('text-muted', '#D7E3F4')}:"
            f"x=72:y=(h*0.62):line_spacing=10"
        )
    # encoder profile 사용: static_card 는 libx264 강제 (정지 영상 품질 + NVENC 호환 회귀 방지)
    from auto_publisher.video_encoder import build_ffmpeg_args
    args = build_ffmpeg_args(
        profile_name="static_card",
        input_args=["-f", "lavfi", "-i", filter_expr],
        out_path=out_path,
    )
    return _ffmpeg_run(args, "fallback_card")


def _build_fallback_cards(
    fallback_visual_plan: list[dict] | None,
    visual_beats: list[dict] | None,
    source_data_points: list[dict] | None,
) -> list[dict]:
    if fallback_visual_plan:
        return fallback_visual_plan

    cards: list[dict] = []
    if source_data_points:
        for point in source_data_points[:4]:
            cards.append(
                {
                    "headline": point.get("label", "핵심 포인트"),
                    "subhead": point.get("context", ""),
                    "accent": point.get("value", "InvestIQs"),
                    "card_type": "number" if _resolve_card_type_from_point(point) == "number" else _resolve_card_type_from_point(point),
                }
            )
    elif visual_beats:
        for beat in visual_beats[:4]:
            cards.append(
                {
                    "headline": beat.get("title", "핵심 포인트"),
                    "subhead": beat.get("focus", ""),
                    "accent": ", ".join(beat.get("numbers", [])[:2]) or "데이터 포인트",
                    "card_type": "comparison",
                }
            )
    if not cards:
        cards = [
            {"headline": "InvestIQs", "subhead": "핵심 내용을 카드형 화면으로 정리합니다", "accent": "Fallback", "card_type": "title"},
            {"headline": "전체 분석은 본문과 영상에서", "subhead": "데이터 근거와 리스크를 함께 확인하세요", "accent": "Research", "card_type": "cta"},
        ]
    return cards


def _resolve_card_type_from_point(point: dict) -> str:
    label = point.get("label", "")
    context = point.get("context", "")
    if any(token in label + context for token in ("리스크", "위험", "변동성", "경고")):
        return "risk"
    if any(token in label + context for token in ("CTA", "블로그", "전체 분석", "다음 액션")):
        return "cta"
    if len(_escape_drawtext(point.get("value", ""))) > 18:
        return "comparison"
    return "number"


def _make_kenburns_clip(image_path: Path, duration_sec: float, out_path: Path,
                       width: int, height: int, zoom_max: float = 1.15) -> bool:
    """단일 이미지 → Ken Burns(zoom-in) 영상 클립.

    zoom_max: 최대 줌 배율. 쇼츠 차트는 정보 잘림 방지를 위해 1.03 권장.
    """
    fps = 30
    total_frames = int(duration_sec * fps)
    # zoom 증분도 zoom_max 도달까지 분포되도록 조정 (정확히 끝에 max 도달)
    zoom_step = max((zoom_max - 1.0) / max(total_frames, 1), 0.0001)
    zoom_expr = f"zoom='min(zoom+{zoom_step:.6f},{zoom_max})'"
    args = [
        "-loop", "1", "-i", str(image_path),
        "-t", f"{duration_sec:.2f}",
        "-vf",
        (f"scale={width*2}:{height*2}:force_original_aspect_ratio=decrease,"
         f"pad={width*2}:{height*2}:(ow-iw)/2:(oh-ih)/2:color=white,"
         f"zoompan={zoom_expr}:d={total_frames}:s={width}x{height}:fps={fps}"),
        "-c:v", os.getenv("FFMPEG_VIDEO_CODEC", "h264_nvenc"),
        "-preset", os.getenv("FFMPEG_PRESET", "p1"),
        "-pix_fmt", "yuv420p", "-r", str(fps),
        str(out_path),
    ]
    return _ffmpeg_run(args, f"kenburns:{image_path.name}")


def _make_solid_clip(duration_sec: float, out_path: Path,
                     width: int, height: int, color: str = "#0f172a") -> bool:
    """단색 배경 클립 생성 (쇼츠 하단 자막 영역용)"""
    args = [
        "-f", "lavfi", "-i",
        f"color=c={color}:s={width}x{height}:d={duration_sec:.2f}:r=30",
        "-c:v", os.getenv("FFMPEG_VIDEO_CODEC", "h264_nvenc"),
        "-preset", os.getenv("FFMPEG_PRESET", "p1"),
        "-pix_fmt", "yuv420p", str(out_path),
    ]
    return _ffmpeg_run(args, "solid_bg")


def _vstack_clips(top_path: Path, bot_path: Path, out_path: Path) -> bool:
    """두 클립을 수직으로 쌓기 (top 위, bot 아래)"""
    args = [
        "-i", str(top_path), "-i", str(bot_path),
        "-filter_complex", "[0:v][1:v]vstack=inputs=2[v]",
        "-map", "[v]",
        "-c:v", os.getenv("FFMPEG_VIDEO_CODEC", "h264_nvenc"),
        "-preset", os.getenv("FFMPEG_PRESET", "p1"),
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    return _ffmpeg_run(args, "vstack")


def _concat_clips(clip_paths: list[Path], out_path: Path) -> bool:
    """여러 mp4 클립을 이어붙임"""
    list_file = out_path.parent / f"{out_path.stem}_concat.txt"
    list_file.write_text(
        "\n".join(f"file '{p.absolute()}'" for p in clip_paths),
        encoding="utf-8"
    )
    args = [
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", str(out_path),
    ]
    ok = _ffmpeg_run(args, "concat")
    list_file.unlink(missing_ok=True)
    return ok


def _build_ai_disclosure_filters(
    font_file: str,
    is_shorts: bool,
    total_duration: float,
) -> str:
    """AI 기본법 §32 준수 워터마크 + 시작/종료 자막 drawtext 필터 체인을 반환.

    환경변수 AI_WATERMARK_DISABLED=true 이면 빈 문자열 반환 (테스트용).
    """
    if os.getenv("AI_WATERMARK_DISABLED", "false").lower() in ("true", "1", "yes"):
        return ""

    font_arg = f":fontfile='{font_file}'" if font_file else ""

    # 공통 outline 스타일
    outline = "borderw=2:bordercolor=black@0.85"

    # 워터마크 크기/위치: 쇼츠 상단 영역(960px) 기준으로 우상단
    wm_size = 18 if is_shorts else 24
    # 쇼츠는 split-screen 상단 960px 안쪽에 워터마크 — y=20 으로 충분
    wm_y = 20

    # 시작 5초 자막 텍스트
    if is_shorts:
        open_text = _escape_drawtext("AI 영상 / 투자 권유 아님")
    else:
        open_text = _escape_drawtext("본 영상은 AI가 제작했으며 투자 권유가 아닙니다")

    close_text = _escape_drawtext("투자 결정은 본인 판단입니다")

    # 자막 크기/위치
    disc_size = 20 if is_shorts else 22
    # 시작/종료 자막: 영상 하단 — 기존 kinetic 자막(하단 960px 중앙, MarginV=440)과 겹침 방지
    # kinetic/SRT 자막은 하단 160px 이하에, 이 자막은 하단 220~260px 영역에 배치
    if is_shorts:
        disc_y = "h-text_h-260"  # 쇼츠 하단 260px 위
    else:
        disc_y = "h-text_h-120"  # 롱폼 하단 120px 위

    end_start = max(total_duration - 5.0, 0.0)

    watermark_filter = (
        f"drawtext=text='AI 생성'{font_arg}"
        f":fontsize={wm_size}:fontcolor=white@0.92"
        f":{outline}"
        f":box=1:boxcolor=black@0.45:boxborderw=4"
        f":x=w-text_w-20:y={wm_y}"
        f":enable='gte(t\\,0)'"
    )

    open_filter = (
        f"drawtext=text='{open_text}'{font_arg}"
        f":fontsize={disc_size}:fontcolor=white@0.95"
        f":{outline}"
        f":box=1:boxcolor=black@0.55:boxborderw=6"
        f":x=(w-text_w)/2:y={disc_y}"
        f":enable='between(t\\,0\\,5)'"
    )

    close_filter = (
        f"drawtext=text='{close_text}'{font_arg}"
        f":fontsize={disc_size}:fontcolor=white@0.95"
        f":{outline}"
        f":box=1:boxcolor=black@0.55:boxborderw=6"
        f":x=(w-text_w)/2:y={disc_y}"
        f":enable='gte(t\\,{end_start:.2f})'"
    )

    return f",{watermark_filter},{open_filter},{close_filter}"


def _mux_audio_subtitle(video_path: Path, audio_path: Path, srt_path: Path,
                        out_path: Path, video_duration: float, audio_duration: float,
                        is_shorts: bool = False) -> bool:
    """비디오 + 음성 + 자막 합치기. 영상이 음성보다 짧으면 마지막 프레임 freeze로 연장"""
    pad_filter = ""
    if video_duration < audio_duration:
        pad_sec = audio_duration - video_duration
        pad_filter = f"[0:v]tpad=stop_mode=clone:stop_duration={pad_sec:.2f}[v];"
        video_in = "[v]"
    else:
        video_in = "[0:v]"

    sub_path = srt_path
    if is_shorts:
        try:
            from auto_publisher.kinetic_subtitles import build_kinetic_ass_or_skip
            ass_text = build_kinetic_ass_or_skip(srt_path.read_text(encoding="utf-8"))
            if ass_text:
                ass_p = srt_path.with_suffix(".ass")
                ass_p.write_text(ass_text, encoding="utf-8")
                sub_path = ass_p
                logger.info(f"kinetic ASS 자막 적용: {ass_p.name}")
        except Exception as e:
            logger.warning(f"kinetic ASS 변환 실패, SRT 사용: {e}")

    srt_escaped = str(sub_path.absolute()).replace(":", "\\:").replace("'", "\\'")
    if is_shorts:
        # 하단 960px 영역 중앙 — SRT 사용 시에만 적용 (ASS 는 자체 style)
        sub_style = (
            "FontName=Noto Sans CJK KR,FontSize=32,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,Outline=3,Shadow=0,Alignment=2,MarginV=440"
        )
    else:
        sub_style = (
            "FontName=Noto Sans CJK KR,FontSize=18,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,Outline=2,Shadow=0,Alignment=2,MarginV=80"
        )

    # ASS 는 자체 Style 사용 — force_style 적용 시 ASS Alignment/MarginV override 됨
    if sub_path.suffix.lower() == ".ass":
        sub_filter = f"subtitles='{srt_escaped}'"
    else:
        sub_filter = f"subtitles='{srt_escaped}':force_style='{sub_style}'"

    # AI 기본법 §32 워터마크 + 시작/종료 공시 자막
    font_file = _resolve_font_file()
    ai_filters = _build_ai_disclosure_filters(font_file, is_shorts, audio_duration)

    # Codex 자문: short_form 프로파일 적용 (8M 비트레이트 + loudnorm 오디오 정규화)
    from auto_publisher.video_encoder import get_profile
    profile = get_profile("short_form" if is_shorts else "long_form")

    audio_filter = profile.get("audio_filter")
    if audio_filter:
        # 비디오 + 오디오 필터 chain 함께
        filter_complex = (
            f"{pad_filter}{video_in}{sub_filter}{ai_filters}[vout];"
            f"[1:a]{audio_filter}[aout]"
        )
        audio_map = "[aout]"
    else:
        filter_complex = f"{pad_filter}{video_in}{sub_filter}{ai_filters}[vout]"
        audio_map = "1:a"

    args = [
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", audio_map,
        "-c:v", profile["codec"],
        "-preset", profile["preset"],
    ]
    if profile.get("tune"):
        args += ["-tune", profile["tune"]]
    args += ["-pix_fmt", profile["pix_fmt"]]
    args += list(profile.get("extra", []))
    args += [
        "-c:a", profile.get("audio_codec", "aac"),
        "-b:a", profile.get("audio_bitrate", "192k"),
        "-ar", profile.get("audio_sample_rate", "48000"),
        "-ac", profile.get("audio_channels", "2"),
        "-shortest",
        "-t", f"{audio_duration:.2f}",
        str(out_path),
    ]
    return _ffmpeg_run(args, "mux")


def compose_video(
    slug: str,
    audio_path: Path,
    srt_path: Path,
    chart_paths: list[str],
    audio_duration_sec: float,
    out_path: Path,
    aspect: str = "16:9",  # "16:9" 롱폼 / "9:16" 쇼츠
    fallback_visual_plan: list[dict] | None = None,
    visual_beats: list[dict] | None = None,
    source_data_points: list[dict] | None = None,
    chapters: list | None = None,
) -> Path | None:
    """차트 슬라이드쇼 + 음성 + 자막 → mp4 합성

    쇼츠(9:16): 상단 1080×960 이미지 / 하단 1080×960 자막 분할 레이아웃
    롱폼(16:9): 기존 전체화면 방식
    """
    is_shorts = (aspect == "9:16")
    if is_shorts:
        width, height = 1080, 1920
        img_w, img_h = 1080, 960  # 상단 절반
    else:
        width, height = 1920, 1080
        img_w, img_h = width, height

    # 차트 경로 해석 + 존재 확인
    valid_charts = []
    for c in chart_paths:
        p = _resolve_chart_path(c) if isinstance(c, str) else c
        if p and Path(p).exists():
            valid_charts.append(Path(p))

    _kenburns_min = float(os.getenv("KENBURNS_PER_CHART_SEC", "2"))
    # 체류 시간 상한. 이전에는 하한만 있어서 이미지가 모자라면 한 장이 무한정 머물렀다
    # (쇼츠 60초에 차트 2장 = 30초씩 정지 화면). 줌이 3% 뿐이라 사실상 멈춘 화면이었다.
    _kenburns_max = float(os.getenv(
        "KENBURNS_MAX_PER_CHART_SEC", "4" if is_shorts else "12"
    ))
    # 순환은 서로 다른 이미지가 2장 이상일 때만 의미가 있다. 1장을 N번 반복하면
    # 화면은 그대로면서 인코딩 비용만 N배로 든다 — 그 경우 비주얼 자체를 늘려야 한다.
    if len(valid_charts) >= 2 and audio_duration_sec / len(valid_charts) > _kenburns_max:
        needed = max(int(math.ceil(audio_duration_sec / _kenburns_max)), len(valid_charts))
        cycled = [valid_charts[i % len(valid_charts)] for i in range(needed)]
        logger.info(
            "비주얼 부족(%d장 / %.1fs) — %d장으로 순환해 화면 전환을 만든다",
            len(valid_charts), audio_duration_sec, needed,
        )
        valid_charts = cycled
    per_chart_sec = max(audio_duration_sec / max(len(valid_charts), 1), _kenburns_min)

    work_dir = audio_path.parent / f"{slug}_clips"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        clip_paths = []
        if not valid_charts:
            logger.warning("유효한 차트 없음 — fallback 카드 비주얼로 합성")
            cards = _build_fallback_cards(fallback_visual_plan, visual_beats, source_data_points)
            _card_min_sec = 3.5
            max_cards = max(int(audio_duration_sec / _card_min_sec), 1)
            if len(cards) > max_cards:
                logger.info(f"fallback cards {len(cards)} → {max_cards} (cap to fit {audio_duration_sec:.1f}s audio)")
                cards = cards[:max_cards]
            per_card_sec = max(audio_duration_sec / max(len(cards), 1), _card_min_sec)
            fallback_color = _cbg("bg-shorts", "#1e293b") if is_shorts else _cbg("bg", "#0f172a")
            for i, card in enumerate(cards):
                clip_out = work_dir / f"fallback_{i:02d}.mp4"
                if not _make_text_card_clip(card, per_card_sec, clip_out, img_w, img_h, color=fallback_color):
                    return None
                clip_paths.append(clip_out)
            per_chart_sec = per_card_sec
        else:
            for i, chart in enumerate(valid_charts):
                if chart.suffix == ".mp4":
                    clip_paths.append(chart)
                    continue
                clip_out = work_dir / f"clip_{i:02d}.mp4"
                # 쇼츠 차트는 정보 잘림 방지 위해 줌 최소화 (default 1.03 = 3%)
                # PPT 슬라이드 (slide_*.png) 도 페이지 번호/브랜드 잘림 방지 위해 줌 최소
                is_slide = chart.name.startswith("slide_")
                if is_slide:
                    zoom_max = float(os.getenv("SLIDE_KENBURNS_ZOOM_MAX", "1.02"))
                else:
                    zoom_env = "SHORTS_KENBURNS_ZOOM_MAX" if is_shorts else "LONG_KENBURNS_ZOOM_MAX"
                    zoom_default = "1.03" if is_shorts else "1.15"
                    zoom_max = float(os.getenv(zoom_env, zoom_default))
                _anim_done = False
                if os.getenv("VIDEO_ANIMATED_CARDS", "1") == "1" and chapters:
                    _ch = chapters[i] if i < len(chapters) else None
                    if _ch:
                        from auto_publisher.motion_cards import (
                            detect_chapter_animation_type,
                            make_animated_number_clip,
                            make_typewriter_card_clip,
                        )
                        _amode = detect_chapter_animation_type(_ch)
                        if _amode == "animated_number":
                            _sp = source_data_points or []
                            _pt = _sp[i] if i < len(_sp) else {}
                            _anim_done = make_animated_number_clip(
                                value=str(_pt.get("display_value") or _pt.get("value", "")),
                                label=str(_pt.get("label", _ch.get("title", ""))),
                                unit="",
                                duration_sec=per_chart_sec,
                                out_path=clip_out,
                                width=img_w, height=img_h,
                            )
                        elif _amode == "typewriter":
                            _anim_done = make_typewriter_card_clip(
                                text=_ch.get("text", "")[:200],
                                duration_sec=per_chart_sec,
                                out_path=clip_out,
                                width=img_w, height=img_h,
                            )
                if not _anim_done:
                    if not _make_kenburns_clip(chart, per_chart_sec, clip_out, img_w, img_h,
                                               zoom_max=zoom_max):
                        logger.warning(f"클립 생성 실패: {chart}")
                        continue
                # -- lower-third overlay --
                if os.getenv("VIDEO_LOWER_THIRD", "1") == "1":
                    _chapter_for_lt = None
                    if chapters:
                        for _ch in chapters:
                            if _ch.get("chart") and str(_ch["chart"]) in str(chart):
                                _chapter_for_lt = _ch
                                break
                        if not _chapter_for_lt and i < len(chapters):
                            _chapter_for_lt = chapters[i]
                    if _chapter_for_lt:
                        from auto_publisher.branding import make_lower_third_overlay
                        _lt_out = work_dir / f"lt_{i:02d}.mp4"
                        if make_lower_third_overlay(_chapter_for_lt.get("title", ""), clip_out, _lt_out):
                            clip_out.unlink(missing_ok=True)
                            _lt_out.rename(clip_out)
                clip_paths.append(clip_out)

        if not clip_paths:
            logger.error("생성된 클립 없음")
            return None

        # -- branding injection --
        if os.getenv("VIDEO_BRANDING", "1") == "1":
            from auto_publisher.branding import make_intro_clip, make_outro_clip
            intro_dur = 1.0 if is_shorts else 2.5
            outro_dur = 1.5 if is_shorts else 3.0
            intro_p = work_dir / "intro.mp4"
            outro_p = work_dir / "outro.mp4"
            _title = chapters[0].get("title", "InvestIQs") if chapters else "InvestIQs"
            _blog_url = os.getenv("BLOG_URL_HINT", "investiqs.net")
            branded = []
            if make_intro_clip(_title, intro_p, img_w, img_h, intro_dur):
                branded.append(intro_p)
            branded.extend(clip_paths)
            if make_outro_clip(_blog_url, outro_p, img_w, img_h, outro_dur):
                branded.append(outro_p)
            branded_concat = work_dir / "branded_concat.mp4"
            if _concat_clips(branded, branded_concat):
                clip_paths = [branded_concat]

        # 클립 합치기 → top.mp4 (상단 이미지 영역)
        concat_path = work_dir / "concat.mp4"
        if not _concat_clips(clip_paths, concat_path):
            return None

        if is_shorts:
            # 하단 960px 어두운 배경 생성 후 vstack → 1080×1920
            total_clip_dur = per_chart_sec * len(clip_paths)
            bot_path = work_dir / "bot.mp4"
            if not _make_solid_clip(total_clip_dur, bot_path, img_w, img_h):
                return None
            stacked_path = work_dir / "stacked.mp4"
            if not _vstack_clips(concat_path, bot_path, stacked_path):
                return None
            video_path = stacked_path
        else:
            video_path = concat_path

        out_path.parent.mkdir(parents=True, exist_ok=True)
        video_duration = per_chart_sec * len(clip_paths)
        if not _mux_audio_subtitle(video_path, audio_path, srt_path, out_path,
                                   video_duration, audio_duration_sec, is_shorts=is_shorts):
            return None

        # BGM 믹스 (VIDEO_BGM=1, 기본 on)
        if os.getenv("VIDEO_BGM", "1").lower() not in ("false", "0", "no"):
            try:
                from auto_publisher.bgm_manager import mix_bgm
                from auto_publisher.stock_broll import slug_to_category
                bgm_category = os.getenv("SHORTS_CATEGORY") or slug_to_category(slug)
                bgm_out = out_path.with_name(out_path.stem + ".bgm.mp4")
                if mix_bgm(out_path, bgm_out, category=bgm_category):
                    import shutil as _sh
                    _sh.move(str(bgm_out), str(out_path))
                    logger.info(f"BGM 합성 완료 (category={bgm_category})")
                else:
                    bgm_out.unlink(missing_ok=True)
                    logger.info("BGM 없음 — 나레이션 단독 유지")
            except Exception as _e:
                logger.warning(f"BGM mix 예외 — 무시하고 계속: {_e}")

        if is_shorts and os.getenv("SHORTS_SPLIT_SCREEN", "false").lower() in ("true", "1", "yes"):
            from auto_publisher.stock_broll import slug_to_category
            category = os.getenv("SHORTS_CATEGORY") or slug_to_category(slug)
            tmp_split = out_path.with_name(out_path.stem + ".split.mp4")
            if apply_split_screen_broll(out_path, category, tmp_split):
                shutil.move(str(tmp_split), str(out_path))
                logger.info(f"split-screen 적용 완료 (category={category}): {out_path}")
            else:
                tmp_split.unlink(missing_ok=True)
                logger.warning("split-screen 적용 실패 — 원본 영상 유지")

        logger.info(f"영상 합성 완료: {out_path}")
        return out_path
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────
# Split-screen Shorts: 위 절반 차트 + 아래 절반 Pixelle B-roll
# ─────────────────────────────────────────────────────────────────

def apply_split_screen_broll(
    input_mp4: Path, category: str, output_mp4: Path,
) -> bool:
    """1080x1920 input 의 위 960px 만 보존 + 아래 960px Pixelle B-roll 합성.

    Pixelle 비활성/실패 시 fallback placeholder (정적 그라디언트 + 라벨) 사용.
    PIXELLE_ENABLED=false 면 input 그대로 복사 (no-op pass-through).

    Returns:
        True: split-screen 합성 성공
        False: ffmpeg 실패 (호출자 fallback)
    """
    import shutil as _sh
    if os.getenv("SHORTS_SPLIT_SCREEN", "false").lower() not in ("true", "1", "yes"):
        # 기능 비활성: input 그대로 복사
        _sh.copy(input_mp4, output_mp4)
        return True

    # B-roll 소스 우선순위: Pexels stock pool (다양성) → 단일 stock → Pixelle AI → placeholder
    from auto_publisher.stock_broll import get_stock_broll, get_broll_pool
    from auto_publisher.pixelle_client import get_broll as pixelle_broll

    # 입력 길이 측정 (B-roll 길이 매칭용)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(input_mp4)],
        capture_output=True, text=True, timeout=10,
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 60.0

    # ladder: 캐시 풀에서 N개 가져와서 각 segment 합성 → 시청자 지루함 방지
    ladder_count = int(os.getenv("BROLL_LADDER_COUNT", "5"))
    brolls = get_broll_pool(category=category, n=ladder_count)
    # 풀 비어있으면 단일 다운로드 시도 → fallback chain
    if not brolls:
        single = get_stock_broll(category=category, duration_sec=duration)
        if single is None:
            single = pixelle_broll(category=category, duration_sec=duration)
        brolls = [single] if single else []
    broll = brolls[0] if brolls else None  # 단일 모드 호환

    work = output_mp4.parent / f"_splitscreen_{output_mp4.stem}"
    work.mkdir(parents=True, exist_ok=True)
    top_mp4 = work / "top.mp4"
    bottom_mp4 = work / "bottom.mp4"

    try:
        # Top: input 위 960px crop
        top_args = build_ffmpeg_args(
            "short_form",
            ["-i", str(input_mp4), "-vf", "crop=1080:960:0:0", "-an"],
            top_mp4,
        ) if False else [  # build_ffmpeg_args 는 audio 처리도 해서 -an 직접 안 먹음
            "-i", str(input_mp4),
            "-vf", "crop=1080:960:0:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-an", str(top_mp4),
        ]
        if not _ffmpeg_run(top_args, "split_top_crop"):
            return False

        # Bottom: B-roll ladder (N개) 또는 단일 또는 placeholder
        if len(brolls) >= 2:
            # Ladder: 각 segment 만들고 concat → 시청자 지루함 방지
            seg_dur = duration / len(brolls)
            seg_files: list[Path] = []
            for i, br in enumerate(brolls):
                seg = work / f"seg_{i:02d}.mp4"
                seg_args = [
                    "-stream_loop", "-1", "-i", str(br),
                    "-t", f"{seg_dur:.2f}",
                    "-vf", "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=30",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-an", str(seg),
                ]
                if not _ffmpeg_run(seg_args, f"split_bottom_seg_{i}"):
                    return False
                seg_files.append(seg)
            if not _concat_clips(seg_files, bottom_mp4):
                return False
            bot_args = None  # ladder 합성 완료, 아래 single-broll 분기 skip
            logger.info(f"split-screen ladder: {len(brolls)}개 B-roll, 각 {seg_dur:.1f}s")
        elif broll is not None and broll.exists():
            # 단일 B-roll → 1080x960 으로 scale + 길이 매칭
            bot_args = [
                "-stream_loop", "-1", "-i", str(broll),
                "-t", f"{duration:.2f}",
                "-vf", "scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-an", str(bottom_mp4),
            ]
        else:
            # Placeholder: 그라디언트 + 라벨
            font = _resolve_font_file()
            font_arg = f":fontfile='{font}'" if font else ""
            bot_args = [
                "-f", "lavfi",
                "-i", f"color=c=0x1e3a5f:size=1080x960:duration={duration:.2f}:rate=30",
                "-vf",
                f"format=yuv420p,drawbox=x=0:y=0:w=iw:h=ih:color=0x38bdf8@0.15:t=fill,"
                f"drawtext=text='InvestIQs'{font_arg}:fontsize=64:fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                "-an", str(bottom_mp4),
            ]
        # ladder 모드는 bot_args=None 이고 bottom_mp4 가 이미 concat 으로 생성됨
        if bot_args is not None:
            if not _ffmpeg_run(bot_args, "split_bottom_broll"):
                return False

        # vstack + 원본 audio 보존
        stack_args = [
            "-i", str(top_mp4), "-i", str(bottom_mp4), "-i", str(input_mp4),
            "-filter_complex", "[0:v][1:v]vstack=inputs=2[vout]",
            "-map", "[vout]", "-map", "2:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "copy", "-shortest",
            str(output_mp4),
        ]
        if not _ffmpeg_run(stack_args, "split_vstack"):
            return False

        return True
    finally:
        _sh.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    # 빠른 테스트: 음성 + 자막 + 차트 1개로 합성
    audio = Path("/tmp/tts_test/test.mp3")
    srt = Path("/tmp/tts_test/test.srt")
    out = Path("/tmp/tts_test/test_video.mp4")
    # 사용 가능한 차트 1개 찾기
    charts = list(WEB_STATIC.glob("images/*/etf-comparison.png"))[:1]
    if charts:
        print(f"테스트 차트: {charts[0]}")
        result = compose_video("test", audio, srt, [str(charts[0])], 12.5, out, aspect="9:16")
        print(f"결과: {result}")
