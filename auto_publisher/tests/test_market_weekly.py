"""주간 시황 (토요일 09:00 KST, 한 주 누적) — TDD 테스트.

market_wrap/intraday 와 차별점:
- 비교 기준: 한 주(월~금 5거래일) 누적 변화율
- 데이터: week_open / week_close / pct_5d / max_drawdown_5d / vol_avg_5d
- 섹터 리더/래거 5일 기준
- 주요 이벤트 회고 + 다음 주 캘린더 섹션
"""

import re
import pytest


@pytest.fixture
def fake_weekly_snapshot():
    return {
        "week_label": "2026년 4월 4주차 (4월 20일~24일)",
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
            {"ticker": "XLK", "name": "Technology", "pct_5d": 3.1},
            {"ticker": "XLC", "name": "Communication Services", "pct_5d": 2.8},
            {"ticker": "XLY", "name": "Consumer Discretionary", "pct_5d": 2.0},
            {"ticker": "XLF", "name": "Financials", "pct_5d": 1.5},
            {"ticker": "XLI", "name": "Industrials", "pct_5d": 1.0},
            {"ticker": "XLV", "name": "Health Care", "pct_5d": 0.4},
            {"ticker": "XLB", "name": "Materials", "pct_5d": 0.0},
            {"ticker": "XLP", "name": "Consumer Staples", "pct_5d": -0.3},
            {"ticker": "XLRE", "name": "Real Estate", "pct_5d": -0.6},
            {"ticker": "XLU", "name": "Utilities", "pct_5d": -1.0},
            {"ticker": "XLE", "name": "Energy", "pct_5d": -2.2},
        ],
        "top_gainers_sectors": ["XLK", "XLC", "XLY"],
        "top_losers_sectors": ["XLE", "XLU", "XLRE"],
        "narrative_hint": "growth_led_week",
        "next_week_calendar": [
            "FOMC 의사록 발표 (수)",
            "PCE 물가지수 (금)",
            "엔비디아 어닝 (목 장 마감 후)",
        ],
    }


# ── 1. 스냅샷 구조 ──────────────────────────────────────────────

def test_fetch_weekly_snapshot_returns_indices(monkeypatch):
    from auto_publisher import market_weekly

    def fake_5d(ticker):
        return {"open": 100.0, "close": 102.0, "pct_5d": 2.0,
                "max_drawdown_5d": -0.5, "vol_avg_5d": 1_000_000}
    monkeypatch.setattr(market_weekly, "_fetch_5d_summary", fake_5d)

    snap = market_weekly.fetch_weekly_snapshot()
    tickers = [i["ticker"] for i in snap["indices"]]
    assert {"SPY", "QQQ", "DIA", "IWM"} <= set(tickers)
    for idx in snap["indices"]:
        assert "open" in idx and "close" in idx and "pct_5d" in idx


def test_fetch_weekly_sector_count_is_11(monkeypatch):
    from auto_publisher import market_weekly
    monkeypatch.setattr(
        market_weekly, "_fetch_5d_summary",
        lambda t: {"open": 50.0, "close": 50.5, "pct_5d": 1.0,
                   "max_drawdown_5d": -0.2, "vol_avg_5d": 100},
    )
    snap = market_weekly.fetch_weekly_snapshot()
    assert len(snap["sectors"]) == 11


def test_snapshot_has_week_label(monkeypatch):
    from auto_publisher import market_weekly
    monkeypatch.setattr(
        market_weekly, "_fetch_5d_summary",
        lambda t: {"open": 50.0, "close": 50.5, "pct_5d": 1.0,
                   "max_drawdown_5d": -0.2, "vol_avg_5d": 100},
    )
    snap = market_weekly.fetch_weekly_snapshot()
    assert "week_label" in snap and "주차" in snap["week_label"]
    assert "us_week_start" in snap and "us_week_end" in snap


# ── 2. 내러티브 ────────────────────────────────────────────────

def test_classify_weekly_growth_led(fake_weekly_snapshot):
    from auto_publisher.market_weekly import classify_weekly_narrative
    assert classify_weekly_narrative(fake_weekly_snapshot) == "growth_led_week"


def test_classify_weekly_defensive_led():
    from auto_publisher.market_weekly import classify_weekly_narrative
    snap = {
        "indices": [{"ticker": "SPY", "pct_5d": -0.5}, {"ticker": "QQQ", "pct_5d": -1.2}],
        "vix": {"pct_5d": 8.0},
        "sectors": [
            {"ticker": "XLP", "name": "Consumer Staples", "pct_5d": 1.5},
            {"ticker": "XLU", "name": "Utilities", "pct_5d": 1.2},
            {"ticker": "XLV", "name": "Health Care", "pct_5d": 0.9},
            {"ticker": "XLK", "name": "Technology", "pct_5d": -2.0},
            {"ticker": "XLC", "name": "Communication Services", "pct_5d": -1.5},
        ],
    }
    assert classify_weekly_narrative(snap) in ("defensive_led_week", "risk_off_week")


def test_classify_weekly_risk_off_on_high_vix():
    from auto_publisher.market_weekly import classify_weekly_narrative
    snap = {
        "indices": [{"ticker": "SPY", "pct_5d": -3.0}, {"ticker": "QQQ", "pct_5d": -4.5}],
        "vix": {"pct_5d": 30.0},
        "sectors": [],
    }
    assert classify_weekly_narrative(snap) == "risk_off_week"


# ── 3. Markdown ────────────────────────────────────────────────

def test_weekly_markdown_h2_count(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    h2_count = len(re.findall(r"^## ", md, re.MULTILINE))
    assert h2_count >= 5


def test_weekly_markdown_title_pattern(fake_weekly_snapshot):
    """제목: '... 미국 증시 주간 ...'"""
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    m = re.search(r'title:\s*"([^"]*미국 증시 주간[^"]*)"', md)
    assert m, f"제목 패턴 불일치:\n{md[:300]}"


def test_weekly_markdown_includes_index_table(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    for t in ("SPY", "QQQ", "DIA", "IWM"):
        assert t in md


def test_weekly_markdown_includes_all_11_sectors(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    sector_count = sum(
        1 for t in ("XLK","XLC","XLY","XLF","XLI","XLV","XLB","XLP","XLRE","XLU","XLE")
        if t in md
    )
    assert sector_count == 11


def test_weekly_markdown_includes_next_week_calendar(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    # next_week_calendar 의 항목들이 본문에 노출
    assert "FOMC" in md or "다음 주" in md
    # 적어도 calendar 항목 1개는 본문에 들어가야 함
    assert any(item in md for item in ("FOMC 의사록 발표", "PCE 물가지수", "엔비디아 어닝"))


def test_weekly_markdown_includes_disclaimer(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    assert ("투자는 본인 책임" in md) or ("정보 제공" in md) or ("면책" in md)


def test_weekly_markdown_min_length(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    assert len(md) >= 2500, f"weekly markdown 길이 부족: {len(md)}"


def test_weekly_markdown_no_forbidden_phrase(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    for phrase in ("원금보장", "확실한 수익", "확실한수익", "리딩방", "100% 수익"):
        assert phrase not in md


def test_weekly_markdown_html_block_spacing_idempotent(fake_weekly_snapshot):
    from auto_publisher.market_weekly import build_weekly_markdown
    from auto_publisher.content_generator import fix_html_block_spacing
    md = build_weekly_markdown(fake_weekly_snapshot)
    once = fix_html_block_spacing(md)
    twice = fix_html_block_spacing(once)
    assert once == twice


def test_weekly_markdown_mentions_5days(fake_weekly_snapshot):
    """주간 글은 '5거래일'·'5일'·'한 주' 류 키워드 포함."""
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    assert any(k in md for k in ("5거래일", "5일", "한 주", "주간 누적", "주간"))


def test_weekly_markdown_categories_include_weekly(fake_weekly_snapshot):
    """frontmatter categories 에 '주간시황' 포함 → migrate 분류기가 weekly tab 으로 분류."""
    from auto_publisher.market_weekly import build_weekly_markdown
    md = build_weekly_markdown(fake_weekly_snapshot)
    # frontmatter 안에서 categories 와 함께 주간시황 등장
    fm_block = md.split("---", 2)[1] if md.startswith("---") else ""
    assert "주간시황" in fm_block
