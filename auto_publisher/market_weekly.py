"""주간 시황 (토요일 09:00 KST, 한 주 누적) 포스트 생성기.

market_wrap/intraday 와 차별점:
- 비교 기준: 한 주(월~금 5거래일) 누적 변화율 + 최대 낙폭 + 평균 거래량
- next_week_calendar 정적 템플릿 (FOMC/지표/어닝 placeholder)
- frontmatter categories 에 '주간시황' 명시 → migrate 분류기가 weekly 로 이동
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from auto_publisher.market_wrap import (
    INDEX_TICKERS,
    SECTOR_TICKERS,
    VIX_TICKER,
    GROWTH_SECTORS,
    DEFENSIVE_SECTORS,
    KST,
    _format_pct,
    _format_price,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# 데이터 수집
# ─────────────────────────────────────────────────────────────────

def _fetch_5d_summary(ticker: str) -> dict:
    """5거래일 누적: open(첫날 시가), close(마지막날 종가), pct_5d, max_drawdown_5d, vol_avg_5d."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="7d", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return {"open": 0.0, "close": 0.0, "pct_5d": 0.0,
                    "max_drawdown_5d": 0.0, "vol_avg_5d": 0}
        last5 = hist.tail(5)
        if last5.empty:
            return {"open": 0.0, "close": 0.0, "pct_5d": 0.0,
                    "max_drawdown_5d": 0.0, "vol_avg_5d": 0}
        open_px = float(last5.iloc[0]["Open"])
        close_px = float(last5.iloc[-1]["Close"])
        pct = ((close_px - open_px) / open_px * 100.0) if open_px else 0.0
        # max drawdown: 5거래일 동안 가장 낮은 종가 vs 시작 시가
        min_low = float(last5["Low"].min())
        max_dd = ((min_low - open_px) / open_px * 100.0) if open_px else 0.0
        vol_avg = int(last5["Volume"].mean())
        return {
            "open": open_px,
            "close": close_px,
            "pct_5d": pct,
            "max_drawdown_5d": max_dd,
            "vol_avg_5d": vol_avg,
        }
    except Exception as e:
        logger.warning(f"yfinance 5d fetch failed for {ticker}: {e}")
        return {"open": 0.0, "close": 0.0, "pct_5d": 0.0,
                "max_drawdown_5d": 0.0, "vol_avg_5d": 0}


def _make_week_label(end_date: datetime) -> str:
    """'2026년 4월 4주차 (4월 20일~24일)' 형식."""
    week_of_month = (end_date.day - 1) // 7 + 1
    start = end_date - timedelta(days=4)
    return (
        f"{end_date.year}년 {end_date.month}월 {week_of_month}주차 "
        f"({start.month}월 {start.day}일~{end_date.day}일)"
    )


def fetch_weekly_snapshot() -> dict:
    """SPY/QQQ/DIA/IWM + 11 섹터 ETF + VIX 의 5거래일 누적 스냅샷."""
    now_kst = datetime.now(tz=KST)
    publish_date = now_kst.strftime("%Y-%m-%d")
    # KST 토요일 09:00 발행 가정 → 직전 미국 거래일은 금요일
    # 5거래일 = 직전 금요일 기준 월~금 (KST 기준 토요일에 발행하므로 미국은 전날 마감)
    # us_week_end = 토요일 - 1일 (KST 금요일 = 미국 금요일)
    us_week_end_dt = now_kst - timedelta(days=1)
    while us_week_end_dt.weekday() != 4:  # 금요일까지 거슬러
        us_week_end_dt -= timedelta(days=1)
    us_week_start_dt = us_week_end_dt - timedelta(days=4)

    indices = []
    for ticker, name in INDEX_TICKERS:
        s = _fetch_5d_summary(ticker)
        indices.append({
            "ticker": ticker, "name": name,
            "open": s["open"], "close": s["close"],
            "pct_5d": s["pct_5d"],
            "max_drawdown_5d": s["max_drawdown_5d"],
            "vol_avg_5d": s["vol_avg_5d"],
        })

    vix_raw = _fetch_5d_summary(VIX_TICKER)
    vix_close = vix_raw["close"]
    vix_level = "low" if vix_close < 15 else "mid" if vix_close < 22 else "high"
    vix = {
        "week_open": vix_raw["open"],
        "week_close": vix_close,
        "pct_5d": vix_raw["pct_5d"],
        "level": vix_level,
    }

    sectors = []
    for ticker, name in SECTOR_TICKERS:
        s = _fetch_5d_summary(ticker)
        sectors.append({
            "ticker": ticker, "name": name,
            "pct_5d": s["pct_5d"],
            "open": s["open"], "close": s["close"],
        })

    sorted_secs = sorted(sectors, key=lambda s: s["pct_5d"], reverse=True)

    # 다음 주 캘린더 (정적 템플릿 — 추후 자동 수집 가능)
    next_week_calendar = [
        "FOMC 의사록·연준 발언 일정 확인",
        "주요 경제지표 발표 (CPI/PPI/소매판매/PCE 등) 캘린더 확인",
        "다음 주 어닝 발표 메이저 종목 (NVDA/AAPL/MSFT/META/AMZN/GOOG/TSLA 등) 확인",
        "10년물 미국채 금리 흐름과 달러 인덱스(DXY) 모니터링",
        "VIX 가 지난 주 종가 기준 어느 방향으로 움직이는지 추적",
    ]

    snapshot = {
        "week_label": _make_week_label(us_week_end_dt),
        "us_week_start": us_week_start_dt.strftime("%Y-%m-%d"),
        "us_week_end": us_week_end_dt.strftime("%Y-%m-%d"),
        "kst_publish_date": publish_date,
        "is_full_week": True,
        "indices": indices,
        "vix": vix,
        "sectors": sectors,
        "top_gainers_sectors": [s["ticker"] for s in sorted_secs[:3]],
        "top_losers_sectors": [s["ticker"] for s in sorted_secs[-3:][::-1]],
        "narrative_hint": None,
        "next_week_calendar": next_week_calendar,
    }
    snapshot["narrative_hint"] = classify_weekly_narrative(snapshot)
    return snapshot


def classify_weekly_narrative(snapshot: dict) -> str:
    """5일 누적 인덱스 + 섹터 + VIX 변화로 주간 분류."""
    indices = snapshot.get("indices") or []
    main = [i for i in indices if i.get("ticker") in ("SPY", "QQQ")]
    avg_pct = (sum(i.get("pct_5d", 0.0) for i in main) / len(main)) if main else 0.0
    vix_pct = (snapshot.get("vix") or {}).get("pct_5d", 0.0)

    sectors = snapshot.get("sectors") or []
    sorted_secs = sorted(sectors, key=lambda s: s.get("pct_5d", 0.0), reverse=True)
    top3 = {s["ticker"] for s in sorted_secs[:3]} if sorted_secs else set()

    # VIX 30%+ 급등 = risk_off
    if vix_pct >= 25.0 or avg_pct <= -3.0:
        return "risk_off_week"

    growth_in_top = len(top3 & GROWTH_SECTORS)
    defensive_in_top = len(top3 & DEFENSIVE_SECTORS)
    if growth_in_top >= 2 and defensive_in_top == 0 and avg_pct >= 0.5:
        return "growth_led_week"
    if defensive_in_top >= 2 and growth_in_top == 0:
        return "defensive_led_week"
    return "mixed_week"


# ─────────────────────────────────────────────────────────────────
# Markdown
# ─────────────────────────────────────────────────────────────────

_DISCLAIMER_BANNER = (
    '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
    'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
    '<strong>⚠️ 정보 제공용 주간 시황 리포트</strong><br>'
    '본 글은 yfinance 공개 데이터를 기준으로 한 주간(5거래일) 흐름을 정리한 정보 콘텐츠입니다. '
    '특정 종목의 매수·매도를 권유하지 않으며, 모든 투자 결정과 손익은 본인 책임입니다.'
    '</div>'
)

_FOOTER_DISCLAIMER = (
    "\n---\n\n"
    "본 분석은 정보 제공 목적이며, 투자 결정은 본인 책임입니다. "
    "한 주 흐름이 다음 주 같은 방향을 보장하지 않으며, 데이터는 발행 시점 기준입니다.\n"
)


def _build_weekly_title(snapshot: dict) -> str:
    label = snapshot.get("week_label", "")
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    spy_pct = _format_pct(spy["pct_5d"]) if spy else ""
    qqq_pct = _format_pct(qqq["pct_5d"]) if qqq else ""
    return (
        f"{label} 미국 증시 주간 정리: "
        f"S&P500 {spy_pct}, 나스닥 {qqq_pct}"
    )


def _build_weekly_description(snapshot: dict) -> str:
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []
    vix_close = (snapshot.get("vix") or {}).get("week_close", 0.0)
    return (
        f"한 주 5거래일 누적 S&P500 {_format_pct(spy['pct_5d']) if spy else ''}, "
        f"나스닥 {_format_pct(qqq['pct_5d']) if qqq else ''}, "
        f"VIX 종가 {vix_close:.2f}. 리더 섹터 {', '.join(leaders[:2])}, "
        f"래거 {', '.join(laggards[:2])}."
    )


def _build_frontmatter_weekly(snapshot: dict) -> tuple[str, str]:
    from auto_publisher.content_generator import make_eeat_slug

    title = _build_weekly_title(snapshot)
    slug = "weekly-" + make_eeat_slug(title)
    description = _build_weekly_description(snapshot)
    publish_date = snapshot.get("kst_publish_date", datetime.now(tz=KST).strftime("%Y-%m-%d"))
    # 발행 시점이 미래 (예: 09:00 KST cron) 이면 Hugo 가 future-dated 글로 간주해 빌드 제외하므로
    # 현재 시각으로 date 를 설정한다.
    now_iso = datetime.now(tz=KST).strftime("%Y-%m-%dT%H:%M:%S%z")
    # %z 는 +0900 → +09:00 변환
    now_iso = now_iso[:-2] + ":" + now_iso[-2:]
    keywords = (
        f"미국 증시 주간, 미국증시 마감 주간, S&P500 주간, 나스닥 주간, VIX 주간, "
        f"{snapshot.get('us_week_start','')} ~ {snapshot.get('us_week_end','')} 시황"
    )
    fm = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {now_iso}\n"
        f"lastmod: {now_iso}\n"
        "draft: false\n"
        f'description: "{description}"\n'
        f'keywords: "{keywords}"\n'
        'schema: "NewsArticle"\n'
        'primary_keyword: "미국 증시 주간"\n'
        "toc: true\n"
        "tags:\n"
        '  - "SPY"\n'
        '  - "QQQ"\n'
        '  - "DIA"\n'
        '  - "IWM"\n'
        '  - "VIX"\n'
        '  - "주간시황"\n'
        '  - "미국증시 주간"\n'
        '  - "S&P500"\n'
        "categories:\n"
        '  - "시장분석"\n'
        '  - "미국증시"\n'
        '  - "주간시황"\n'
        f'author: "InvestIQs 편집팀"\n'
        f'reviewedBy: "InvestIQs 감수팀"\n'
        "---\n\n"
    )
    return fm, slug


def _build_weekly_index_table(snapshot: dict) -> str:
    rows = ["<table><caption>한 주 미국 주요 지수 누적 흐름</caption>"]
    rows.append("<tr><th>지수</th><th>티커</th><th>주간 시가</th><th>주간 종가</th>"
                "<th>5일 누적</th><th>주중 최대낙폭</th><th>평균 거래량</th></tr>")
    for idx in snapshot["indices"]:
        vol_str = f"{idx['vol_avg_5d']/1_000_000:.1f}M" if idx.get("vol_avg_5d") else "-"
        rows.append(
            f"<tr><td>{idx['name']}</td><td>{idx['ticker']}</td>"
            f"<td>{_format_price(idx['open'])}</td>"
            f"<td>{_format_price(idx['close'])}</td>"
            f"<td>{_format_pct(idx['pct_5d'])}</td>"
            f"<td>{_format_pct(idx['max_drawdown_5d'])}</td>"
            f"<td>{vol_str}</td></tr>"
        )
    vix = snapshot.get("vix") or {}
    if vix:
        rows.append(
            f"<tr><td>VIX (변동성)</td><td>^VIX</td>"
            f"<td>{vix.get('week_open', 0.0):.2f}</td>"
            f"<td>{vix.get('week_close', 0.0):.2f}</td>"
            f"<td>{_format_pct(vix.get('pct_5d', 0.0))}</td>"
            f"<td>-</td><td>-</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _build_weekly_sector_table(snapshot: dict) -> str:
    sectors = sorted(snapshot.get("sectors", []), key=lambda s: s["pct_5d"], reverse=True)
    rows = ["<table><caption>한 주 11개 섹터 ETF 5일 누적 (내림차순)</caption>"]
    rows.append("<tr><th>순위</th><th>섹터</th><th>티커</th><th>5일 누적</th></tr>")
    for i, s in enumerate(sectors, 1):
        rows.append(
            f"<tr><td>{i}</td><td>{s['name']}</td>"
            f"<td>{s['ticker']}</td>"
            f"<td>{_format_pct(s['pct_5d'])}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _build_weekly_narrative(snapshot: dict) -> str:
    hint = snapshot.get("narrative_hint") or "mixed_week"
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    vix = snapshot.get("vix", {})
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []

    base = (
        f"한 주 5거래일 동안 S&P500은 누적 {_format_pct(spy['pct_5d']) if spy else '-'}, "
        f"나스닥은 {_format_pct(qqq['pct_5d']) if qqq else '-'} 변화를 보였다. "
        f"VIX는 주초 {vix.get('week_open', 0.0):.2f} 에서 주말 {vix.get('week_close', 0.0):.2f} 로 "
        f"{_format_pct(vix.get('pct_5d', 0.0))} 변동했다. "
    )
    tone = {
        "growth_led_week": (
            f"섹터에서는 {', '.join(leaders[:2])} 등 성장 섹터가 주간 상위였고, "
            f"{', '.join(laggards[:2])} 는 부진했다. 위험 선호 흐름이 한 주 동안 우세했다."
        ),
        "defensive_led_week": (
            f"필수소비재·유틸리티·헬스케어 등 방어 섹터가 주간 상위에 위치했고, "
            f"{', '.join(laggards[:2])} 는 약세였다. 한 주간 자금 회전이 방어로 기울었다."
        ),
        "risk_off_week": (
            "VIX 가 큰 폭으로 상승하거나 지수가 크게 하락한 위험 회피 주간이다. "
            "원인이 거시 헤드라인(연준/지표/지정학)인지 미시 어닝 충격인지 확인이 필요하다."
        ),
        "mixed_week": (
            f"섹터별 방향이 갈렸다. 리더 {', '.join(leaders[:2])} 와 래거 {', '.join(laggards[:2])} 가 "
            "공존하는 교차 주간이었다. 단일 내러티브로 묶기 어려운 구간이다."
        ),
    }.get(hint, "")
    return base + tone


def build_weekly_markdown(snapshot: dict, lang: str = "ko") -> str:
    """Front matter + 5~6 H2 + 표 2 + 다음 주 캘린더 + 면책."""
    if lang and lang != "ko":
        from auto_publisher.market_localized import build_localized_weekly_markdown
        return build_localized_weekly_markdown(snapshot, lang)

    from auto_publisher.content_generator import fix_html_block_spacing

    fm, _slug = _build_frontmatter_weekly(snapshot)
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    vix = snapshot.get("vix", {})
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []
    calendar = snapshot.get("next_week_calendar") or []

    summary = (
        f"**주간 요약**: "
        f"S&P500 {_format_pct(spy['pct_5d']) if spy else ''}, "
        f"나스닥 {_format_pct(qqq['pct_5d']) if qqq else ''}, "
        f"VIX 종가 {vix.get('week_close', 0.0):.2f}. "
        f"리더 섹터 {', '.join(leaders[:3])} / 래거 {', '.join(laggards[:3])}."
    )

    body = [
        fm,
        _DISCLAIMER_BANNER,
        "",
        summary,
        "",
        f"한 주 5거래일을 누적해 보면, 매일의 잡음을 빼고 흐름의 방향과 폭이 더 분명히 보인다. "
        f"이번 주 ({snapshot.get('week_label')}) 데이터를 지수·섹터·변동성 세 축으로 정리한다.",
        "",
        "## 📊 주간 지수 누적 흐름",
        "",
        _build_weekly_index_table(snapshot),
        "",
        (
            "위 표는 미국 4대 지수의 한 주 시가·종가·5일 누적 변화율과 주중 최대낙폭을 정리한 것이다. "
            "단순 종가 변화만 보면 흐름의 강도를 놓치기 쉽다. 주중 최대낙폭과 평균 거래량을 함께 보면, "
            "추세가 일관됐는지 변동성이 컸는지 가늠할 수 있다. VIX 종가 흐름은 옵션 시장이 다음 주를 "
            "어떻게 예상하는지의 단서가 된다."
        ),
        "",
        "## 📈 주간 섹터 강약",
        "",
        _build_weekly_sector_table(snapshot),
        "",
        (
            f"한 주 누적 기준 리더 섹터는 **{', '.join(leaders[:3])}**, 래거 섹터는 "
            f"**{', '.join(laggards[:3])}** 다. 일별 리더가 매일 바뀌는 구간과 한 주 내내 같은 섹터가 "
            "상위인 구간은 의미가 다르다. 후자는 자금이 한 방향으로 누적된다는 뜻이고, 전자는 회전이 "
            "빠른 단기 트레이딩 구간일 가능성이 크다."
        ),
        "",
        "## 💡 한 주 시장 내러티브",
        "",
        _build_weekly_narrative(snapshot),
        "",
        (
            "주간 내러티브를 읽을 때는 단일 요인에 의존하지 않는다. 지수가 올라도 섹터가 좁은 종목 몇 개에 "
            "집중되어 있으면 추세의 폭이 좁고, 반대로 지수가 약해도 섹터 폭이 넓게 견뎠다면 체감 시장은 더 "
            "건강할 수 있다. VIX 흐름과 섹터 분포를 함께 보면 다음 주 변동성 구간을 예측하는 단서가 된다."
        ),
        "",
        "## 🔮 다음 주 주목 캘린더",
        "",
    ]

    if calendar:
        for item in calendar:
            body.append(f"- {item}")
    else:
        body.append("- FOMC 의사록·연준 발언 일정")
        body.append("- 주요 경제지표 발표 (CPI/PPI/소매판매/PCE)")
        body.append("- 메이저 종목 어닝")
    body += [
        "",
        (
            "이벤트가 몰린 주는 평소보다 변동성이 커지기 쉽다. 어떤 이벤트가 가격에 이미 반영됐고 어떤 "
            "이벤트가 새로운 충격이 될 수 있는지 사전에 분류해 두면, 주중 의사결정 속도가 빨라진다."
        ),
        "",
        "## ⚡ Action Point (정보 제공)",
        "",
        "- 보유 섹터·종목이 이번 주 리더/래거 중 어디였는지 확인하고, 다음 주에도 같은 분포가 유지될지 가설을 세운다.",
        "- VIX 종가 흐름이 다음 주에 어떤 이벤트와 만나는지 확인한다 (지표·어닝).",
        "- 5일 최대낙폭이 큰 인덱스는 단기 변동성이 커진 것이므로 포지션 사이즈와 손절 기준을 점검한다.",
        "- 한 주 누적이 강했다고 해서 다음 주 같은 속도가 유지된다는 보장은 없다.",
        "",
        _FOOTER_DISCLAIMER,
    ]

    md = "\n".join(body)
    return fix_html_block_spacing(md)
