"""Pillow + ffmpeg motion graphics — count-up number cards and typewriter text cards.

No new dependencies. Pillow already used by slide_renderer.py and thumbnail_generator.py.
Frames rendered as PNG sequence to temp dir, then muxed to mp4 via ffmpeg.

Env: VIDEO_ANIMATED_CARDS=1 (default on)
"""
import logging
import re
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)
_FPS = 30


def _resolve_font(size: int) -> ImageFont.FreeTypeFont:
    """Get Noto Sans CJK KR font, fallback to default."""
    # Reuse video_composer's font resolver
    try:
        from auto_publisher.video_composer import _resolve_font_file
        fp = _resolve_font_file()
        if fp and Path(fp).exists():
            return ImageFont.truetype(fp, size)
    except Exception:
        pass
    # fc-match fallback
    try:
        import subprocess
        r = subprocess.run(["fc-match", "--format=%{file}", "Noto Sans CJK KR"],
                           capture_output=True, text=True, timeout=5)
        fp = r.stdout.strip()
        if fp and Path(fp).exists():
            return ImageFont.truetype(fp, size)
    except Exception:
        pass
    return ImageFont.load_default()


def _parse_number(value_str: str) -> tuple[float, str]:
    """'7.85%' -> (7.85, '%'); '$420.5B' -> (420.5, 'B'); '15년' -> (15.0, '년')."""
    m = re.search(r"(-?\d[\d,]*\.?\d*)", str(value_str))
    if not m:
        return (0.0, str(value_str))
    raw = m.group(1).replace(",", "")
    val = float(raw)
    suffix = str(value_str)[m.end():].strip() or str(value_str)[:m.start()].strip()
    return (val, suffix)


def _ease_out_quart(t: float) -> float:
    return 1.0 - (1.0 - min(t, 1.0)) ** 4


def _mux_frames(frames_dir: Path, out_path: Path, duration_sec: float) -> bool:
    """PNG sequence -> mp4 via ffmpeg. Uses same codec as rest of pipeline."""
    import os
    from auto_publisher.video_composer import _ffmpeg_run
    codec = os.getenv("FFMPEG_VIDEO_CODEC", "h264_nvenc")
    preset = os.getenv("FFMPEG_PRESET", "p1")
    args = [
        "-framerate", str(_FPS),
        "-i", str(frames_dir / "f%05d.png"),
        "-t", f"{duration_sec:.2f}",
        "-c:v", codec, "-preset", preset,
        "-pix_fmt", "yuv420p", "-r", str(_FPS),
        str(out_path),
    ]
    return _ffmpeg_run(args, f"motion_card:{out_path.name}")


def make_animated_number_clip(
    value: str, label: str, unit: str,
    duration_sec: float, out_path: Path,
    width: int = 1920, height: int = 1080,
    bg_color: str = "#0f172a",
    number_color: str = "#FACC15",
) -> bool:
    """Count-up animation: 0 → value over 60% of duration, hold 40%."""
    target, parsed_unit = _parse_number(value)
    unit = unit or parsed_unit
    total_frames = max(int(duration_sec * _FPS), 1)
    countup_frames = max(int(total_frames * 0.6), 1)
    work = out_path.parent / f"_mn_{out_path.stem}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        label_font = _resolve_font(56)
        num_font = _resolve_font(int(height * 0.22))
        unit_font = _resolve_font(int(height * 0.10))

        is_int = "." not in str(value).replace(unit, "")
        for i in range(total_frames):
            t = min(i / max(countup_frames - 1, 1), 1.0)
            current = target * _ease_out_quart(t)
            img = Image.new("RGB", (width, height), bg_color)
            d = ImageDraw.Draw(img)
            # Label
            d.text((width // 2, int(height * 0.20)), label, fill="#CBD5E1",
                   font=label_font, anchor="mm")
            # Number
            num_text = str(int(round(current))) if is_int else f"{current:.2f}"
            if i >= countup_frames:
                num_text = str(int(target)) if is_int else f"{target:.2f}"
            d.text((width // 2, int(height * 0.50)), num_text, fill=number_color,
                   font=num_font, anchor="mm")
            # Unit
            d.text((width // 2, int(height * 0.72)), unit, fill="#FFFFFF",
                   font=unit_font, anchor="mm")
            img.save(work / f"f{i:05d}.png", optimize=False)
        return _mux_frames(work, out_path, duration_sec)
    except Exception as e:
        logger.warning("make_animated_number_clip 실패: %s", e)
        return False
    finally:
        shutil.rmtree(work, ignore_errors=True)


def make_typewriter_card_clip(
    text: str, duration_sec: float, out_path: Path,
    width: int = 1920, height: int = 1080,
    bg_color: str = "#0f172a",
    text_color: str = "#FFFFFF",
    accent: str = "InvestIQs Research",
) -> bool:
    """Character-by-character typewriter. Reveal completes at 80% of duration."""
    from textwrap import wrap
    total_frames = max(int(duration_sec * _FPS), 1)
    reveal_frames = max(int(total_frames * 0.8), 1)
    chars_per_frame = max(len(text) / reveal_frames, 0.5)
    work = out_path.parent / f"_tw_{out_path.stem}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        body_font = _resolve_font(int(height * 0.06))
        accent_font = _resolve_font(28)
        line_h = int(height * 0.10)
        for i in range(total_frames):
            n = min(int(i * chars_per_frame), len(text))
            shown = text[:n]
            cursor = "|" if (i < reveal_frames and (i // 15) % 2 == 0) else ""
            img = Image.new("RGB", (width, height), bg_color)
            d = ImageDraw.Draw(img)
            d.text((96, 80), accent, fill="#38BDF8", font=accent_font)
            lines = wrap(shown + cursor, width=max(int(width / (height * 0.05)), 20))
            for li, ln in enumerate(lines[:6]):
                d.text((96, 220 + li * line_h), ln, fill=text_color, font=body_font)
            img.save(work / f"f{i:05d}.png", optimize=False)
        return _mux_frames(work, out_path, duration_sec)
    except Exception as e:
        logger.warning("make_typewriter_card_clip 실패: %s", e)
        return False
    finally:
        shutil.rmtree(work, ignore_errors=True)


def detect_chapter_animation_type(chapter: dict, source_data_points: list | None = None) -> str:
    """Return 'animated_number' | 'typewriter' | 'static'.

    animated_number: data/evidence/risk chapters with a number present
    typewriter: hook/contrarian/cta chapters
    static: everything else (existing Ken Burns)
    """
    title = chapter.get("title", "")
    text = chapter.get("text", "")
    has_number = bool(re.search(r"\d", text))
    data_keywords = ("데이터", "Data", "근거", "리스크", "위험", "수익", "수치")
    hook_keywords = ("Hook", "반전", "정리", "CTA", "프레임", "문제")
    if any(k in title for k in data_keywords) and has_number:
        return "animated_number"
    if any(k in title for k in hook_keywords):
        return "typewriter"
    return "static"
