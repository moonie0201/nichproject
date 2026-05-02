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


# ── 6. wrap 5개 언어 섹션 패리티 (10/10 강화 회귀 보호) ────────

@pytest.fixture
def full_wrap_snapshot(fake_wrap_snapshot):
    """ko 기준 풀 데이터 — 매크로/breadth/asia/crypto/mag7/movers/bonds 포함."""
    snap = dict(fake_wrap_snapshot)
    snap.update({
        "macro": [
            {"ticker": "^TNX", "name": "미국 10년물 수익률", "price": 4.38, "pct": -0.27},
            {"ticker": "^TYX", "name": "미국 30년물 수익률", "price": 4.97, "pct": -0.42},
            {"ticker": "^FVX", "name": "미국 5년물 수익률", "price": 4.02, "pct": -0.05},
            {"ticker": "DX-Y.NYB", "name": "달러 인덱스 (DXY)", "price": 98.21, "pct": 0.13},
        ],
        "asia": [
            {"ticker": "^N225", "name": "Nikkei 225 (일본)", "price": 38000.0, "pct": 0.4},
            {"ticker": "^HSI", "name": "Hang Seng (홍콩)", "price": 17500.0, "pct": -1.2},
            {"ticker": "^KS11", "name": "KOSPI Composite (한국)", "price": 2700.0, "pct": -0.8},
            {"ticker": "000001.SS", "name": "Shanghai (중국)", "price": 3100.0, "pct": 0.2},
        ],
        "crypto": [
            {"ticker": "BTC-USD", "name": "Bitcoin", "price": 65000.0, "pct": 1.5},
            {"ticker": "ETH-USD", "name": "Ethereum", "price": 3300.0, "pct": 2.1},
        ],
        "mag7": [
            {"ticker": t, "name": n, "price": p, "pct": pct, "rsi": rsi}
            for t, n, p, pct, rsi in [
                ("AAPL", "Apple", 245.0, 1.2, 65.0),
                ("MSFT", "Microsoft", 420.0, 0.8, 60.0),
                ("NVDA", "NVIDIA", 130.0, -0.5, 55.0),
                ("GOOGL", "Alphabet", 175.0, 0.3, 58.0),
                ("AMZN", "Amazon", 200.0, 1.0, 62.0),
                ("META", "Meta", 580.0, -0.3, 50.0),
                ("TSLA", "Tesla", 250.0, 2.0, 70.0),
            ]
        ],
        "bonds": [
            {"ticker": "TLT", "name": "TLT", "price": 90.0, "pct": -0.2},
            {"ticker": "IEF", "name": "IEF", "price": 95.0, "pct": -0.1},
            {"ticker": "SHY", "name": "SHY", "price": 82.0, "pct": -0.05},
        ],
        "commodities": [
            {"ticker": "GLD", "name": "GLD", "price": 250.0, "pct": 0.5},
            {"ticker": "SLV", "name": "SLV", "price": 30.0, "pct": 1.5},
            {"ticker": "USO", "name": "USO", "price": 75.0, "pct": -1.5},
        ],
        "fear_greed": {"score": 65, "label": "탐욕"},
        "breadth": {"sector_positive": 6, "sector_negative": 5, "sector_total": 11,
                    "mag7_positive": 5, "mag7_negative": 2, "mag7_total": 7},
        "index_rsi": {"SPY": 65.0, "QQQ": 72.0, "DIA": 60.0, "IWM": 55.0},
        "index_5d": {"SPY": 1.2, "QQQ": 2.0, "DIA": 0.5, "IWM": -0.5},
        "top_movers": {
            "gainers": [
                {"ticker": "INTC", "name": "Intel", "price": 25.0, "pct": 5.4},
                {"ticker": "CRM", "name": "Salesforce", "price": 280.0, "pct": 4.1},
                {"ticker": "MRK", "name": "Merck", "price": 105.0, "pct": 2.7},
            ],
            "losers": [
                {"ticker": "ABBV", "name": "AbbVie", "price": 180.0, "pct": -2.2},
                {"ticker": "COP", "name": "ConocoPhillips", "price": 105.0, "pct": -2.0},
                {"ticker": "WFC", "name": "Wells Fargo", "price": 75.0, "pct": -1.7},
            ],
        },
    })
    return snap


REQUIRED_TICKER_TOKENS = ["^TNX", "DX-Y.NYB", "BTC-USD", "AAPL", "INTC", "TLT", "GLD"]


@pytest.mark.parametrize("lang", ["ko", "en", "ja", "vi", "id"])
def test_wrap_all_required_data_tokens_present(full_wrap_snapshot, lang):
    """모든 언어가 핵심 데이터 토큰(매크로/asia/crypto/mag7/movers/bonds/comms)을 노출."""
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(full_wrap_snapshot, lang=lang)
    for token in REQUIRED_TICKER_TOKENS:
        assert token in md, f"{lang}: 필수 데이터 토큰 누락: {token}"


@pytest.mark.parametrize("lang", ["ko", "en", "ja", "vi", "id"])
def test_wrap_fg_gauge_present(full_wrap_snapshot, lang):
    """모든 언어가 Fear & Greed 게이지 박스를 렌더링."""
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(full_wrap_snapshot, lang=lang)
    assert "fg-gauge" in md, f"{lang}: FG 게이지 누락"
    assert "🧭" in md, f"{lang}: FG 이모지 누락"


@pytest.mark.parametrize("lang", ["ko", "en", "ja", "vi", "id"])
def test_wrap_breadth_box_present(full_wrap_snapshot, lang):
    """모든 언어가 시장 폭(Breadth) 박스를 렌더링."""
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(full_wrap_snapshot, lang=lang)
    assert "breadth-box" in md, f"{lang}: breadth 박스 누락"


@pytest.mark.parametrize("lang", ["en", "ja", "vi", "id"])
def test_wrap_h2_count_at_least_9(full_wrap_snapshot, lang):
    """비-한국어가 최소 9개 H2 섹션을 가져야 한다 (ko 11개 / non-ko 10개 목표)."""
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(full_wrap_snapshot, lang=lang)
    h2_count = len(re.findall(r"^## ", md, re.MULTILINE))
    assert h2_count >= 9, f"{lang}: H2 카운트 부족 ({h2_count} < 9)"


def test_intraday_en_contains_intraday_keyword(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot, lang="en")
    assert any(kw in md for kw in ("Intraday", "First 30 min", "Snapshot"))


def test_weekly_en_contains_weekly_keyword(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot, lang="en")
    assert any(kw in md for kw in ("Weekly", "Wrap", "5-day", "5 trading"))
