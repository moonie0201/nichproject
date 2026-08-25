"""Branding clips: intro card, chapter transitions, outro card, lower-third overlay.
Pure ffmpeg lavfi + drawtext. No Pillow needed.
Env flags: VIDEO_BRANDING=1, VIDEO_LOWER_THIRD=1, BLOG_URL_HINT=investiqs.net
"""
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _escape_drawtext(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")


def _vc():
    """Lazy import of video_composer helpers to avoid circular import."""
    import auto_publisher.video_composer as vc
    return vc


def _make_branding_clip(filter_expr: str, out_path: Path, duration_sec: float) -> bool:
    vc = _vc()
    codec = os.getenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    preset = os.getenv("FFMPEG_PRESET", "p1")
    args = [
        "-f", "lavfi", "-i", filter_expr,
        "-t", f"{duration_sec:.2f}",
        "-c:v", codec, "-preset", preset,
        "-pix_fmt", "yuv420p", "-r", "30",
        str(out_path),
    ]
    return vc._ffmpeg_run(args, f"branding:{out_path.name}")


def make_intro_clip(title: str, out_path: Path, width: int, height: int,
                    duration_sec: float = 2.5) -> bool:
    """InvestIQs logo + title + date, fade-in/out."""
    vc = _vc()
    font_arg = ""
    try:
        fp = vc._resolve_font_file()
        if fp:
            font_arg = f":fontfile='{fp}'"
    except Exception:
        pass

    try:
        title_safe = vc._escape_drawtext(title[:40])
    except Exception:
        title_safe = _escape_drawtext(title[:40])

    date_str = datetime.now().strftime("%Y.%m.%d")
    fade_in = 0.4
    fade_out = 0.3
    d = duration_sec

    filter_expr = (
        f"color=c=0x0f172a:s={width}x{height}:d={d:.2f}:r=30,"
        f"drawbox=x=0:y=(ih*0.46):w=iw:h=8:color=0x38BDF8:t=fill,"
        f"drawtext=text='InvestIQs'{font_arg}:fontsize={int(height*0.10)}:fontcolor=0x38BDF8:"
        f"x=(w-text_w)/2:y=(h*0.28):"
        f"alpha='if(lt(t,{fade_in}),t/{fade_in},if(gt(t,{d-fade_out:.2f}),max(0,({d}-t)/{fade_out}),1))',"
        f"drawtext=text='{title_safe}'{font_arg}:fontsize={int(height*0.04)}:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h*0.54):"
        f"alpha='if(lt(t,0.6),max(0,(t-0.2)/0.4),1)',"
        f"drawtext=text='{date_str}'{font_arg}:fontsize={int(height*0.035)}:fontcolor=0xFACC15:"
        f"x=(w-text_w)/2:y=(h*0.68)"
    )
    return _make_branding_clip(filter_expr, out_path, duration_sec)


def make_transition_clip(label: str, out_path: Path, width: int, height: int,
                         duration_sec: float = 0.6) -> bool:
    """Brief colored chapter transition card."""
    vc = _vc()
    font_arg = ""
    try:
        fp = vc._resolve_font_file()
        if fp:
            font_arg = f":fontfile='{fp}'"
    except Exception:
        pass
    try:
        safe = vc._escape_drawtext(label[:20])
    except Exception:
        safe = _escape_drawtext(label[:20])

    d = duration_sec
    filter_expr = (
        f"color=c=0x38BDF8:s={width}x{height}:d={d:.2f}:r=30,"
        f"drawtext=text='{safe}'{font_arg}:fontsize={int(height*0.07)}:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"alpha='if(lt(t,0.15),t/0.15,if(gt(t,{d-0.15:.2f}),max(0,({d}-t)/0.15),1))'"
    )
    return _make_branding_clip(filter_expr, out_path, duration_sec)


def make_outro_clip(blog_url: str, out_path: Path, width: int, height: int,
                    duration_sec: float = 3.0) -> bool:
    """Subscribe + blog CTA card."""
    vc = _vc()
    font_arg = ""
    try:
        fp = vc._resolve_font_file()
        if fp:
            font_arg = f":fontfile='{fp}'"
    except Exception:
        pass

    url_short = blog_url.replace("https://", "").replace("http://", "")[:40]
    try:
        url_safe = vc._escape_drawtext(url_short)
    except Exception:
        url_safe = _escape_drawtext(url_short)

    d = duration_sec
    filter_expr = (
        f"color=c=0x0f172a:s={width}x{height}:d={d:.2f}:r=30,"
        f"drawbox=x=0:y=0:w=iw:h=10:color=0xFACC15:t=fill,"
        f"drawtext=text='구독 + 알림 설정'{font_arg}:fontsize={int(height*0.08)}:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h*0.28),"
        f"drawtext=text='전체 분석'{font_arg}:fontsize={int(height*0.045)}:fontcolor=0x38BDF8:"
        f"x=(w-text_w)/2:y=(h*0.52),"
        f"drawtext=text='{url_safe}'{font_arg}:fontsize={int(height*0.038)}:fontcolor=0xFACC15:"
        f"x=(w-text_w)/2:y=(h*0.65)"
    )
    return _make_branding_clip(filter_expr, out_path, duration_sec)


def make_lower_third_overlay(chapter_title: str, base_clip: Path, out_path: Path,
                             show_from_sec: float = 0.5, show_until_sec: float = 4.5) -> bool:
    """Overlay translucent chapter title strip on existing clip."""
    vc = _vc()
    font_arg = ""
    try:
        fp = vc._resolve_font_file()
        if fp:
            font_arg = f":fontfile='{fp}'"
    except Exception:
        pass
    try:
        safe = vc._escape_drawtext(chapter_title[:30])
    except Exception:
        safe = _escape_drawtext(chapter_title[:30])

    enable = f"between(t,{show_from_sec:.2f},{show_until_sec:.2f})"
    codec = os.getenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    preset = os.getenv("FFMPEG_PRESET", "p1")
    vf = (
        f"drawbox=x=64:y=ih-180:w=iw-128:h=110:color=black@0.6:t=fill:enable='{enable}',"
        f"drawbox=x=64:y=ih-180:w=8:h=110:color=0x38BDF8:t=fill:enable='{enable}',"
        f"drawtext=text='{safe}'{font_arg}:fontsize=44:fontcolor=white:"
        f"x=96:y=h-150:enable='{enable}'"
    )
    args = [
        "-i", str(base_clip),
        "-vf", vf,
        "-c:v", codec, "-preset", preset,
        "-c:a", "copy",
        str(out_path),
    ]
    return vc._ffmpeg_run(args, "lower_third")
