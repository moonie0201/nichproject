"""매일 아침 '미국 증시 마감' 포스트 자동 발행 — TDD 테스트.

범위:
- fetch_us_market_snapshot(): SPY/QQQ/DIA/IWM/VIX + 11개 섹터 ETF
- is_us_market_holiday(snapshot): 휴장일 감지
- build_markdown(snapshot): Front matter + 5개 H2 + 표 2개
"""

import re
import pytest


# 픽스처용 가짜 스냅샷 (LLM/yfinance 없이 순수 로직 테스트)

@pytest.fixture
def fake_snapshot():
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
            {"ticker": "XLK", "name": "Technology", "pct": 1.2},
            {"ticker": "XLC", "name": "Communication Services", "pct": 0.9},
            {"ticker": "XLY", "name": "Consumer Discretionary", "pct": 0.6},
            {"ticker": "XLF", "name": "Financials", "pct": 0.5},
            {"ticker": "XLI", "name": "Industrials", "pct": 0.3},
            {"ticker": "XLV", "name": "Health Care", "pct": 0.1},
            {"ticker": "XLB", "name": "Materials", "pct": -0.1},
            {"ticker": "XLP", "name": "Consumer Staples", "pct": -0.2},
            {"ticker": "XLRE", "name": "Real Estate", "pct": -0.4},
            {"ticker": "XLU", "name": "Utilities", "pct": -0.6},
            {"ticker": "XLE", "name": "Energy", "pct": -1.1},
        ],
        "top_gainers_sectors": ["XLK", "XLC", "XLY"],
        "top_losers_sectors": ["XLE", "XLU", "XLRE"],
        "narrative_hint": "growth_led",
    }


# ── 1. 스냅샷 구조 ────────────────────────────────────────────

def test_fetch_snapshot_returns_indices(monkeypatch):
    """fetch_us_market_snapshot()가 SPY/QQQ/DIA/IWM 4종 인덱스를 반환한다."""
    from auto_publisher import market_wrap

    # yfinance 호출 없이 테스트하기 위해 _fetch_one_price 를 스텁
    def fake_price(ticker):
        return {"price": 100.0, "pct": 0.5, "vol": 1_000_000, "prev_close_ts": "2026-04-23"}
    monkeypatch.setattr(market_wrap, "_fetch_one_price", fake_price)

    snap = market_wrap.fetch_us_market_snapshot()
    tickers = [idx["ticker"] for idx in snap["indices"]]
    assert {"SPY", "QQQ", "DIA", "IWM"} <= set(tickers)


def test_fetch_snapshot_includes_vix(monkeypatch):
    from auto_publisher import market_wrap
    monkeypatch.setattr(
        market_wrap, "_fetch_one_price",
        lambda t: {"price": 15.0, "pct": -1.0, "vol": 0, "prev_close_ts": "2026-04-23"},
    )
    snap = market_wrap.fetch_us_market_snapshot()
    assert "vix" in snap
    assert "price" in snap["vix"]


def test_fetch_snapshot_sector_count_is_11(monkeypatch):
    from auto_publisher import market_wrap
    monkeypatch.setattr(
        market_wrap, "_fetch_one_price",
        lambda t: {"price": 50.0, "pct": 0.3, "vol": 100, "prev_close_ts": "2026-04-23"},
    )
    snap = market_wrap.fetch_us_market_snapshot()
    assert len(snap["sectors"]) == 11
    sector_tickers = {s["ticker"] for s in snap["sectors"]}
    assert sector_tickers == {"XLK", "XLC", "XLY", "XLF", "XLI", "XLV", "XLB", "XLP", "XLRE", "XLU", "XLE"}


# ── 2. 휴장일 감지 ──────────────────────────────────────────────

def test_holiday_detection_sets_flag():
    """모든 인덱스의 prev_close_ts 가 예상 거래일보다 오래 전이면 holiday=True."""
    from auto_publisher.market_wrap import is_us_market_holiday

    # 예상 전 거래일(=2026-04-24의 US trading day)이 2026-04-23 이라고 가정
    # 모든 prev_close_ts 가 그보다 더 오래된 경우 휴장으로 판단
    snapshot_stale = {
        "date_kst": "2026-04-24",
        "indices": [
            {"ticker": "SPY", "prev_close_ts": "2026-04-21"},
            {"ticker": "QQQ", "prev_close_ts": "2026-04-21"},
        ],
    }
    assert is_us_market_holiday(snapshot_stale) is True


def test_holiday_detection_normal_day_false():
    from auto_publisher.market_wrap import is_us_market_holiday
    snapshot_ok = {
        "date_kst": "2026-04-24",
        "indices": [
            {"ticker": "SPY", "prev_close_ts": "2026-04-23"},
            {"ticker": "QQQ", "prev_close_ts": "2026-04-23"},
        ],
    }
    assert is_us_market_holiday(snapshot_ok) is False


# ── 3. Markdown 조립 ──────────────────────────────────────────

def test_build_markdown_contains_5_h2_sections(fake_snapshot):
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_snapshot)
    h2_count = len(re.findall(r"^## ", md, re.MULTILINE))
    assert h2_count == 5, f"H2 개수 5 기대, 실제 {h2_count}\nMD preview:\n{md[:500]}"


def test_build_markdown_contains_index_table(fake_snapshot):
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_snapshot)
    # 인덱스 표에 SPY/QQQ/DIA/IWM 가격 모두 포함
    for t in ("SPY", "QQQ", "DIA", "IWM"):
        assert t in md, f"인덱스 {t} 표에 없음"


def test_build_markdown_contains_sector_table(fake_snapshot):
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_snapshot)
    # 최소 11개 섹터 티커가 본문에 있어야 함
    sector_count = sum(1 for t in ("XLK","XLC","XLY","XLF","XLI","XLV","XLB","XLP","XLRE","XLU","XLE") if t in md)
    assert sector_count == 11


def test_build_markdown_title_matches_pattern(fake_snapshot):
    """front matter title 이 '{년}년 {월}월 {일}일 미국 증시 마감' 패턴."""
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_snapshot)
    m = re.search(r'title:\s*"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일 미국 증시 마감[^"]*)"', md)
    assert m, f"제목 패턴 불일치:\n{md[:300]}"


def test_build_markdown_includes_disclaimer(fake_snapshot):
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_snapshot)
    assert ("투자는 본인 책임" in md) or ("정보 제공" in md) or ("면책" in md)


def test_build_markdown_min_length(fake_snapshot):
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_snapshot)
    assert len(md) >= 1500, f"MD 길이 부족: {len(md)}자"


def test_build_markdown_no_forbidden_phrase(fake_snapshot):
    """생성된 MD 에 자본시장법 금칙어(원금보장/리딩방/확실한 수익)가 없어야 한다."""
    from auto_publisher.market_wrap import build_markdown
    md = build_markdown(fake_snapshot)
    for phrase in ("원금보장", "확실한 수익", "확실한수익", "리딩방", "100% 수익"):
        assert phrase not in md, f"금칙어 '{phrase}' 포함"


def test_build_markdown_fix_html_block_spacing_idempotent(fake_snapshot):
    """fix_html_block_spacing 적용 후 재적용해도 동일."""
    from auto_publisher.market_wrap import build_markdown
    from auto_publisher.content_generator import fix_html_block_spacing
    md = build_markdown(fake_snapshot)
    once = fix_html_block_spacing(md)
    twice = fix_html_block_spacing(once)
    assert once == twice


def test_narrative_hint_growth_led(fake_snapshot):
    """XLK/XLC/XLY 가 상위면 narrative_hint = growth_led."""
    from auto_publisher.market_wrap import classify_narrative
    hint = classify_narrative(fake_snapshot)
    assert hint == "growth_led"


def test_narrative_hint_defensive_led():
    from auto_publisher.market_wrap import classify_narrative
    snap = {
        "sectors": [
            {"ticker": "XLP", "name": "Consumer Staples", "pct": 1.5},
            {"ticker": "XLU", "name": "Utilities", "pct": 1.3},
            {"ticker": "XLV", "name": "Health Care", "pct": 0.9},
            {"ticker": "XLK", "name": "Technology", "pct": -1.2},
            {"ticker": "XLC", "name": "Communication Services", "pct": -0.8},
            {"ticker": "XLY", "name": "Consumer Discretionary", "pct": -0.5},
        ],
        "vix": {"price": 18.0, "pct": 5.0},
    }
    assert classify_narrative(snap) in ("defensive_led", "risk_off")
