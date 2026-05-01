"""미국 장중 시황 (22:30 KST, 개장 30분 후 첫 인상) 포스트 생성기.

market_wrap.py 와 차별점:
- 비교 기준: 어제 마감 vs 오늘 종가  →  "오늘 개장가 vs 현재가" (첫 30분 모멘텀)
- 갭(gap_up/gap_down/gap_flat) 분류
- 본문 톤: "방금 개장해서..." (첫 인상)
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
    _parse_kst_date,
)

logger = logging.getLogger(__name__)


def _fetch_intraday_price(ticker: str) -> dict:
    """오늘 개장가 + 현재가 + 첫 30분 거래량.

    Returns:
        {
            "open": float,         # 오늘 개장가
            "current": float,      # 현재가 (또는 가장 최근 5분봉 종가)
            "pct_from_open": float,    # (current-open)/open*100
            "pct_gap_from_prev": float,# (open - prev_close)/prev_close*100
            "vol_30m": int,        # 첫 30분 누적 거래량
            "prev_close_ts": str,
        }
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        # 오늘 5분봉 데이터 (개장 직후 ~30분)
        intra = t.history(period="1d", interval="5m", auto_adjust=False)
        prev = t.history(period="5d", interval="1d", auto_adjust=False)
        if intra is None or intra.empty or prev is None or prev.empty:
            return {"open": 0.0, "current": 0.0, "pct_from_open": 0.0,
                    "pct_gap_from_prev": 0.0, "vol_30m": 0, "prev_close_ts": ""}
        # 5분봉 6개(=30분) 미만이면 아직 장이 안 열렸거나 휴장
        if len(intra) < 6:
            return {"open": 0.0, "current": 0.0, "pct_from_open": 0.0,
                    "pct_gap_from_prev": 0.0, "vol_30m": 0, "prev_close_ts": ""}
        open_px = float(intra.iloc[0]["Open"])
        current_px = float(intra.iloc[-1]["Close"])
        first_30m = intra.iloc[:6]  # 5분*6 = 30분
        vol_30m = int(first_30m["Volume"].sum())
        prev_close = float(prev.iloc[-2]["Close"]) if len(prev) >= 2 else open_px
        pct_open = ((current_px - open_px) / open_px * 100.0) if open_px else 0.0
        pct_gap = ((open_px - prev_close) / prev_close * 100.0) if prev_close else 0.0
        ts = str(prev.index[-2].date()) if len(prev) >= 2 else ""
        return {
            "open": open_px,
            "current": current_px,
            "pct_from_open": pct_open,
            "pct_gap_from_prev": pct_gap,
            "vol_30m": vol_30m,
            "prev_close_ts": ts,
        }
    except Exception as e:
        logger.warning(f"yfinance intraday fetch failed for {ticker}: {e}")
        return {"open": 0.0, "current": 0.0, "pct_from_open": 0.0,
                "pct_gap_from_prev": 0.0, "vol_30m": 0, "prev_close_ts": ""}


def fetch_intraday_snapshot() -> dict:
    """SPY/QQQ/DIA/IWM + VIX + 11 섹터 ETF 의 개장 30분 후 스냅샷."""
    now_kst = datetime.now(tz=KST)
    date_kst = now_kst.strftime("%Y-%m-%d")
    us_dt = now_kst - timedelta(days=0 if now_kst.hour >= 22 else 1)
    us_session_date = us_dt.strftime("%Y-%m-%d")

    # 주말(토·일) 감지 — 미국장 휴장
    if us_dt.weekday() >= 5:  # 5=Saturday, 6=Sunday
        logger.info(f"[intraday] {us_session_date} 주말 휴장 — 스냅샷 스킵")
        return {
            "date_kst": date_kst,
            "us_session_date": us_session_date,
            "is_us_market_holiday": True,
            "minutes_after_open": 0,
            "indices": [], "vix": {}, "sectors": [],
            "top_gainers_sectors": [], "top_losers_sectors": [],
            "gap": "gap_flat", "narrative_hint": "mixed",
        }

    indices = []
    for ticker, name in INDEX_TICKERS:
        p = _fetch_intraday_price(ticker)
        indices.append({
            "ticker": ticker,
            "name": name,
            "open": p["open"],
            "current": p["current"],
            "pct_from_open": p["pct_from_open"],
            "pct_gap_from_prev": p["pct_gap_from_prev"],
            "vol_30m": p["vol_30m"],
            "prev_close_ts": p["prev_close_ts"],
        })

    vix_raw = _fetch_intraday_price(VIX_TICKER)
    vix_price = vix_raw["current"] or 0.0
    vix_level = "low" if vix_price < 15 else "mid" if vix_price < 22 else "high"
    vix = {
        "price": vix_price,
        "pct_from_prev": vix_raw["pct_gap_from_prev"],
        "level": vix_level,
    }

    sectors = []
    for ticker, name in SECTOR_TICKERS:
        p = _fetch_intraday_price(ticker)
        sectors.append({
            "ticker": ticker,
            "name": name,
            "pct_from_open": p["pct_from_open"],
            "open": p["open"],
            "current": p["current"],
        })

    sorted_secs = sorted(sectors, key=lambda s: s["pct_from_open"], reverse=True)
    snapshot = {
        "date_kst": date_kst,
        "us_session_date": us_session_date,
        "is_us_market_holiday": False,
        "minutes_after_open": 30,
        "indices": indices,
        "vix": vix,
        "sectors": sectors,
        "top_gainers_sectors": [s["ticker"] for s in sorted_secs[:3]],
        "top_losers_sectors": [s["ticker"] for s in sorted_secs[-3:][::-1]],
        "gap": None,
        "narrative_hint": None,
    }
    snapshot["gap"] = classify_gap(snapshot)
    snapshot["narrative_hint"] = classify_intraday_narrative(snapshot)
    snapshot["is_us_market_holiday"] = not is_us_market_in_session(snapshot)
    return snapshot


def is_us_market_in_session(snapshot: dict) -> bool:
    """모든 인덱스의 open=0 이면 장이 안 열린 것 (휴장 또는 데이터 부재)."""
    indices = snapshot.get("indices") or []
    if not indices:
        return False
    for idx in indices:
        if (idx.get("open") or 0) > 0 and (idx.get("current") or 0) > 0:
            return True
    return False


def classify_gap(snapshot: dict) -> str:
    """SPY+QQQ 평균 갭으로 시장 갭 분류."""
    indices = snapshot.get("indices") or []
    main = [i for i in indices if i.get("ticker") in ("SPY", "QQQ")]
    if not main:
        return "gap_flat"
    avg = sum(i.get("pct_gap_from_prev", 0.0) for i in main) / len(main)
    if avg >= 0.4:
        return "gap_up"
    if avg <= -0.4:
        return "gap_down"
    return "gap_flat"


def classify_intraday_narrative(snapshot: dict) -> str:
    """첫 30분 인덱스 + VIX 변화로 장중 분류."""
    indices = snapshot.get("indices") or []
    main = [i for i in indices if i.get("ticker") in ("SPY", "QQQ")]
    avg_pct = (sum(i.get("pct_from_open", 0.0) for i in main) / len(main)) if main else 0.0
    vix_pct = (snapshot.get("vix") or {}).get("pct_from_prev", 0.0)

    if avg_pct >= 0.3 and vix_pct <= 0:
        return "early_strength"
    if avg_pct <= -0.3 and vix_pct >= 0:
        return "early_weakness"
    if vix_pct >= 8:
        return "risk_off"
    return "mixed"


# ─────────────────────────────────────────────────────────────────
# Markdown 조립
# ─────────────────────────────────────────────────────────────────

_DISCLAIMER_BANNER = (
    '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
    'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
    '<strong>⚠️ 정보 제공용 장중 스냅샷 리포트</strong><br>'
    '본 글은 미국장 개장 30분 후의 yfinance 공개 데이터를 정리한 정보 콘텐츠입니다. '
    '시간 흐름에 따라 수치는 빠르게 변할 수 있으며, 특정 종목 매수·매도를 권유하지 않습니다. '
    '모든 투자 결정과 손익은 본인 책임입니다.'
    '</div>'
)

_FOOTER_DISCLAIMER = (
    "\n---\n\n"
    "본 분석은 정보 제공 목적이며, 투자 결정은 본인 책임입니다. "
    "장중 데이터는 분 단위로 변할 수 있고, 첫 30분 흐름이 일중 마감과 일치한다는 보장이 없습니다.\n"
)


def _build_intraday_title(snapshot: dict) -> str:
    d = _parse_kst_date(snapshot.get("date_kst", ""))
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    spy_pct = _format_pct(spy["pct_from_open"]) if spy else ""
    qqq_pct = _format_pct(qqq["pct_from_open"]) if qqq else ""
    return (
        f"{d.year}년 {d.month}월 {d.day}일 미국 증시 장중: "
        f"개장 30분 S&P500 {spy_pct}, 나스닥 {qqq_pct}"
    )


def _build_intraday_description(snapshot: dict) -> str:
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []
    vix = snapshot.get("vix", {}).get("price", 0.0)
    return (
        f"미국장 개장 30분 후 S&P500 {_format_pct(spy['pct_from_open']) if spy else ''}, "
        f"나스닥 {_format_pct(qqq['pct_from_open']) if qqq else ''}, "
        f"VIX {vix:.2f}. 초반 리더 {', '.join(leaders[:2])}, 약세 {', '.join(laggards[:2])}."
    )


def _build_frontmatter_intraday(snapshot: dict) -> tuple[str, str]:
    from auto_publisher.content_generator import make_eeat_slug

    title = _build_intraday_title(snapshot)
    slug = "intraday-" + make_eeat_slug(title)
    description = _build_intraday_description(snapshot)
    date_iso = snapshot.get("date_kst", datetime.now(tz=KST).strftime("%Y-%m-%d"))
    d = _parse_kst_date(snapshot.get("date_kst", ""))
    keywords = (
        f"미국 증시 장중, S&P500 장중, 나스닥 장중, 미국증시 개장, 개장 30분, "
        f"{d.year}-{d.month:02d}-{d.day:02d} 시황"
    )
    fm = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {date_iso}T22:30:00+09:00\n"
        f"lastmod: {date_iso}T22:30:00+09:00\n"
        "draft: false\n"
        f'description: "{description}"\n'
        f'keywords: "{keywords}"\n'
        'schema: "NewsArticle"\n'
        'primary_keyword: "미국 증시 장중"\n'
        "toc: true\n"
        "tags:\n"
        '  - "SPY"\n'
        '  - "QQQ"\n'
        '  - "DIA"\n'
        '  - "IWM"\n'
        '  - "VIX"\n'
        '  - "장중시황"\n'
        '  - "미국증시 개장"\n'
        '  - "오늘증시"\n'
        "categories:\n"
        '  - "시장분석"\n'
        '  - "미국증시"\n'
        '  - "일일시황"\n'
        f'author: "InvestIQs 편집팀"\n'
        f'reviewedBy: "InvestIQs 감수팀"\n'
        "---\n\n"
    )
    return fm, slug


def _build_intraday_index_table(snapshot: dict) -> str:
    rows = ["<table><caption>개장 30분 후 미국 주요 지수</caption>"]
    rows.append("<tr><th>지수</th><th>티커</th><th>개장가</th><th>현재가</th>"
                "<th>개장가 대비</th><th>전일종가 대비 갭</th><th>30분 거래량</th></tr>")
    for idx in snapshot["indices"]:
        vol_str = f"{idx['vol_30m']/1_000_000:.1f}M" if idx.get("vol_30m") else "-"
        rows.append(
            f"<tr><td>{idx['name']}</td><td>{idx['ticker']}</td>"
            f"<td>{_format_price(idx['open'])}</td>"
            f"<td>{_format_price(idx['current'])}</td>"
            f"<td>{_format_pct(idx['pct_from_open'])}</td>"
            f"<td>{_format_pct(idx['pct_gap_from_prev'])}</td>"
            f"<td>{vol_str}</td></tr>"
        )
    vix = snapshot.get("vix") or {}
    if vix:
        rows.append(
            f"<tr><td>VIX (변동성)</td><td>^VIX</td>"
            f"<td>-</td><td>{vix.get('price', 0.0):.2f}</td>"
            f"<td>-</td><td>{_format_pct(vix.get('pct_from_prev', 0.0))}</td><td>-</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _build_intraday_sector_table(snapshot: dict) -> str:
    sectors = sorted(snapshot.get("sectors", []), key=lambda s: s["pct_from_open"], reverse=True)
    rows = ["<table><caption>개장 30분 후 11개 섹터 ETF 변화율 (내림차순)</caption>"]
    rows.append("<tr><th>순위</th><th>섹터</th><th>티커</th><th>개장가 대비</th></tr>")
    for i, s in enumerate(sectors, 1):
        rows.append(
            f"<tr><td>{i}</td><td>{s['name']}</td>"
            f"<td>{s['ticker']}</td>"
            f"<td>{_format_pct(s['pct_from_open'])}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def _build_intraday_narrative(snapshot: dict) -> str:
    hint = snapshot.get("narrative_hint") or "mixed"
    gap = snapshot.get("gap") or "gap_flat"
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    vix = snapshot.get("vix", {})
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []

    base = (
        f"미국장이 방금 개장해 약 30분이 지난 시점이다. "
        f"S&P500은 개장가 대비 {_format_pct(spy['pct_from_open']) if spy else '-'}, "
        f"나스닥은 {_format_pct(qqq['pct_from_open']) if qqq else '-'} 를 기록 중이다. "
        f"VIX는 {vix.get('price', 0.0):.2f} ({_format_pct(vix.get('pct_from_prev', 0.0))})로 집계된다. "
    )
    gap_text = {
        "gap_up": "오늘 시장은 갭상승으로 출발했다. 전일종가보다 높은 가격에 매매가 시작됐다는 뜻이다. ",
        "gap_down": "오늘 시장은 갭하락으로 출발했다. 전일종가보다 낮은 가격에 매매가 시작됐다는 뜻이다. ",
        "gap_flat": "오늘 시장은 거의 평행으로 출발했다. 전일종가와 비슷한 가격에서 매매가 시작됐다. ",
    }.get(gap, "")

    tone = {
        "early_strength": (
            f"개장 30분 동안 {', '.join(leaders[:2])} 중심의 위험자산 섹터가 강세를 보였고, "
            f"{', '.join(laggards[:2])} 는 상대적으로 부진했다. 단기 모멘텀은 일단 매수 우위 구간이다."
        ),
        "early_weakness": (
            f"개장 30분 동안 시장 전반이 압력을 받았고, "
            f"{', '.join(laggards[:2])} 가 특히 약했다. VIX 도 함께 상승해 단기 위험 회피 신호가 동반됐다."
        ),
        "risk_off": (
            "VIX 급등이 동반된 위험 회피 시작이다. 첫 30분 흐름은 단기 변동성을 가르는 분기점이 될 수 있다. "
            "거시 헤드라인이나 어닝 충격이 있는지 확인이 필요하다."
        ),
        "mixed": (
            f"섹터별로 방향성이 갈렸다. {', '.join(leaders[:2])} 는 위에 있고 "
            f"{', '.join(laggards[:2])} 는 아래에 있어 일중 후반부 자금 이동을 더 봐야 한다."
        ),
    }.get(hint, "")
    return base + gap_text + tone


def build_intraday_markdown(snapshot: dict, lang: str = "ko") -> str:
    """Front matter + 4~5 H2 + 표 2 + 면책."""
    if lang and lang != "ko":
        from auto_publisher.market_localized import build_localized_intraday_markdown
        return build_localized_intraday_markdown(snapshot, lang)

    from auto_publisher.content_generator import fix_html_block_spacing

    fm, _slug = _build_frontmatter_intraday(snapshot)
    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    vix = snapshot.get("vix", {})
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []
    gap = snapshot.get("gap") or "gap_flat"

    summary = (
        f"**개장 30분 요약**: "
        f"S&P500 {_format_pct(spy['pct_from_open']) if spy else ''}, "
        f"나스닥 {_format_pct(qqq['pct_from_open']) if qqq else ''}, "
        f"VIX {vix.get('price', 0.0):.2f}. "
        f"갭 분류: {gap}. "
        f"초반 리더 {', '.join(leaders[:3])} / 약세 {', '.join(laggards[:3])}."
    )

    body = [
        fm,
        _DISCLAIMER_BANNER,
        "",
        summary,
        "",
        "## 📊 개장 30분 지수 스냅샷",
        "",
        _build_intraday_index_table(snapshot),
        "",
        (
            "위 표는 미국 4대 지수(S&P 500, Nasdaq-100, Dow 30, Russell 2000)의 "
            "오늘 개장가, 현재가, 개장가 대비 변화율, 그리고 전일종가 대비 갭(gap) 을 정리한 것이다. "
            "갭은 장 시작 직전의 수급 의지를 압축적으로 보여주고, 개장가 대비 변화율은 첫 30분 동안의 "
            "참여자 심리 변화를 반영한다. 두 수치를 함께 보면 단기 모멘텀이 갭 방향과 일치하는지, "
            "아니면 되돌리는지 판단할 수 있다."
        ),
        "",
        "## 📈 섹터 초반 강약",
        "",
        _build_intraday_sector_table(snapshot),
        "",
        (
            f"개장 30분 기준 리더 섹터는 **{', '.join(leaders[:3])}**, 약세 섹터는 "
            f"**{', '.join(laggards[:3])}** 다. 장 초반 섹터 분포는 거래량이 작아 신뢰도가 낮을 수 있지만, "
            "특정 섹터가 시장 평균을 크게 벗어나면 뉴스 또는 어닝 영향이 깔려 있을 가능성이 높다. "
            "이 단계에서는 어떤 자금이 어디로 들어가고 있는지 가설만 세우고, 일중 후반부 추가 확인이 필요하다."
        ),
        "",
        "## 💡 첫 30분 시장 인상",
        "",
        _build_intraday_narrative(snapshot),
        "",
        (
            "장 초반 30분 데이터는 일중 마감 결과로 그대로 이어진다는 보장이 없다. "
            "특히 미국장은 개장 직후 변동성이 가장 큰 구간이라, 갭 방향이 후반부에 되돌려지는 경우도 흔하다. "
            "지금 흐름은 어디까지나 출발점이며, 마감 데이터(다음 날 07:15 KST 발행 마감 정리 글)와 비교해 "
            "패턴이 유지됐는지 확인하는 게 좋다."
        ),
        "",
        "## 🔮 일중 모니터링 포인트",
        "",
        "- 미국 시간 10:00 EST 발표(KST 23:00) 경제지표가 있는지 캘린더 확인",
        "- 갭 방향이 11:00 EST 까지 유지되는지, 되돌려지는지 추적",
        "- VIX 가 급등/급락 흐름과 함께 지수가 같이 움직이는지 동조 여부",
        "- 메이저 종목(NVDA, MSFT, AAPL, AMZN, GOOG, META, TSLA) 개별 변동성",
        "- 어닝 발표 직전/직후 종목의 갭 정상화 속도",
        "",
        "## ⚡ Action Point (정보 제공)",
        "",
        "- 첫 30분 흐름만 보고 포지션을 새로 잡지 않는다.",
        "- 보유 섹터·종목이 오늘 리더/약세 중 어디에 속하는지 확인만 한다.",
        "- VIX 와 지수가 정상적으로 음의 상관을 보이는지 점검한다.",
        "- 일중 큰 이벤트(경제지표/연준 발언)가 있는 날인지 캘린더로 다시 확인한다.",
        "",
        _FOOTER_DISCLAIMER,
    ]

    md = "\n".join(body)
    return fix_html_block_spacing(md)


def publish_intraday(langs: list[str] | None = None) -> dict:
    """장중 스냅샷을 가져와 지정 언어로 발행. 주말/휴장이면 스킵."""
    from auto_publisher.publishers.hugo import HugoPublisher

    snapshot = fetch_intraday_snapshot()

    if snapshot.get("is_us_market_holiday"):
        logger.info("[intraday] 휴장일 — 발행 스킵")
        return {"skipped": True, "reason": "us_market_holiday"}

    if not snapshot.get("indices"):
        logger.warning("[intraday] indices 비어있음 — 발행 스킵")
        return {"skipped": True, "reason": "no_data"}

    langs = langs or ["ko", "en", "ja", "vi", "id"]
    results = {}
    for lang in langs:
        try:
            md = build_intraday_markdown(snapshot, lang=lang)
            _, slug = _build_frontmatter_intraday(snapshot)
            publisher = HugoPublisher(lang=lang, section="daily")
            r = publisher.publish_raw_markdown(md, slug, section="daily")
            results[lang] = r
            logger.info(f"[intraday] {lang} 발행 완료: {r['url']}")
        except Exception as e:
            logger.error(f"[intraday] {lang} 발행 실패: {e}", exc_info=True)
            results[lang] = {"error": str(e)}

    return {"skipped": False, "results": results}
