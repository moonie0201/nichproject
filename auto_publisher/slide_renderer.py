"""Pillow 로 PPT 슬라이드 PNG 렌더 (1920×1080 16:9 롱폼용).

레이아웃:
    ┌──────────────────────────────────────┬─────────┐
    │  제목 (88pt, bold)                  │ accent  │
    │                                     │ 그라    │
    │  • bullet 1 (44pt)                  │ 디언트  │
    │  • bullet 2                         │         │
    │  • bullet 3                         │         │
    │                                     │  i/N    │
    └──────────────────────────────────────┴─────────┘

색상: 배경 #0F172A 다크, 텍스트 #F1F5F9, accent_color 그라디언트 우측.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


CANVAS_W = 1920
CANVAS_H = 1080
ACCENT_PANEL_W = 480  # 우측 accent 영역
TEXT_AREA_PAD = 96


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _wrap_text(text: str, font, max_width: int, draw) -> list[str]:
    """글자 단위 wrapping (한국어/영문 mix 지원)."""
    if not text:
        return []
    lines = []
    current = ""
    for ch in text:
        candidate = current + ch
        bbox = draw.textbbox((0, 0), candidate, font=font)
        w = bbox[2] - bbox[0]
        if w > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _draw_gradient_panel(img, x_start: int, accent_rgb: tuple[int, int, int]) -> None:
    """우측 accent 그라디언트 패널 (수직 페이드)."""
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    base_r, base_g, base_b = accent_rgb
    panel_w = CANVAS_W - x_start
    for y in range(CANVAS_H):
        # 위쪽은 진하게, 아래쪽으로 갈수록 밝게
        t = y / CANVAS_H
        r = int(base_r * (0.7 + 0.3 * (1 - t)))
        g = int(base_g * (0.7 + 0.3 * (1 - t)))
        b = int(base_b * (0.7 + 0.3 * (1 - t)))
        draw.rectangle([x_start, y, CANVAS_W, y + 1], fill=(r, g, b))


def render_slide(slide: dict, out_path: Path, page: int, total: int,
                 brand: str = "investiqs.net") -> bool:
    """슬라이드 1개 → PNG (1920x1080). 실패 시 False."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.error("Pillow 미설치 → 슬라이드 렌더 불가")
        return False

    from auto_publisher.video_composer import _resolve_font_file
    font_path = _resolve_font_file()
    if not font_path:
        logger.warning("한국어 폰트 못 찾음 → 슬라이드 렌더 실패")
        return False

    try:
        font_title = ImageFont.truetype(font_path, 88)
        font_bullet = ImageFont.truetype(font_path, 44)
        font_meta = ImageFont.truetype(font_path, 28)
    except OSError as e:
        logger.warning(f"폰트 로드 실패: {e}")
        return False

    # 캔버스 + 배경 다크
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), color=(15, 23, 42))  # #0F172A
    accent_rgb = _hex_to_rgb(slide.get("accent_color", "#1E40AF"))
    _draw_gradient_panel(img, CANVAS_W - ACCENT_PANEL_W, accent_rgb)
    draw = ImageDraw.Draw(img)

    # 좌측 컬러 액센트 바 (8px)
    draw.rectangle([0, 0, 8, CANVAS_H], fill=accent_rgb)

    # 제목 (왼쪽 위)
    text_area_w = CANVAS_W - ACCENT_PANEL_W - TEXT_AREA_PAD * 2
    title = slide.get("title", "")
    title_lines = _wrap_text(title, font_title, text_area_w, draw)
    y = TEXT_AREA_PAD + 40
    for line in title_lines[:2]:
        draw.text((TEXT_AREA_PAD, y), line, font=font_title, fill=(241, 245, 249))
        y += 100

    # 제목과 bullets 사이 가로선 (accent_color)
    y += 24
    draw.rectangle([TEXT_AREA_PAD, y, TEXT_AREA_PAD + 120, y + 4], fill=accent_rgb)
    y += 52

    # bullets
    bullets = slide.get("bullets", [])
    for bullet in bullets[:5]:
        # 마커
        draw.text((TEXT_AREA_PAD, y), "▶", font=font_bullet, fill=accent_rgb)
        # 본문
        bullet_lines = _wrap_text(bullet, font_bullet, text_area_w - 60, draw)
        for j, line in enumerate(bullet_lines[:2]):
            draw.text((TEXT_AREA_PAD + 60, y), line, font=font_bullet, fill=(226, 232, 240))
            y += 64
        y += 16

    # 우하단 페이지 번호 + 브랜드 (accent 패널 안)
    page_text = f"{page}/{total}"
    bbox = draw.textbbox((0, 0), page_text, font=font_meta)
    pw = bbox[2] - bbox[0]
    draw.text((CANVAS_W - ACCENT_PANEL_W // 2 - pw // 2, CANVAS_H - 100),
              page_text, font=font_meta, fill=(255, 255, 255))
    bbox = draw.textbbox((0, 0), brand, font=font_meta)
    bw = bbox[2] - bbox[0]
    draw.text((CANVAS_W - ACCENT_PANEL_W // 2 - bw // 2, CANVAS_H - 60),
              brand, font=font_meta, fill=(255, 255, 255, 200))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return True


def render_slides(slides: list[dict], out_dir: Path, brand: str = "investiqs.net") -> list[Path]:
    """슬라이드 리스트 → PNG 파일 리스트. 실패한 슬라이드는 skip."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    total = len(slides)
    for i, slide in enumerate(slides, start=1):
        out = out_dir / f"slide_{i:02d}.png"
        if render_slide(slide, out, i, total, brand=brand):
            paths.append(out)
    return paths
