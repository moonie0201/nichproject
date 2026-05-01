"""
영상 합성 — ffmpeg 기반
- 차트 PNG 슬라이드쇼 + Ken Burns 효과
- TTS 음성 오버레이
- SRT 자막 burned-in (가독성 고대비)
- 롱폼 (16:9, 1920x1080) / 쇼츠 (9:16, 1080x1920) 자동 분기
"""

import logging
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
    args = [
        "-f", "lavfi", "-i", filter_expr,
        "-c:v", os.getenv("FFMPEG_VIDEO_CODEC", "h264_nvenc"),
        "-preset", os.getenv("FFMPEG_PRESET", "p1"),
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
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
                       width: int, height: int) -> bool:
    """단일 이미지 → Ken Burns(zoom-in) 영상 클립"""
    fps = 30
    total_frames = int(duration_sec * fps)
    zoom_expr = f"zoom='min(zoom+0.0008,1.15)'"
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

    srt_escaped = str(srt_path.absolute()).replace(":", "\\:").replace("'", "\\'")
    if is_shorts:
        # 하단 960px 영역 중앙: 전체 1920에서 bottom 기준 440px 위 = 하단 절반 중앙
        sub_style = (
            "FontName=Noto Sans CJK KR,FontSize=32,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,Outline=3,Shadow=0,Alignment=2,MarginV=440"
        )
    else:
        sub_style = (
            "FontName=Noto Sans CJK KR,FontSize=18,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,Outline=2,Shadow=0,Alignment=2,MarginV=80"
        )

    sub_filter = f"subtitles='{srt_escaped}':force_style='{sub_style}'"
    filter_complex = f"{pad_filter}{video_in}{sub_filter}[vout]"

    args = [
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "1:a",
        "-c:v", os.getenv("FFMPEG_VIDEO_CODEC", "h264_nvenc"),
        "-preset", os.getenv("FFMPEG_PRESET", "p1"),
        "-c:a", "aac",
        "-b:a", "192k", "-shortest",
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

    per_chart_sec = max(audio_duration_sec / max(len(valid_charts), 1), 3.0)

    work_dir = audio_path.parent / f"{slug}_clips"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        clip_paths = []
        if not valid_charts:
            logger.warning("유효한 차트 없음 — fallback 카드 비주얼로 합성")
            cards = _build_fallback_cards(fallback_visual_plan, visual_beats, source_data_points)
            per_card_sec = max(audio_duration_sec / max(len(cards), 1), 3.5)
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
                if not _make_kenburns_clip(chart, per_chart_sec, clip_out, img_w, img_h):
                    logger.warning(f"클립 생성 실패: {chart}")
                    continue
                clip_paths.append(clip_out)

        if not clip_paths:
            logger.error("생성된 클립 없음")
            return None

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

        logger.info(f"영상 합성 완료: {out_path}")
        return out_path
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


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
