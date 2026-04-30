"""다국어 시황 i18n 텍스트 모듈 — TDD 테스트.

언어별 dict 구조:
- title_pattern_wrap / intraday / weekly: 제목 템플릿 (Python format placeholder)
- section_headers: H2 라벨 (지수/섹터/내러티브/캘린더/액션)
- disclaimer_banner_html: 정보 제공 배너 HTML
- footer_disclaimer: 마지막 면책
- summary_label: '요약' 라벨
- categories: frontmatter categories (시장분석/일일/주간)
- tags_extra: 언어별 추가 태그
"""

import re
import pytest


SUPPORTED_LANGS = ("en", "ja", "vi", "id")


# ── 1. 모듈 구조 검증 ──────────────────────────────────────────

def test_get_i18n_returns_dict_for_each_lang():
    from auto_publisher.i18n_market import get_i18n
    for lang in SUPPORTED_LANGS + ("ko",):
        d = get_i18n(lang)
        assert isinstance(d, dict)
        # 핵심 키들이 있어야 함
        for key in (
            "title_pattern_wrap", "title_pattern_intraday", "title_pattern_weekly",
            "section_h2_index", "section_h2_sector", "section_h2_narrative",
            "section_h2_calendar", "section_h2_action",
            "disclaimer_banner_html", "footer_disclaimer",
            "summary_label", "categories_market", "tags_extra",
        ):
            assert key in d, f"{lang}: missing key '{key}'"


def test_unsupported_lang_falls_back_to_en():
    from auto_publisher.i18n_market import get_i18n
    d_unknown = get_i18n("xx")
    d_en = get_i18n("en")
    # 알 수 없는 언어는 en 으로 대체
    assert d_unknown["title_pattern_wrap"] == d_en["title_pattern_wrap"]


# ── 2. 제목 패턴 ──────────────────────────────────────────────

def test_en_title_wrap_format():
    from auto_publisher.i18n_market import get_i18n
    d = get_i18n("en")
    title = d["title_pattern_wrap"].format(
        date="April 24, 2026", spy_pct="+0.42%", qqq_pct="+0.81%", spy_price="$653.14",
    )
    assert "Market Close" in title or "Daily Wrap" in title or "Closing" in title
    assert "S&P 500" in title or "S&P500" in title


def test_ja_title_wrap_contains_japanese():
    from auto_publisher.i18n_market import get_i18n
    d = get_i18n("ja")
    title = d["title_pattern_wrap"].format(
        date="2026年4月24日", spy_pct="+0.42%", qqq_pct="+0.81%", spy_price="$653",
    )
    # 일본어 마감/시장 표현
    assert any(kw in title for kw in ("米国市場", "米国株", "終値", "S&P"))


def test_vi_title_contains_vietnamese():
    from auto_publisher.i18n_market import get_i18n
    d = get_i18n("vi")
    title = d["title_pattern_wrap"].format(
        date="24/04/2026", spy_pct="+0.42%", qqq_pct="+0.81%", spy_price="$653",
    )
    assert any(kw in title for kw in ("Thị trường", "Mỹ", "S&P"))


def test_id_title_contains_indonesian():
    from auto_publisher.i18n_market import get_i18n
    d = get_i18n("id")
    title = d["title_pattern_wrap"].format(
        date="24 April 2026", spy_pct="+0.42%", qqq_pct="+0.81%", spy_price="$653",
    )
    assert any(kw in title for kw in ("Pasar", "Saham", "AS", "S&P"))


# ── 3. 섹션 헤더 ──────────────────────────────────────────────

def test_en_section_headers_are_english():
    from auto_publisher.i18n_market import get_i18n
    d = get_i18n("en")
    # 영어 섹션 헤더는 한글이 없어야 함
    for key in ("section_h2_index", "section_h2_sector", "section_h2_narrative"):
        val = d[key]
        assert not re.search(r"[가-힣]", val), f"{key} 에 한글이 포함됨: {val}"


def test_ja_section_headers_are_japanese():
    from auto_publisher.i18n_market import get_i18n
    d = get_i18n("ja")
    h2 = d["section_h2_index"] + d["section_h2_sector"]
    # 적어도 일본어 문자(히라가나/카타카나/한자) 포함
    assert re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", h2)


# ── 4. 면책/배너 ──────────────────────────────────────────────

def test_en_disclaimer_in_english():
    from auto_publisher.i18n_market import get_i18n
    d = get_i18n("en")
    text = d["disclaimer_banner_html"] + d["footer_disclaimer"]
    # 영어 disclaimer 키워드
    assert any(kw.lower() in text.lower() for kw in (
        "informational", "not investment advice", "responsibility", "no warranty"
    ))
    # 한글 비포함
    assert not re.search(r"[가-힣]", text)


def test_ja_disclaimer_in_japanese():
    from auto_publisher.i18n_market import get_i18n
    d = get_i18n("ja")
    text = d["disclaimer_banner_html"] + d["footer_disclaimer"]
    assert re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", text)


# ── 5. 카테고리 + 태그 ────────────────────────────────────────

def test_each_lang_has_3_market_categories():
    from auto_publisher.i18n_market import get_i18n
    for lang in SUPPORTED_LANGS + ("ko",):
        d = get_i18n(lang)
        cats = d.get("categories_market", {})
        # 최소 3개 카테고리 키: market_analysis / us_market / daily (or 주간 별도)
        assert "market_analysis" in cats
        assert "us_market" in cats
        assert "daily_market" in cats
        assert "weekly_market" in cats


def test_no_korean_in_non_ko_categories():
    from auto_publisher.i18n_market import get_i18n
    for lang in SUPPORTED_LANGS:
        d = get_i18n(lang)
        cats_str = " ".join(d["categories_market"].values())
        assert not re.search(r"[가-힣]", cats_str), f"{lang}: 카테고리에 한글이 포함됨: {cats_str}"


# ── 6. 금칙어 검사 — 다국어 본문에 한글 금칙어가 들어가면 안 됨 ──

def test_en_disclaimer_no_korean_forbidden_phrases():
    from auto_publisher.i18n_market import get_i18n
    d = get_i18n("en")
    blob = " ".join(str(v) for v in d.values() if isinstance(v, str))
    for phrase in ("원금보장", "확실한 수익", "리딩방", "100% 수익"):
        assert phrase not in blob


# ── 7. 요약 라벨 다국어 ──────────────────────────────────────

def test_summary_label_each_lang():
    from auto_publisher.i18n_market import get_i18n
    expected_substrings = {
        "en": ("Summary", "Snapshot"),
        "ja": ("要約", "まとめ"),
        "vi": ("Tóm tắt", "Tổng kết"),
        "id": ("Ringkasan", "Rangkuman"),
    }
    for lang, opts in expected_substrings.items():
        d = get_i18n(lang)
        label = d["summary_label"]
        assert any(opt.lower() in label.lower() for opt in opts), (
            f"{lang}: summary_label='{label}' 에 기대 키워드({opts}) 없음"
        )
