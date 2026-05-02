"""다국어(en/ja/vi/id) 시황 마크다운 빌더.

market_wrap / market_intraday / market_weekly 의 build_markdown 이
lang != "ko" 일 때 호출하는 공통 모듈.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from auto_publisher.i18n_market import get_i18n, date_label
from auto_publisher.market_wrap import (
    KST,
    _format_pct,
    _format_price,
    _parse_kst_date,
)


def _build_localized_frontmatter(
    snapshot: dict,
    lang: str,
    title: str,
    description: str,
    publish_iso: str,
    section_categories_keys: list[str],
    primary_keyword: str,
    extra_tags: list[str] | None = None,
) -> tuple[str, str]:
    """공통 frontmatter 빌더 — i18n 카테고리 자동 적용."""
    from auto_publisher.content_generator import make_eeat_slug

    i18n = get_i18n(lang)
    cats_dict = i18n["categories_market"]
    cats_lines = "\n".join(
        f'  - "{cats_dict[k]}"' for k in section_categories_keys if k in cats_dict
    )

    base_tags = ["SPY", "QQQ", "DIA", "IWM", "VIX"] + (extra_tags or [])
    tags_lines = "\n".join(f'  - "{t}"' for t in base_tags)

    slug = make_eeat_slug(title)

    _fetched_at = snapshot.get("fetched_at") if isinstance(snapshot, dict) else ""
    if not _fetched_at:
        from datetime import datetime, timezone, timedelta
        _fetched_at = datetime.now(tz=timezone(timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M:%S+09:00")
    fm = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {publish_iso}\n"
        f"lastmod: {publish_iso}\n"
        "draft: false\n"
        f'description: "{description}"\n'
        'schema: "NewsArticle"\n'
        f'primary_keyword: "{primary_keyword}"\n'
        "toc: true\n"
        "ai_generated: true\n"
        'ai_models: ["claude-sonnet-4.6", "yfinance"]\n'
        f'data_fetched_at: "{_fetched_at}"\n'
        'data_source: "yfinance"\n'
        "tags:\n"
        f"{tags_lines}\n"
        "categories:\n"
        f"{cats_lines}\n"
        f'author: "InvestIQs Editorial"\n'
        f'reviewedBy: "InvestIQs Review Team"\n'
        f'lang: "{lang}"\n'
        "---\n\n"
    )
    return fm, slug


def _build_index_table_localized(snapshot: dict, lang: str, mode: str = "wrap") -> str:
    """인덱스 표 — 헤더는 i18n, 데이터 행은 숫자 그대로."""
    headers_by_lang_mode = {
        ("en", "wrap"): ["Index", "Ticker", "Close", "Change", "Volume"],
        ("en", "intraday"): ["Index", "Ticker", "Open", "Current", "vs Open", "Gap vs Prev", "30m Vol"],
        ("en", "weekly"): ["Index", "Ticker", "Week Open", "Week Close", "5D Pct", "Max DD", "Avg Vol"],
        ("ja", "wrap"): ["指数", "ティッカー", "終値", "騰落率", "出来高"],
        ("ja", "intraday"): ["指数", "ティッカー", "始値", "現在値", "始値比", "前日比ギャップ", "30分出来高"],
        ("ja", "weekly"): ["指数", "ティッカー", "週初", "週末", "5日騰落率", "最大下落幅", "平均出来高"],
        ("vi", "wrap"): ["Chỉ số", "Mã", "Giá đóng cửa", "Thay đổi", "Khối lượng"],
        ("vi", "intraday"): ["Chỉ số", "Mã", "Giá mở", "Hiện tại", "So với mở", "Gap với hôm trước", "KL 30 phút"],
        ("vi", "weekly"): ["Chỉ số", "Mã", "Mở tuần", "Đóng tuần", "5 ngày", "Mức giảm tối đa", "KL trung bình"],
        ("id", "wrap"): ["Indeks", "Ticker", "Penutupan", "Perubahan", "Volume"],
        ("id", "intraday"): ["Indeks", "Ticker", "Pembukaan", "Saat ini", "vs Pembukaan", "Gap vs Sebelumnya", "Volume 30m"],
        ("id", "weekly"): ["Indeks", "Ticker", "Pembukaan Mingguan", "Penutupan Mingguan", "5 hari", "Penurunan Maks", "Volume Rata-rata"],
    }
    captions = {
        ("en", "wrap"): "US Major Indices — Today's Close",
        ("en", "intraday"): "US Major Indices — First 30 Minutes",
        ("en", "weekly"): "US Major Indices — Weekly Cumulative",
        ("ja", "wrap"): "米国主要指数の終値",
        ("ja", "intraday"): "米国主要指数 寄り付き30分",
        ("ja", "weekly"): "米国主要指数 週間累計",
        ("vi", "wrap"): "Chỉ số chính Mỹ — Đóng cửa hôm nay",
        ("vi", "intraday"): "Chỉ số chính Mỹ — 30 phút đầu",
        ("vi", "weekly"): "Chỉ số chính Mỹ — Tổng kết tuần",
        ("id", "wrap"): "Indeks Utama AS — Penutupan Hari Ini",
        ("id", "intraday"): "Indeks Utama AS — 30 Menit Pertama",
        ("id", "weekly"): "Indeks Utama AS — Kumulatif Mingguan",
    }
    headers = headers_by_lang_mode.get((lang, mode), headers_by_lang_mode[("en", mode)])
    caption = captions.get((lang, mode), captions[("en", mode)])

    rows = [f"<table><caption>{caption}</caption>"]
    rows.append("<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>")

    for idx in snapshot.get("indices", []):
        if mode == "wrap":
            vol = idx.get("vol", 0)
            vol_str = f"{vol/1_000_000:.1f}M" if vol else "-"
            rows.append(
                f"<tr><td>{idx['name']}</td><td>{idx['ticker']}</td>"
                f"<td>{_format_price(idx['price'])}</td>"
                f"<td>{_format_pct(idx['pct'])}</td>"
                f"<td>{vol_str}</td></tr>"
            )
        elif mode == "intraday":
            vol = idx.get("vol_30m", 0)
            vol_str = f"{vol/1_000_000:.1f}M" if vol else "-"
            rows.append(
                f"<tr><td>{idx['name']}</td><td>{idx['ticker']}</td>"
                f"<td>{_format_price(idx['open'])}</td>"
                f"<td>{_format_price(idx['current'])}</td>"
                f"<td>{_format_pct(idx['pct_from_open'])}</td>"
                f"<td>{_format_pct(idx['pct_gap_from_prev'])}</td>"
                f"<td>{vol_str}</td></tr>"
            )
        elif mode == "weekly":
            vol = idx.get("vol_avg_5d", 0)
            vol_str = f"{vol/1_000_000:.1f}M" if vol else "-"
            rows.append(
                f"<tr><td>{idx['name']}</td><td>{idx['ticker']}</td>"
                f"<td>{_format_price(idx['open'])}</td>"
                f"<td>{_format_price(idx['close'])}</td>"
                f"<td>{_format_pct(idx['pct_5d'])}</td>"
                f"<td>{_format_pct(idx['max_drawdown_5d'])}</td>"
                f"<td>{vol_str}</td></tr>"
            )

    # VIX 행 추가
    vix = snapshot.get("vix") or {}
    if vix:
        if mode == "wrap":
            rows.append(
                f"<tr><td>VIX</td><td>^VIX</td>"
                f"<td>{vix.get('price', 0.0):.2f}</td>"
                f"<td>{_format_pct(vix.get('pct', 0.0))}</td>"
                f"<td>-</td></tr>"
            )
        elif mode == "intraday":
            rows.append(
                f"<tr><td>VIX</td><td>^VIX</td><td>-</td>"
                f"<td>{vix.get('price', 0.0):.2f}</td>"
                f"<td>-</td><td>{_format_pct(vix.get('pct_from_prev', 0.0))}</td>"
                f"<td>-</td></tr>"
            )
        elif mode == "weekly":
            rows.append(
                f"<tr><td>VIX</td><td>^VIX</td>"
                f"<td>{vix.get('week_open', 0.0):.2f}</td>"
                f"<td>{vix.get('week_close', 0.0):.2f}</td>"
                f"<td>{_format_pct(vix.get('pct_5d', 0.0))}</td>"
                f"<td>-</td><td>-</td></tr>"
            )

    rows.append("</table>")
    return "\n".join(rows)


def _build_sector_table_localized(snapshot: dict, lang: str, key: str) -> str:
    captions = {
        "en": "Sector ETF Performance (descending)",
        "ja": "セクター ETF パフォーマンス(降順)",
        "vi": "Hiệu suất ETF theo nhóm ngành (giảm dần)",
        "id": "Kinerja ETF Sektor (urutan menurun)",
    }
    headers = {
        "en": ["#", "Sector", "Ticker", "Change"],
        "ja": ["#", "セクター", "ティッカー", "騰落率"],
        "vi": ["#", "Ngành", "Mã", "Thay đổi"],
        "id": ["#", "Sektor", "Ticker", "Perubahan"],
    }
    h = headers.get(lang, headers["en"])
    cap = captions.get(lang, captions["en"])

    sectors = sorted(snapshot.get("sectors", []), key=lambda s: s.get(key, 0.0), reverse=True)
    rows = [f"<table><caption>{cap}</caption>"]
    rows.append("<tr>" + "".join(f"<th>{x}</th>" for x in h) + "</tr>")
    for i, s in enumerate(sectors, 1):
        rows.append(
            f"<tr><td>{i}</td><td>{s['name']}</td>"
            f"<td>{s['ticker']}</td>"
            f"<td>{_format_pct(s.get(key, 0.0))}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


# ─────────────────────────────────────────────────────────────────
# wrap (마감)
# ─────────────────────────────────────────────────────────────────

def build_localized_wrap_markdown(snapshot: dict, lang: str) -> str:
    from auto_publisher.content_generator import fix_html_block_spacing
    i18n = get_i18n(lang)

    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    vix = snapshot.get("vix", {})
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []

    d = _parse_kst_date(snapshot.get("date_kst", ""))
    title = i18n["title_pattern_wrap"].format(
        date=date_label(lang, d),
        spy_pct=_format_pct(spy["pct"]) if spy else "",
        qqq_pct=_format_pct(qqq["pct"]) if qqq else "",
        spy_price=_format_price(spy["price"]) if spy else "",
    )
    description = (
        f"S&P 500 {_format_pct(spy['pct']) if spy else ''}, "
        f"Nasdaq {_format_pct(qqq['pct']) if qqq else ''}, "
        f"VIX {vix.get('price', 0.0):.2f}."
    )
    now_iso = datetime.now(tz=KST).strftime("%Y-%m-%dT%H:%M:%S%z")
    now_iso = now_iso[:-2] + ":" + now_iso[-2:]

    fm, _slug = _build_localized_frontmatter(
        snapshot, lang, title, description, now_iso,
        ["market_analysis", "us_market", "daily_market"],
        primary_keyword="US Market Close",
        extra_tags=i18n.get("tags_extra", []),
    )

    summary_label = i18n["summary_label"]
    summary = (
        f"**{summary_label}**: "
        f"S&P 500 {_format_price(spy['price']) if spy else ''} {_format_pct(spy['pct']) if spy else ''}, "
        f"Nasdaq {_format_pct(qqq['pct']) if qqq else ''}, "
        f"VIX {vix.get('price', 0.0):.2f}. "
        f"Leaders: {', '.join(leaders[:3])} / Laggards: {', '.join(laggards[:3])}."
    )

    # 신규 섹션 빌더 (lang-aware)
    from auto_publisher.market_wrap import (
        _build_macro_table, _build_asia_crypto_table,
        _build_mag7_table, _build_top_movers,
        _build_bond_commodity_table, _build_fear_greed_block,
    )
    macro_table = _build_macro_table(snapshot, lang=lang)
    asia_table = _build_asia_crypto_table(snapshot, lang=lang)
    mag7_table = _build_mag7_table(snapshot, lang=lang)
    movers_table = _build_top_movers(snapshot, lang=lang)
    bonds_table = _build_bond_commodity_table(snapshot, lang=lang)
    fg_block = _build_fear_greed_block(snapshot, lang=lang)

    # Breadth 박스 (i18n 라벨)
    breadth_box = ""
    b = snapshot.get("breadth") or {}
    sec_pos = b.get("sector_positive", 0)
    sec_tot = b.get("sector_total", 0)
    m7_pos = b.get("mag7_positive", 0)
    m7_tot = b.get("mag7_total", 0)
    if sec_tot:
        sec_ratio = sec_pos / sec_tot if sec_tot else 0
        m7_ratio = m7_pos / m7_tot if m7_tot else 0
        sec_emoji = "🟢" if sec_ratio >= 0.6 else "🟡" if sec_ratio >= 0.4 else "🔴"
        m7_emoji = "🟢" if m7_ratio >= 0.6 else "🟡" if m7_ratio >= 0.4 else "🔴"
        b_label = i18n.get("breadth_label", "Market Breadth")
        s_word = i18n.get("breadth_sector_word", "sectors")
        m7_word = i18n.get("breadth_mag7_word", "Mag7")
        up_word = i18n.get("breadth_up_word", "advancing")
        breadth_box = (
            f'<div class="breadth-box" style="background:#f8f9fa;border:1px solid #dee2e6;'
            f'border-radius:8px;padding:0.8em 1.2em;margin:0 0 1.5em 0;font-size:0.95em;">'
            f"<strong>📊 {b_label}</strong> · "
            f"{sec_emoji} {s_word} {sec_pos}/{sec_tot} {up_word} ({sec_ratio*100:.0f}%) · "
            f"{m7_emoji} {m7_word} {m7_pos}/{m7_tot} {up_word} ({m7_ratio*100:.0f}%)"
            f"</div>"
        )

    body = [
        fm,
        i18n["disclaimer_banner_html"],
        "",
        fg_block,
        breadth_box,
        summary,
        "",
        f"## {i18n['section_h2_index']}",
        "",
        _build_index_table_localized(snapshot, lang, "wrap"),
        "",
        f"## {i18n['section_h2_macro']}",
        "",
        macro_table or "_(no macro data)_",
        "",
        i18n.get("macro_note", ""),
        "",
        f"## {i18n['section_h2_sector']}",
        "",
        _build_sector_table_localized(snapshot, lang, "pct"),
        "",
        f"## {i18n['section_h2_bonds_comms']}",
        "",
        bonds_table or "_(no bonds/commodities data)_",
        "",
        i18n.get("bonds_comms_note", ""),
        "",
        f"## {i18n['section_h2_mag7']}",
        "",
        mag7_table or "_(no mag7 data)_",
        "",
        i18n.get("mag7_note", ""),
        "",
        f"## {i18n['section_h2_movers']}",
        "",
        movers_table or "_(no movers data)_",
        "",
        i18n.get("movers_note", ""),
        "",
        f"## {i18n['section_h2_asia_crypto']}",
        "",
        asia_table or "_(no asia/crypto data)_",
        "",
        i18n.get("asia_crypto_note", ""),
        "",
        f"## {i18n['section_h2_narrative']}",
        "",
        i18n.get("wrap_narrative", (
            "S&P 500 closed {spy_pct}, Nasdaq {qqq_pct}, with VIX at {vix_price} ({vix_pct}). "
            "Sector leaders today: {leaders}. Laggards: {laggards}."
        )).format(
            spy_pct=_format_pct(spy["pct"]) if spy else "-",
            qqq_pct=_format_pct(qqq["pct"]) if qqq else "-",
            vix_price=f"{vix.get('price', 0.0):.2f}",
            vix_pct=_format_pct(vix.get("pct", 0.0)),
            leaders=", ".join(leaders[:3]),
            laggards=", ".join(laggards[:3]),
        ),
        "",
        f"## {i18n['section_h2_scenario']}",
        "",
        f"{i18n.get('scenario_up_label', '**Upside Scenario**')}: {i18n.get('scenario_up_text', '')}",
        "",
        f"{i18n.get('scenario_down_label', '**Downside Scenario**')}: {i18n.get('scenario_down_text', '')}",
        "",
        f"## {i18n['section_h2_calendar']}",
        "",
        *[f"- {item}" for item in i18n.get("wrap_calendar", [
            "Watch upcoming US economic releases (CPI/PPI/Retail Sales/PCE).",
            "Monitor Fed officials' speeches and FOMC schedule.",
            "Track 10-year Treasury yield and DXY direction.",
            "VIX trend vs prior session close.",
        ])],
        "",
        f"## {i18n['section_h2_action']}",
        "",
        *[f"- {item}" for item in i18n.get("wrap_action", [
            "A single session is not a trend; check sector breadth.",
            "Verify whether your held sectors are among today's leaders or laggards.",
            "Compare VIX vs your portfolio volatility tolerance.",
        ])],
        "",
        i18n["footer_disclaimer"],
    ]
    md = "\n".join(body)
    return fix_html_block_spacing(md)


# ─────────────────────────────────────────────────────────────────
# intraday (장중)
# ─────────────────────────────────────────────────────────────────

def build_localized_intraday_markdown(snapshot: dict, lang: str) -> str:
    from auto_publisher.content_generator import fix_html_block_spacing
    i18n = get_i18n(lang)

    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    vix = snapshot.get("vix", {})
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []
    gap = snapshot.get("gap") or "gap_flat"

    d = _parse_kst_date(snapshot.get("date_kst", ""))
    title = i18n["title_pattern_intraday"].format(
        date=date_label(lang, d),
        spy_pct=_format_pct(spy["pct_from_open"]) if spy else "",
        qqq_pct=_format_pct(qqq["pct_from_open"]) if qqq else "",
        spy_price=_format_price(spy["current"]) if spy else "",
    )
    description = (
        f"30-minute snapshot — S&P 500 {_format_pct(spy['pct_from_open']) if spy else ''}, "
        f"Nasdaq {_format_pct(qqq['pct_from_open']) if qqq else ''}, "
        f"VIX {vix.get('price', 0.0):.2f}, gap={gap}."
    )
    now_iso = datetime.now(tz=KST).strftime("%Y-%m-%dT%H:%M:%S%z")
    now_iso = now_iso[:-2] + ":" + now_iso[-2:]

    fm, _slug = _build_localized_frontmatter(
        snapshot, lang, title, description, now_iso,
        ["market_analysis", "us_market", "daily_market"],
        primary_keyword="US Market Intraday",
        extra_tags=i18n.get("tags_extra", []),
    )

    summary_label = i18n["summary_label"]
    summary = (
        f"**{summary_label}**: "
        f"S&P 500 {_format_pct(spy['pct_from_open']) if spy else ''}, "
        f"Nasdaq {_format_pct(qqq['pct_from_open']) if qqq else ''}, "
        f"VIX {vix.get('price', 0.0):.2f}. "
        f"Gap: {gap}. Leaders: {', '.join(leaders[:3])} / Laggards: {', '.join(laggards[:3])}."
    )

    # 매크로·Mag7·FG 섹션 (intraday 도 모두 보유)
    from auto_publisher.market_wrap import _build_macro_table, _build_mag7_table, _build_fear_greed_block
    intraday_macro_table = _build_macro_table(snapshot, lang=lang)
    intraday_mag7_table = _build_mag7_table(snapshot, lang=lang)
    intraday_fg_block = _build_fear_greed_block(snapshot, lang=lang)

    body = [
        fm,
        i18n["disclaimer_banner_html"],
        "",
        intraday_fg_block,
        summary,
        "",
        f"## {i18n['section_h2_index']}",
        "",
        _build_index_table_localized(snapshot, lang, "intraday"),
        "",
        f"## {i18n['section_h2_macro']}",
        "",
        intraday_macro_table or "_(no macro data)_",
        "",
        i18n.get("macro_note", ""),
        "",
        f"## {i18n['section_h2_sector']}",
        "",
        _build_sector_table_localized(snapshot, lang, "pct_from_open"),
        "",
        f"## {i18n['section_h2_mag7']}",
        "",
        intraday_mag7_table or "_(no mag7 data)_",
        "",
        i18n.get("mag7_note", ""),
        "",
        f"## {i18n['section_h2_narrative']}",
        "",
        i18n.get("intraday_narrative", (
            "US market just opened ~30 minutes ago. S&P 500 is {spy_pct} from open, "
            "Nasdaq {qqq_pct}. VIX prints {vix_price} ({vix_pct}). "
            "First-30-minute leaders: {leaders}. Laggards: {laggards}."
        )).format(
            spy_pct=_format_pct(spy["pct_from_open"]) if spy else "-",
            qqq_pct=_format_pct(qqq["pct_from_open"]) if qqq else "-",
            vix_price=f"{vix.get('price', 0.0):.2f}",
            vix_pct=_format_pct(vix.get("pct_from_prev", 0.0)),
            leaders=", ".join(leaders[:3]),
            laggards=", ".join(laggards[:3]),
        ),
        "",
        f"## {i18n['section_h2_calendar']}",
        "",
        *[f"- {item}" for item in i18n.get("intraday_calendar", [
            "Watch 10:00 EST data releases (KST 23:00) for surprises.",
            "Confirm whether the gap holds through 11:00 EST.",
            "Track VIX co-movement with index direction.",
            "Monitor mega-cap names (NVDA/MSFT/AAPL/AMZN/GOOG/META/TSLA).",
        ])],
        "",
        f"## {i18n['section_h2_action']}",
        "",
        *[f"- {item}" for item in i18n.get("intraday_action", [
            "Do not size new positions based on the first 30 minutes alone.",
            "Verify whether your held sectors are leaders or laggards today.",
            "Cross-check VIX and index direction for normal correlation.",
        ])],
        "",
        i18n["footer_disclaimer"],
    ]
    md = "\n".join(body)
    return fix_html_block_spacing(md)


# ─────────────────────────────────────────────────────────────────
# weekly (주간)
# ─────────────────────────────────────────────────────────────────

def build_localized_weekly_markdown(snapshot: dict, lang: str) -> str:
    from auto_publisher.content_generator import fix_html_block_spacing
    i18n = get_i18n(lang)

    spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
    qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
    vix = snapshot.get("vix", {})
    leaders = snapshot.get("top_gainers_sectors") or []
    laggards = snapshot.get("top_losers_sectors") or []
    calendar = snapshot.get("next_week_calendar") or []
    label = snapshot.get("week_label", "")

    title = i18n["title_pattern_weekly"].format(
        label=label,
        spy_pct=_format_pct(spy["pct_5d"]) if spy else "",
        qqq_pct=_format_pct(qqq["pct_5d"]) if qqq else "",
    )
    description = (
        f"5-trading-day cumulative — S&P 500 {_format_pct(spy['pct_5d']) if spy else ''}, "
        f"Nasdaq {_format_pct(qqq['pct_5d']) if qqq else ''}, "
        f"VIX close {vix.get('week_close', 0.0):.2f}."
    )
    now_iso = datetime.now(tz=KST).strftime("%Y-%m-%dT%H:%M:%S%z")
    now_iso = now_iso[:-2] + ":" + now_iso[-2:]

    fm, _slug = _build_localized_frontmatter(
        snapshot, lang, title, description, now_iso,
        ["market_analysis", "us_market", "weekly_market"],
        primary_keyword="US Market Weekly",
        extra_tags=i18n.get("tags_extra", []),
    )

    summary_label = i18n["summary_label"]
    summary = (
        f"**{summary_label}**: "
        f"S&P 500 {_format_pct(spy['pct_5d']) if spy else ''}, "
        f"Nasdaq {_format_pct(qqq['pct_5d']) if qqq else ''}, "
        f"VIX {vix.get('week_close', 0.0):.2f}. "
        f"Leaders: {', '.join(leaders[:3])} / Laggards: {', '.join(laggards[:3])}."
    )

    weekly_intro = i18n.get("weekly_intro", (
        "This 5-day cumulative wrap covers {label}, smoothing intraday noise to highlight "
        "directional bias and breadth. Reading three axes (indices, sectors, volatility) "
        "together is more reliable than any single number."
    )).format(label=label)

    weekly_narrative = i18n.get("weekly_narrative", (
        "Across 5 trading days, S&P 500 cumulative return: {spy_pct}, Nasdaq: {qqq_pct}. "
        "VIX moved from {vix_open} to {vix_close} ({vix_pct}). "
        "Top sectors: {leaders}. Bottom: {laggards}."
    )).format(
        spy_pct=_format_pct(spy["pct_5d"]) if spy else "-",
        qqq_pct=_format_pct(qqq["pct_5d"]) if qqq else "-",
        vix_open=f"{vix.get('week_open', 0.0):.2f}",
        vix_close=f"{vix.get('week_close', 0.0):.2f}",
        vix_pct=_format_pct(vix.get("pct_5d", 0.0)),
        leaders=", ".join(leaders[:3]),
        laggards=", ".join(laggards[:3]),
    )

    weekly_calendar_fallback = i18n.get("weekly_calendar_fallback", [
        "FOMC minutes and Fed officials' speeches",
        "Major economic releases (CPI/PPI/Retail Sales/PCE)",
        "Mega-cap earnings (NVDA/AAPL/MSFT/META/AMZN/GOOG/TSLA)",
    ])
    weekly_action = i18n.get("weekly_action", [
        "Compare your held sectors against the week's leaders and laggards.",
        "Track whether the same sector leadership persists into next week.",
        "Reassess position sizing if 5-day max drawdown widened materially.",
        "A strong week does not guarantee the same pace next week.",
    ])

    # 매크로·Mag7·FG 섹션 (weekly 도 모두 보유)
    from auto_publisher.market_wrap import _build_macro_table, _build_mag7_table, _build_fear_greed_block
    weekly_macro_table = _build_macro_table(snapshot, lang=lang)
    weekly_mag7_table = _build_mag7_table(snapshot, lang=lang)
    weekly_fg_block = _build_fear_greed_block(snapshot, lang=lang)

    body = [
        fm,
        i18n["disclaimer_banner_html"],
        "",
        weekly_fg_block,
        summary,
        "",
        weekly_intro,
        "",
        f"## {i18n['section_h2_index']}",
        "",
        _build_index_table_localized(snapshot, lang, "weekly"),
        "",
        f"## {i18n['section_h2_macro']}",
        "",
        weekly_macro_table or "_(no macro data)_",
        "",
        i18n.get("macro_note", ""),
        "",
        f"## {i18n['section_h2_sector']}",
        "",
        _build_sector_table_localized(snapshot, lang, "pct_5d"),
        "",
        f"## {i18n['section_h2_mag7']}",
        "",
        weekly_mag7_table or "_(no mag7 data)_",
        "",
        i18n.get("mag7_note", ""),
        "",
        f"## {i18n['section_h2_narrative']}",
        "",
        weekly_narrative,
        "",
        f"## {i18n['section_h2_calendar']}",
        "",
    ]
    if calendar:
        for item in calendar:
            body.append(f"- {item}")
    else:
        for item in weekly_calendar_fallback:
            body.append(f"- {item}")
    body += [
        "",
        f"## {i18n['section_h2_action']}",
        "",
        *[f"- {item}" for item in weekly_action],
        "",
        i18n["footer_disclaimer"],
    ]
    md = "\n".join(body)
    return fix_html_block_spacing(md)
