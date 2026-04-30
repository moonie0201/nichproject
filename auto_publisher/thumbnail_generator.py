"""
썸네일 생성기 — Pillow 기반, YouTube 1280×720
- 콘텐츠 타입(daily/study/weekly)별 레이아웃 자동 분기
- 5개 언어 지원 (NotoSansCJK-Bold)
- video_script.py 메타 또는 블로그 .md frontmatter에서 직접 파싱
"""

import re
import textwrap
import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── 경로 ──────────────────────────────────────────────
STATIC_DIR = Path("/home/mh/ocstorage/workspace/nichproject/web/static/images")
_FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
_FONT_REG  = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# ── 팔레트 ────────────────────────────────────────────
BG_DARK   = (15, 23, 42)       # #0f172a
BG_CARD   = (30, 41, 59)       # #1e293b
ACCENT_BLUE   = (56, 189, 248) # #38BDF8
ACCENT_YELLOW = (250, 204, 21) # #FACC15
ACCENT_GREEN  = (34, 197, 94)  # #22C55E
ACCENT_RED    = (239, 68, 68)  # #EF4444
WHITE     = (255, 255, 255)
GRAY      = (148, 163, 184)    # #94A3B8
DARK_TEXT = (203, 213, 225)    # #CBD5E1

# 콘텐츠 타입별 액센트 색상
TYPE_COLORS = {
    "daily":  ACCENT_BLUE,
    "weekly": ACCENT_GREEN,
    "study":  ACCENT_YELLOW,
    "default": ACCENT_BLUE,
}


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = _FONT_BOLD if bold else _FONT_REG
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _draw_rounded_rect(draw: ImageDraw.Draw, xy, radius: int, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.ellipse([x0, y0, x0 + radius*2, y0 + radius*2], fill=fill)
    draw.ellipse([x1 - radius*2, y0, x1, y0 + radius*2], fill=fill)
    draw.ellipse([x0, y1 - radius*2, x0 + radius*2, y1], fill=fill)
    draw.ellipse([x1 - radius*2, y1 - radius*2, x1, y1], fill=fill)


def _gradient_bg(img: Image.Image):
    """상단→하단 그라디언트 (BG_DARK → BG_CARD)"""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = y / h
        r = int(BG_DARK[0] + (BG_CARD[0] - BG_DARK[0]) * t)
        g = int(BG_DARK[1] + (BG_CARD[1] - BG_DARK[1]) * t)
        b = int(BG_DARK[2] + (BG_CARD[2] - BG_DARK[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """폰트 기준으로 max_width 넘지 않게 줄바꿈"""
    words = text.split()
    lines, current = [], ""
    dummy = Image.new("RGB", (1, 1))
    dd = ImageDraw.Draw(dummy)
    for word in words:
        test = (current + " " + word).strip()
        w = dd.textlength(test, font=font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _parse_frontmatter(md_path: Path) -> dict:
    """블로그 .md frontmatter 파싱 → 썸네일 메타 반환"""
    raw = md_path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    front = parts[1] if len(parts) >= 3 else ""

    def _get(key):
        m = re.search(rf'^{key}:\s*"?([^"\n]+)"?', front, re.MULTILINE)
        return m.group(1).strip() if m else ""

    title = _get("title")
    description = _get("description")
    date = _get("date")[:10] if _get("date") else ""

    # 핵심 숫자 추출 — 우선순위: ±%변화율 > S&P500 직후 수치
    body = parts[2] if len(parts) >= 3 else ""
    text = title + " " + description

    # 1순위: +/-로 시작하는 퍼센트 (수익률/등락률)
    pct_matches = re.findall(r"([+-]\d+[\d.,]*%)", text)
    key_num = pct_matches[0].strip() if pct_matches else ""

    # 2순위: S&P500/나스닥 뒤에 오는 수치
    if not key_num:
        m = re.search(
            r"(?:S&P\s*500|나스닥|NASDAQ|SP500)[^\d]*([+-]?\d+[\d.,]*%?)",
            text
        )
        if m:
            key_num = m.group(1).strip()

    return {
        "title": title,
        "description": description,
        "date": date,
        "key_num": key_num,
    }


def _detect_content_type(md_path: Path) -> str:
    parts = md_path.parts
    if "daily" in parts:
        return "daily"
    if "weekly" in parts:
        return "weekly"
    if "study" in parts:
        return "study"
    return "default"


def _detect_lang(md_path: Path) -> str:
    for lang in ("ko", "en", "ja", "vi", "id"):
        if f"/{lang}/" in str(md_path):
            return lang
    return "ko"


def _label_for_type(content_type: str, lang: str) -> str:
    labels = {
        "daily": {"ko": "일일 시황", "en": "DAILY MARKET", "ja": "デイリー市況",
                  "vi": "THỊ TRƯỜNG", "id": "PASAR HARIAN"},
        "weekly": {"ko": "주간 시황", "en": "WEEKLY WRAP", "ja": "ウィークリー",
                   "vi": "TUẦN", "id": "MINGGUAN"},
        "study": {"ko": "투자 분석", "en": "ANALYSIS", "ja": "投資分析",
                  "vi": "PHÂN TÍCH", "id": "ANALISIS"},
        "default": {"ko": "InvestIQs", "en": "InvestIQs", "ja": "InvestIQs",
                    "vi": "InvestIQs", "id": "InvestIQs"},
    }
    return labels.get(content_type, {}).get(lang, "InvestIQs")


# ─────────────────────────────────────────────────────
# 레이아웃 함수
# ─────────────────────────────────────────────────────

def _layout_daily(draw: ImageDraw.Draw, meta: dict, accent: tuple, lang: str):
    """일일 시황: 지수 수치 대형 + 날짜 + 제목"""
    W, H = 1280, 720

    # 좌측 액센트 바
    draw.rectangle([0, 0, 10, H], fill=accent)

    # 카테고리 배지 (상단 좌)
    label = _label_for_type("daily", lang)
    f_badge = _font(26)
    _draw_rounded_rect(draw, [36, 36, 36 + draw.textlength(label, f_badge) + 32, 80], 8, accent)
    draw.text((52, 44), label, font=f_badge, fill=BG_DARK)

    # 날짜 (우측 상단)
    if meta.get("date"):
        f_date = _font(24, bold=False)
        draw.text((W - 200, 44), meta["date"], font=f_date, fill=GRAY)

    # 핵심 숫자 (중앙 대형)
    key_num = meta.get("key_num", "")
    if key_num:
        f_num = _font(120)
        num_w = draw.textlength(key_num, f_num)
        color = ACCENT_GREEN if "+" in key_num else (ACCENT_RED if "-" in key_num else ACCENT_YELLOW)
        draw.text(((W - num_w) / 2, 160), key_num, font=f_num, fill=color)

    # 제목 (하단 2/3)
    title = meta.get("title", "")
    f_title = _font(48)
    lines = _wrap_text(title, f_title, W - 120)[:3]
    y = 360 if key_num else 240
    for line in lines:
        lw = draw.textlength(line, f_title)
        draw.text(((W - lw) / 2, y), line, font=f_title, fill=WHITE)
        y += 62

    # 브랜딩 (하단 우측)
    f_brand = _font(28, bold=False)
    draw.text((W - 180, H - 54), "InvestIQs", font=f_brand, fill=GRAY)


def _layout_study(draw: ImageDraw.Draw, meta: dict, accent: tuple, lang: str):
    """투자 분석: 제목 중심 + 핵심 지표 배지"""
    W, H = 1280, 720

    # 상단 컬러 바
    draw.rectangle([0, 0, W, 8], fill=accent)

    # 좌측 세로 라인 장식
    draw.rectangle([60, 120, 68, H - 80], fill=(*accent, 120))

    # 카테고리 배지
    label = _label_for_type("study", lang)
    f_badge = _font(24)
    badge_w = int(draw.textlength(label, f_badge)) + 32
    _draw_rounded_rect(draw, [88, 48, 88 + badge_w, 88], 8, accent)
    draw.text((104, 55), label, font=f_badge, fill=BG_DARK)

    # 날짜
    if meta.get("date"):
        f_date = _font(22, bold=False)
        draw.text((W - 200, 56), meta["date"], font=f_date, fill=GRAY)

    # 제목 (메인)
    title = meta.get("title", "")
    f_title = _font(54)
    lines = _wrap_text(title, f_title, W - 180)[:3]
    y = 150
    for line in lines:
        draw.text((88, y), line, font=f_title, fill=WHITE)
        y += 70

    # 설명 한 줄
    desc = meta.get("description", "")
    if desc:
        f_desc = _font(30, bold=False)
        desc_lines = _wrap_text(desc, f_desc, W - 180)[:2]
        for dl in desc_lines:
            draw.text((88, y + 20), dl, font=f_desc, fill=DARK_TEXT)
            y += 40

    # 핵심 숫자 배지 (우하단)
    key_num = meta.get("key_num", "")
    if key_num:
        f_num = _font(64)
        num_w = int(draw.textlength(key_num, f_num))
        px, py = W - num_w - 80, H - 140
        _draw_rounded_rect(draw, [px - 20, py - 10, px + num_w + 20, py + 80], 12, BG_CARD)
        color = ACCENT_GREEN if "+" in key_num else (ACCENT_RED if "-" in key_num else accent)
        draw.text((px, py), key_num, font=f_num, fill=color)

    # 브랜딩
    f_brand = _font(26, bold=False)
    draw.text((88, H - 52), "InvestIQs", font=f_brand, fill=GRAY)


def _layout_weekly(draw: ImageDraw.Draw, meta: dict, accent: tuple, lang: str):
    """주간 시황: 주차 강조 + 제목"""
    W, H = 1280, 720

    # 배경 카드
    draw.rectangle([40, 40, W - 40, H - 40], fill=BG_CARD)
    draw.rectangle([40, 40, W - 40, 48], fill=accent)
    draw.rectangle([40, H - 48, W - 40, H - 40], fill=accent)

    # 카테고리 배지
    label = _label_for_type("weekly", lang)
    f_badge = _font(26)
    badge_w = int(draw.textlength(label, f_badge)) + 32
    _draw_rounded_rect(draw, [72, 72, 72 + badge_w, 112], 8, accent)
    draw.text((88, 79), label, font=f_badge, fill=BG_DARK)

    if meta.get("date"):
        f_date = _font(24, bold=False)
        draw.text((W - 220, 79), meta["date"], font=f_date, fill=GRAY)

    # 제목
    title = meta.get("title", "")
    f_title = _font(52)
    lines = _wrap_text(title, f_title, W - 180)[:3]
    y = 160
    for line in lines:
        draw.text((72, y), line, font=f_title, fill=WHITE)
        y += 68

    # 설명
    desc = meta.get("description", "")
    if desc:
        f_desc = _font(30, bold=False)
        desc_lines = _wrap_text(desc, f_desc, W - 180)[:2]
        for dl in desc_lines:
            draw.text((72, y + 16), dl, font=f_desc, fill=DARK_TEXT)
            y += 40

    # 브랜딩
    f_brand = _font(26, bold=False)
    draw.text((W - 200, H - 80), "InvestIQs", font=f_brand, fill=GRAY)


# ─────────────────────────────────────────────────────
# 공개 인터페이스
# ─────────────────────────────────────────────────────

def generate_thumbnail(
    slug: str,
    title: str,
    description: str = "",
    key_num: str = "",
    date: str = "",
    content_type: str = "study",
    lang: str = "ko",
    out_dir: Path | None = None,
) -> Path:
    """썸네일 PNG 생성 → 저장 경로 반환"""
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), BG_DARK)
    _gradient_bg(img)
    draw = ImageDraw.Draw(img)

    accent = TYPE_COLORS.get(content_type, ACCENT_BLUE)
    meta = {"title": title, "description": description,
            "key_num": key_num, "date": date}

    if content_type == "daily":
        _layout_daily(draw, meta, accent, lang)
    elif content_type == "weekly":
        _layout_weekly(draw, meta, accent, lang)
    else:
        _layout_study(draw, meta, accent, lang)

    out_dir = out_dir or (STATIC_DIR / slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "thumbnail.png"
    img.save(out_path, "PNG", optimize=True)
    logger.info(f"썸네일 생성: {out_path}")
    return out_path


def generate_thumbnail_from_md(md_path: Path) -> Path | None:
    """블로그 .md 파일 경로만으로 썸네일 자동 생성"""
    md_path = Path(md_path)
    if not md_path.exists():
        logger.error(f"파일 없음: {md_path}")
        return None

    meta = _parse_frontmatter(md_path)
    content_type = _detect_content_type(md_path)
    lang = _detect_lang(md_path)
    slug = md_path.stem

    return generate_thumbnail(
        slug=slug,
        title=meta["title"],
        description=meta["description"],
        key_num=meta["key_num"],
        date=meta["date"],
        content_type=content_type,
        lang=lang,
    )


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    # 테스트: 3가지 타입 생성
    test_cases = [
        dict(slug="test-daily", title="미국 증시 마감 S&P500 -0.49% 나스닥 -1.01%",
             description="관세 우려 재부각으로 하락 마감", key_num="-0.49%",
             date="2026-04-30", content_type="daily", lang="ko"),
        dict(slug="test-study", title="VOO vs SCHD 5년 누적수익률 분석",
             description="배당률 가설이 깨지는 지점 데이터 검증", key_num="+108%",
             date="2026-04-30", content_type="study", lang="ko"),
        dict(slug="test-weekly", title="4월 4주차 주간 시황 — S&P500 -0.73%",
             description="관세 협상 불확실성 속 변동성 확대", key_num="-0.73%",
             date="2026-04-30", content_type="weekly", lang="ko"),
    ]

    out_dir = Path("/tmp/thumb_test")
    for tc in test_cases:
        tc["out_dir"] = out_dir
        path = generate_thumbnail(**tc)
        print(f"생성: {path}")

    # md 파일로 직접 테스트 (있으면)
    if len(sys.argv) > 1:
        result = generate_thumbnail_from_md(Path(sys.argv[1]))
        print(f"md→썸네일: {result}")
