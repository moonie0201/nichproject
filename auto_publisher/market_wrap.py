"""매일 아침 '미국 증시 마감' 포스트 생성기.

데이터 스펙과 템플릿은 /home/mh/.claude/plans/peaceful-jumping-charm.md 참조.

핵심 함수:
- fetch_us_market_snapshot(): 4대 지수·VIX·11섹터·채권3·원자재3·Mag7·매크로4(10Y/30Y/5Y/DXY)·대형주 30개 모버 병렬 수집
- is_us_market_holiday(snapshot): 휴장일 감지
- classify_narrative(snapshot): growth_led / defensive_led / risk_off / mixed
- build_markdown(snapshot): Hugo front matter + 10개 H2 (지수/매크로/섹터/채권원자재/Mag7/모버/내러티브/시나리오/내일포인트/Action) + 히트맵
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Iterable

logger = logging.getLogger(__name__)


INDEX_TICKERS = [
    ("SPY", "S&P 500"),
    ("QQQ", "Nasdaq-100"),
    ("DIA", "Dow 30"),
    ("IWM", "Russell 2000"),
]

SECTOR_TICKERS = [
    ("XLK", "Technology"),
    ("XLC", "Communication Services"),
    ("XLY", "Consumer Discretionary"),
    ("XLF", "Financials"),
    ("XLI", "Industrials"),
    ("XLV", "Health Care"),
    ("XLB", "Materials"),
    ("XLP", "Consumer Staples"),
    ("XLRE", "Real Estate"),
    ("XLU", "Utilities"),
    ("XLE", "Energy"),
]

VIX_TICKER = "^VIX"

GROWTH_SECTORS = {"XLK", "XLC", "XLY"}
DEFENSIVE_SECTORS = {"XLP", "XLU", "XLV"}

BOND_TICKERS = [
    ("TLT", "미국 장기채 (20Y+)"),
    ("IEF", "미국 중기채 (7-10Y)"),
    ("SHY", "미국 단기채 (1-3Y)"),
]

COMMODITY_TICKERS = [
    ("GLD", "금 ETF"),
    ("SLV", "은 ETF"),
    ("USO", "원유 ETF"),
]

MAG7_TICKERS = [
    ("AAPL", "Apple"),
    ("MSFT", "Microsoft"),
    ("NVDA", "NVIDIA"),
    ("GOOGL", "Alphabet"),
    ("AMZN", "Amazon"),
    ("META", "Meta"),
    ("TSLA", "Tesla"),
]

MOVER_TICKERS = [
    "JPM", "BAC", "GS", "MS", "WFC",
    "JNJ", "UNH", "PFE", "MRK", "ABBV",
    "XOM", "CVX", "COP", "SLB", "EOG",
    "BA", "CAT", "HON", "LMT", "GE",
    "PG", "KO", "PEP", "WMT", "COST",
    "DIS", "NFLX", "CRM", "ADBE", "INTC",
]

MOVER_NAMES = {
    "JPM": "JPMorgan", "BAC": "Bank of America", "GS": "Goldman Sachs",
    "MS": "Morgan Stanley", "WFC": "Wells Fargo",
    "JNJ": "Johnson & Johnson", "UNH": "UnitedHealth", "PFE": "Pfizer",
    "MRK": "Merck", "ABBV": "AbbVie",
    "XOM": "ExxonMobil", "CVX": "Chevron", "COP": "ConocoPhillips",
    "SLB": "Schlumberger", "EOG": "EOG Resources",
    "BA": "Boeing", "CAT": "Caterpillar", "HON": "Honeywell",
    "LMT": "Lockheed Martin", "GE": "GE Aerospace",
    "PG": "Procter & Gamble", "KO": "Coca-Cola", "PEP": "PepsiCo",
    "WMT": "Walmart", "COST": "Costco",
    "DIS": "Disney", "NFLX": "Netflix", "CRM": "Salesforce",
    "ADBE": "Adobe", "INTC": "Intel",
}

# 핵심 매크로: 10년물·30년물 미국채 수익률, 달러 인덱스
MACRO_TICKERS = [
    ("^TNX", "미국 10년물 수익률"),
    ("^TYX", "미국 30년물 수익률"),
    ("^FVX", "미국 5년물 수익률"),
    ("DX-Y.NYB", "달러 인덱스 (DXY)"),
]

# 아시아 핸드오프: 미국 마감 후 한국 독자가 만나는 다음 시장
ASIA_TICKERS = [
    ("^N225", "Nikkei 225 (일본)"),
    ("^HSI", "Hang Seng (홍콩)"),
    ("^KS11", "KOSPI Composite (한국)"),
    ("000001.SS", "Shanghai Composite (중국)"),
]

# 디지털 자산: 위험선호 24시간 바로미터
CRYPTO_TICKERS = [
    ("BTC-USD", "Bitcoin"),
    ("ETH-USD", "Ethereum"),
]

KST = timezone(timedelta(hours=9))


def _fetch_one_price(ticker: str) -> dict:
    """단일 티커 가격 조회. market_cache 우선, 그 다음 yfinance.

    Returns:
        {"price": float, "pct": float, "vol": int, "prev_close_ts": "YYYY-MM-DD"}
    """
    try:
        from auto_publisher.market_cache import get_cached_data
        cached = get_cached_data(ticker)
        # prev_close 없으면 pct 계산 불가 — yfinance 직접 조회로 폴백
        if cached:
            price = cached.get("current_price") or cached.get("price") or 0.0
            prev = cached.get("prev_close") or cached.get("previous_close")
            if price and prev:
                pct = ((price - prev) / prev * 100.0) if prev else 0.0
                ts = cached.get("last_updated") or cached.get("timestamp") or ""
                return {
                    "price": float(price),
                    "pct": float(pct),
                    "vol": int(cached.get("volume") or 0),
                    "prev_close_ts": str(ts)[:10] if ts else "",
                }
    except Exception as e:
        logger.debug(f"cache miss for {ticker}: {e}")

    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", auto_adjust=False)
        if hist is None or hist.empty:
            return {"price": 0.0, "pct": 0.0, "vol": 0, "prev_close_ts": ""}
        last = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else last
        price = float(last["Close"])
        prev_price = float(prev["Close"]) if len(hist) >= 2 else price
        pct = ((price - prev_price) / prev_price * 100.0) if prev_price else 0.0
        ts = str(hist.index[-1].date())
        return {
            "price": price,
            "pct": pct,
            "vol": int(last.get("Volume") or 0),
            "prev_close_ts": ts,
        }
    except Exception as e:
        logger.warning(f"yfinance fetch failed for {ticker}: {e}")
        return {"price": 0.0, "pct": 0.0, "vol": 0, "prev_close_ts": ""}


def _fetch_history(ticker: str, period: str = "1mo") -> list[float]:
    """최근 종가 리스트 반환 (RSI 계산용)."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=False)
        if hist is None or hist.empty:
            return []
        return [float(c) for c in hist["Close"].tolist()]
    except Exception as e:
        logger.debug(f"history fetch failed {ticker}: {e}")
        return []


def _compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """순수 Python RSI 계산. 데이터 부족 시 None."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 1)


def _fetch_item_with_rsi(ticker: str, name: str) -> dict:
    """단일 티커 가격 + RSI 수집."""
    p = _fetch_one_price(ticker)
    closes = _fetch_history(ticker, period="1mo")
    rsi = _compute_rsi(closes)
    return {"ticker": ticker, "name": name, "price": p["price"], "pct": p["pct"], "rsi": rsi}


def _fetch_extended_items(ticker_list: list[tuple], with_rsi: bool = False) -> list[dict]:
    """ThreadPoolExecutor로 병렬 수집."""
    results: list[dict] = []
    fetch_fn = _fetch_item_with_rsi if with_rsi else lambda t, n: {**_fetch_one_price(t), "ticker": t, "name": n}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_fn, ticker, name): (ticker, name) for ticker, name in ticker_list}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                t, n = futures[fut]
                logger.debug(f"fetch failed {t}: {e}")
                results.append({"ticker": t, "name": n, "price": 0.0, "pct": 0.0, "rsi": None})
    # 원래 순서 복원
    order = {ticker: i for i, (ticker, _) in enumerate(ticker_list)}
    return sorted(results, key=lambda d: order.get(d["ticker"], 999))


def _compute_fear_greed(snapshot: dict) -> dict:
    """VIX 레벨 + SPY 5일 모멘텀 기반 Fear & Greed 추정."""
    vix = (snapshot.get("vix") or {}).get("price", 20.0)
    spy = next((i for i in snapshot.get("indices", []) if i["ticker"] == "SPY"), None)
    spy_pct = spy["pct"] if spy else 0.0

    # VIX 기반 기본 점수 (VIX 낮을수록 탐욕)
    if vix <= 12:
        base = 85
    elif vix <= 16:
        base = 70
    elif vix <= 20:
        base = 55
    elif vix <= 25:
        base = 40
    elif vix <= 30:
        base = 25
    else:
        base = 10

    # SPY 당일 모멘텀 보정 (-10 ~ +10)
    adjustment = max(-10, min(10, int(spy_pct * 2)))
    score = max(0, min(100, base + adjustment))

    if score >= 76:
        label = "극단적 탐욕"
    elif score >= 56:
        label = "탐욕"
    elif score >= 46:
        label = "중립"
    elif score >= 26:
        label = "공포"
    else:
        label = "극단적 공포"

    return {"score": score, "label": label}


def _fetch_top_movers(ticker_list: list[str]) -> dict:
    """대형주 리스트에서 당일 Top 3 상승/하락 수집 (회사명 포함)."""
    pairs = [(t, MOVER_NAMES.get(t, t)) for t in ticker_list]
    items = _fetch_extended_items(pairs, with_rsi=False)
    items = [i for i in items if i["price"] > 0]
    sorted_items = sorted(items, key=lambda x: x["pct"], reverse=True)
    return {
        "gainers": sorted_items[:3],
        "losers": sorted_items[-3:][::-1],
    }


def _compute_breadth(snapshot: dict) -> dict:
    """섹터·Mag7 어드밴스/디클라인 폭(breadth) 집계."""
    sectors = snapshot.get("sectors") or []
    pos_sec = sum(1 for s in sectors if s.get("pct", 0) > 0)
    neg_sec = sum(1 for s in sectors if s.get("pct", 0) < 0)
    mag7 = snapshot.get("mag7") or []
    pos_m7 = sum(1 for m in mag7 if m.get("price", 0) > 0 and m.get("pct", 0) > 0)
    neg_m7 = sum(1 for m in mag7 if m.get("price", 0) > 0 and m.get("pct", 0) < 0)
    return {
        "sector_positive": pos_sec,
        "sector_negative": neg_sec,
        "sector_total": len(sectors),
        "mag7_positive": pos_m7,
        "mag7_negative": neg_m7,
        "mag7_total": sum(1 for m in mag7 if m.get("price", 0) > 0),
    }


def _compute_5d_change(closes: list[float]) -> float | None:
    """최근 5거래일 수익률(%) — 종가 기준."""
    if len(closes) < 6 or closes[-6] == 0:
        return None
    return round((closes[-1] / closes[-6] - 1.0) * 100.0, 2)


def fetch_us_market_snapshot() -> dict:
    """SPY/QQQ/DIA/IWM + VIX + 섹터 + 매크로(yields/DXY) + Mag7 + 모버 병렬 수집."""
    now_kst = datetime.now(tz=KST)
    date_kst = now_kst.strftime("%Y-%m-%d")
    # 미국장 마감 기준 = KST 전날
    us_close_date = (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")

    # 1단계: 가격 데이터 병렬 수집 (indices, vix, sectors, bonds, comms, mag7, macro, asia, crypto)
    with ThreadPoolExecutor(max_workers=12) as ex:
        fut_indices = ex.submit(_fetch_extended_items, INDEX_TICKERS, False)
        fut_vix = ex.submit(_fetch_one_price, VIX_TICKER)
        fut_sectors = ex.submit(_fetch_extended_items, SECTOR_TICKERS, False)
        fut_bonds = ex.submit(_fetch_extended_items, BOND_TICKERS, False)
        fut_comms = ex.submit(_fetch_extended_items, COMMODITY_TICKERS, False)
        fut_mag7 = ex.submit(_fetch_extended_items, MAG7_TICKERS, True)
        fut_macro = ex.submit(_fetch_extended_items, MACRO_TICKERS, False)
        fut_asia = ex.submit(_fetch_extended_items, ASIA_TICKERS, False)
        fut_crypto = ex.submit(_fetch_extended_items, CRYPTO_TICKERS, False)
        fut_movers = ex.submit(_fetch_top_movers, MOVER_TICKERS)
        # 인덱스 RSI 및 5일 트렌드용 history 도 같이
        fut_index_hist = {
            ticker: ex.submit(_fetch_history, ticker, "1mo")
            for ticker, _ in INDEX_TICKERS
        }

        # vol·prev_close_ts 가 필요한 indices 는 보강 fetch (cache 가 부족할 때)
        indices_raw = fut_indices.result()
        # _fetch_extended_items 는 vol/prev_close_ts 를 내려주지 않으므로 보강
        indices_full = []
        for ticker, name in INDEX_TICKERS:
            base = next((i for i in indices_raw if i.get("ticker") == ticker), None) or {}
            extra = _fetch_one_price(ticker)
            indices_full.append({
                "ticker": ticker,
                "name": name,
                "price": base.get("price") or extra.get("price", 0.0),
                "pct": base.get("pct") if base.get("pct") is not None else extra.get("pct", 0.0),
                "vol": extra.get("vol", 0),
                "prev_close_ts": extra.get("prev_close_ts", ""),
            })

        vix_raw = fut_vix.result()
        vix = {"price": vix_raw["price"], "pct": vix_raw["pct"]}

        sectors_raw = fut_sectors.result()
        sectors = [
            {"ticker": s["ticker"], "name": s["name"], "pct": s["pct"], "price": s["price"]}
            for s in sectors_raw
        ]

        bonds = fut_bonds.result()
        commodities = fut_comms.result()
        mag7 = fut_mag7.result()
        macro = fut_macro.result()
        asia = fut_asia.result()
        crypto = fut_crypto.result()
        top_movers = fut_movers.result()

        # RSI 및 5일 트렌드 계산
        index_rsi: dict[str, float | None] = {}
        index_5d: dict[str, float | None] = {}
        for ticker, fut in fut_index_hist.items():
            closes = fut.result()
            index_rsi[ticker] = _compute_rsi(closes)
            index_5d[ticker] = _compute_5d_change(closes)

    sorted_sectors = sorted(sectors, key=lambda s: s["pct"], reverse=True)
    top_gainers = [s["ticker"] for s in sorted_sectors[:3]]
    top_losers = [s["ticker"] for s in sorted_sectors[-3:][::-1]]

    snapshot = {
        "date_kst": date_kst,
        "us_close_date": us_close_date,
        "is_us_market_holiday": False,
        "indices": indices_full,
        "vix": vix,
        "sectors": sectors,
        "top_gainers_sectors": top_gainers,
        "top_losers_sectors": top_losers,
        "narrative_hint": None,
        "bonds": bonds,
        "commodities": commodities,
        "mag7": mag7,
        "macro": macro,
        "asia": asia,
        "crypto": crypto,
        "index_rsi": index_rsi,
        "index_5d": index_5d,
        "top_movers": top_movers,
    }
    snapshot["is_us_market_holiday"] = is_us_market_holiday(snapshot)
    snapshot["narrative_hint"] = classify_narrative(snapshot)
    snapshot["fear_greed"] = _compute_fear_greed(snapshot)
    snapshot["breadth"] = _compute_breadth(snapshot)

    return snapshot


def is_us_market_holiday(snapshot: dict) -> bool:
    """prev_close_ts 가 예상 전 거래일 이전이면 휴장 판단.

    예상 전 거래일 = KST 날짜의 전날(주말은 건너뜀).
    """
    indices = snapshot.get("indices") or []
    if not indices:
        return False
    date_kst_str = snapshot.get("date_kst") or ""
    if not date_kst_str:
        return False
    try:
        date_kst = datetime.strptime(date_kst_str, "%Y-%m-%d").date()
    except ValueError:
        return False

    # 전 거래일 계산 (주말 skip)
    expected = date_kst - timedelta(days=1)
    while expected.weekday() >= 5:
        expected -= timedelta(days=1)

    # 모든 인덱스의 prev_close_ts 가 expected 보다 빠르면 (더 오래전) 휴장
    for idx in indices:
        ts = idx.get("prev_close_ts") or ""
        if not ts:
            return False  # 데이터 부재는 휴장으로 보지 않음 (안전 쪽)
        try:
            ts_date = datetime.strptime(ts[:10], "%Y-%m-%d").date()
        except ValueError:
            return False
        if ts_date >= expected:
            return False
    return True


def classify_narrative(snapshot: dict) -> str:
    """섹터 리더/래거 + VIX 변화로 시장 내러티브 분류."""
    sectors = snapshot.get("sectors") or []
    vix_pct = (snapshot.get("vix") or {}).get("pct", 0.0)

    if not sectors:
        return "mixed"

    sorted_secs = sorted(sectors, key=lambda s: s.get("pct", 0.0), reverse=True)
    top3 = {s["ticker"] for s in sorted_secs[:3]}
    bottom3 = {s["ticker"] for s in sorted_secs[-3:]}

    # VIX 급등(+10% 이상) 은 risk_off
    if vix_pct >= 10.0:
        return "risk_off"

    growth_in_top = len(top3 & GROWTH_SECTORS)
    defensive_in_top = len(top3 & DEFENSIVE_SECTORS)
    if growth_in_top >= 2 and defensive_in_top == 0:
        return "growth_led"
    if defensive_in_top >= 2 and growth_in_top == 0:
        return "defensive_led"

    return "mixed"


# ─────────────────────────────────────────────────────────────────
# Markdown 조립
# ─────────────────────────────────────────────────────────────────

_DISCLAIMER_BANNER = (
    '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
    'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
    '<strong>⚠️ 정보 제공용 데일리 마켓 리포트</strong><br>'
    '본 글은 yfinance 공개 데이터를 정리한 정보 콘텐츠입니다. '
    '특정 종목의 매수·매도를 권유하지 않으며 투자 자문이 아닙니다. '
    '모든 투자 결정과 손익은 본인 책임입니다.'
    '</div>'
)

_FOOTER_DISCLAIMER = (
    "\n---\n\n"
    "본 분석은 정보 제공 목적이며, 투자 결정은 본인 책임입니다. "
    "과거 수익률이 미래 수익을 보장하지 않습니다.\n"
)


def _format_pct(pct: float) -> str:
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


def _format_price(p: float) -> str:
    if p >= 100:
        return f"${p:,.2f}"
    return f"${p:.2f}"


def _parse_kst_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return datetime.now(tz=KST).replace(tzinfo=None)


def _build_title(snapshot: dict) -> str:
    d = _parse_kst_date(snapshot.get("date_kst", ""))
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    spy_pct = _format_pct(spy["pct"]) if spy else ""
    qqq_pct = _format_pct(qqq["pct"]) if qqq else ""
    spy_price = _format_price(spy["price"]) if spy else ""
    return (
        f"{d.year}년 {d.month}월 {d.day}일 미국 증시 마감: "
        f"S&P500 {spy_price} {spy_pct}, 나스닥 {qqq_pct}"
    )


def _build_description(snapshot: dict) -> str:
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []
    vix = snapshot.get("vix", {}).get("price", 0.0)
    macro = snapshot.get("macro") or []
    tnx = next((m for m in macro if m["ticker"] == "^TNX"), None)
    dxy = next((m for m in macro if m["ticker"] == "DX-Y.NYB"), None)
    macro_part = ""
    if tnx and tnx.get("price", 0) > 0:
        macro_part = f", 10Y {tnx['price']:.2f}%"
    if dxy and dxy.get("price", 0) > 0:
        macro_part += f", DXY {dxy['price']:.2f}"
    return (
        f"S&P500 {_format_pct(spy['pct']) if spy else ''}, "
        f"나스닥 {_format_pct(qqq['pct']) if qqq else ''}, "
        f"VIX {vix:.2f}{macro_part}. "
        f"리더 섹터 {', '.join(leaders[:2])}, "
        f"래거 섹터 {', '.join(laggards[:2])}."
    )


def _build_frontmatter(snapshot: dict) -> tuple[str, str]:
    from auto_publisher.content_generator import make_eeat_slug

    title = _build_title(snapshot)
    slug = make_eeat_slug(title)
    description = _build_description(snapshot)

    date_iso = snapshot.get("date_kst", datetime.now(tz=KST).strftime("%Y-%m-%d"))
    d = _parse_kst_date(snapshot.get("date_kst", ""))
    keywords = (
        f"S&P500 마감, 나스닥 마감, 다우 마감, VIX, 미국 증시 마감, "
        f"{d.year}-{d.month:02d}-{d.day:02d} 증시, 오늘 증시"
    )

    fm = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {date_iso}T07:15:00+09:00\n"
        f"lastmod: {date_iso}T07:15:00+09:00\n"
        "draft: false\n"
        f'description: "{description}"\n'
        f'keywords: "{keywords}"\n'
        'schema: "NewsArticle"\n'
        'primary_keyword: "미국 증시 마감"\n'
        "toc: true\n"
        "tags:\n"
        '  - "SPY"\n'
        '  - "QQQ"\n'
        '  - "DIA"\n'
        '  - "IWM"\n'
        '  - "VIX"\n'
        '  - "나스닥마감"\n'
        '  - "S&P500"\n'
        '  - "오늘증시"\n'
        "categories:\n"
        '  - "시장분석"\n'
        '  - "미국증시"\n'
        '  - "데일리마켓"\n'
        f'author: "InvestIQs 편집팀"\n'
        f'reviewedBy: "InvestIQs 감수팀"\n'
        "---\n\n"
    )
    return fm, slug


def _rsi_badge(rsi: float | None) -> str:
    if rsi is None:
        return "-"
    if rsi >= 70:
        return f"{rsi} ⚠️과매수"
    if rsi <= 30:
        return f"{rsi} 🔵과매도"
    return str(rsi)


def _build_index_table(snapshot: dict) -> str:
    index_rsi = snapshot.get("index_rsi") or {}
    index_5d = snapshot.get("index_5d") or {}
    rows = []
    rows.append("<table><caption>오늘 미국 주요 지수 마감</caption>")
    rows.append("<tr><th>지수</th><th>티커</th><th>종가</th><th>등락률</th><th>5일</th><th>RSI(14)</th><th>거래량</th></tr>")
    for idx in snapshot["indices"]:
        vol_str = f"{idx['vol']/1_000_000:.1f}M" if idx["vol"] else "-"
        rsi = index_rsi.get(idx["ticker"])
        d5 = index_5d.get(idx["ticker"])
        d5_str = _format_pct(d5) if d5 is not None else "-"
        rows.append(
            f"<tr><td>{idx['name']}</td><td>{idx['ticker']}</td>"
            f"<td>{_format_price(idx['price'])}</td>"
            f"<td>{_format_pct(idx['pct'])}</td>"
            f"<td>{d5_str}</td>"
            f"<td>{_rsi_badge(rsi)}</td>"
            f"<td>{vol_str}</td></tr>"
        )
    vix = snapshot.get("vix") or {}
    if vix:
        rows.append(
            f"<tr><td>VIX (변동성 지수)</td><td>^VIX</td>"
            f"<td>{vix.get('price', 0.0):.2f}</td>"
            f"<td>{_format_pct(vix.get('pct', 0.0))}</td>"
            f"<td>-</td><td>-</td><td>-</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


_MACRO_NAMES_BY_LANG = {
    "ko": {
        "^TNX": "미국 10년물 수익률", "^TYX": "미국 30년물 수익률",
        "^FVX": "미국 5년물 수익률", "DX-Y.NYB": "달러 인덱스 (DXY)",
    },
    "en": {
        "^TNX": "US 10Y Treasury Yield", "^TYX": "US 30Y Treasury Yield",
        "^FVX": "US 5Y Treasury Yield", "DX-Y.NYB": "Dollar Index (DXY)",
    },
    "ja": {
        "^TNX": "米国10年国債利回り", "^TYX": "米国30年国債利回り",
        "^FVX": "米国5年国債利回り", "DX-Y.NYB": "ドル指数 (DXY)",
    },
    "vi": {
        "^TNX": "Lợi suất TPCP Mỹ 10 năm", "^TYX": "Lợi suất TPCP Mỹ 30 năm",
        "^FVX": "Lợi suất TPCP Mỹ 5 năm", "DX-Y.NYB": "Chỉ số USD (DXY)",
    },
    "id": {
        "^TNX": "Imbal Hasil Treasury AS 10Y", "^TYX": "Imbal Hasil Treasury AS 30Y",
        "^FVX": "Imbal Hasil Treasury AS 5Y", "DX-Y.NYB": "Indeks Dolar (DXY)",
    },
}

_ASIA_NAMES_BY_LANG = {
    "ko": {"^N225": "Nikkei 225 (일본)", "^HSI": "Hang Seng (홍콩)",
           "^KS11": "KOSPI Composite (한국)", "000001.SS": "Shanghai Composite (중국)"},
    "en": {"^N225": "Nikkei 225 (Japan)", "^HSI": "Hang Seng (Hong Kong)",
           "^KS11": "KOSPI Composite (Korea)", "000001.SS": "Shanghai Composite (China)"},
    "ja": {"^N225": "日経平均株価", "^HSI": "ハンセン指数 (香港)",
           "^KS11": "KOSPI総合 (韓国)", "000001.SS": "上海総合指数"},
    "vi": {"^N225": "Nikkei 225 (Nhật)", "^HSI": "Hang Seng (Hồng Kông)",
           "^KS11": "KOSPI Composite (Hàn Quốc)", "000001.SS": "Shanghai Composite (Trung Quốc)"},
    "id": {"^N225": "Nikkei 225 (Jepang)", "^HSI": "Hang Seng (Hong Kong)",
           "^KS11": "KOSPI Composite (Korea)", "000001.SS": "Shanghai Composite (Tiongkok)"},
}

_MACRO_CAPTIONS = {
    "ko": ("핵심 매크로 — 국채 수익률 · 달러 인덱스", "지표", "티커", "현재값", "전일 대비"),
    "en": ("Macro Pulse — Treasury Yields · Dollar Index", "Indicator", "Ticker", "Current", "vs Prior"),
    "ja": ("マクロ — 国債利回り・ドル指数", "指標", "ティッカー", "現在値", "前日比"),
    "vi": ("Vĩ mô — Lợi suất TPCP · Chỉ số USD", "Chỉ báo", "Mã", "Hiện tại", "So với trước"),
    "id": ("Makro — Imbal Hasil Treasury · Indeks USD", "Indikator", "Ticker", "Saat ini", "vs Sebelumnya"),
}

_ASIA_CAPTIONS = {
    "ko": ("아시아 지수 · 디지털 자산 — 미국 마감 → 다음 시장 핸드오프", "구분", "자산", "티커", "현재값", "등락률", "🌏 아시아", "₿ 디지털"),
    "en": ("Asia Indices · Digital Assets — US close → next market handoff", "Type", "Asset", "Ticker", "Current", "Change", "🌏 Asia", "₿ Crypto"),
    "ja": ("アジア指数・デジタル資産 — 米国引け → 次市場への引継ぎ", "区分", "資産", "ティッカー", "現在値", "騰落率", "🌏 アジア", "₿ デジタル"),
    "vi": ("Chỉ số châu Á · Tài sản số — Bàn giao sau khi Mỹ đóng cửa", "Loại", "Tài sản", "Mã", "Hiện tại", "Thay đổi", "🌏 Châu Á", "₿ Số"),
    "id": ("Indeks Asia · Aset Digital — Sambungan setelah pasar AS tutup", "Jenis", "Aset", "Ticker", "Saat ini", "Perubahan", "🌏 Asia", "₿ Digital"),
}


def _build_macro_table(snapshot: dict, lang: str = "ko") -> str:
    """미 국채 수익률·달러 인덱스 핵심 매크로 테이블 (lang-aware)."""
    macro = snapshot.get("macro") or []
    if not any(m.get("price", 0) > 0 for m in macro):
        return ""
    name_map = _MACRO_NAMES_BY_LANG.get(lang) or _MACRO_NAMES_BY_LANG["en"]
    cap, h_ind, h_tk, h_cur, h_pct = _MACRO_CAPTIONS.get(lang) or _MACRO_CAPTIONS["en"]
    rows = [f"<table><caption>{cap}</caption>"]
    rows.append(f"<tr><th>{h_ind}</th><th>{h_tk}</th><th>{h_cur}</th><th>{h_pct}</th></tr>")
    for m in macro:
        if m.get("price", 0) <= 0:
            continue
        is_yield = m["ticker"].startswith("^")
        value_str = f"{m['price']:.2f}%" if is_yield else f"{m['price']:.2f}"
        display_name = name_map.get(m["ticker"], m.get("name") or m["ticker"])
        rows.append(
            f"<tr><td>{display_name}</td><td>{m['ticker']}</td>"
            f"<td>{value_str}</td>"
            f"<td>{_format_pct(m['pct'])}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _build_asia_crypto_table(snapshot: dict, lang: str = "ko") -> str:
    """아시아 지수 + 비트코인/이더리움 — lang-aware 자산명."""
    asia = snapshot.get("asia") or []
    crypto = snapshot.get("crypto") or []
    if not any(a.get("price", 0) > 0 for a in asia) and not any(c.get("price", 0) > 0 for c in crypto):
        return ""
    name_map = _ASIA_NAMES_BY_LANG.get(lang) or _ASIA_NAMES_BY_LANG["en"]
    cap, h_type, h_asset, h_tk, h_cur, h_chg, asia_label, crypto_label = (
        _ASIA_CAPTIONS.get(lang) or _ASIA_CAPTIONS["en"]
    )
    rows = [f"<table><caption>{cap}</caption>"]
    rows.append(
        f"<tr><th>{h_type}</th><th>{h_asset}</th><th>{h_tk}</th>"
        f"<th>{h_cur}</th><th>{h_chg}</th></tr>"
    )
    for a in asia:
        if a.get("price", 0) <= 0:
            continue
        bg = _heatmap_bg(a["pct"])
        fg = _heatmap_fg(a["pct"])
        cell_style = f'style="background:{bg};color:{fg};font-weight:600;"'
        display_name = name_map.get(a["ticker"], a.get("name") or a["ticker"])
        rows.append(
            f"<tr><td>{asia_label}</td><td>{display_name}</td><td>{a['ticker']}</td>"
            f"<td>{a['price']:,.2f}</td><td {cell_style}>{_format_pct(a['pct'])}</td></tr>"
        )
    for c in crypto:
        if c.get("price", 0) <= 0:
            continue
        bg = _heatmap_bg(c["pct"])
        fg = _heatmap_fg(c["pct"])
        cell_style = f'style="background:{bg};color:{fg};font-weight:600;"'
        rows.append(
            f"<tr><td>{crypto_label}</td><td>{c['name']}</td><td>{c['ticker']}</td>"
            f"<td>${c['price']:,.0f}</td><td {cell_style}>{_format_pct(c['pct'])}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _build_breadth_block(snapshot: dict) -> str:
    """섹터·Mag7 폭(breadth) 시각 박스."""
    b = snapshot.get("breadth") or {}
    sec_pos = b.get("sector_positive", 0)
    sec_tot = b.get("sector_total", 0)
    m7_pos = b.get("mag7_positive", 0)
    m7_tot = b.get("mag7_total", 0)
    if sec_tot == 0:
        return ""
    sec_ratio = (sec_pos / sec_tot) if sec_tot else 0
    m7_ratio = (m7_pos / m7_tot) if m7_tot else 0
    sec_emoji = "🟢" if sec_ratio >= 0.6 else "🟡" if sec_ratio >= 0.4 else "🔴"
    m7_emoji = "🟢" if m7_ratio >= 0.6 else "🟡" if m7_ratio >= 0.4 else "🔴"
    return (
        f'<div class="breadth-box" style="background:#f8f9fa;border:1px solid #dee2e6;'
        f'border-radius:8px;padding:0.8em 1.2em;margin:0 0 1.5em 0;font-size:0.95em;">'
        f"<strong>📊 시장 폭(Breadth)</strong> · "
        f"{sec_emoji} 섹터 {sec_pos}/{sec_tot} 상승 "
        f"({sec_ratio*100:.0f}%) · "
        f"{m7_emoji} Mag7 {m7_pos}/{m7_tot} 상승 "
        f"({m7_ratio*100:.0f}%)"
        f"</div>"
    )


def _build_fear_greed_block(snapshot: dict) -> str:
    fg = snapshot.get("fear_greed") or {}
    score = fg.get("score", 50)
    label = fg.get("label", "중립")
    vix_price = (snapshot.get("vix") or {}).get("price", 0.0)
    filled = round(score / 10)
    bar = "█" * filled + "░" * (10 - filled)
    emoji = "😨" if score < 26 else "😟" if score < 46 else "😐" if score < 56 else "😊" if score < 76 else "🤑"
    return (
        f'<div class="fg-gauge" style="background:#f8f9fa;border:1px solid #dee2e6;'
        f'border-radius:8px;padding:1em 1.2em;margin:0 0 1.5em 0;">'
        f"<strong>🧭 시장 심리: {label} {emoji} ({score}/100)</strong><br>"
        f"<code style=\"font-size:1.1em;letter-spacing:2px;\">{bar}</code> "
        f"<span style=\"font-size:0.85em;color:#666;\">VIX {vix_price:.2f} 기준 추정치</span>"
        f"</div>"
    )


def _build_bond_commodity_table(snapshot: dict) -> str:
    bonds = snapshot.get("bonds") or []
    comms = snapshot.get("commodities") or []
    rows = ["<table><caption>채권 ETF · 원자재 ETF 등락률</caption>"]
    rows.append("<tr><th>구분</th><th>자산</th><th>티커</th><th>종가</th><th>등락률</th></tr>")
    for item in bonds:
        if item["price"] > 0:
            rows.append(
                f"<tr><td>채권</td><td>{item['name']}</td><td>{item['ticker']}</td>"
                f"<td>{_format_price(item['price'])}</td><td>{_format_pct(item['pct'])}</td></tr>"
            )
    for item in comms:
        if item["price"] > 0:
            rows.append(
                f"<tr><td>원자재</td><td>{item['name']}</td><td>{item['ticker']}</td>"
                f"<td>{_format_price(item['price'])}</td><td>{_format_pct(item['pct'])}</td></tr>"
            )
    rows.append("</table>")
    return "\n".join(rows)


_MAG7_CAPTIONS = {
    "ko": ("Magnificent 7 — 오늘 퍼포먼스 (내림차순·히트맵)", "기업", "티커", "종가", "등락률"),
    "en": ("Magnificent 7 — Today's Performance (sorted, heatmap)", "Company", "Ticker", "Close", "Change"),
    "ja": ("Magnificent 7 — 本日のパフォーマンス (降順・ヒートマップ)", "企業", "ティッカー", "終値", "騰落率"),
    "vi": ("Magnificent 7 — Hiệu suất hôm nay (giảm dần, heatmap)", "Công ty", "Mã", "Giá đóng", "Thay đổi"),
    "id": ("Magnificent 7 — Performa Hari Ini (terurut, heatmap)", "Perusahaan", "Ticker", "Penutupan", "Perubahan"),
}

_MOVERS_CAPTIONS = {
    "ko": ("오늘 대형주 상승/하락 주도 종목 (Top 3)", "구분", "종목", "티커", "종가", "등락률", "📈 상승", "📉 하락"),
    "en": ("Top 3 Large-Cap Movers Today", "Type", "Name", "Ticker", "Close", "Change", "📈 Up", "📉 Down"),
    "ja": ("本日の大型株 値上がり/値下がり主導 (Top 3)", "区分", "銘柄", "ティッカー", "終値", "騰落率", "📈 上昇", "📉 下落"),
    "vi": ("Top 3 cổ phiếu vốn hóa lớn dẫn dắt hôm nay", "Loại", "Tên", "Mã", "Giá đóng", "Thay đổi", "📈 Tăng", "📉 Giảm"),
    "id": ("Top 3 Saham Large-Cap Pendorong Hari Ini", "Tipe", "Nama", "Ticker", "Penutupan", "Perubahan", "📈 Naik", "📉 Turun"),
}


def _build_mag7_table(snapshot: dict, lang: str = "ko") -> str:
    mag7 = snapshot.get("mag7") or []
    visible = [m for m in mag7 if m.get("price", 0) > 0]
    visible.sort(key=lambda m: m["pct"], reverse=True)
    cap, h_co, h_tk, h_cl, h_pct = _MAG7_CAPTIONS.get(lang) or _MAG7_CAPTIONS["en"]
    rows = [f"<table><caption>{cap}</caption>"]
    rows.append(f"<tr><th>{h_co}</th><th>{h_tk}</th><th>{h_cl}</th><th>{h_pct}</th><th>RSI(14)</th></tr>")
    for item in visible:
        bg = _heatmap_bg(item["pct"])
        fg = _heatmap_fg(item["pct"])
        cell_style = f'style="background:{bg};color:{fg};font-weight:600;"'
        rows.append(
            f"<tr><td>{item['name']}</td><td>{item['ticker']}</td>"
            f"<td>{_format_price(item['price'])}</td>"
            f"<td {cell_style}>{_format_pct(item['pct'])}</td>"
            f"<td>{_rsi_badge(item.get('rsi'))}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _build_top_movers(snapshot: dict, lang: str = "ko") -> str:
    movers = snapshot.get("top_movers") or {}
    gainers = movers.get("gainers") or []
    losers = movers.get("losers") or []
    if not gainers and not losers:
        return ""
    cap, h_type, h_name, h_tk, h_cl, h_pct, up_label, down_label = (
        _MOVERS_CAPTIONS.get(lang) or _MOVERS_CAPTIONS["en"]
    )
    rows = [f"<table><caption>{cap}</caption>"]
    rows.append(
        f"<tr><th>{h_type}</th><th>{h_name}</th><th>{h_tk}</th>"
        f"<th>{h_cl}</th><th>{h_pct}</th></tr>"
    )
    for g in gainers:
        name = g.get("name") or g["ticker"]
        rows.append(
            f"<tr><td>{up_label}</td><td>{name}</td><td>{g['ticker']}</td>"
            f"<td>{_format_price(g['price'])}</td><td>{_format_pct(g['pct'])}</td></tr>"
        )
    for l in losers:
        name = l.get("name") or l["ticker"]
        rows.append(
            f"<tr><td>{down_label}</td><td>{name}</td><td>{l['ticker']}</td>"
            f"<td>{_format_price(l['price'])}</td><td>{_format_pct(l['pct'])}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _heatmap_bg(pct: float) -> str:
    """등락률 → 인라인 셀 배경색 (그린 그라디언트 / 레드 그라디언트)."""
    if pct >= 1.5:
        return "#15803d"   # deep green
    if pct >= 0.5:
        return "#22c55e"   # green
    if pct > 0:
        return "#bbf7d0"   # light green
    if pct == 0:
        return "#f3f4f6"   # neutral
    if pct > -0.5:
        return "#fecaca"   # light red
    if pct > -1.5:
        return "#ef4444"   # red
    return "#991b1b"       # deep red


def _heatmap_fg(pct: float) -> str:
    """배경 채도에 맞춘 글자색."""
    return "#fff" if abs(pct) >= 0.5 else "#1f2937"


def _build_sector_table(snapshot: dict) -> str:
    sectors = sorted(snapshot.get("sectors", []), key=lambda s: s["pct"], reverse=True)
    rows = ["<table><caption>오늘 11개 섹터 ETF 변화율 (히트맵·내림차순)</caption>"]
    rows.append("<tr><th>순위</th><th>섹터</th><th>티커</th><th>등락률</th></tr>")
    for i, s in enumerate(sectors, 1):
        bg = _heatmap_bg(s["pct"])
        fg = _heatmap_fg(s["pct"])
        cell_style = f'style="background:{bg};color:{fg};font-weight:600;"'
        rows.append(
            f"<tr><td>{i}</td><td>{s['name']}</td>"
            f"<td>{s['ticker']}</td>"
            f"<td {cell_style}>{_format_pct(s['pct'])}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _build_narrative_paragraph(snapshot: dict) -> str:
    hint = snapshot.get("narrative_hint") or "mixed"
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    vix = snapshot.get("vix", {})
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []

    base = (
        f"오늘 S&P500은 {_format_pct(spy['pct']) if spy else '-'}, "
        f"나스닥은 {_format_pct(qqq['pct']) if qqq else '-'} 를 기록했다. "
        f"VIX는 {vix.get('price', 0.0):.2f} "
        f"({_format_pct(vix.get('pct', 0.0))})로 집계됐다. "
    )
    if hint == "growth_led":
        tone = (
            f"섹터에서는 {', '.join(leaders[:2])} 중심의 성장 섹터가 시장을 끌었고, "
            f"{', '.join(laggards[:2])} 는 상대적으로 약했다. "
            "성장 자금이 기술·소비재로 회전한 구간이다."
        )
    elif hint == "defensive_led":
        tone = (
            f"필수소비재·유틸리티·헬스케어 등 방어 섹터가 상위를 차지했고, "
            f"{', '.join(laggards[:2])} 는 부진했다. 위험 회피 심리가 우세한 구간이다."
        )
    elif hint == "risk_off":
        tone = (
            "VIX 가 큰 폭으로 상승하면서 전반적으로 위험 회피 구간으로 분류된다. "
            "섹터 전반이 조정 받는 구간이며, 뉴스/거시 이벤트 확인이 필요하다."
        )
    else:
        tone = (
            f"섹터별 방향성이 혼재됐다. 리더 {', '.join(leaders[:2])} 와 "
            f"래거 {', '.join(laggards[:2])} 가 공존하는 교차 구간이다."
        )
    return base + tone


def build_markdown(snapshot: dict, lang: str = "ko") -> str:
    """Front matter + 5개 H2 + 표 2개 + 면책조항 조립.

    lang != "ko" 인 경우 i18n_market 의 다국어 텍스트로 분기.
    """
    if lang and lang != "ko":
        from auto_publisher.market_localized import build_localized_wrap_markdown
        return build_localized_wrap_markdown(snapshot, lang)

    from auto_publisher.content_generator import fix_html_block_spacing

    fm, _slug = _build_frontmatter(snapshot)
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    vix = snapshot.get("vix", {})
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []

    summary = (
        f"**요약**: "
        f"S&P500 {_format_price(spy['price']) if spy else ''} {_format_pct(spy['pct']) if spy else ''}, "
        f"나스닥 {_format_pct(qqq['pct']) if qqq else ''}, "
        f"VIX {vix.get('price', 0.0):.2f}. "
        f"리더 섹터 {', '.join(leaders[:3])} / 래거 섹터 {', '.join(laggards[:3])}."
    )

    fg = snapshot.get("fear_greed") or {}
    fg_label = fg.get("label", "중립")
    fg_score = fg.get("score", 50)

    mag7 = snapshot.get("mag7") or []
    mag7_best = sorted([m for m in mag7 if m["price"] > 0], key=lambda x: x["pct"], reverse=True)
    mag7_leader = mag7_best[0]["ticker"] if mag7_best else ""
    mag7_laggard = mag7_best[-1]["ticker"] if mag7_best else ""

    bonds = snapshot.get("bonds") or []
    tlt = next((b for b in bonds if b["ticker"] == "TLT"), None)
    tlt_note = ""
    if tlt and tlt["price"] > 0:
        direction = "상승" if tlt["pct"] >= 0 else "하락"
        tlt_note = f" 장기채 TLT는 {_format_pct(tlt['pct'])} {direction}했다."

    movers_table = _build_top_movers(snapshot)

    macro_table = _build_macro_table(snapshot)
    breadth_block = _build_breadth_block(snapshot)
    breadth = snapshot.get("breadth") or {}

    # 매크로 데이터 기반 동적 코멘트
    macro_list = snapshot.get("macro") or []
    tnx = next((m for m in macro_list if m["ticker"] == "^TNX"), None)
    tyx = next((m for m in macro_list if m["ticker"] == "^TYX"), None)
    dxy = next((m for m in macro_list if m["ticker"] == "DX-Y.NYB"), None)
    macro_note_parts: list[str] = []
    if tnx and tnx.get("price", 0) > 0:
        direction = "상승" if tnx["pct"] >= 0 else "하락"
        macro_note_parts.append(
            f"10년물 수익률은 {tnx['price']:.2f}% ({_format_pct(tnx['pct'])}) {direction}했다."
        )
    if tyx and tyx.get("price", 0) > 0 and tnx and tnx.get("price", 0) > 0:
        spread = tyx["price"] - tnx["price"]
        spread_note = "정상" if spread >= 0 else "역전"
        macro_note_parts.append(
            f"30년-10년 스프레드는 {spread:+.2f}%p ({spread_note})."
        )
    if dxy and dxy.get("price", 0) > 0:
        direction = "강세" if dxy["pct"] >= 0 else "약세"
        macro_note_parts.append(
            f"달러 인덱스(DXY)는 {dxy['price']:.2f} ({_format_pct(dxy['pct'])}) {direction}."
        )
    macro_note = " ".join(macro_note_parts) if macro_note_parts else ""

    # RSI 과열/과매도 카운트
    index_rsi = snapshot.get("index_rsi") or {}
    overbought = [t for t, r in index_rsi.items() if r is not None and r >= 70]
    oversold = [t for t, r in index_rsi.items() if r is not None and r <= 30]
    rsi_note = ""
    if overbought:
        rsi_note = f"현재 {', '.join(overbought)} 지수 RSI(14)가 70선을 넘어 단기 과매수 구간이다. "
    elif oversold:
        rsi_note = f"현재 {', '.join(oversold)} 지수 RSI(14)가 30선 아래로 단기 과매도 구간이다. "

    # VIX 임계 동적 가이드
    vix_price = vix.get("price", 20.0)
    if vix_price < 15:
        vix_focus = f"VIX {vix_price:.2f} — 낮은 변동성 구간(15 이하). 갭 위험은 낮으나 안주는 금물"
    elif vix_price < 20:
        vix_focus = f"VIX {vix_price:.2f} — 중립 구간(15~20). 임계 20선 돌파 여부가 분수령"
    elif vix_price < 30:
        vix_focus = f"VIX {vix_price:.2f} — 경계 구간(20~30). 패닉 매도 가능성 점검"
    else:
        vix_focus = f"VIX {vix_price:.2f} — 패닉 구간(30 초과). 단기 반등 가능성과 추가 하락 모두 열려 있음"

    # 섹터 폭 코멘트
    sec_pos = breadth.get("sector_positive", 0)
    sec_tot = breadth.get("sector_total", 0)
    breadth_focus = ""
    if sec_tot:
        if sec_pos >= sec_tot - 2:
            breadth_focus = f"섹터 {sec_pos}/{sec_tot} 상승 — 폭 넓은 위험 선호"
        elif sec_pos <= 2:
            breadth_focus = f"섹터 {sec_pos}/{sec_tot} 만 상승 — 폭 좁은 약세 시장"
        else:
            breadth_focus = f"섹터 {sec_pos}/{sec_tot} 상승 — 혼조 구간"

    body_parts = [
        fm,
        _DISCLAIMER_BANNER,
        "",
        _build_fear_greed_block(snapshot),
        breadth_block,
        summary,
        "",
        "## 📊 지수 한눈에 보기",
        "",
        _build_index_table(snapshot),
        "",
        (
            "위 표는 미국 4대 지수(S&P 500, Nasdaq-100, Dow 30, Russell 2000)와 VIX 변동성 지수의 "
            "오늘 마감 수치를 한 줄로 정리한 것이다. RSI(14)가 70 이상이면 단기 과매수, "
            "30 이하면 과매도 구간으로 해석한다. 5일 컬럼은 최근 한 주 추세를 나타내며 "
            "당일 등락과 추세가 같은 방향이면 모멘텀 지속, 반대 방향이면 반전 시그널 후보다. "
            "VIX는 어제 대비 변화율의 방향이 핵심이다."
        ),
        "",
        "## 🌐 핵심 매크로 — 국채 수익률 · 달러",
        "",
        macro_table if macro_table else "_(매크로 데이터 없음)_",
        "",
        (
            "10년물 수익률(^TNX)은 위험자산 할인율의 핵심 변수다. "
            "수익률이 빠르게 오르면 성장주(특히 PER이 높은 기술주)에 압력이 가해지고, "
            "달러 인덱스(DXY)가 동반 강세면 외국인 자금 유입이 둔화될 수 있다. "
            "30년-10년 스프레드가 역전되어 있으면 장기 경기 둔화 신호로 본다."
            + (" " + macro_note if macro_note else "")
        ),
        "",
        "## 📈 섹터별 강약",
        "",
        _build_sector_table(snapshot),
        "",
        (
            f"리더 섹터는 **{', '.join(leaders[:3])}**, 래거 섹터는 **{', '.join(laggards[:3])}** 로 집계됐다. "
            f"오늘 11개 섹터 중 {sec_pos}개가 상승 마감했다. "
            "성장주 섹터(XLK·XLC·XLY)가 상위에 있으면 위험 선호 구간, "
            "방어주 섹터(XLP·XLU·XLV)가 상위에 있으면 위험 회피 구간으로 해석한다."
        ),
        "",
        "## 💎 채권·원자재",
        "",
        _build_bond_commodity_table(snapshot),
        "",
        (
            "채권과 원자재는 주식시장의 맥락을 읽는 보조 지표다. "
            "장기채(TLT)가 오르면 경기 둔화 우려 또는 안전자산 선호, "
            "금(GLD) 상승은 달러 약세 또는 불확실성 확대 신호로 해석하는 경우가 많다."
            + tlt_note
        ),
        "",
        "## 🚀 Magnificent 7",
        "",
        _build_mag7_table(snapshot),
        "",
        (
            f"빅테크 7개 종목 중 오늘 가장 강했던 종목은 **{mag7_leader}**, "
            f"가장 약했던 종목은 **{mag7_laggard}** 다. "
            f"Mag7 중 {breadth.get('mag7_positive', 0)}/{breadth.get('mag7_total', 0)}개 종목이 상승 마감했다. "
            "Mag7의 방향은 나스닥100(QQQ) 추세에 직결되므로 지수 등락과 함께 확인한다."
        ) if mag7_leader else "",
        "",
        "## 📉 오늘의 상승/하락 주도 종목",
        "",
        movers_table if movers_table else "_(모버 데이터 없음)_",
        "",
        "## 🌏 아시아 핸드오프 · 디지털 자산",
        "",
        _build_asia_crypto_table(snapshot) or "_(아시아·디지털 자산 데이터 없음)_",
        "",
        (
            "한국 독자에게 미국 마감 → 아시아 개장은 자금 흐름의 자연스러운 다음 페이지다. "
            "특히 닛케이225·홍콩H지수가 미국 흐름을 따라가는지, 디커플링되는지 첫 시간 안에 드러난다. "
            "비트코인·이더리움은 24시간 거래되는 위험선호 바로미터로, 미국장 마감 후의 즉각적인 위험심리 변화를 "
            "가장 빠르게 반영한다."
        ),
        "",
        "## 💡 오늘의 시장 내러티브",
        "",
        _build_narrative_paragraph(snapshot),
        "",
        (
            f"시장 심리 지수는 **{fg_label}({fg_score})** 으로 집계됐다. "
            f"{breadth_focus}. "
            "내러티브를 읽을 때는 한 요인만 보지 않는 것이 중요하다. 지수 한 곳이 올라도 섹터별 분포가 "
            "편중되어 있으면 추세 지속성이 약할 수 있고, 반대로 지수가 약해도 섹터 폭이 넓게 오르면 "
            "체감 건강도는 더 좋을 수 있다."
        ),
        "",
        "## 🎯 시나리오 박스 (정보 제공·투자 자문 아님)",
        "",
        (
            "**상승 시나리오**: "
            f"{rsi_note}이 구간에서 추가 상승이 이어지려면 (1) VIX가 현재 {vix_price:.2f} 에서 추가로 안정, "
            "(2) 채권 수익률이 상단을 시도하지 않고 박스권 유지, "
            "(3) 섹터 폭이 더 넓게 확장되며 방어주가 함께 따라오는 흐름이 필요하다."
        ),
        "",
        (
            "**하락 시나리오**: 반대로 단기 조정 가능성을 견인할 수 있는 요인은 "
            "(1) VIX 20선 돌파, (2) 10년물 수익률 급등 + DXY 동반 강세 (위험자산 압박), "
            "(3) 섹터 폭 급락(상승 섹터 3개 미만)과 Mag7 동반 약세, (4) 어닝 시즌 가이던스 하향이다. "
            "어느 시나리오로 갈지는 단정할 수 없으며 양쪽 시나리오 모두 사전에 점검하는 것이 위험관리의 핵심이다."
        ),
        "",
        "## 🔮 내일 주목할 포인트",
        "",
        f"- {vix_focus}",
        f"- {breadth_focus}" if breadth_focus else "- 섹터 폭(상승 섹터 비중) 확장 또는 축소 여부",
        (
            f"- 10년물 수익률 (현재 {tnx['price']:.2f}%) — 4.5% 돌파 시 성장주 압력 확대"
            if tnx and tnx.get("price", 0) > 0
            else "- 10년물 미국채 수익률 방향성"
        ),
        (
            f"- 달러 인덱스(DXY {dxy['price']:.2f}) — 강세 지속 시 다국적 기업·신흥국 자산 압박"
            if dxy and dxy.get("price", 0) > 0
            else "- 달러 인덱스(DXY) 강세/약세 흐름"
        ),
        "- 미국 경제지표 발표 시간 (CPI/PPI/소매판매/ISM 등) 확인",
        "- FOMC 의사록 발표일과 주요 연준 위원 발언 일정",
        "- 실적 발표 시즌이면 어닝 컨센서스와 실제 차이",
        "- 채권(TLT) · 달러(DXY) · 금(GLD) 동반 움직임 여부",
        "",
        "## ⚡ Action Point (정보 제공)",
        "",
        "- 오늘 마감 데이터는 단기 이벤트이며, 단일 세션만으로 방향을 단정하지 않는다.",
        "- 내가 보유한 섹터·티커가 오늘의 리더/래거 중 어디에 속하는지 확인만 한다.",
        "- VIX 흐름과 개별 포지션의 변동성을 비교해 리스크 허용도를 점검한다.",
        "- Mag7 RSI가 70 이상이면 단기 과열 신호로 추가 진입 시 유의한다.",
        "- 10년물 수익률·DXY가 동반 급등하는 구간에서는 성장주 비중을 점검한다.",
        "- 다음 발표 이벤트(경제지표/FOMC/어닝)까지는 포지션 변경을 서두르지 않는다.",
        "",
        _FOOTER_DISCLAIMER,
    ]

    md = "\n".join(body_parts)
    return fix_html_block_spacing(md)
