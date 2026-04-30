"""미국 장중 시황 (22:30 KST, 개장 30분 후 첫 인상) — TDD 테스트.

market_wrap 과 차별점:
- 비교 기준: 어제 마감 vs 오늘 종가 → "오늘 개장가 vs 현재가" (첫 30분 모멘텀)
- 데이터: open / current / pct_from_open / volume_first30m
- 갭 분류 (gap_up/gap_down/flat)
- 본문 톤: "방금 개장해서 ..." (첫 인상)
"""

import re
import pytest


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
            {"ticker": "XLK", "name": "Technology", "pct_from_open": 0.9},
            {"ticker": "XLC", "name": "Communication Services", "pct_from_open": 0.7},
            {"ticker": "XLY", "name": "Consumer Discretionary", "pct_from_open": 0.5},
            {"ticker": "XLF", "name": "Financials", "pct_from_open": 0.4},
            {"ticker": "XLI", "name": "Industrials", "pct_from_open": 0.2},
            {"ticker": "XLV", "name": "Health Care", "pct_from_open": 0.1},
            {"ticker": "XLB", "name": "Materials", "pct_from_open": -0.1},
            {"ticker": "XLP", "name": "Consumer Staples", "pct_from_open": -0.2},
            {"ticker": "XLRE", "name": "Real Estate", "pct_from_open": -0.4},
            {"ticker": "XLU", "name": "Utilities", "pct_from_open": -0.5},
            {"ticker": "XLE", "name": "Energy", "pct_from_open": -0.8},
        ],
        "top_gainers_sectors": ["XLK", "XLC", "XLY"],
        "top_losers_sectors": ["XLE", "XLU", "XLRE"],
        "gap": "gap_up",
        "narrative_hint": "early_strength",
    }


# ── 1. 스냅샷 구조 ────────────────────────────────────────────

def test_fetch_snapshot_returns_indices_with_open_field(monkeypatch):
    from auto_publisher import market_intraday

    def fake_intraday(ticker):
        return {
            "open": 100.0,
            "current": 101.0,
            "pct_from_open": 1.0,
            "pct_gap_from_prev": 0.5,
            "vol_30m": 1_000_000,
            "prev_close_ts": "2026-04-25",
        }
    monkeypatch.setattr(market_intraday, "_fetch_intraday_price", fake_intraday)

    snap = market_intraday.fetch_intraday_snapshot()
    tickers = [i["ticker"] for i in snap["indices"]]
    assert {"SPY", "QQQ", "DIA", "IWM"} <= set(tickers)
    for idx in snap["indices"]:
        assert "open" in idx
        assert "current" in idx
        assert "pct_from_open" in idx


def test_fetch_snapshot_sector_count_is_11(monkeypatch):
    from auto_publisher import market_intraday
    monkeypatch.setattr(
        market_intraday, "_fetch_intraday_price",
        lambda t: {"open": 50.0, "current": 50.5, "pct_from_open": 1.0,
                   "pct_gap_from_prev": 0.0, "vol_30m": 100, "prev_close_ts": "2026-04-25"},
    )
    snap = market_intraday.fetch_intraday_snapshot()
    assert len(snap["sectors"]) == 11


def test_snapshot_has_minutes_after_open_field(monkeypatch):
    from auto_publisher import market_intraday
    monkeypatch.setattr(
        market_intraday, "_fetch_intraday_price",
        lambda t: {"open": 50.0, "current": 50.5, "pct_from_open": 1.0,
                   "pct_gap_from_prev": 0.0, "vol_30m": 100, "prev_close_ts": "2026-04-25"},
    )
    snap = market_intraday.fetch_intraday_snapshot()
    assert "minutes_after_open" in snap
    assert isinstance(snap["minutes_after_open"], int)


# ── 2. 갭(gap) 분류 ──────────────────────────────────────────

def test_classify_gap_up():
    from auto_publisher.market_intraday import classify_gap
    snap = {"indices": [
        {"ticker": "SPY", "pct_gap_from_prev": 0.6},
        {"ticker": "QQQ", "pct_gap_from_prev": 0.7},
    ]}
    assert classify_gap(snap) == "gap_up"


def test_classify_gap_down():
    from auto_publisher.market_intraday import classify_gap
    snap = {"indices": [
        {"ticker": "SPY", "pct_gap_from_prev": -0.6},
        {"ticker": "QQQ", "pct_gap_from_prev": -0.7},
    ]}
    assert classify_gap(snap) == "gap_down"


def test_classify_gap_flat():
    from auto_publisher.market_intraday import classify_gap
    snap = {"indices": [
        {"ticker": "SPY", "pct_gap_from_prev": 0.05},
        {"ticker": "QQQ", "pct_gap_from_prev": -0.10},
    ]}
    assert classify_gap(snap) == "gap_flat"


# ── 3. 휴장 감지 ───────────────────────────────────────────────

def test_holiday_detection_when_no_intraday_data():
    """모든 인덱스의 open=0 이면 미장이 안 열린 휴장 상태."""
    from auto_publisher.market_intraday import is_us_market_in_session
    snap = {
        "indices": [
            {"ticker": "SPY", "open": 0.0, "current": 0.0},
            {"ticker": "QQQ", "open": 0.0, "current": 0.0},
        ]
    }
    assert is_us_market_in_session(snap) is False


def test_in_session_when_data_present():
    from auto_publisher.market_intraday import is_us_market_in_session
    snap = {
        "indices": [
            {"ticker": "SPY", "open": 651.0, "current": 654.0},
        ]
    }
    assert is_us_market_in_session(snap) is True


# ── 4. Markdown 조립 ──────────────────────────────────────────

def test_build_markdown_contains_h2_sections(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot)
    h2_count = len(re.findall(r"^## ", md, re.MULTILINE))
    assert h2_count >= 4


def test_build_markdown_title_pattern(fake_intraday_snapshot):
    """제목: '{년}년 {월}월 {일}일 미국 증시 장중...' """
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot)
    m = re.search(r'title:\s*"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일 미국 증시 장중[^"]*)"', md)
    assert m, f"제목 패턴 불일치:\n{md[:300]}"


def test_build_markdown_contains_index_table(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot)
    for t in ("SPY", "QQQ", "DIA", "IWM"):
        assert t in md


def test_build_markdown_contains_sector_table(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot)
    sector_count = sum(
        1 for t in ("XLK","XLC","XLY","XLF","XLI","XLV","XLB","XLP","XLRE","XLU","XLE")
        if t in md
    )
    assert sector_count == 11


def test_build_markdown_includes_disclaimer(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot)
    assert ("투자는 본인 책임" in md) or ("정보 제공" in md) or ("면책" in md)


def test_build_markdown_min_length(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot)
    assert len(md) >= 1500


def test_build_markdown_no_forbidden_phrase(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot)
    for phrase in ("원금보장", "확실한 수익", "확실한수익", "리딩방", "100% 수익"):
        assert phrase not in md


def test_build_markdown_html_block_spacing_idempotent(fake_intraday_snapshot):
    from auto_publisher.market_intraday import build_intraday_markdown
    from auto_publisher.content_generator import fix_html_block_spacing
    md = build_intraday_markdown(fake_intraday_snapshot)
    once = fix_html_block_spacing(md)
    twice = fix_html_block_spacing(once)
    assert once == twice


def test_build_markdown_mentions_open_in_narrative(fake_intraday_snapshot):
    """장중 시황은 '개장' 또는 '개장가' 키워드를 본문에 포함해야 한다."""
    from auto_publisher.market_intraday import build_intraday_markdown
    md = build_intraday_markdown(fake_intraday_snapshot)
    assert ("개장" in md) or ("개장가" in md)


# ── 5. 내러티브 분류 ────────────────────────────────────────

def test_narrative_early_strength(fake_intraday_snapshot):
    from auto_publisher.market_intraday import classify_intraday_narrative
    hint = classify_intraday_narrative(fake_intraday_snapshot)
    assert hint == "early_strength"


def test_narrative_early_weakness():
    from auto_publisher.market_intraday import classify_intraday_narrative
    snap = {
        "indices": [
            {"ticker": "SPY", "pct_from_open": -0.6},
            {"ticker": "QQQ", "pct_from_open": -0.9},
        ],
        "vix": {"pct_from_prev": 4.0},
        "sectors": [],
    }
    assert classify_intraday_narrative(snap) == "early_weakness"


def test_narrative_mixed_low_vol():
    from auto_publisher.market_intraday import classify_intraday_narrative
    snap = {
        "indices": [
            {"ticker": "SPY", "pct_from_open": 0.05},
            {"ticker": "QQQ", "pct_from_open": -0.05},
        ],
        "vix": {"pct_from_prev": 0.2},
        "sectors": [],
    }
    assert classify_intraday_narrative(snap) == "mixed"
