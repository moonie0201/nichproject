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
    "section_h2_macro": "🌐 핵심 매크로 — 국채 수익률 · 달러",
    "section_h2_sector": "📈 섹터별 강약",
    "section_h2_bonds_comms": "💎 채권 · 원자재",
    "section_h2_mag7": "🚀 Magnificent 7",
    "section_h2_movers": "📉 오늘의 상승/하락 주도 종목",
    "section_h2_asia_crypto": "🌏 아시아 핸드오프 · 디지털 자산",
    "section_h2_narrative": "💡 오늘의 시장 내러티브",
    "section_h2_scenario": "🎯 시나리오 박스 (정보 제공·투자 자문 아님)",
    "section_h2_calendar": "🔮 내일 주목 포인트",
    "section_h2_action": "⚡ Action Point (정보 제공)",
    "scenario_up_label": "**상승 시나리오**",
    "scenario_up_text": "이 구간에서 추가 상승이 이어지려면 (1) VIX가 현재 수준에서 추가 안정, (2) 채권 수익률이 박스권 유지, (3) 섹터 폭이 더 넓게 확장되며 방어주가 함께 따라오는 흐름이 필요하다.",
    "scenario_down_label": "**하락 시나리오**",
    "scenario_down_text": "단기 조정 가능성을 견인할 수 있는 요인은 (1) VIX 20선 돌파, (2) 10년물 수익률 급등 + DXY 동반 강세, (3) 섹터 폭 급락(상승 섹터 3개 미만)과 Mag7 동반 약세, (4) 어닝 시즌 가이던스 하향이다. 양쪽 시나리오 모두 사전에 점검하는 것이 위험관리의 핵심이다.",
    "breadth_label": "시장 폭(Breadth)",
    "breadth_sector_word": "섹터",
    "breadth_mag7_word": "Mag7",
    "breadth_up_word": "상승",
    "fg_gauge_label": "시장 심리",
    "fg_extreme_fear": "극단적 공포",
    "fg_fear": "공포",
    "fg_neutral": "중립",
    "fg_greed": "탐욕",
    "fg_extreme_greed": "극단적 탐욕",
    "fg_basis": "VIX {vix} 기준 추정치",
    "macro_note": "10년물 수익률(^TNX)은 위험자산 할인율의 핵심 변수다. DXY 강세는 외국인 자금 유입 둔화 신호로 해석된다.",
    "mag7_note": "빅테크 7개 종목의 방향은 나스닥100(QQQ) 추세에 직결된다. RSI 70 이상은 단기 과매수 시그널이다.",
    "movers_note": "당일 가장 크게 움직인 대형주 6종을 정리한다. 단일 세션 변동은 단기 이벤트일 수 있으므로 5일 차트와 함께 본다.",
    "bonds_comms_note": "장기채(TLT) 상승은 경기 둔화 또는 안전자산 선호 신호. 금(GLD) 강세는 달러 약세 또는 불확실성 확대 신호로 해석되는 경우가 많다.",
    "asia_crypto_note": "한국 독자에게 미국 마감 → 아시아 개장은 자금 흐름의 다음 페이지다. 비트코인/이더리움은 24시간 위험선호 바로미터다.",
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
    "section_h2_macro": "🌐 Macro Pulse — Treasury Yields & Dollar",
    "section_h2_sector": "📈 Sector Strength & Weakness",
    "section_h2_bonds_comms": "💎 Bonds & Commodities",
    "section_h2_mag7": "🚀 Magnificent 7",
    "section_h2_movers": "📉 Top Gainers & Losers Today",
    "section_h2_asia_crypto": "🌏 Asia Handoff & Digital Assets",
    "section_h2_narrative": "💡 Today's Market Narrative",
    "section_h2_scenario": "🎯 Scenario Box (Informational, not advice)",
    "section_h2_calendar": "🔮 What to Watch Next",
    "section_h2_action": "⚡ Action Points (Informational)",
    "scenario_up_label": "**Upside Scenario**",
    "scenario_up_text": "For continued strength: (1) VIX must stabilize at current levels, (2) Treasury yields stay range-bound, (3) sector breadth expands and defensives confirm. All three together raise the probability of follow-through.",
    "scenario_down_label": "**Downside Scenario**",
    "scenario_down_text": "Potential catalysts for a short-term pullback: (1) VIX breaking above 20, (2) 10-year yield jumping with DXY strength (risk-asset pressure), (3) breadth collapse (fewer than 3 sectors green) with Mag7 weakness, (4) earnings guidance cuts. Pre-checking both scenarios is the heart of risk management.",
    "breadth_label": "Market Breadth",
    "breadth_sector_word": "sectors",
    "breadth_mag7_word": "Mag7",
    "breadth_up_word": "advancing",
    "fg_gauge_label": "Market Sentiment",
    "fg_extreme_fear": "Extreme Fear",
    "fg_fear": "Fear",
    "fg_neutral": "Neutral",
    "fg_greed": "Greed",
    "fg_extreme_greed": "Extreme Greed",
    "fg_basis": "Estimated from VIX {vix}",
    "macro_note": "The 10-year Treasury yield (^TNX) is a core discount-rate variable for risk assets. A stronger DXY tends to slow foreign inflows.",
    "mag7_note": "The mega-cap seven drive Nasdaq-100 (QQQ) direction. RSI above 70 signals short-term overbought conditions.",
    "movers_note": "Today's six biggest large-cap movers. Single-session moves may be event-driven; cross-check with 5-day charts.",
    "bonds_comms_note": "Long-bond (TLT) strength signals growth concerns or safe-haven demand. Gold (GLD) strength often reflects dollar weakness or rising uncertainty.",
    "asia_crypto_note": "After the US close, Asian markets (Nikkei/HangSeng/KOSPI/Shanghai) open next. Bitcoin and Ethereum trade 24/7, serving as a real-time risk-appetite barometer.",
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
    # intraday body texts
    "intraday_narrative": (
        "US market just opened ~30 minutes ago. S&P 500 is {spy_pct} from open, "
        "Nasdaq {qqq_pct}. VIX prints {vix_price} ({vix_pct}). "
        "First-30-minute leaders: {leaders}. Laggards: {laggards}."
    ),
    "intraday_calendar": [
        "Watch 10:00 EST data releases (KST 23:00) for surprises.",
        "Confirm whether the gap holds through 11:00 EST.",
        "Track VIX co-movement with index direction.",
        "Monitor mega-cap names (NVDA/MSFT/AAPL/AMZN/GOOG/META/TSLA).",
    ],
    "intraday_action": [
        "Do not size new positions based on the first 30 minutes alone.",
        "Verify whether your held sectors are leaders or laggards today.",
        "Cross-check VIX and index direction for normal correlation.",
    ],
    # wrap body texts
    "wrap_narrative": (
        "S&P 500 closed {spy_pct}, Nasdaq {qqq_pct}, with VIX at {vix_price} ({vix_pct}). "
        "Sector leaders today: {leaders}. Laggards: {laggards}."
    ),
    "wrap_calendar": [
        "Watch upcoming US economic releases (CPI/PPI/Retail Sales/PCE).",
        "Monitor Fed officials' speeches and FOMC schedule.",
        "Track 10-year Treasury yield and DXY direction.",
        "VIX trend vs prior session close.",
    ],
    "wrap_action": [
        "A single session is not a trend; check sector breadth.",
        "Verify whether your held sectors are among today's leaders or laggards.",
        "Compare VIX vs your portfolio volatility tolerance.",
        "If a Mag7 name shows RSI > 70, treat any add as short-term overbought risk.",
        "When 10-year yield and DXY rise together, re-check your growth-stock exposure.",
        "Wait for the next major event (CPI/FOMC/earnings) before changing position size.",
    ],
    # weekly body texts
    "weekly_intro": (
        "This 5-day cumulative wrap covers {label}, smoothing intraday noise to highlight "
        "directional bias and breadth. Reading three axes (indices, sectors, volatility) "
        "together is more reliable than any single number."
    ),
    "weekly_narrative": (
        "Across 5 trading days, S&P 500 cumulative return: {spy_pct}, Nasdaq: {qqq_pct}. "
        "VIX moved from {vix_open} to {vix_close} ({vix_pct}). "
        "Top sectors: {leaders}. Bottom: {laggards}."
    ),
    "weekly_calendar_fallback": [
        "FOMC minutes and Fed officials' speeches",
        "Major economic releases (CPI/PPI/Retail Sales/PCE)",
        "Mega-cap earnings (NVDA/AAPL/MSFT/META/AMZN/GOOG/TSLA)",
    ],
    "weekly_action": [
        "Compare your held sectors against the week's leaders and laggards.",
        "Track whether the same sector leadership persists into next week.",
        "Reassess position sizing if 5-day max drawdown widened materially.",
        "A strong week does not guarantee the same pace next week.",
    ],
}


_JA = {
    "title_pattern_wrap": "{date} 米国市場の終値: S&P 500 {spy_price} {spy_pct}、ナスダック {qqq_pct}",
    "title_pattern_intraday": "{date} 米国市場の場中: 寄り付き30分 S&P 500 {spy_pct}、ナスダック {qqq_pct}",
    "title_pattern_weekly": "{label} 米国株 週間まとめ: S&P 500 {spy_pct}、ナスダック {qqq_pct}",
    "section_h2_index": "📊 主要指数スナップショット",
    "section_h2_macro": "🌐 マクロ指標 — 米国債利回り・ドル",
    "section_h2_sector": "📈 セクターの強弱",
    "section_h2_bonds_comms": "💎 債券・コモディティ",
    "section_h2_mag7": "🚀 Magnificent 7",
    "section_h2_movers": "📉 本日の値上がり・値下がり主導銘柄",
    "section_h2_asia_crypto": "🌏 アジア市場・デジタル資産",
    "section_h2_narrative": "💡 本日のマーケット・ナラティブ",
    "section_h2_scenario": "🎯 シナリオ(情報提供・投資助言ではありません)",
    "section_h2_calendar": "🔮 翌営業日の注目ポイント",
    "section_h2_action": "⚡ Action Point(情報提供)",
    "scenario_up_label": "**上昇シナリオ**",
    "scenario_up_text": "上昇継続のためには (1) VIXが現在の水準で安定、(2) 国債利回りがレンジ内維持、(3) セクター幅が拡大しディフェンシブが追従する流れが必要です。",
    "scenario_down_label": "**下落シナリオ**",
    "scenario_down_text": "短期調整の材料となり得るのは (1) VIX 20突破、(2) 10年金利急騰とDXY強さの併発(リスク資産圧迫)、(3) セクター幅崩壊(上昇セクター3未満)とMag7同時弱気、(4) 決算ガイダンス引下げです。両シナリオを事前確認するのがリスク管理の核心です。",
    "breadth_label": "マーケットブレッドス",
    "breadth_sector_word": "セクター",
    "breadth_mag7_word": "Mag7",
    "breadth_up_word": "上昇",
    "fg_gauge_label": "マーケットセンチメント",
    "fg_extreme_fear": "極端な恐怖",
    "fg_fear": "恐怖",
    "fg_neutral": "中立",
    "fg_greed": "強欲",
    "fg_extreme_greed": "極端な強欲",
    "fg_basis": "VIX {vix} に基づく推定",
    "macro_note": "10年国債利回り(^TNX)はリスク資産の割引率を決める重要変数です。DXY上昇は海外資金流入の鈍化シグナルと解釈されます。",
    "mag7_note": "大型テック7銘柄の方向はナスダック100(QQQ)のトレンドに直結します。RSI 70以上は短期過熱シグナルです。",
    "movers_note": "本日最も大きく動いた大型株6銘柄。単一セッションの変動はイベントドリブンの可能性があるため、5日チャートと併せて確認します。",
    "bonds_comms_note": "長期債(TLT)の上昇は景気減速懸念または安全資産選好のシグナル。金(GLD)の上昇はドル安または不確実性拡大の兆候として解釈されることが多いです。",
    "asia_crypto_note": "米国市場引け後、アジア市場(日経・香港H・KOSPI・上海)が次に開きます。ビットコイン/イーサリアムは24時間取引のリスク選好バロメーターです。",
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
    # intraday body texts
    "intraday_narrative": (
        "米国市場が開場してから約30分が経過しました。S&P 500は始値から{spy_pct}、"
        "ナスダックは{qqq_pct}。VIXは{vix_price}（{vix_pct}）です。"
        "寄り付き30分のリーダー：{leaders}。出遅れ：{laggards}。"
    ),
    "intraday_calendar": [
        "米国東部時間10:00（KST 23:00）の経済指標発表を確認。",
        "ギャップが11:00 ESTまで維持されるか確認。",
        "VIXと指数の連動性を追う。",
        "大型株（NVDA/MSFT/AAPL/AMZN/GOOG/META/TSLA）の動向を監視。",
    ],
    "intraday_action": [
        "最初の30分だけで新規ポジションを取らない。",
        "保有セクター・銘柄が今日のリーダー・出遅れのどちらにいるか確認する。",
        "VIXと指数の逆相関が正常かクロスチェックする。",
    ],
    # wrap body texts
    "wrap_narrative": (
        "S&P 500は{spy_pct}で引け、ナスダックは{qqq_pct}、VIXは{vix_price}（{vix_pct}）でした。"
        "本日のセクターリーダー：{leaders}。出遅れ：{laggards}。"
    ),
    "wrap_calendar": [
        "米国の主要経済指標（CPI/PPI/小売売上/PCE）に注目。",
        "FRB高官発言とFOMCスケジュールを確認。",
        "10年国債利回りとDXYの方向性を追う。",
        "前日終値比のVIXトレンドを確認。",
    ],
    "wrap_action": [
        "1セッションはトレンドではない。セクター全体の強弱を確認する。",
        "保有セクターが今日のリーダー・出遅れのどちらに入っているか確認する。",
        "VIXとポートフォリオのボラティリティ許容度を比較する。",
        "Mag7 銘柄の RSI が 70 を超えた場合、追加買いは短期過熱リスクとして扱う。",
        "10年金利と DXY が同時に上昇する局面では、グロース株の比重を再点検する。",
        "次の主要イベント(CPI/FOMC/決算)までポジションサイズの変更を急がない。",
    ],
    # weekly body texts
    "weekly_intro": (
        "この週間まとめは{label}をカバーし、日中ノイズを平滑化して"
        "方向性とブレッドスを浮き彫りにします。"
        "指数・セクター・ボラティリティの3軸を合わせて読むことが最も信頼できます。"
    ),
    "weekly_narrative": (
        "5営業日の累計リターン：S&P 500 {spy_pct}、ナスダック {qqq_pct}。"
        "VIXは{vix_open}から{vix_close}へ（{vix_pct}）。"
        "トップセクター：{leaders}。最下位：{laggards}。"
    ),
    "weekly_calendar_fallback": [
        "FOMC議事録とFRB高官発言",
        "主要経済指標（CPI/PPI/小売売上/PCE）",
        "大型株決算（NVDA/AAPL/MSFT/META/AMZN/GOOG/TSLA）",
    ],
    "weekly_action": [
        "保有セクターを今週のリーダー・出遅れと比較する。",
        "同じセクターリーダーシップが来週も続くか追う。",
        "5日間の最大下落幅が広がった場合はポジションサイズを見直す。",
        "強い週が来週も同じペースを保証するわけではない。",
    ],
}


_VI = {
    "title_pattern_wrap": "{date} Đóng cửa thị trường Mỹ: S&P 500 {spy_price} {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_intraday": "{date} Thị trường Mỹ trong phiên: 30 phút đầu S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_weekly": "{label} Tổng kết tuần thị trường Mỹ: S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "section_h2_index": "📊 Tổng quan chỉ số",
    "section_h2_macro": "🌐 Chỉ báo vĩ mô — Lợi suất TPCP & USD",
    "section_h2_sector": "📈 Sức mạnh từng nhóm ngành",
    "section_h2_bonds_comms": "💎 Trái phiếu & Hàng hóa",
    "section_h2_mag7": "🚀 Magnificent 7",
    "section_h2_movers": "📉 Cổ phiếu tăng/giảm dẫn dắt hôm nay",
    "section_h2_asia_crypto": "🌏 Bàn giao châu Á & Tài sản số",
    "section_h2_narrative": "💡 Câu chuyện thị trường hôm nay",
    "section_h2_scenario": "🎯 Kịch bản (Thông tin tham khảo, không phải tư vấn)",
    "section_h2_calendar": "🔮 Điều cần theo dõi tiếp theo",
    "section_h2_action": "⚡ Hành động tham khảo (Thông tin)",
    "scenario_up_label": "**Kịch bản tăng**",
    "scenario_up_text": "Để duy trì đà tăng cần: (1) VIX ổn định ở mức hiện tại, (2) lợi suất trái phiếu duy trì trong biên độ, (3) độ rộng ngành mở rộng và nhóm phòng thủ xác nhận theo. Cả ba yếu tố cùng xuất hiện sẽ tăng xác suất nối dài xu hướng.",
    "scenario_down_label": "**Kịch bản giảm**",
    "scenario_down_text": "Các tác nhân có thể gây điều chỉnh ngắn hạn: (1) VIX vượt 20, (2) lợi suất 10 năm tăng vọt cùng USD mạnh (áp lực tài sản rủi ro), (3) độ rộng sụp đổ (dưới 3 ngành tăng) cùng Mag7 yếu, (4) hạ guidance mùa earnings. Kiểm tra trước cả hai kịch bản là cốt lõi của quản trị rủi ro.",
    "breadth_label": "Độ rộng thị trường",
    "breadth_sector_word": "ngành",
    "breadth_mag7_word": "Mag7",
    "breadth_up_word": "tăng",
    "fg_gauge_label": "Tâm lý thị trường",
    "fg_extreme_fear": "Sợ hãi cực độ",
    "fg_fear": "Sợ hãi",
    "fg_neutral": "Trung lập",
    "fg_greed": "Tham lam",
    "fg_extreme_greed": "Tham lam cực độ",
    "fg_basis": "Ước tính từ VIX {vix}",
    "macro_note": "Lợi suất Trái phiếu Mỹ 10 năm (^TNX) là biến số chiết khấu chính cho tài sản rủi ro. DXY mạnh lên thường làm chậm dòng tiền nước ngoài.",
    "mag7_note": "Bảy cổ phiếu công nghệ vốn hóa lớn quyết định hướng đi của Nasdaq-100 (QQQ). RSI trên 70 báo hiệu vùng quá mua ngắn hạn.",
    "movers_note": "Sáu cổ phiếu vốn hóa lớn biến động mạnh nhất hôm nay. Biến động một phiên có thể do sự kiện; nên kiểm tra chéo biểu đồ 5 ngày.",
    "bonds_comms_note": "Trái phiếu dài hạn (TLT) tăng báo hiệu lo ngại tăng trưởng hoặc nhu cầu tài sản trú ẩn. Vàng (GLD) tăng thường phản ánh USD yếu hoặc bất định gia tăng.",
    "asia_crypto_note": "Sau khi thị trường Mỹ đóng cửa, các thị trường châu Á (Nikkei/HangSeng/KOSPI/Shanghai) mở tiếp theo. Bitcoin và Ethereum giao dịch 24/7 như phong vũ biểu khẩu vị rủi ro thời gian thực.",
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
    # intraday body texts
    "intraday_narrative": (
        "Thị trường Mỹ vừa mở cửa khoảng 30 phút. S&P 500 {spy_pct} so với giá mở, "
        "Nasdaq {qqq_pct}. VIX ở mức {vix_price} ({vix_pct}). "
        "Dẫn đầu 30 phút đầu: {leaders}. Yếu nhất: {laggards}."
    ),
    "intraday_calendar": [
        "Theo dõi dữ liệu kinh tế 10:00 EST (KST 23:00) có bất ngờ không.",
        "Xác nhận gap có duy trì đến 11:00 EST không.",
        "Theo dõi sự đồng pha giữa VIX và hướng chỉ số.",
        "Quan sát biến động cổ phiếu vốn hóa lớn (NVDA/MSFT/AAPL/AMZN/GOOG/META/TSLA).",
    ],
    "intraday_action": [
        "Không mở vị thế mới chỉ dựa trên 30 phút đầu.",
        "Kiểm tra xem ngành bạn đang nắm giữ thuộc nhóm dẫn đầu hay yếu nhất hôm nay.",
        "Kiểm tra tương quan ngược giữa VIX và chỉ số có bình thường không.",
    ],
    # wrap body texts
    "wrap_narrative": (
        "S&P 500 đóng cửa {spy_pct}, Nasdaq {qqq_pct}, VIX ở mức {vix_price} ({vix_pct}). "
        "Ngành dẫn đầu hôm nay: {leaders}. Yếu nhất: {laggards}."
    ),
    "wrap_calendar": [
        "Theo dõi các số liệu kinh tế Mỹ sắp công bố (CPI/PPI/Doanh thu bán lẻ/PCE).",
        "Theo dõi phát biểu của quan chức Fed và lịch FOMC.",
        "Theo dõi lợi suất trái phiếu 10 năm và hướng DXY.",
        "Xu hướng VIX so với phiên trước.",
    ],
    "wrap_action": [
        "Một phiên không phải xu hướng; kiểm tra độ rộng toàn ngành.",
        "Xác nhận ngành bạn đang nắm thuộc nhóm dẫn đầu hay yếu nhất hôm nay.",
        "So sánh VIX với mức chịu đựng biến động của danh mục.",
        "Nếu một cổ phiếu Mag7 có RSI > 70, hãy xem việc gia tăng vị thế là rủi ro quá mua ngắn hạn.",
        "Khi lợi suất 10 năm và DXY cùng tăng, hãy kiểm tra lại tỷ trọng cổ phiếu tăng trưởng.",
        "Đợi sự kiện quan trọng tiếp theo (CPI/FOMC/earnings) trước khi thay đổi quy mô vị thế.",
    ],
    # weekly body texts
    "weekly_intro": (
        "Tổng kết tuần này bao gồm {label}, làm mịn nhiễu trong ngày để làm nổi bật "
        "xu hướng và độ rộng thị trường. Đọc ba trục (chỉ số, ngành, biến động) "
        "cùng nhau đáng tin cậy hơn bất kỳ con số đơn lẻ nào."
    ),
    "weekly_narrative": (
        "Trong 5 ngày giao dịch, S&P 500 tích lũy {spy_pct}, Nasdaq {qqq_pct}. "
        "VIX di chuyển từ {vix_open} đến {vix_close} ({vix_pct}). "
        "Ngành đứng đầu: {leaders}. Cuối bảng: {laggards}."
    ),
    "weekly_calendar_fallback": [
        "Biên bản FOMC và phát biểu quan chức Fed",
        "Số liệu kinh tế lớn (CPI/PPI/Doanh thu bán lẻ/PCE)",
        "Kết quả kinh doanh vốn hóa lớn (NVDA/AAPL/MSFT/META/AMZN/GOOG/TSLA)",
    ],
    "weekly_action": [
        "So sánh ngành đang nắm với nhóm dẫn đầu và yếu nhất trong tuần.",
        "Theo dõi liệu cùng nhóm ngành dẫn đầu có tiếp tục sang tuần tới không.",
        "Xem xét lại kích thước vị thế nếu biên độ giảm tối đa 5 ngày mở rộng đáng kể.",
        "Một tuần tăng mạnh không đảm bảo cùng tốc độ tuần tới.",
    ],
}


_ID = {
    "title_pattern_wrap": "{date} Penutupan Pasar AS: S&P 500 {spy_price} {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_intraday": "{date} Pasar AS dalam sesi: 30 menit pertama S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "title_pattern_weekly": "{label} Rangkuman Mingguan Pasar AS: S&P 500 {spy_pct}, Nasdaq {qqq_pct}",
    "section_h2_index": "📊 Ringkasan Indeks Utama",
    "section_h2_macro": "🌐 Indikator Makro — Imbal Hasil Treasury & USD",
    "section_h2_sector": "📈 Kekuatan & Kelemahan Sektor",
    "section_h2_bonds_comms": "💎 Obligasi & Komoditas",
    "section_h2_mag7": "🚀 Magnificent 7",
    "section_h2_movers": "📉 Saham Pendorong Naik/Turun Hari Ini",
    "section_h2_asia_crypto": "🌏 Sambungan Pasar Asia & Aset Digital",
    "section_h2_narrative": "💡 Narasi Pasar Hari Ini",
    "section_h2_scenario": "🎯 Skenario (Informasi, bukan saran)",
    "section_h2_calendar": "🔮 Yang Perlu Dipantau Berikutnya",
    "section_h2_action": "⚡ Action Point (Informasi)",
    "scenario_up_label": "**Skenario Naik**",
    "scenario_up_text": "Untuk kelanjutan tren naik: (1) VIX harus stabil di level saat ini, (2) imbal hasil Treasury tetap dalam rentang, (3) luas sektor meluas dan defensif mengkonfirmasi. Ketiganya bersama meningkatkan probabilitas kelanjutan.",
    "scenario_down_label": "**Skenario Turun**",
    "scenario_down_text": "Katalis potensial koreksi jangka pendek: (1) VIX menembus 20, (2) imbal hasil 10 tahun melonjak dengan DXY menguat (tekanan aset berisiko), (3) luas runtuh (kurang 3 sektor hijau) dengan Mag7 lemah, (4) penurunan guidance earnings. Memeriksa kedua skenario adalah inti dari manajemen risiko.",
    "breadth_label": "Luasnya Pasar",
    "breadth_sector_word": "sektor",
    "breadth_mag7_word": "Mag7",
    "breadth_up_word": "naik",
    "fg_gauge_label": "Sentimen Pasar",
    "fg_extreme_fear": "Ketakutan Ekstrem",
    "fg_fear": "Ketakutan",
    "fg_neutral": "Netral",
    "fg_greed": "Keserakahan",
    "fg_extreme_greed": "Keserakahan Ekstrem",
    "fg_basis": "Estimasi berdasarkan VIX {vix}",
    "macro_note": "Imbal hasil Treasury AS 10 tahun (^TNX) adalah variabel diskon utama untuk aset berisiko. DXY yang menguat cenderung memperlambat aliran dana asing.",
    "mag7_note": "Tujuh saham mega-cap teknologi menggerakkan arah Nasdaq-100 (QQQ). RSI di atas 70 menandakan kondisi overbought jangka pendek.",
    "movers_note": "Enam saham large-cap dengan pergerakan terbesar hari ini. Pergerakan satu sesi mungkin berdasarkan event; periksa silang dengan chart 5 hari.",
    "bonds_comms_note": "Kekuatan obligasi jangka panjang (TLT) menandakan kekhawatiran pertumbuhan atau permintaan aset aman. Emas (GLD) menguat sering mencerminkan USD melemah atau ketidakpastian meningkat.",
    "asia_crypto_note": "Setelah pasar AS tutup, pasar Asia (Nikkei/HangSeng/KOSPI/Shanghai) buka berikutnya. Bitcoin dan Ethereum diperdagangkan 24/7 sebagai barometer selera risiko real-time.",
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
    # intraday body texts
    "intraday_narrative": (
        "Pasar AS baru saja dibuka ~30 menit lalu. S&P 500 {spy_pct} dari pembukaan, "
        "Nasdaq {qqq_pct}. VIX di {vix_price} ({vix_pct}). "
        "Pemimpin 30 menit pertama: {leaders}. Tertinggal: {laggards}."
    ),
    "intraday_calendar": [
        "Pantau rilis data pukul 10:00 EST (KST 23:00) untuk kejutan.",
        "Konfirmasi apakah gap bertahan hingga 11:00 EST.",
        "Pantau pergerakan VIX bersamaan dengan arah indeks.",
        "Monitor saham mega-cap (NVDA/MSFT/AAPL/AMZN/GOOG/META/TSLA).",
    ],
    "intraday_action": [
        "Jangan buka posisi baru hanya berdasarkan 30 menit pertama.",
        "Verifikasi apakah sektor yang dipegang termasuk pemimpin atau tertinggal hari ini.",
        "Periksa korelasi negatif normal antara VIX dan arah indeks.",
    ],
    # wrap body texts
    "wrap_narrative": (
        "S&P 500 ditutup {spy_pct}, Nasdaq {qqq_pct}, VIX di {vix_price} ({vix_pct}). "
        "Sektor pemimpin hari ini: {leaders}. Tertinggal: {laggards}."
    ),
    "wrap_calendar": [
        "Pantau rilis ekonomi AS mendatang (CPI/PPI/Penjualan Ritel/PCE).",
        "Monitor pidato pejabat Fed dan jadwal FOMC.",
        "Pantau imbal hasil Treasury 10 tahun dan arah DXY.",
        "Tren VIX dibanding penutupan sesi sebelumnya.",
    ],
    "wrap_action": [
        "Satu sesi bukan tren; periksa luasnya sektor.",
        "Verifikasi apakah sektor yang dipegang termasuk pemimpin atau tertinggal hari ini.",
        "Bandingkan VIX dengan toleransi volatilitas portofolio Anda.",
        "Jika saham Mag7 menunjukkan RSI > 70, perlakukan penambahan posisi sebagai risiko overbought jangka pendek.",
        "Saat imbal hasil 10 tahun dan DXY naik bersamaan, periksa kembali eksposur saham pertumbuhan.",
        "Tunggu event utama berikutnya (CPI/FOMC/earnings) sebelum mengubah ukuran posisi.",
    ],
    # weekly body texts
    "weekly_intro": (
        "Rangkuman mingguan ini mencakup {label}, memperhalus noise harian untuk "
        "menyoroti bias arah dan luasnya pasar. Membaca tiga sumbu (indeks, sektor, "
        "volatilitas) bersama lebih andal daripada satu angka saja."
    ),
    "weekly_narrative": (
        "Selama 5 hari perdagangan, return kumulatif S&P 500: {spy_pct}, Nasdaq: {qqq_pct}. "
        "VIX bergerak dari {vix_open} ke {vix_close} ({vix_pct}). "
        "Sektor teratas: {leaders}. Terbawah: {laggards}."
    ),
    "weekly_calendar_fallback": [
        "Risalah FOMC dan pidato pejabat Fed",
        "Rilis ekonomi besar (CPI/PPI/Penjualan Ritel/PCE)",
        "Earnings mega-cap (NVDA/AAPL/MSFT/META/AMZN/GOOG/TSLA)",
    ],
    "weekly_action": [
        "Bandingkan sektor yang dipegang dengan pemimpin dan tertinggal minggu ini.",
        "Pantau apakah kepemimpinan sektor yang sama berlanjut ke minggu depan.",
        "Tinjau kembali ukuran posisi jika max drawdown 5 hari melebar signifikan.",
        "Minggu yang kuat tidak menjamin kecepatan yang sama minggu depan.",
    ],
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
