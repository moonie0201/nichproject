"""다국어 시황 모듈 통합 테스트.

market_wrap / market_intraday / market_weekly 의 build_markdown 이
lang 파라미터로 en/ja/vi/id 분기 가능한지 검증.
"""

import re
import pytest


# ── 공통 픽스처 ──────────────────────────────────────────────────

@pytest.fixture
def fake_wrap_snapshot():
    return {
        "date_kst": "2026-04-24",
        "us_close_date": "2026-04-23",
        "is_us_market_holiday": False,
        "indices": [
            {"ticker": "SPY", "name": "S&P 500", "price": 653.14, "pct": 0.42, "vol": 45_000_000},
            {"ticker": "QQQ", "name": "Nasdaq-100", "price": 520.30, "pct": 0.81, "vol": 38_000_000},
            {"ticker": "DIA", "name": "Dow 30", "price": 450.10, "pct": 0.21, "vol": 3_200_000},
            {"ticker": "IWM", "name": "Russell 2000", "price": 220.05, "pct": -0.15, "vol": 22_000_000},
        ],
        "vix": {"price": 14.3, "pct": -2.1},
        "sectors": [
            {"ticker": t, "name": n, "pct": p, "price": 50.0}
            for t, n, p in [
                ("XLK","Technology",1.2),("XLC","Communication Services",0.9),
                ("XLY","Consumer Discretionary",0.6),("XLF","Financials",0.5),
                ("XLI","Industrials",0.3),("XLV","Health Care",0.1),
                ("XLB","Materials",-0.1),("XLP","Consumer Staples",-0.2),
                ("XLRE","Real Estate",-0.4),("XLU","Utilities",-0.6),
                ("XLE","Energy",-1.1),
            ]
        ],
        "top_gainers_sectors": ["XLK","XLC","XLY"],
        "top_losers_sectors": ["XLE","XLU","XLRE"],
        "narrative_hint": "growth_led",
    }


@pytest.fixture
def fake_intraday_snapshot():
    return {
        "date_kst": "2026-04-26",
        "us_session_date": "2026-04-25",
        "is_us_market_holiday": False,
        "minutes_after_open": 30,
        "indices": [
            {"ticker": "SPY", "name": "S&P 500", "open": 651.0, "current": 654.2,
             "pct_from_open": 0.49, "pct_gap_from_prev": 0.30, "vol_30m": 12_000_000,
             "prev_close_ts": "2026-04-25"},
            {"ticker": "QQQ", "name": "Nasdaq-100", "open": 518.0, "current": 521.5,
             "pct_from_open": 0.68, "pct_gap_from_prev": 0.20, "vol_30m": 9_500_000,
             "prev_close_ts": "2026-04-25"},
            {"ticker": "DIA", "name": "Dow 30", "open": 449.0, "current": 449.8,
             "pct_from_open": 0.18, "pct_gap_from_prev": -0.05, "vol_30m": 800_000,
             "prev_close_ts": "2026-04-25"},
            {"ticker": "IWM", "name": "Russell 2000", "open": 219.0, "current": 218.7,
             "pct_from_open": -0.14, "pct_gap_from_prev": 0.10, "vol_30m": 5_500_000,
             "prev_close_ts": "2026-04-25"},
        ],
        "vix": {"price": 14.2, "pct_from_prev": -3.1, "level": "low"},
        "sectors": [
            {"ticker": t, "name": n, "pct_from_open": p}
            for t, n, p in [
                ("XLK","Technology",0.9),("XLC","Communication Services",0.7),
                ("XLY","Consumer Discretionary",0.5),("XLF","Financials",0.4),
                ("XLI","Industrials",0.2),("XLV","Health Care",0.1),
                ("XLB","Materials",-0.1),("XLP","Consumer Staples",-0.2),
                ("XLRE","Real Estate",-0.4),("XLU","Utilities",-0.5),
                ("XLE","Energy",-0.8),
            ]
        ],
        "top_gainers_sectors": ["XLK","XLC","XLY"],
        "top_losers_sectors": ["XLE","XLU","XLRE"],
        "gap": "gap_up",
        "narrative_hint": "early_strength",
    }


@pytest.fixture
def fake_weekly_snapshot():
    return {
        "week_label": "Week 17 (Apr 20-24, 2026)",
        "us_week_start": "2026-04-20",
        "us_week_end": "2026-04-24",
        "kst_publish_date": "2026-04-25",
        "is_full_week": True,
        "indices": [
            {"ticker": "SPY", "name": "S&P 500", "open": 645.0, "close": 658.0,
             "pct_5d": 2.02, "max_drawdown_5d": -0.85, "vol_avg_5d": 42_000_000},
            {"ticker": "QQQ", "name": "Nasdaq-100", "open": 510.0, "close": 522.5,
             "pct_5d": 2.45, "max_drawdown_5d": -1.10, "vol_avg_5d": 35_000_000},
            {"ticker": "DIA", "name": "Dow 30", "open": 446.0, "close": 451.2,
             "pct_5d": 1.17, "max_drawdown_5d": -0.55, "vol_avg_5d": 3_100_000},
            {"ticker": "IWM", "name": "Russell 2000", "open": 218.0, "close": 219.5,
             "pct_5d": 0.69, "max_drawdown_5d": -1.50, "vol_avg_5d": 21_000_000},
        ],
        "vix": {"week_open": 15.5, "week_close": 14.2, "pct_5d": -8.4, "level": "low"},
        "sectors": [
            {"ticker": t, "name": n, "pct_5d": p}
            for t, n, p in [
                ("XLK","Technology",3.1),("XLC","Communication Services",2.8),
                ("XLY","Consumer Discretionary",2.0),("XLF","Financials",1.5),
                ("XLI","Industrials",1.0),("XLV","Health Care",0.4),
                ("XLB","Materials",0.0),("XLP","Consumer Staples",-0.3),
                ("XLRE","Real Estate",-0.6),("XLU","Utilities",-1.0),
                ("XLE","Energy",-2.2),
            ]
        ],
        "top_gainers_sectors": ["XLK","XLC","XLY"],
        "top_losers_sectors": ["XLE","XLU","XLRE"],
        "narrative_hint": "growth_led_week",
        "next_week_calendar": ["FOMC minutes", "PCE inflation", "NVDA earnings"],
    }


LANGS = ("en", "ja", "vi", "id")


# ── 1. wrap 다국어 ──────────────────────────────────────────────

@pytest.mark.parametrize("lang", LANGS)
def test_wrap_build_markdown_no_korean(fake_wrap_snapshot, lang):
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_wrap_snapshot, lang=lang)
    # 본문(코드블록·티커 제외)에 한글이 없어야 함
    # 단순 검사: 한글 자모 비율이 매우 낮아야 함
    korean_chars = len(re.findall(r"[가-힣]", md))
    total = len(md) or 1
    assert korean_chars / total < 0.005, (
        f"{lang}: 한글 비율이 너무 높음 ({korean_chars}/{total}={korean_chars/total:.3%})"
    )


@pytest.mark.parametrize("lang", LANGS)
def test_wrap_frontmatter_lang_field(fake_wrap_snapshot, lang):
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_wrap_snapshot, lang=lang)
    # frontmatter 의 categories 가 lang 별 i18n 카테고리
    fm_block = md.split("---", 2)[1]
    # ko 카테고리 ('시장분석' 등) 가 비-한국어에는 없어야 함
    assert "시장분석" not in fm_block
    assert "주간시황" not in fm_block


# ── 2. intraday 다국어 ──────────────────────────────────────────

@pytest.mark.parametrize("lang", LANGS)
def test_intraday_build_markdown_no_korean(fake_intraday_snapshot, lang):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot, lang=lang)
    korean_chars = len(re.findall(r"[가-힣]", md))
    total = len(md) or 1
    assert korean_chars / total < 0.005


# ── 3. weekly 다국어 ────────────────────────────────────────────

@pytest.mark.parametrize("lang", LANGS)
def test_weekly_build_markdown_no_korean(fake_weekly_snapshot, lang):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot, lang=lang)
    korean_chars = len(re.findall(r"[가-힣]", md))
    total = len(md) or 1
    assert korean_chars / total < 0.005


# ── 4. ko default 회귀 ────────────────────────────────────────

def test_wrap_default_lang_ko_still_korean(fake_wrap_snapshot):
    """lang 파라미터 없이 호출 시 기존 한국어 동작 유지."""
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_wrap_snapshot)
    assert "시장분석" in md or "미국 증시 마감" in md


def test_intraday_default_lang_ko_still_korean(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot)
    assert "장중" in md or "개장" in md


def test_weekly_default_lang_ko_still_korean(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    assert "주간" in md


# ── 5. en 본문 핵심 키워드 ─────────────────────────────────────

def test_wrap_en_contains_market_close_keyword(fake_wrap_snapshot):
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_wrap_snapshot, lang="en")
    assert any(kw in md for kw in ("Market Close", "Daily Wrap", "Closing", "S&P 500"))


def test_intraday_en_contains_intraday_keyword(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot, lang="en")
    assert any(kw in md for kw in ("Intraday", "First 30 min", "Snapshot"))


def test_weekly_en_contains_weekly_keyword(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot, lang="en")
    assert any(kw in md for kw in ("Weekly", "Wrap", "5-day", "5 trading"))
