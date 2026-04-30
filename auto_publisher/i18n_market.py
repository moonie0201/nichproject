"""다국어 시황 i18n 텍스트 모듈.

지원 언어: ko, en, ja, vi, id
미지원 언어 요청 시 en 으로 fallback.
"""

from __future__ import annotations


_KO = {
    "title_pattern_wrap": "{date} 미국 증시 마감: S&P500 {spy_price} {spy_pct}, 나스닥 {qqq_pct}",
    "title_pattern_intraday": "{date} 미국 증시 장중: 개장 30분 S&P500 {spy_pct}, 나스닥 {qqq_pct}",
    "title_pattern_weekly": "{label} 미국 증시 주간 정리: S&P500 {spy_pct}, 나스닥 {qqq_pct}",
    "section_h2_index": "📊 지수 한눈에 보기",
    "section_h2_sector": "📈 섹터별 강약",
    "section_h2_narrative": "💡 오늘의 시장 내러티브",
    "section_h2_calendar": "🔮 내일 주목 포인트",
    "section_h2_action": "⚡ Action Point (정보 제공)",
    "summary_label": "요약",
    "disclaimer_banner_html": (
        '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
        'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
        '<strong>⚠️ 정보 제공용 데일리 마켓 리포트</strong><br>'
        '본 글은 yfinance 공개 데이터를 정리한 정보 콘텐츠입니다. '
        '특정 종목의 매수·매도를 권유하지 않으며 투자 자문이 아닙니다. '
        '모든 투자 결정과 손익은 본인 책임입니다.'
        '</div>'
    ),
    "footer_disclaimer": (
        "\n---\n\n본 분석은 정보 제공 목적이며, 투자 결정은 본인 책임입니다. "
        "과거 수익률이 미래 수익을 보장하지 않습니다.\n"
    ),
    "categories_market": {
        "market_analysis": "시장분석",
        "us_market": "미국증시",
        "daily_market": "일일시황",
        "weekly_market": "주간시황",
    },
    "tags_extra": ["오늘증시", "S&P500"],
}


_EN = {
    "title_pattern_wrap": "{date} US Market Close: S&P 500 {spy_price} {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_intraday": "{date} US Market Intraday: First 30 min S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_weekly": "{label} US Market Weekly Wrap: S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "section_h2_index": "📊 Index Snapshot",
    "section_h2_sector": "📈 Sector Strength & Weakness",
    "section_h2_narrative": "💡 Today's Market Narrative",
    "section_h2_calendar": "🔮 What to Watch Next",
    "section_h2_action": "⚡ Action Points (Informational)",
    "summary_label": "Summary",
    "disclaimer_banner_html": (
        '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
        'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
        '<strong>⚠️ Daily market snapshot — informational only</strong><br>'
        'This article summarizes publicly available yfinance data. '
        'It is not investment advice and does not recommend buying or selling any security. '
        'All investment decisions and outcomes are your own responsibility.'
        '</div>'
    ),
    "footer_disclaimer": (
        "\n---\n\nThis analysis is informational only and not investment advice. "
        "Past performance does not guarantee future results.\n"
    ),
    "categories_market": {
        "market_analysis": "Market Analysis",
        "us_market": "US Market",
        "daily_market": "Daily Market",
        "weekly_market": "Weekly Market",
    },
    "tags_extra": ["US Stocks", "S&P 500"],
}


_JA = {
    "title_pattern_wrap": "{date} 米国市場の終値: S&P 500 {spy_price} {spy_pct}、ナスダック {qqq_pct}",
    "title_pattern_intraday": "{date} 米国市場の場中: 寄り付き30分 S&P 500 {spy_pct}、ナスダック {qqq_pct}",
    "title_pattern_weekly": "{label} 米国株 週間まとめ: S&P 500 {spy_pct}、ナスダック {qqq_pct}",
    "section_h2_index": "📊 主要指数スナップショット",
    "section_h2_sector": "📈 セクターの強弱",
    "section_h2_narrative": "💡 本日のマーケット・ナラティブ",
    "section_h2_calendar": "🔮 翌営業日の注目ポイント",
    "section_h2_action": "⚡ Action Point(情報提供)",
    "summary_label": "要約",
    "disclaimer_banner_html": (
        '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
        'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
        '<strong>⚠️ 情報提供を目的としたデイリーマーケットレポート</strong><br>'
        '本記事は yfinance の公開データを整理した情報コンテンツです。'
        '特定銘柄の売買を勧誘するものではなく、投資助言ではありません。'
        'すべての投資判断と損益は読者ご本人の責任となります。'
        '</div>'
    ),
    "footer_disclaimer": (
        "\n---\n\n本分析は情報提供を目的としており、投資判断は読者ご本人の責任です。"
        "過去の実績は将来の成果を保証しません。\n"
    ),
    "categories_market": {
        "market_analysis": "マーケット分析",
        "us_market": "米国株",
        "daily_market": "デイリー市況",
        "weekly_market": "ウィークリー市況",
    },
    "tags_extra": ["米国株", "S&P 500"],
}


_VI = {
    "title_pattern_wrap": "{date} Đóng cửa thị trường Mỹ: S&P 500 {spy_price} {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_intraday": "{date} Thị trường Mỹ trong phiên: 30 phút đầu S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_weekly": "{label} Tổng kết tuần thị trường Mỹ: S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "section_h2_index": "📊 Tổng quan chỉ số",
    "section_h2_sector": "📈 Sức mạnh từng nhóm ngành",
    "section_h2_narrative": "💡 Câu chuyện thị trường hôm nay",
    "section_h2_calendar": "🔮 Điều cần theo dõi tiếp theo",
    "section_h2_action": "⚡ Hành động tham khảo (Thông tin)",
    "summary_label": "Tóm tắt",
    "disclaimer_banner_html": (
        '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
        'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
        '<strong>⚠️ Báo cáo thị trường hằng ngày — chỉ mang tính thông tin</strong><br>'
        'Bài viết tổng hợp dữ liệu công khai từ yfinance. '
        'Đây không phải khuyến nghị mua/bán cổ phiếu cụ thể, cũng không phải tư vấn đầu tư. '
        'Mọi quyết định và rủi ro đầu tư thuộc về bạn.'
        '</div>'
    ),
    "footer_disclaimer": (
        "\n---\n\nBài viết chỉ mang tính cung cấp thông tin, không phải tư vấn đầu tư. "
        "Hiệu suất quá khứ không bảo đảm kết quả tương lai.\n"
    ),
    "categories_market": {
        "market_analysis": "Phân tích thị trường",
        "us_market": "Thị trường Mỹ",
        "daily_market": "Thị trường hằng ngày",
        "weekly_market": "Thị trường hằng tuần",
    },
    "tags_extra": ["Cổ phiếu Mỹ", "S&P 500"],
}


_ID = {
    "title_pattern_wrap": "{date} Penutupan Pasar AS: S&P 500 {spy_price} {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_intraday": "{date} Pasar AS dalam sesi: 30 menit pertama S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_weekly": "{label} Rangkuman Mingguan Pasar AS: S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "section_h2_index": "📊 Ringkasan Indeks Utama",
    "section_h2_sector": "📈 Kekuatan & Kelemahan Sektor",
    "section_h2_narrative": "💡 Narasi Pasar Hari Ini",
    "section_h2_calendar": "🔮 Yang Perlu Dipantau Berikutnya",
    "section_h2_action": "⚡ Action Point (Informasi)",
    "summary_label": "Ringkasan",
    "disclaimer_banner_html": (
        '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
        'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
        '<strong>⚠️ Laporan pasar harian — hanya untuk informasi</strong><br>'
        'Artikel ini merangkum data publik yfinance. '
        'Bukan rekomendasi beli/jual saham tertentu maupun saran investasi. '
        'Seluruh keputusan dan risiko investasi menjadi tanggung jawab Anda.'
        '</div>'
    ),
    "footer_disclaimer": (
        "\n---\n\nAnalisis ini bersifat informasi saja dan bukan saran investasi. "
        "Kinerja masa lalu tidak menjamin hasil di masa depan.\n"
    ),
    "categories_market": {
        "market_analysis": "Analisis Pasar",
        "us_market": "Pasar AS",
        "daily_market": "Pasar Harian",
        "weekly_market": "Pasar Mingguan",
    },
    "tags_extra": ["Saham AS", "S&P 500"],
}


_BY_LANG = {
    "ko": _KO,
    "en": _EN,
    "ja": _JA,
    "vi": _VI,
    "id": _ID,
}


def get_i18n(lang: str) -> dict:
    """언어별 i18n dict 반환. 미지원 언어는 en 으로 fallback."""
    return _BY_LANG.get(lang) or _BY_LANG["en"]


def date_label(lang: str, dt) -> str:
    """언어별 날짜 라벨 (제목용)."""
    if lang == "ko":
        return f"{dt.year}년 {dt.month}월 {dt.day}일"
    if lang == "ja":
        return f"{dt.year}年{dt.month}月{dt.day}日"
    if lang == "en":
        # April 24, 2026
        return dt.strftime("%B %-d, %Y") if hasattr(dt, "strftime") else str(dt)
    if lang == "vi":
        # 24/04/2026
        return dt.strftime("%d/%m/%Y")
    if lang == "id":
        # 24 April 2026
        months = ["Januari","Februari","Maret","April","Mei","Juni",
                 "Juli","Agustus","September","Oktober","November","Desember"]
        return f"{dt.day} {months[dt.month-1]} {dt.year}"
    return dt.strftime("%Y-%m-%d")
