"""매일 아침 '미국 증시 마감' 포스트 생성기.

데이터 스펙과 템플릿은 /home/mh/.claude/plans/peaceful-jumping-charm.md 참조.

핵심 함수:
- fetch_us_market_snapshot(): SPY/QQQ/DIA/IWM + 11개 섹터 ETF + VIX 수집
- is_us_market_holiday(snapshot): 휴장일 감지
- classify_narrative(snapshot): growth_led / defensive_led / risk_off / mixed
- build_markdown(snapshot): Hugo front matter + 5개 H2 + 표 2개
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
    """대형주 리스트에서 당일 Top 3 상승/하락 수집."""
    pairs = [(t, t) for t in ticker_list]
    items = _fetch_extended_items(pairs, with_rsi=False)
    items = [i for i in items if i["price"] > 0]
    sorted_items = sorted(items, key=lambda x: x["pct"], reverse=True)
    return {
        "gainers": sorted_items[:3],
        "losers": sorted_items[-3:][::-1],
    }


def fetch_us_market_snapshot() -> dict:
    """SPY/QQQ/DIA/IWM + VIX + 11개 섹터 ETF 스냅샷 수집."""
    now_kst = datetime.now(tz=KST)
    date_kst = now_kst.strftime("%Y-%m-%d")
    # 미국장 마감 기준 = KST 전날
    us_close_date = (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")

    indices = []
    for ticker, name in INDEX_TICKERS:
        p = _fetch_one_price(ticker)
        indices.append({
            "ticker": ticker,
            "name": name,
            "price": p["price"],
            "pct": p["pct"],
            "vol": p["vol"],
            "prev_close_ts": p["prev_close_ts"],
        })

    vix_raw = _fetch_one_price(VIX_TICKER)
    vix = {"price": vix_raw["price"], "pct": vix_raw["pct"]}

    sectors = []
    for ticker, name in SECTOR_TICKERS:
        p = _fetch_one_price(ticker)
        sectors.append({
            "ticker": ticker,
            "name": name,
            "pct": p["pct"],
            "price": p["price"],
        })

    sorted_sectors = sorted(sectors, key=lambda s: s["pct"], reverse=True)
    top_gainers = [s["ticker"] for s in sorted_sectors[:3]]
    top_losers = [s["ticker"] for s in sorted_sectors[-3:][::-1]]

    snapshot = {
        "date_kst": date_kst,
        "us_close_date": us_close_date,
        "is_us_market_holiday": False,
        "indices": indices,
        "vix": vix,
        "sectors": sectors,
        "top_gainers_sectors": top_gainers,
        "top_losers_sectors": top_losers,
        "narrative_hint": None,
    }
    snapshot["is_us_market_holiday"] = is_us_market_holiday(snapshot)
    snapshot["narrative_hint"] = classify_narrative(snapshot)

    # 확장 데이터 병렬 수집
    snapshot["fear_greed"] = _compute_fear_greed(snapshot)

    with ThreadPoolExecutor(max_workers=3) as ex:
        fut_bonds = ex.submit(_fetch_extended_items, BOND_TICKERS, False)
        fut_comms = ex.submit(_fetch_extended_items, COMMODITY_TICKERS, False)
        fut_mag7 = ex.submit(_fetch_extended_items, MAG7_TICKERS, True)
        snapshot["bonds"] = fut_bonds.result()
        snapshot["commodities"] = fut_comms.result()
        snapshot["mag7"] = fut_mag7.result()

    # 지수 RSI 병렬 계산
    index_rsi: dict[str, float | None] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        rsi_futures = {ex.submit(_fetch_history, ticker, "1mo"): ticker for ticker, _ in INDEX_TICKERS}
        for fut in as_completed(rsi_futures):
            ticker = rsi_futures[fut]
            closes = fut.result()
            index_rsi[ticker] = _compute_rsi(closes)
    snapshot["index_rsi"] = index_rsi

    snapshot["top_movers"] = _fetch_top_movers(MOVER_TICKERS)

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

    if top3 & GROWTH_SECTORS == GROWTH_SECTORS & {s["ticker"] for s in sorted_secs[:3]}:
        growth_in_top = len(top3 & GROWTH_SECTORS)
        defensive_in_top = len(top3 & DEFENSIVE_SECTORS)
        if growth_in_top >= 2 and defensive_in_top == 0:
            return "growth_led"

    if len(top3 & DEFENSIVE_SECTORS) >= 2 and len(top3 & GROWTH_SECTORS) == 0:
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
    return (
        f"S&P500 {_format_pct(spy['pct']) if spy else ''}, "
        f"나스닥 {_format_pct(qqq['pct']) if qqq else ''}, "
        f"VIX {vix:.2f}. 리더 섹터 {', '.join(leaders[:2])}, "
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
    rows = []
    rows.append("<table><caption>오늘 미국 주요 지수 마감</caption>")
    rows.append("<tr><th>지수</th><th>티커</th><th>종가</th><th>등락률</th><th>RSI(14)</th><th>거래량</th></tr>")
    for idx in snapshot["indices"]:
        vol_str = f"{idx['vol']/1_000_000:.1f}M" if idx["vol"] else "-"
        rsi = index_rsi.get(idx["ticker"])
        rows.append(
            f"<tr><td>{idx['name']}</td><td>{idx['ticker']}</td>"
            f"<td>{_format_price(idx['price'])}</td>"
            f"<td>{_format_pct(idx['pct'])}</td>"
            f"<td>{_rsi_badge(rsi)}</td>"
            f"<td>{vol_str}</td></tr>"
        )
    vix = snapshot.get("vix") or {}
    if vix:
        rows.append(
            f"<tr><td>VIX (변동성 지수)</td><td>^VIX</td>"
            f"<td>{vix.get('price', 0.0):.2f}</td>"
            f"<td>{_format_pct(vix.get('pct', 0.0))}</td>"
            f"<td>-</td><td>-</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


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


def _build_mag7_table(snapshot: dict) -> str:
    mag7 = snapshot.get("mag7") or []
    rows = ["<table><caption>Magnificent 7 — 오늘 퍼포먼스</caption>"]
    rows.append("<tr><th>기업</th><th>티커</th><th>종가</th><th>등락률</th><th>RSI(14)</th></tr>")
    for item in mag7:
        if item["price"] > 0:
            rows.append(
                f"<tr><td>{item['name']}</td><td>{item['ticker']}</td>"
                f"<td>{_format_price(item['price'])}</td>"
                f"<td>{_format_pct(item['pct'])}</td>"
                f"<td>{_rsi_badge(item.get('rsi'))}</td></tr>"
            )
    rows.append("</table>")
    return "\n".join(rows)


def _build_top_movers(snapshot: dict) -> str:
    movers = snapshot.get("top_movers") or {}
    gainers = movers.get("gainers") or []
    losers = movers.get("losers") or []
    if not gainers and not losers:
        return ""
    rows = ["<table><caption>오늘 대형주 상승/하락 주도 종목 (Top 3)</caption>"]
    rows.append("<tr><th>구분</th><th>티커</th><th>등락률</th></tr>")
    for g in gainers:
        rows.append(f"<tr><td>📈 상승</td><td>{g['ticker']}</td><td>{_format_pct(g['pct'])}</td></tr>")
    for l in losers:
        rows.append(f"<tr><td>📉 하락</td><td>{l['ticker']}</td><td>{_format_pct(l['pct'])}</td></tr>")
    rows.append("</table>")
    return "\n".join(rows)


def _build_sector_table(snapshot: dict) -> str:
    sectors = sorted(snapshot.get("sectors", []), key=lambda s: s["pct"], reverse=True)
    rows = ["<table><caption>오늘 11개 섹터 ETF 변화율 (내림차순)</caption>"]
    rows.append("<tr><th>순위</th><th>섹터</th><th>티커</th><th>등락률</th></tr>")
    for i, s in enumerate(sectors, 1):
        rows.append(
            f"<tr><td>{i}</td><td>{s['name']}</td>"
            f"<td>{s['ticker']}</td>"
            f"<td>{_format_pct(s['pct'])}</td></tr>"
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

    body_parts = [
        fm,
        _DISCLAIMER_BANNER,
        "",
        _build_fear_greed_block(snapshot),
        summary,
        "",
        "## 📊 지수 한눈에 보기",
        "",
        _build_index_table(snapshot),
        "",
        (
            "위 표는 미국 4대 지수(S&P 500, Nasdaq-100, Dow 30, Russell 2000)와 VIX 변동성 지수의 "
            "오늘 마감 수치를 한 줄로 정리한 것이다. RSI(14)가 70 이상이면 단기 과매수, "
            "30 이하면 과매도 구간으로 해석한다. VIX는 어제 대비 변화율의 방향이 핵심이다."
        ),
        "",
        "## 📈 섹터별 강약",
        "",
        _build_sector_table(snapshot),
        "",
        (
            f"리더 섹터는 **{', '.join(leaders[:3])}**, 래거 섹터는 **{', '.join(laggards[:3])}** 로 집계됐다. "
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
            "Mag7의 방향은 나스닥100(QQQ) 추세에 직결되므로 지수 등락과 함께 확인한다."
        ) if mag7_leader else "",
        "",
        "## 📉 오늘의 상승/하락 주도 종목",
        "",
        movers_table if movers_table else "_(모버 데이터 없음)_",
        "",
        "## 💡 오늘의 시장 내러티브",
        "",
        _build_narrative_paragraph(snapshot),
        "",
        (
            f"시장 심리 지수는 **{fg_label}({fg_score})** 으로 집계됐다. "
            "내러티브를 읽을 때는 한 요인만 보지 않는 것이 중요하다. 지수 한 곳이 올라도 섹터별 분포가 "
            "편중되어 있으면 추세 지속성이 약할 수 있고, 반대로 지수가 약해도 섹터 폭이 넓게 오르면 "
            "체감 건강도는 더 좋을 수 있다."
        ),
        "",
        "## 🔮 내일 주목할 포인트",
        "",
        "- 미국 경제지표 발표 시간 (CPI/PPI/소매판매/ISM 등) 확인",
        "- FOMC 의사록 발표일과 주요 연준 위원 발언 일정",
        "- 실적 발표 시즌이면 어닝 컨센서스와 실제 차이",
        "- VIX 가 20선을 돌파하거나 이탈하는지 모니터링",
        "- 10년물 미국채 수익률 방향성",
        "- 채권(TLT) · 달러(DXY) · 금(GLD) 동반 움직임 여부",
        "",
        "## ⚡ Action Point (정보 제공)",
        "",
        "- 오늘 마감 데이터는 단기 이벤트이며, 단일 세션만으로 방향을 단정하지 않는다.",
        "- 내가 보유한 섹터·티커가 오늘의 리더/래거 중 어디에 속하는지 확인만 한다.",
        "- VIX 흐름과 개별 포지션의 변동성을 비교해 리스크 허용도를 점검한다.",
        "- Mag7 RSI가 70 이상이면 단기 과열 신호로 추가 진입 시 유의한다.",
        "- 다음 발표 이벤트(경제지표/FOMC/어닝)까지는 포지션 변경을 서두르지 않는다.",
        "",
        _FOOTER_DISCLAIMER,
    ]

    md = "\n".join(body_parts)
    return fix_html_block_spacing(md)
