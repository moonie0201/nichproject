"""
콘텐츠 생성기 — Codex (gpt-5.4-mini) 기반
- 블로그 포스트 (페르소나 일관성 + yfinance 실데이터 + 차트 힌트 + 품질 게이트)
- 분석 포스트 (김단테형, ai-hedge-fund + yfinance 주입)
- SNS / 숏폼 (Phase 2/3)
"""

import json
import os
import subprocess
import time
import logging
import re
from pathlib import Path

from auto_publisher.config import CONTENT_NICHE, FORBIDDEN_PHRASES
from auto_publisher.compliance import apply_compliance

PERSONA_DIR = Path(__file__).parent / "data" / "personas"
CASE_DIR = Path(__file__).parent / "data" / "cases"


def _load_case(lang: str) -> dict:
    """가상 시나리오 케이스 프로필 로드 (분석 대상 주인공)."""
    path = CASE_DIR / f"case_{lang}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _case_brief(case: dict) -> str:
    """시나리오 케이스를 LLM 프롬프트용 블록으로 변환."""
    if not case:
        return ""
    lines = [
        "[가상 시나리오 케이스 — 분석 대상 주인공 (작가가 아님)]",
        f"- 태그: {case.get('tag', '')} (글에서 이 이름으로 부름)",
        f"- 컨텍스트: {case.get('context', '')}",
        f"- 시작 연도: {case.get('starting_year', '')}",
        f"- 증권사 가정: {case.get('broker_assumption', '')}",
        f"- 절세계좌 가정: {case.get('tax_account_assumption', '')}",
    ]
    for k in (
        "monthly_invest_krw",
        "monthly_invest_usd",
        "monthly_invest_jpy",
        "monthly_invest_vnd",
        "monthly_invest_idr",
    ):
        if case.get(k):
            lines.append(f"- 월 투자금: {case[k]}")
    if case.get("fx_assumption"):
        lines.append(f"- 환율 가정: {case['fx_assumption']}")
    for k in (
        "disclosure_ko",
        "disclosure_en",
        "disclosure_ja",
        "disclosure_vi",
        "disclosure_id",
    ):
        if case.get(k):
            lines.append(f"- 면책 (시나리오 박스 푸터에 포함 필수): {case[k]}")
            break
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 페르소나 일관성 — 동일한 캐릭터가 모든 글을 작성
# ─────────────────────────────────────────────


def _load_persona(lang: str) -> dict:
    """분석가 페르소나 JSON 로드. analyst_{lang}.json 우선, 없으면 빈 dict."""
    for prefix in ("analyst", "taber"):  # analyst 우선, 레거시 fallback
        path = PERSONA_DIR / f"{prefix}_{lang}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {}


def _persona_brief(persona: dict) -> str:
    """전문 리서치 분석가 톤 주입 — 3인칭, 증거 기반, contrarian 강제."""
    if not persona:
        return ""
    lines = [
        "[작성자 설정 — 전문 리서치 애널리스트 톤]",
        "블로그/분석 글은 '개인 후기/1인칭 시나리오'가 아니라 '3인칭 리서치 노트'로 작성하세요.",
        "'내가', '제가', '저는' 같은 1인칭 표현 절대 금지.",
        "'이재훈', '직장인 캐릭터', '월 70만원 시뮬레이션' 등 가상 인물 언급 금지.",
        "",
        f"[Role] {persona.get('role', '')}",
        f"[Voice] {persona.get('voice', '')}",
        f"[Tone] {persona.get('tone', '')}",
    ]
    spec = persona.get("specialty", [])
    if spec:
        lines.append(f"[Specialty] {', '.join(spec)}")

    methodology = persona.get("methodology", [])
    if methodology:
        lines.append("\n[분석 방법론 — 모든 글에 반영]")
        for m in methodology:
            lines.append(f"- {m}")

    disallow = persona.get("disallowed_phrases", [])
    if disallow:
        lines.append("\n[절대 금지 표현]")
        lines.append(", ".join(f'"{d}"' for d in disallow))

    signature = persona.get("signature_phrasing", [])
    if signature:
        lines.append("\n[선호 문구 (참고 — 그대로 복사 금지, 자연스럽게 응용)]")
        for s in signature:
            lines.append(f"- {s}")

    struct = persona.get("structural_preferences", [])
    if struct:
        lines.append("\n[구조 원칙]")
        for s in struct:
            lines.append(f"- {s}")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 키워드 → 티커 추출 + yfinance 데이터 주입
# ─────────────────────────────────────────────

KNOWN_TICKERS = {
    # US
    "VOO",
    "SPY",
    "QQQ",
    "QQQM",
    "SCHD",
    "JEPI",
    "JEPQ",
    "VT",
    "VTI",
    "VXUS",
    "BND",
    "TLT",
    "GLD",
    "VYM",
    "SCHG",
    "SOXX",
    "SMH",
    "XLF",
    "XLK",
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "TSLA",
    "NVDA",
    # Domestic Korea (티커 매칭은 제한적이지만 키워드로 인식)
}

KOREAN_ETF_HINTS = {
    "TIGER 미국S&P500": "VOO",  # 동일지수
    "TIGER 미국배당다우존스": "SCHD",
    "TIGER 미국나스닥100": "QQQ",
    "KODEX 미국S&P500": "VOO",
    "KODEX 200": None,  # 한국 코스피200, US 티커 없음
    "TIGER 200": None,
}

# 한국 ETF 종목코드 매핑 (pykrx용)
KOREAN_ETF_CODES = {
    "KODEX 200": "069500",
    "TIGER 200": "102110",
    "KBSTAR 200": "148020",
    "TIGER 미국S&P500": "360750",
    "KODEX 미국S&P500TR": "379800",
    "ACE 미국S&P500": "360200",
    "TIGER 미국나스닥100": "133690",
    "KODEX 미국나스닥100TR": "379810",
    "TIGER 미국배당다우존스": "458730",
    "SOL 미국배당다우존스": "446720",
    "KODEX 미국배당다우존스": "458760",
    "TIGER 반도체": "091230",
    "KODEX 반도체": "091160",
    "HANARO 반도체": "365040",
}


def _fetch_korean_etf_data(krx_name: str) -> dict:
    """yfinance .KS suffix로 한국 상장 ETF 데이터 수집 — 국내 ETF 폴백"""
    code = KOREAN_ETF_CODES.get(krx_name)
    if not code:
        return {}
    try:
        import yfinance as yf

        yf_ticker = f"{code}.KS"
        hist = yf.download(yf_ticker, period="3y", progress=False, auto_adjust=True)
        if hist.empty:
            return {}
        close_raw = hist["Close"]
        if hasattr(close_raw, "squeeze"):
            close_raw = close_raw.squeeze()
        close = close_raw.dropna().astype(float)
        current = float(close.iloc[-1])

        def _pct(n_days):
            if len(close) >= n_days:
                old = float(close.iloc[-n_days])
                return round((current / old - 1) * 100, 1) if old > 0 else None
            return None

        r1 = _pct(252)
        r3 = _pct(len(close) - 1) if len(close) > 252 else None
        # 액면병합/분할 이상치 제거: ETF 수익률 |200%| 초과 시 의심 → 버림
        if r1 is not None and abs(r1) > 150:
            r1 = None
        if r3 is not None and abs(r3) > 300:
            r3 = None
        return {
            "current_price_krw": round(current, 2),
            "1y_return_pct": r1,
            "3y_return_pct": r3,
            "source": "yfinance.KS",
            "krx_code": code,
            "krx_name": krx_name,
        }
    except Exception as e:
        logger.warning(f"_fetch_korean_etf_data({krx_name}) 실패: {e}")
        return {}


PEER_ETF = {
    "VOO": "SCHD",  # S&P500 → 배당성장 비교
    "SPY": "VTI",  # S&P500 → 총주식
    "QQQ": "QQQM",  # 나스닥100 → 저비용 버전
    "QQQM": "QQQ",
    "SCHD": "VIG",  # 배당성장 → 배당성장
    "JEPI": "SCHD",  # 커버드콜 → 배당성장
    "JEPQ": "JEPI",
    "VT": "VOO",  # 전세계 → 미국
    "VTI": "SPY",
    "VXUS": "VT",
    "BND": "TLT",
    "VYM": "SCHD",
    "SCHG": "QQQ",
    "SOXX": "SMH",
    "SMH": "SOXX",
}


def _extract_tickers_from_keywords(keywords: list[str], topic: str = "") -> list[str]:
    """키워드와 토픽에서 알려진 ETF 티커 추출 + 단독 티커 시 peer 자동 추가"""
    tickers = []
    text = " ".join(keywords) + " " + topic
    upper = text.upper()
    for t in KNOWN_TICKERS:
        if (
            t in upper.split()
            or f" {t} " in f" {upper} "
            or f"{t}," in upper
            or f"{t}." in upper
        ):
            if t not in tickers:
                tickers.append(t)
    # 한국 ETF 힌트 (US 동등 티커 매핑)
    for kr_name, us_eq in KOREAN_ETF_HINTS.items():
        if kr_name in text and us_eq and us_eq not in tickers:
            tickers.append(us_eq)
    # 단일 티커만 추출된 경우 peer 자동 추가 (비교표 강화)
    if len(tickers) == 1:
        peer = PEER_ETF.get(tickers[0])
        if peer and peer not in tickers:
            tickers.append(peer)
    return tickers[:3]


def _market_data_block(
    tickers: list[str], topic: str = "", keywords: list[str] = None
) -> str:
    """티커 리스트의 yfinance 데이터 + 국내 ETF pykrx 데이터를 프롬프트용 텍스트로 변환"""
    keywords = keywords or []
    text = topic + " " + " ".join(keywords)
    lines = [
        "[다음 실시간 데이터를 본문에 그대로 사용하세요. 절대 다른 숫자 만들지 마세요.]"
    ]

    # 미국 ETF (yfinance)
    for t in tickers:
        d = _fetch_market_data(t)
        if not d:
            continue
        lines.append(f"\n■ {t} (yfinance)")
        if d.get("current_price") is not None:
            lines.append(f"  현재가: ${d['current_price']}")
        if d.get("1y_return_pct") is not None:
            lines.append(f"  1년 수익률: {d['1y_return_pct']:+.1f}%")
        if d.get("3y_return_pct") is not None:
            lines.append(f"  3년 누적: {d['3y_return_pct']:+.1f}%")
        if d.get("5y_return_pct") is not None:
            lines.append(f"  5년 누적: {d['5y_return_pct']:+.1f}%")
        if d.get("10y_return_pct") is not None:
            lines.append(f"  10년 누적: {d['10y_return_pct']:+.1f}%")
        if d.get("dividend_yield_pct") is not None:
            lines.append(f"  배당수익률: {d['dividend_yield_pct']}%")
        if d.get("expense_ratio_pct") is not None:
            lines.append(f"  운용보수: {d['expense_ratio_pct']}%")

    # 국내 ETF (pykrx 폴백)
    for krx_name in KOREAN_ETF_CODES:
        if krx_name in text:
            d = _fetch_korean_etf_data(krx_name)
            if not d:
                continue
            lines.append(f"\n■ {krx_name} (국내 ETF, 종목코드 {d.get('krx_code')})")
            if d.get("current_price_krw") is not None:
                lines.append(f"  현재가: {d['current_price_krw']:,}원")
            if d.get("1y_return_pct") is not None:
                lines.append(f"  1년 수익률: {d['1y_return_pct']:+.1f}%")
            if d.get("3y_return_pct") is not None:
                lines.append(f"  3년 누적: {d['3y_return_pct']:+.1f}%")

    # 거시경제 지표 (FRED) — 선택적
    try:
        from auto_publisher.macro_data import fetch_macro_data, macro_block_text
        macro = fetch_macro_data()
        macro_text = macro_block_text(macro)
        if macro_text:
            lines.append("\n" + macro_text)
    except Exception:
        pass

    return "\n".join(lines) if len(lines) > 1 else ""


# ─────────────────────────────────────────────
# 차트 힌트 — 본문에 차트 자연 참조 유도
# ─────────────────────────────────────────────


def _chart_summaries_for_blog(category: str, keywords: list[str]) -> list[str]:
    """블로그 포스트용 차트 요약 (본문에 참조될 차트 미리 알림)"""
    from auto_publisher.chart_generator import CATEGORY_CHART_MAP, chart_compound_growth

    fns = CATEGORY_CHART_MAP.get(category, [chart_compound_growth])
    summaries = []
    for fn in fns[:2]:
        name = fn.__name__
        if name == "chart_etf_comparison":
            summaries.append(
                "ETF 핵심 지표 3패널 비교 (운용보수/배당수익률/5년 누적수익률)"
            )
        elif name == "chart_compound_growth":
            summaries.append("월 30만원 적립식 20년 시뮬레이션 (연 4%/7%/10%)")
        elif name == "chart_fee_impact":
            summaries.append("ETF 수수료별 20년 후 자산 비교 (0.05%~1.0%)")
        elif name == "chart_dividend_income":
            summaries.append("월 100만원 배당 수입 달성 필요 투자금 (배당률별)")
        elif name == "chart_tax_saving":
            summaries.append("ISA/IRP/연금저축 세후 수익 비교 (1000만원, 10년)")
        elif name == "chart_real_estate_yield":
            summaries.append("부동산 vs ETF vs 예금 20년 수익률 비교")
    return summaries


def _chart_summaries_for_analysis(ticker: str, mkt_data: dict) -> list[str]:
    """분석 포스트용 차트 요약"""
    summaries = [
        f"{ticker} 최근 3년 가격 추이 (저점·고점 표시)",
    ]
    if mkt_data:
        parts = []
        for label, key in [
            ("1년", "1y_return_pct"),
            ("3년", "3y_return_pct"),
            ("5년", "5y_return_pct"),
            ("10년", "10y_return_pct"),
        ]:
            v = mkt_data.get(key)
            if v is not None:
                parts.append(f"{label} {v:+.1f}%")
        ret_str = ", ".join(parts) if parts else "기간별"
        summaries.append(f"{ticker} 기간별 누적 수익률 막대차트 ({ret_str})")
    summaries.append(f"{ticker} 최근 5년 최대낙폭(Drawdown) 차트 — 위험도 시각화")
    return summaries


# ─────────────────────────────────────────────
# 품질 게이트 — 글자수/표/금지어/키워드 검증
# ─────────────────────────────────────────────

MIN_LEN = {"ko": 4000, "en": 3000, "ja": 3500, "vi": 3000, "id": 3000}


def _validate_post(post: dict, lang: str) -> tuple[bool, list[str]]:
    """품질 게이트: 글자수, 비교표, 금지어, 키워드 검증"""
    issues = []
    html = post.get("content_html", "")
    title = post.get("title", "")
    pkw = post.get("primary_keyword", "")

    if len(html) < MIN_LEN.get(lang, 3000):
        issues.append(f"글자수 {len(html)} < {MIN_LEN.get(lang, 3000)}")

    if "<table" not in html:
        issues.append("비교표(<table>) 누락")

    for f in FORBIDDEN_PHRASES.get(lang, []):
        if f in html or f in title:
            issues.append(f"금지어: {f}")

    if pkw and pkw.lower() not in title.lower() and pkw not in title:
        issues.append(f"제목에 primary_keyword '{pkw}' 누락")

    if html.count("<h2") < 3:
        issues.append(f"H2 개수 부족 ({html.count('<h2')})")

    return len(issues) == 0, issues


def _author_bio_html(lang: str) -> str:
    """페르소나 기반 저자 바이오 HTML 생성 (E-E-A-T 신호 + 신뢰도)"""
    persona = _load_persona(lang)
    if not persona:
        return ""

    name = persona.get("name", "")
    age = persona.get("age", "")
    occ = persona.get("occupation", "")
    since = persona.get("investing_since", "")
    broker = persona.get("broker", "")
    philosophy = persona.get("investment_philosophy", "")

    # 언어별 라벨 — 가상 시뮬레이션 캐릭터임을 명시
    labels = {
        "ko": (
            "📚 시나리오 캐릭터",
            "가상 직업",
            "가정 투자 시작",
            "가정 증권사",
            "투자 철학",
            "본 시나리오는 데이터 분석을 위한 가상 캐릭터입니다 — 실제 인물의 투자 기록이 아닙니다.",
        ),
        "en": (
            "📚 Case-Study Character",
            "Hypothetical Job",
            "Assumed Start",
            "Assumed Broker",
            "Philosophy",
            "This is a hypothetical persona used for scenario analysis — not a real investor's record.",
        ),
        "ja": (
            "📚 シナリオキャラクター",
            "仮想職業",
            "想定投資開始",
            "想定証券",
            "投資哲学",
            "本キャラクターはシナリオ分析用の仮想プロフィールです — 実在する投資家の記録ではありません。",
        ),
        "vi": (
            "📚 Nhân vật mô phỏng",
            "Nghề nghiệp giả định",
            "Bắt đầu đầu tư giả định",
            "Sàn giả định",
            "Triết lý",
            "Đây là nhân vật giả định dùng để phân tích kịch bản — không phải hồ sơ nhà đầu tư thực.",
        ),
        "id": (
            "📚 Karakter Studi Kasus",
            "Pekerjaan Hipotetis",
            "Mulai Investasi Hipotetis",
            "Broker Hipotetis",
            "Filosofi",
            "Ini karakter hipotetis untuk analisis skenario — bukan catatan investor nyata.",
        ),
    }
    L = labels.get(lang, labels["en"])

    return f"""
<aside class="author-bio" style="border-left:4px solid #2563eb;background:#f9fafb;padding:1em 1.2em;margin:2em 0 1em 0;border-radius:4px;">
<h3 style="margin:0 0 0.5em 0;font-size:1.05em;">{L[0]}: {name}</h3>
<p style="margin:0.3em 0;font-size:0.92em;"><strong>{L[1]}:</strong> {age}{"세" if lang == "ko" else "yrs"} {occ}</p>
<p style="margin:0.3em 0;font-size:0.92em;"><strong>{L[2]}:</strong> {since} · <strong>{L[3]}:</strong> {broker}</p>
<p style="margin:0.4em 0 0.4em 0;font-size:0.9em;color:#444;"><em>{L[4]}: {philosophy}</em></p>
<p style="margin:0.5em 0 0 0;font-size:0.82em;color:#666;border-top:1px dashed #ccc;padding-top:0.4em;">{L[5]}</p>
</aside>
"""


def _inject_disclaimer(html: str, lang: str, data_fetched_at: str = None) -> str:
    """면책 문구 + AI 고지 + 이해충돌 고지 + 저자 바이오를 본문 끝에 삽입."""
    _STYLE = (
        'background:#f8f9fa;border:1px solid #dee2e6;'
        'border-radius:6px;padding:0.9em 1.1em;margin:2em 0 1em 0;font-size:0.88em;color:#495057;'
    )
    _delay = ""
    if data_fetched_at:
        _delay = f" (데이터 기준: {data_fetched_at} · yfinance 최대 15분 지연)" if lang == "ko" else \
                 f" (Data as of {data_fetched_at} · yfinance up to 15-min delay)"

    AI_DISCLOSURE = {
        "ko": (
            '<div class="ai-disclosure" style="background:#e8f4fd;border:1px solid #bee3f8;'
            'border-radius:6px;padding:0.7em 1em;margin:1.5em 0 0.5em 0;font-size:0.85em;color:#2c5282;">'
            "🤖 <strong>AI 생성 콘텐츠</strong>: 이 콘텐츠는 AI(Claude/Gemini)가 생성한 초안을 "
            "자동화 검증 시스템으로 필터링하여 게시했습니다. 개별 인간 편집자의 검토를 거치지 않습니다.</div>"
        ),
        "en": (
            '<div class="ai-disclosure" style="background:#e8f4fd;border:1px solid #bee3f8;'
            'border-radius:6px;padding:0.7em 1em;margin:1.5em 0 0.5em 0;font-size:0.85em;color:#2c5282;">'
            "🤖 <strong>AI-Generated Content</strong>: This content was drafted by AI (Claude/Gemini) "
            "and filtered through an automated verification system. It has not been reviewed by a human editor.</div>"
        ),
        "ja": (
            '<div class="ai-disclosure" style="background:#e8f4fd;border:1px solid #bee3f8;'
            'border-radius:6px;padding:0.7em 1em;margin:1.5em 0 0.5em 0;font-size:0.85em;color:#2c5282;">'
            "🤖 <strong>AI生成コンテンツ</strong>: このコンテンツはAI(Claude/Gemini)が生成し、"
            "自動検証システムでフィルタリングされています。人間の編集者によるレビューは行っていません。</div>"
        ),
        "vi": (
            '<div class="ai-disclosure" style="background:#e8f4fd;border:1px solid #bee3f8;'
            'border-radius:6px;padding:0.7em 1em;margin:1.5em 0 0.5em 0;font-size:0.85em;color:#2c5282;">'
            "🤖 <strong>Nội dung AI tạo ra</strong>: Nội dung này được tạo bởi AI (Claude/Gemini) "
            "và lọc qua hệ thống xác minh tự động. Chưa được biên tập viên xem xét.</div>"
        ),
        "id": (
            '<div class="ai-disclosure" style="background:#e8f4fd;border:1px solid #bee3f8;'
            'border-radius:6px;padding:0.7em 1em;margin:1.5em 0 0.5em 0;font-size:0.85em;color:#2c5282;">'
            "🤖 <strong>Konten yang Dibuat AI</strong>: Konten ini dibuat oleh AI (Claude/Gemini) "
            "dan difilter melalui sistem verifikasi otomatis. Belum ditinjau oleh editor manusia.</div>"
        ),
    }
    DISCLAIMERS = {
        "ko": (
            f'<div class="disclaimer" style="{_STYLE}">'
            "⚠️ <strong>면책 고지</strong>: 본 콘텐츠는 정보 제공 목적이며 투자 권유가 아닙니다. "
            f"모든 투자 결정과 손익은 본인 책임입니다.{_delay}<br>"
            "<small>이 사이트는 Google AdSense 광고 수익으로 운영됩니다. "
            "특정 ETF·증권사·금융상품으로부터 어떠한 보상·협찬도 받지 않습니다.</small></div>"
        ),
        "en": (
            f'<div class="disclaimer" style="{_STYLE}">'
            "⚠️ <strong>Disclaimer</strong>: This content is for informational purposes only "
            f"and does not constitute investment advice. All investment decisions are at your own risk.{_delay}<br>"
            "<small>This site is supported by Google AdSense advertising revenue. "
            "We receive no compensation or sponsorship from any ETF, broker, or financial product.</small></div>"
        ),
        "ja": (
            f'<div class="disclaimer" style="{_STYLE}">'
            "⚠️ <strong>免責事項</strong>: 本コンテンツは情報提供のみを目的としており、"
            f"投資勧誘ではありません。投資判断はご自身の責任で行ってください。{_delay}<br>"
            "<small>本サイトはGoogle AdSense広告収入で運営されています。"
            "いかなるETF・証券会社・金融商品からも報酬・スポンサーを受けていません。</small></div>"
        ),
        "vi": (
            f'<div class="disclaimer" style="{_STYLE}">'
            "⚠️ <strong>Tuyên bố miễn trách</strong>: Nội dung này chỉ mang tính chất thông tin, "
            f"không phải tư vấn đầu tư. Mọi quyết định đầu tư là trách nhiệm của bạn.{_delay}<br>"
            "<small>Trang web này được hỗ trợ bởi doanh thu quảng cáo Google AdSense. "
            "Chúng tôi không nhận bất kỳ khoản thù lao hay tài trợ nào từ ETF, môi giới, hay sản phẩm tài chính.</small></div>"
        ),
        "id": (
            f'<div class="disclaimer" style="{_STYLE}">'
            "⚠️ <strong>Penafian</strong>: Konten ini hanya untuk tujuan informasi dan bukan "
            f"merupakan saran investasi. Semua keputusan investasi adalah tanggung jawab Anda sendiri.{_delay}<br>"
            "<small>Situs ini didukung oleh pendapatan iklan Google AdSense. "
            "Kami tidak menerima kompensasi atau sponsor dari ETF, broker, atau produk keuangan manapun.</small></div>"
        ),
    }
    ai_banner = AI_DISCLOSURE.get(lang, AI_DISCLOSURE["en"])
    disclaimer = DISCLAIMERS.get(lang, DISCLAIMERS["en"])
    bio = _author_bio_html(lang)

    if 'class="ai-disclosure"' not in html:
        html = html + "\n" + ai_banner
    if 'class="disclaimer"' not in html:
        html = html + "\n" + disclaimer
    if 'class="author-bio"' not in html and bio:
        html = html + "\n" + bio
    return html


logger = logging.getLogger(__name__)


def _format_signal_with_badge(
    agent: str, signal: str, confidence: float, sample_size: int | None = None
) -> str:
    """에이전트 신호를 신뢰도 뱃지와 함께 포맷. confidence < 0.60이면 경고 뱃지 추가."""
    badge = ""
    if confidence < 0.60:
        n_note = f" — 표본 {sample_size}건, 참고 수준" if sample_size else ", 참고 수준"
        badge = f" ⚠️ [낮은 신뢰도{n_note}]"
    return f"- {agent}: {signal} (confidence {confidence:.2f}){badge}"


def _build_verification_snippet(ticker: str, lang: str = "ko") -> str:
    """yfinance로 데이터를 직접 재현할 수 있는 코드 스니펫 반환.
    한국 주식(.KS/.KQ)은 yfinance 지원이 불안정하므로 빈 문자열 반환."""
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        return ""
    if lang == "ko":
        header = "📊 **이 데이터를 직접 확인하는 방법**"
    else:
        header = "📊 **Verify this data yourself**"
    return (
        f"\n{header}\n"
        f"```python\n"
        f"import yfinance as yf\n"
        f't = yf.Ticker("{ticker}")\n'
        f't.history(period="5y")["Close"].pct_change().add(1).cumprod()\n'
        f"```\n"
    )

CODEX_MODEL = os.getenv("CODEX_MODEL", "gpt-5.4-mini")
GEMINI_CLI_MODEL = os.getenv("GEMINI_CLI_MODEL", "gemini-2.5-pro")
CLAUDE_CLI_MODEL = os.getenv("CLAUDE_CLI_MODEL", "claude-sonnet-4-6")
LLM_PRIMARY_BACKEND = os.getenv("LLM_PRIMARY_BACKEND", "gemini").strip().lower()
LLM_BACKENDS = ("gemini", "claude", "codex", "ollama")


def _call_codex(prompt: str, max_retries: int = 3) -> str:
    """codex exec subprocess 호출 (ChatGPT Plus 인증, stdin 방식)"""
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["codex", "exec", "-c", f'model="{CODEX_MODEL}"', "-"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"codex 오류: {result.stderr[:300]}")
            return result.stdout
        except subprocess.TimeoutExpired:
            wait = 2 ** (attempt + 1)
            logger.warning(f"codex 타임아웃 (시도 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                raise RuntimeError("codex exec 타임아웃 3회")
        except Exception as e:
            wait = 2 ** (attempt + 1)
            logger.warning(f"codex 호출 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                raise RuntimeError(f"codex exec {max_retries}회 실패: {e}")


def _call_claude_cli(prompt: str, max_retries: int = 2) -> str:
    """claude CLI 호출 (gemini 실패 시 폴백, sonnet 기본)"""
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--model", CLAUDE_CLI_MODEL],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"claude 오류: {result.stderr[:300]}")
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning(f"claude 타임아웃 (시도 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(4)
            else:
                raise RuntimeError("claude CLI 타임아웃")
        except Exception as e:
            logger.warning(f"claude 호출 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(4)
            else:
                raise RuntimeError(f"claude CLI {max_retries}회 실패: {e}")


def _call_gemini_cli(prompt: str, max_retries: int = 2) -> str:
    """gemini CLI 호출 (codex 실패 시 폴백)"""
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["gemini", "-m", GEMINI_CLI_MODEL, "-p", prompt],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"gemini 오류: {result.stderr[:300]}")
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning(f"gemini 타임아웃 (시도 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(4)
            else:
                raise RuntimeError("gemini CLI 타임아웃")
        except Exception as e:
            logger.warning(f"gemini 호출 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(4)
            else:
                raise RuntimeError(f"gemini CLI {max_retries}회 실패: {e}")


OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.6:35b-a3b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "1200"))
OLLAMA_THINK_MODE = os.getenv("OLLAMA_THINK_MODE", "script").strip().lower()


def _call_ollama(prompt: str, max_retries: int = 2, think: bool = False) -> str:
    """Ollama HTTP API 호출 (gemini CLI 실패 시 최종 폴백)"""
    import urllib.request, json as _json
    for attempt in range(max_retries):
        try:
            content = _prepare_ollama_prompt(prompt, think=think)
            body = _json.dumps({
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": content}],
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                f"{OLLAMA_HOST}/api/chat",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SEC) as resp:
                data = _json.loads(resp.read())
                return data["message"]["content"]
        except Exception as e:
            logger.warning(f"ollama 호출 실패 (시도 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(4)
            else:
                raise RuntimeError(f"ollama {max_retries}회 실패: {e}")


def _prepare_ollama_prompt(prompt: str, think: bool = False) -> str:
    """Qwen thinking 모델은 JSON 파이프라인에서 reasoning 출력을 막는다."""
    model = OLLAMA_MODEL.lower()
    stripped = prompt.lstrip()
    if not model.startswith("qwen"):
        return prompt
    if think:
        if stripped.startswith("/think"):
            return prompt
        return "/think\n" + prompt
    if not stripped.startswith("/no_think"):
        return "/no_think\n" + prompt
    return prompt


def _call_llm(prompt: str, max_retries: int = 3, think: bool = False) -> str:
    """환경변수 기반 LLM 백엔드 선택 + 폴백."""
    primary = LLM_PRIMARY_BACKEND if LLM_PRIMARY_BACKEND in LLM_BACKENDS else "gemini"
    non_ollama = [b for b in LLM_BACKENDS if b != "ollama"]
    if primary != "ollama":
        non_ollama = [primary] + [b for b in non_ollama if b != primary]
    order = non_ollama + ["ollama"]
    errors: list[str] = []

    for backend in order:
        try:
            if backend == "gemini":
                logger.info("LLM backend: gemini model=%s", GEMINI_CLI_MODEL)
                return _call_gemini_cli(prompt)
            if backend == "claude":
                logger.info("LLM backend: claude model=%s", CLAUDE_CLI_MODEL)
                return _call_claude_cli(prompt)
            if backend == "ollama":
                logger.info("LLM backend: ollama model=%s think=%s", OLLAMA_MODEL, think)
                return _call_ollama(prompt, think=think)
            if backend == "codex":
                logger.info("LLM backend: codex model=%s", CODEX_MODEL)
                return _call_codex(prompt, max_retries=max_retries)
        except Exception as e:
            message = f"{backend} model={_backend_model_name(backend)} reason={e}"
            errors.append(message)
            logger.warning("LLM backend failed: %s", message)

    raise RuntimeError("모든 LLM 백엔드 실패: " + " | ".join(errors))


def _backend_model_name(backend: str) -> str:
    if backend == "gemini":
        return GEMINI_CLI_MODEL
    if backend == "ollama":
        return OLLAMA_MODEL
    if backend == "claude":
        return CLAUDE_CLI_MODEL
    if backend == "codex":
        return CODEX_MODEL
    return "-"


CATEGORIES_BY_LANG = {
    "ko": ["투자", "재테크"],
    "en": ["Investing", "Personal Finance"],
    "ja": ["投資", "資産運用"],
    "vi": ["Đầu tư", "Tài chính cá nhân"],
    "id": ["Investasi", "Keuangan Pribadi"],
}

LANG_PROMPTS = {
    "ko": {
        "persona": (
            "직장 다니면서 ETF·배당주 투자를 5년째 하고 있는 30대 한국인 투자자 블로거. "
            "실제 투자 금액(월 30~100만원)과 실적 수치를 공개하고, 수익뿐 아니라 손실·실수·멘탈 관리도 솔직하게 씀. "
            "VOO, SCHD, KODEX, TIGER 같은 구체적 상품명과 수수료%, 배당률%을 항상 언급함."
        ),
        "forbidden": (
            '"완벽 가이드", "총정리", "살펴보겠습니다", "알아보겠습니다", "정리해 드리겠습니다", '
            '"도움이 되셨으면", "마치며", "이상으로", "~해드리겠습니다"'
        ),
        "style": (
            "친구한테 솔직하게 설명하는 말투. 구체적 수치 필수. "
            "마크다운 비교표(상품명 | 수수료 | 배당률 | 수익률) 최소 1개 포함. "
            "결론은 반드시 '나는 이래서 이걸 선택한다' 형식. "
            "실수했거나 예상과 달랐던 점 1개 이상 포함. 최소 4000자."
        ),
        "faq_label": "자주 묻는 질문",
        "output_lang": "한국어",
    },
    "en": {
        "persona": "a personal finance blogger who has actually invested and made mistakes — writing for real people, not textbooks",
        "forbidden": '"In conclusion", "In summary", "It is worth noting", "It is important to", "As mentioned above"',
        "style": "Conversational, like explaining to a friend. Mix short punchy sentences with detailed explanations. Include real numbers. Don't be a cheerleader — mention downsides too.",
        "faq_label": "Frequently Asked Questions",
        "output_lang": "English",
    },
    "ja": {
        "persona": "実際に投資経験のある日本人の個人投資家ブロガー",
        "forbidden": '"まとめると", "以上を踏まえて", "ぜひ参考にしてください", "最後に", "いかがでしたか"',
        "style": "普通の日本語で、友人に説明するような口調。専門用語は使うが必ず解説。具体的な数字を入れる。",
        "faq_label": "よくある質問",
        "output_lang": "日本語",
    },
    "vi": {
        "persona": "một blogger tài chính cá nhân người Việt Nam đã thực sự đầu tư và có kinh nghiệm thực tế",
        "forbidden": '"Tóm lại", "Như vậy", "Hy vọng bài viết", "Kết luận", "Trên đây là"',
        "style": "Viết tự nhiên như giải thích cho bạn bè. Dùng số liệu cụ thể. Nói thẳng ưu và nhược điểm.",
        "faq_label": "Câu hỏi thường gặp",
        "output_lang": "tiếng Việt",
    },
    "id": {
        "persona": "seorang blogger keuangan pribadi Indonesia yang sudah berinvestasi langsung dan berbagi pengalaman nyata",
        "forbidden": '"Kesimpulannya", "Demikianlah", "Semoga bermanfaat", "Sekian", "Sebagai penutup"',
        "style": "Santai dan natural seperti menjelaskan ke teman. Pakai angka nyata. Jujur soal risiko dan kekurangan.",
        "faq_label": "Pertanyaan yang Sering Ditanyakan",
        "output_lang": "Bahasa Indonesia",
    },
}


def _build_blog_prompt(
    topic: str,
    keywords: list[str],
    lang: str,
    persona_brief: str,
    market_block: str,
    chart_summaries: list[str],
    category: str = "",
    retry_issues: list[str] = None,
    case_brief: str = "",
) -> str:
    """블로그 포스트 프롬프트 빌더 (페르소나 + 실데이터 + 차트 힌트 통합)"""
    lp = LANG_PROMPTS.get(lang, LANG_PROMPTS["ko"])
    kw_str = ", ".join(keywords)
    primary_kw = keywords[0] if keywords else topic
    style_extra = lp.get("style", "")

    chart_block = ""
    if chart_summaries:
        chart_lines = [f"  {i + 1}. {s}" for i, s in enumerate(chart_summaries)]
        chart_block = (
            "\n[다음 차트들이 본문 첫 H2 직후에 자동 삽입됩니다. "
            "본문에서 반드시 자연스럽게 인용하세요. "
            "예: '아래 차트를 보면 5년간 +85%로 가장 인상적이다.']\n"
            + "\n".join(chart_lines)
        )

    persona_block = f"\n{persona_brief}\n" if persona_brief else ""
    market_inject = f"\n{market_block}\n" if market_block else ""
    case_inject = f"\n{case_brief}\n" if case_brief else ""

    retry_block = ""
    if retry_issues:
        retry_block = (
            "\n[이전 응답이 다음 검증을 통과하지 못했습니다. 반드시 수정하세요:]\n"
            + "\n".join(f"  - {x}" for x in retry_issues)
        )

    scenario_block = ""
    if case_brief:
        scenario_block = """
[선택적 시나리오 박스 — 데이터 구체화용 (강력 권장 1회)]
- 본문 중간 한 번만, 위 가상 시나리오 케이스를 활용한 박스를 삽입할 수 있다.
- 박스 형식 (HTML 그대로 사용):
  <aside class="scenario-box">
    <div class="scenario-header">💡 가상 시나리오: [케이스 태그]의 [구체 상황]</div>
    <div class="scenario-body">
      <p><strong>설정</strong>: 케이스 컨텍스트 + 가정 (월 투자금, 시작연도, 증권사)</p>
      <p>본문에서 인용된 yfinance 실수치를 케이스에 적용해 환산값 제시</p>
      <p>조건이 바뀌면(시작 시점, 환율, 보수율 등)이 달라진다 — disconfirming 한 줄</p>
    </div>
    <div class="scenario-footnote">[케이스 태그]는 데이터를 구체화하기 위한 가상 인물입니다. 실존 인물·실제 거래가 아닙니다.</div>
  </aside>
- 박스 안에서만 케이스 이름 사용. 박스 밖에서는 다시 3인칭 애널리스트 톤.
- 박스 1회 초과 금지. 어색하면 생략 가능.
- 절대 1인칭("내가/제가") 금지 — 박스도 3인칭 서술("K씨가...")
"""

    return f"""You are {lp["persona"]}.
{persona_block}
Write a blog post on the topic below. Output language: {lp["output_lang"]}.

Topic: {topic}
Keywords: {kw_str}
{market_inject}{case_inject}{chart_block}{retry_block}{scenario_block}

[Writing Style — MOST IMPORTANT — follow strictly]
{style_extra}
- NEVER use these phrases: {lp["forbidden"]}
- Do NOT use overly symmetric numbered lists — flowing prose with natural breaks
- Mention downsides, risks, mistakes honestly — cheerleading looks like an ad
- Include at least one HTML comparison table. You can choose between:
  - Template A (Performance Focus): Product Name | Fee | Yield | 5Y Return | 1Y Return
  - Template B (Valuation Focus): Product Name | Fee | Yield | P/E Ratio | Market Cap
  - Use <table><thead>...</thead><tbody>...</tbody></table> format for either template.
- If market data is provided above, use those EXACT numbers — do NOT invent different ones

[CRITICAL — 전문 리서치 애널리스트 톤 필수]
- 3인칭, 증거 기반. 1인칭("내가/제가/저는") 절대 금지.
- 개인 일화/시뮬레이션 캐릭터("이재훈", "34세 직장인") 일체 금지 — 데이터 리서치 노트 형식.
- 모든 주장은 연도+수치 포함 (예: "2020~2026 CAGR 12.3%", "1년 배당 총액 $47.2").
- Contrarian angle 1개 이상: 시장 통설/컨센서스와 다른 해석을 한 번은 제시.
- Disconfirming evidence 1개: "이 분석이 틀릴 수 있는 시나리오"를 명시적으로 작성.
- 불확실성 인정: 데이터가 부족하거나 확신하기 어려운 지점은 숨기지 않고 드러냄.
- 구조 비대칭: 모든 글이 동일 템플릿이면 안 됨 — 주제별로 FAQ 생략, 표 생략, Q&A 단독 등 변주 허용.
- 문장 리듬: 짧은 문장(6~15자)과 긴 문장(50자+) 혼합. 동일 길이 문장 연속 금지.
- 교과서 문체 금지: "다음과 같이", "앞서 살펴본 바와 같이", "결론적으로", "마치며", "이상으로", "이렇게", "이런 식으로"
- 역사 비유 허용: 1999 닷컴, 2008 금융위기, 2020 코로나락 등 구체적 시점 참조 가능.

[Content Structure]
1. Return ONLY pure JSON. No markdown code blocks, no extra text.
2. Title: include main keyword, compelling, 40-80 chars
3. Body: HTML format, {MIN_LEN.get(lang, 3000)}+ characters
4. Minimum 4 H2/H3 subheadings — specific & curiosity-driven
5. Intro summary box: <div class="summary-box"><ul><li>...</li></ul></div> (3-5 concrete numeric takeaways)
6. One HTML comparison table with 3+ columns
7. FAQ: <h2>{lp["faq_label"]}</h2> — 5 real-search-style questions
8. Meta description: under 160 chars, include keyword
9. Tags: 8-10 tags
10. AdSense-compliant — no investment advice phrasing

[Output format - pure JSON only]
{{"title": "...", "content_html": "...", "meta_description": "...", "tags": ["..."], "primary_keyword": "{primary_kw}", "keywords_long_tail": ["...", "..."], "schema_faq": [{{"question": "...?", "answer": "..."}}], "content_type": "guide"}}
"""


def generate_blog_post(
    topic: str,
    keywords: list[str],
    niche: str = None,
    lang: str = "ko",
    category: str = "",
) -> dict:
    """
    블로그 포스트 생성 (페르소나·yfinance·차트힌트·품질게이트·재시도·면책 통합)

    Returns:
        {title, content_html, meta_description, tags,
         primary_keyword, keywords_long_tail, schema_faq, content_type}
    """
    primary_kw = keywords[0] if keywords else topic

    # 1) 페르소나 + yfinance + 차트 힌트 + 시나리오 케이스 사전 수집
    persona = _load_persona(lang)
    persona_brief = _persona_brief(persona)
    case = _load_case(lang)
    case_brief = _case_brief(case)

    tickers = _extract_tickers_from_keywords(keywords, topic)
    market_block = _market_data_block(tickers, topic=topic, keywords=keywords)
    chart_summaries = _chart_summaries_for_blog(category, keywords) if category else []

    # 2) 1차 생성
    prompt = _build_blog_prompt(
        topic,
        keywords,
        lang,
        persona_brief,
        market_block,
        chart_summaries,
        category,
        case_brief=case_brief,
    )
    raw = _call_llm(prompt)
    result = _parse_json_response(raw, "blog_post")

    # 3) 2단계 검증 (규칙 + Gemini 의미) — 최대 2회 재시도 + 치명 미달 reject
    from auto_publisher.content_verifier import verify_two_stage

    # source_data 구성 (yfinance 검증용)
    verif_source = {}
    for t in tickers:
        d = _fetch_market_data(t)
        if d:
            verif_source[t] = d

    result.setdefault("primary_keyword", primary_kw)
    best = result
    best_verif = verify_two_stage(
        best, verif_source, lang, min_len=MIN_LEN.get(lang, 3000)
    )
    best_ok = best_verif["ok"]

    for attempt in range(2):
        if best_ok:
            break
        retry_reason = best_verif.get("retry_prompt", "")
        logger.warning(f"검증 실패 ({lang}) 재시도 {attempt + 1}/2: {retry_reason}")
        try:
            issues_for_prompt = best_verif.get("stage1_issues", [])[:5]
            s2 = best_verif.get("stage2_report", {})
            for k in ("hallucination", "bad_phrasing", "contradiction"):
                issues_for_prompt.extend([f"{k}: {x}" for x in s2.get(k, [])[:2]])
            prompt_r = _build_blog_prompt(
                topic,
                keywords,
                lang,
                persona_brief,
                market_block,
                chart_summaries,
                category,
                retry_issues=issues_for_prompt or [retry_reason],
                case_brief=case_brief,
            )
            raw_r = _call_llm(prompt_r)
            result_r = _parse_json_response(raw_r, f"blog_post_retry_{attempt + 1}")
            result_r.setdefault("primary_keyword", primary_kw)
            verif_r = verify_two_stage(
                result_r, verif_source, lang, min_len=MIN_LEN.get(lang, 3000)
            )
            if verif_r["ok"] or len(result_r.get("content_html", "")) > len(
                best.get("content_html", "")
            ):
                best = result_r
                best_verif = verif_r
                best_ok = verif_r["ok"]
                if verif_r["ok"]:
                    logger.info(f"재시도 {attempt + 1} 성공 — 2단계 검증 통과")
                else:
                    logger.info(
                        f"재시도 {attempt + 1} 더 긴 버전 채택 (남은: {verif_r.get('retry_prompt', '')[:120]})"
                    )
        except Exception as e:
            logger.warning(f"재시도 {attempt + 1} 파싱 실패: {e}")

    best_issues = best_verif.get("stage1_issues", [])

    # 치명 미달 체크: 글자수가 최소치의 50% 미만이면 reject (실패큐로)
    critical_min = MIN_LEN.get(lang, 3000) // 2
    if len(best.get("content_html", "")) < critical_min:
        raise RuntimeError(
            f"치명적 품질 미달: 글자수 {len(best.get('content_html', ''))} < 최소치의 50% ({critical_min})"
        )

    result = best

    # 4) 면책 조항 자동 삽입
    result["content_html"] = apply_compliance(result.get("content_html", ""), lang)

    # 5) 재현 가능 검증 스니펫 삽입 (미국 ETF/주식만)
    if tickers:
        snippet = _build_verification_snippet(tickers[0], lang)
        if snippet:
            result["content_html"] += snippet

    # 6) 기본값 보장
    result.setdefault("content_type", "guide")
    result.setdefault("keywords_long_tail", keywords)
    result.setdefault("schema_faq", [])

    return result


_ANALYSIS_LANG = {
    "ko": {
        "title_hint": (
            "한국어 제목, 50자 이내, 정보성 표현. "
            "절대 '매수/매도/사야 한다/지금 사도 될까' 같은 권유성 표현 금지. "
            "예: '{ticker} 5년 데이터로 보는 가격 패턴 / {ticker} 백테스트: 1년 +12% 의미'"
        ),
        "output_lang": "한국어",
        "signal_map": {
            "BUY": "데이터상 강세 흐름",
            "SELL": "데이터상 약세 흐름",
            "HOLD": "혼조 흐름",
        },
        "faq_label": "자주 묻는 질문",
    },
    "en": {
        "title_hint": (
            "English title under 60 chars, INFORMATIONAL not advisory. "
            "Forbidden: 'Should You Buy', 'Buy Now', 'Recommend', 'Time to Buy'. "
            "Example: '{ticker} 5-Year Pattern Analysis / What Data Says About {ticker}'"
        ),
        "output_lang": "English",
        "signal_map": {
            "BUY": "data shows bullish pattern",
            "SELL": "data shows bearish pattern",
            "HOLD": "data is mixed",
        },
        "faq_label": "Frequently Asked Questions",
    },
    "ja": {
        "title_hint": (
            "日本語タイトル、50文字以内、情報提供型。"
            "禁止：「買うべき」「売るべき」「今買え」のような推奨表現。"
            "例：「{ticker} 5年データで見る価格パターン」"
        ),
        "output_lang": "日本語",
        "signal_map": {
            "BUY": "データ上は強気パターン",
            "SELL": "データ上は弱気パターン",
            "HOLD": "データは混在",
        },
        "faq_label": "よくある質問",
    },
    "vi": {
        "title_hint": (
            "Tiêu đề tiếng Việt dưới 60 ký tự, chỉ thông tin, không gợi ý mua/bán. "
            "VD: 'Mô hình giá {ticker} 5 năm qua dữ liệu'"
        ),
        "output_lang": "tiếng Việt",
        "signal_map": {
            "BUY": "dữ liệu cho thấy xu hướng tăng",
            "SELL": "dữ liệu cho thấy xu hướng giảm",
            "HOLD": "dữ liệu hỗn hợp",
        },
        "faq_label": "Câu hỏi thường gặp",
    },
    "id": {
        "title_hint": (
            "Judul Bahasa Indonesia di bawah 60 karakter, hanya informasi. "
            "Contoh: 'Pola Harga {ticker} dari Data 5 Tahun'"
        ),
        "output_lang": "Bahasa Indonesia",
        "signal_map": {
            "BUY": "data menunjukkan tren bullish",
            "SELL": "data menunjukkan tren bearish",
            "HOLD": "data campur",
        },
        "faq_label": "Pertanyaan yang Sering Ditanyakan",
    },
}


# ─────────────────────────────────────────────
# 데이터 무결성 레이어 — 필드별 검증 + 교차 검증
# ─────────────────────────────────────────────

FIELD_RANGES = {
    "dividend_yield_pct": (0, 15),  # 0~15% (REIT 예외 일부)
    "expense_ratio_pct": (0, 3),  # ETF 운용보수 0~3%
    "pe_ratio": (1, 200),  # P/E 1~200
    "1y_return_pct": (-90, 500),  # 1년 -90 ~ +500%
    "3y_return_pct": (-95, 1000),
    "5y_return_pct": (-95, 2000),
    "10y_return_pct": (-95, 5000),
    "current_price": (0.01, 1_000_000),
}


def _validate_field(value, field: str):
    """필드별 sanity 범위 검증 — 벗어나면 None 반환"""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    lo, hi = FIELD_RANGES.get(field, (None, None))
    if lo is not None and (v < lo or v > hi):
        logger.warning(f"필드 '{field}' 값 {v} 범위 [{lo}, {hi}] 벗어남 → None")
        return None
    return v


def _compute_dividend_yield(ticker_obj, current_price: float) -> tuple:
    """배당수익률 직접 계산 — 최근 12개월 합산 (분기/월배당 자동 대응)"""
    try:
        from datetime import datetime, timedelta

        divs = ticker_obj.dividends
        if divs is None or len(divs) == 0 or not current_price:
            return None, "no_dividends"

        # 최근 365일치만 합산 (월배당이든 분기배당이든 정확)
        cutoff = (
            datetime.now(divs.index.tz) - timedelta(days=365)
            if divs.index.tz
            else datetime.now() - timedelta(days=365)
        )
        try:
            recent_12m = divs[divs.index >= cutoff]
        except TypeError:
            # 시간대 문제 시 fallback: 최근 12개 (대부분 분기배당 3년 또는 월배당 1년)
            recent_12m = divs.tail(12)

        if len(recent_12m) == 0:
            return None, "no_recent_dividends"

        annual = float(recent_12m.sum())
        if annual <= 0:
            return None, "zero_sum"
        yield_pct = round(annual / current_price * 100, 2)
        validated = _validate_field(yield_pct, "dividend_yield_pct")
        return validated, f"computed_ttm({len(recent_12m)}분배)"
    except Exception as e:
        return None, f"error:{e}"


def _fetch_market_data(ticker: str, use_cache: bool = True) -> dict:
    """캐시 우선 → live fallback. n8n cron이 매일 캐시 갱신해두면 yfinance 부하 ↓"""
    if use_cache:
        try:
            from auto_publisher.market_cache import get_cached_data

            cached = get_cached_data(ticker)
            if cached:
                logger.debug(f"[{ticker}] 캐시 히트")
                return cached
        except Exception as e:
            logger.debug(f"[{ticker}] 캐시 조회 실패, live fetch: {e}")
    return _fetch_market_data_live(ticker)


def _fetch_market_data_live(ticker: str) -> dict:
    """다중 소스 + 검증된 시장 데이터 (캐시 미경유 직접 fetch).

    설계 원칙:
    1) 모든 필드는 sanity 범위 검증 → 벗어나면 None
    2) 배당률은 yfinance.info 대신 dividends 시계열로 직접 계산 (더 정확)
    3) yfinance.info 값과 계산 값이 30% 이상 차이나면 신뢰 불가로 None
    4) 모든 데이터에 source 표시 (디버깅 + 신뢰도 추적)
    """
    sources = {}  # 필드별 소스 추적
    try:
        import yfinance as yf
        import pandas as pd

        t = yf.Ticker(ticker)
        info = {}
        try:
            info = t.info or {}
        except Exception:
            pass
        hist = yf.download(ticker, period="10y", progress=False, auto_adjust=True)

        # 가격 + 수익률
        if not hist.empty:
            close_raw = hist["Close"]
            if hasattr(close_raw, "squeeze"):
                close_raw = close_raw.squeeze()
            close = close_raw.dropna().astype(float)
            now = float(close.iloc[-1])
            sources["current_price"] = "yfinance.history"

            def _ret(years):
                n = years * 252
                if len(close) >= n:
                    old = float(close.iloc[-n])
                    if old > 0:
                        return round((now / old - 1) * 100, 1)
                return None

            r1, r3, r5, r10 = _ret(1), _ret(3), _ret(5), _ret(10)
        else:
            now = r1 = r3 = r5 = r10 = None

        # 배당수익률: yfinance.info 값과 직접 계산 값 교차 검증
        info_dy = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
        # info_dy 정규화 (0~1 소수 vs >=1 퍼센트)
        info_dy_pct = None
        if info_dy is not None:
            info_dy_f = float(info_dy)
            info_dy_pct = info_dy_f if info_dy_f >= 1 else info_dy_f * 100
            info_dy_pct = round(info_dy_pct, 2)

        computed_dy, dy_src = _compute_dividend_yield(t, now)

        # 두 값 모두 있으면 교차 검증
        final_dy = None
        if computed_dy is not None and info_dy_pct is not None:
            diff_pct = (
                abs(computed_dy - info_dy_pct) / max(computed_dy, info_dy_pct) * 100
            )
            if diff_pct < 30:
                # 일치 → 보수적으로 작은 값 채택
                final_dy = min(computed_dy, info_dy_pct)
                sources["dividend_yield_pct"] = f"verified(diff={diff_pct:.0f}%)"
            else:
                # 불일치 → computed 우선 (더 신뢰)
                final_dy = computed_dy
                sources["dividend_yield_pct"] = (
                    f"computed_only(info_diff={diff_pct:.0f}%)"
                )
        elif computed_dy is not None:
            final_dy = computed_dy
            sources["dividend_yield_pct"] = "computed"
        elif info_dy_pct is not None:
            # info 값만 있으면 검증 후 사용
            final_dy = _validate_field(info_dy_pct, "dividend_yield_pct")
            sources["dividend_yield_pct"] = "info_only"

        # P/E + 운용보수
        pe = info.get("trailingPE") or info.get("forwardPE")
        pe_v = _validate_field(pe, "pe_ratio")
        if pe_v:
            sources["pe_ratio"] = "yfinance.info"

        expense_raw = info.get("annualReportExpenseRatio") or info.get("expenseRatio")
        if expense_raw is not None:
            expense_v = (
                float(expense_raw)
                if float(expense_raw) >= 0.01
                else float(expense_raw) * 100
            )
            expense_v = _validate_field(round(expense_v, 3), "expense_ratio_pct")
            if expense_v:
                sources["expense_ratio_pct"] = "yfinance.info"
        else:
            expense_v = None

        # 수익률 검증
        r1_v = _validate_field(r1, "1y_return_pct")
        r3_v = _validate_field(r3, "3y_return_pct")
        r5_v = _validate_field(r5, "5y_return_pct")
        r10_v = _validate_field(r10, "10y_return_pct")

        market_cap = info.get("marketCap")

        logger.info(f"[{ticker}] 데이터 소스: {sources}")

        return {
            "current_price": round(now, 2) if now else None,
            "1y_return_pct": r1_v,
            "3y_return_pct": r3_v,
            "5y_return_pct": r5_v,
            "10y_return_pct": r10_v,
            "dividend_yield_pct": final_dy,
            "expense_ratio_pct": expense_v,
            "market_cap": market_cap,
            "pe_ratio": round(pe_v, 1) if pe_v else None,
            "_sources": sources,
        }
    except Exception as e:
        logger.warning(f"_fetch_market_data({ticker}) 실패: {e}")
        return {}


def generate_shorts_script(
    topic: str, data: dict, template_name: str, lang: str = "ko"
) -> dict:
    """
    Shorts 스크립트 생성기: 템플릿 기반으로 쇼츠 스크립트 생성
    """
    template_path = PERSONA_DIR.parent / "shorts_templates" / f"{template_name}.json"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_name}")

    template = json.loads(template_path.read_text(encoding="utf-8"))

    prompt = f"""You are a financial YouTube Shorts creator.
Create a 60-second script for the topic: {topic}
Using the template: {template["name"]} - {template["description"]}

Structure requirements:
{json.dumps(template["structure"], ensure_ascii=False, indent=2)}

Context data:
{json.dumps(data, ensure_ascii=False, indent=2)}

Rules:
- Duration: 60 seconds (~300 characters in {lang})
- Language: {lang}
- Strict 3rd person tone
- No "Buy/Sell/Recommend" advice

Output as pure JSON:
{{
  "title": "Shorts Title (include #shorts)",
  "chapters": [
    {{"start_sec": 0, "title": "Hook", "text": "..."}},
    {{"start_sec": 3, "title": "Content", "text": "..."}},
    {{"start_sec": 50, "title": "CTA", "text": "..."}}
  ]
}}
"""
    raw = _call_llm(prompt)
    return _parse_json_response(raw, "shorts_script")
    lp = _ANALYSIS_LANG.get(lang, _ANALYSIS_LANG["en"])
    lw = LANG_PROMPTS.get(lang, LANG_PROMPTS["en"])

    final_action = analysis.get("final_action", "HOLD")
    signal_label = lp["signal_map"].get(final_action, final_action)
    signals = analysis.get("analyst_signals", {})
    news = analysis.get("news_headlines", [])
    analysis_date = analysis.get("analysis_date", "")

    # yfinance 실데이터 — analysis에 mkt_data 있으면 재사용, 없으면 fetch
    mkt = analysis.get("mkt_data") or _fetch_market_data(ticker)
    mkt_lines = []
    if mkt.get("current_price"):
        mkt_lines.append(f"- 현재가: ${mkt['current_price']}")
    if mkt.get("1y_return_pct") is not None:
        mkt_lines.append(f"- 1년 수익률: {mkt['1y_return_pct']}%")
    if mkt.get("3y_return_pct") is not None:
        mkt_lines.append(f"- 3년 수익률: {mkt['3y_return_pct']}%")
    if mkt.get("5y_return_pct") is not None:
        mkt_lines.append(f"- 5년 수익률: {mkt['5y_return_pct']}%")
    if mkt.get("10y_return_pct") is not None:
        mkt_lines.append(f"- 10년 수익률: {mkt['10y_return_pct']}%")
    if mkt.get("dividend_yield_pct") is not None:
        mkt_lines.append(f"- 배당수익률: {mkt['dividend_yield_pct']}%")
    if mkt.get("expense_ratio_pct") is not None:
        mkt_lines.append(f"- 운용보수: {mkt['expense_ratio_pct']}%")
    if mkt.get("pe_ratio") is not None:
        mkt_lines.append(f"- P/E: {mkt['pe_ratio']}")
    mkt_text = "\n".join(mkt_lines) if mkt_lines else "데이터 없음"

    # 에이전트 시그널 요약
    signal_lines = []
    for agent, data in signals.items():
        sig = data.get("signal", "neutral")
        conf = data.get("confidence", 0)
        reason = str(data.get("reasoning", ""))[:300]
        signal_lines.append(f"- {agent}: {sig} (confidence {conf}) — {reason}")
    signals_text = "\n".join(signal_lines) if signal_lines else "N/A"

    news_text = "\n".join(f"- {h}" for h in news) if news else "N/A"

    # 차트 힌트
    chart_summaries = _chart_summaries_for_analysis(ticker, mkt)
    chart_lines = [f"  {i + 1}. {s}" for i, s in enumerate(chart_summaries)]
    chart_block = (
        "\n[다음 차트들이 본문 첫 H2 직후에 자동 삽입됩니다. "
        "본문에서 반드시 자연스럽게 인용하세요. "
        "예: '아래 가격 차트에서 2022년 -25% 빠진 적이 있다.']\n"
        + "\n".join(chart_lines)
    )

    def _build_prompt(retry_issues=None):
        retry_block = ""
        if retry_issues:
            retry_block = (
                "\n[이전 응답이 다음 검증을 통과하지 못함. 반드시 수정:]\n"
                + "\n".join(f"  - {x}" for x in retry_issues)
            )
        return f"""You are an investment data analyst with 10 years of index fund experience.
Write a data-driven analysis blog post for {ticker}. Output language: {lp["output_lang"]}.

[Real Market Data — USE THESE EXACT NUMBERS, do NOT invent different ones]
{mkt_text}

[AI Multi-Agent Analysis Results]
Ticker: {ticker}
Final Signal: {final_action} ({signal_label})
Analysis Date: {analysis_date}

Agent Signals:
{signals_text}

Recent News:
{news_text}
{chart_block}{retry_block}

[Title]
{lp["title_hint"].replace("{ticker}", ticker)}

[Writing Style — Kim Dante style: data-driven, evidence-based]
- Every claim backed by a number from market data above
- Use exact % figures provided — never make up different ones
- Include at least one HTML comparison table. You can choose between:
  - Template A (Performance Focus): Product Name | Fee | Yield | 5Y Return | 1Y Return
  - Template B (Valuation Focus): Product Name | Fee | Yield | P/E Ratio | Market Cap
  - Use <table><thead>...</thead><tbody>...</tbody></table> format for either template.
- Be honest about what could make this analysis WRONG (risks/disconfirming evidence)
- Reference the auto-inserted charts naturally (e.g. "아래 낙폭 차트를 보면 5년 최대 -34%")
- NEVER use: {lw["forbidden"]}
- Conclusion format: "데이터상 X가 유리하지만, Y를 고려하면 Z" (or equivalent in output lang)
- Minimum 5000 characters (Korean) / 3500 (other languages)

[규제 준수 — 매우 중요]
- 절대 사용 금지: "매수하세요", "사야 한다", "추천", "투자 권유", "신호", "Buy", "Sell"
- 대신 사용: "데이터 패턴", "흐름", "백테스트 결과", "통계상", "과거 추이로는"
- AI 분석 결과는 "에이전트 데이터 분석" 또는 "AI 데이터 검토"로 표현 (신호 단어 회피)
- 본문 첫 문단에 "본 글은 데이터 분석 정보이며 투자 자문/권유가 아닙니다"를 자연스럽게 녹여 넣기
- 결론에서도 "데이터로 보면 X 패턴" 형식 (사라/팔라 단언 금지)

[Content Structure]
1. Return ONLY pure JSON. No markdown code blocks.
2. Body: HTML format
3. H2 sections: 핵심 지표 요약 → AI 에이전트 분석 → 차트로 보는 패턴 → 리스크 요인 → 결론 → FAQ
4. Intro summary box: <div class="summary-box"><ul><li>...</li></ul></div> with actual numbers
5. One HTML <table> comparing {ticker} with peer ETF
6. Disclaimer: <p class="disclaimer">본 분석은 AI가 생성한 정보로 투자 권고가 아닙니다.</p>
7. FAQ: <h2>{lp["faq_label"]}</h2> — 5 real-search questions about {ticker}
8. Meta description: under 160 chars, include {ticker}, signal, and a key metric

[Output format - pure JSON only]
{{"title": "...", "content_html": "...", "meta_description": "...", "tags": ["tag1"], "primary_keyword": "{ticker}", "keywords_long_tail": ["..."], "schema_faq": [{{"question": "Q?", "answer": "A"}}], "content_type": "analysis"}}
"""

    raw = _call_llm(_build_prompt())
    result = _parse_json_response(raw, "analysis_post")

    # 2단계 검증 (규칙 + Gemini) — 최대 2회 재시도
    from auto_publisher.content_verifier import verify_two_stage

    verif_source = {ticker: mkt} if mkt else {}

    result.setdefault("primary_keyword", ticker)
    best = result
    best_verif = verify_two_stage(
        best, verif_source, lang, min_len=MIN_LEN.get(lang, 3000)
    )
    best_ok = best_verif["ok"]

    for attempt in range(2):
        if best_ok:
            break
        retry_reason = best_verif.get("retry_prompt", "")
        logger.warning(f"분석 포스트 검증 실패 재시도 {attempt + 1}/2: {retry_reason}")
        try:
            issues_for_prompt = best_verif.get("stage1_issues", [])[:5]
            s2 = best_verif.get("stage2_report", {})
            for k in ("hallucination", "bad_phrasing", "contradiction"):
                issues_for_prompt.extend([f"{k}: {x}" for x in s2.get(k, [])[:2]])
            raw_r = _call_llm(
                _build_prompt(retry_issues=issues_for_prompt or [retry_reason])
            )
            result_r = _parse_json_response(raw_r, f"analysis_post_retry_{attempt + 1}")
            result_r.setdefault("primary_keyword", ticker)
            verif_r = verify_two_stage(
                result_r, verif_source, lang, min_len=MIN_LEN.get(lang, 3000)
            )
            if verif_r["ok"] or len(result_r.get("content_html", "")) > len(
                best.get("content_html", "")
            ):
                best = result_r
                best_verif = verif_r
                best_ok = verif_r["ok"]
                if verif_r["ok"]:
                    logger.info(f"분석 재시도 {attempt + 1} 성공 — 2단계 검증 통과")
        except Exception as e:
            logger.warning(f"분석 재시도 {attempt + 1} 실패: {e}")

    critical_min = MIN_LEN.get(lang, 3000) // 2
    if len(best.get("content_html", "")) < critical_min:
        raise RuntimeError(
            f"분석 포스트 치명적 품질 미달: {len(best.get('content_html', ''))} < {critical_min}"
        )
    result = best

    # 상단 규제 배너 + 저자 바이오 + 면책 조항
    html = result.get("content_html", "")
    top_banner = (
        '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
        'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
        "<strong>⚠️ 정보 제공용 데이터 분석</strong><br>"
        "본 글은 yfinance 공개 데이터와 AI 멀티에이전트 분석을 정리한 정보 콘텐츠입니다. "
        "특정 종목의 매수·매도를 권유하지 않으며 투자 자문이 아닙니다. "
        "모든 투자 결정과 손익은 본인 책임입니다."
        "</div>\n"
    )
    if 'class="reg-banner"' not in html:
        html = top_banner + html
    result["content_html"] = _inject_disclaimer(html, lang)

    result.setdefault("content_type", "analysis")
    result.setdefault(
        "keywords_long_tail", [ticker, f"{ticker} 분석", f"{ticker} {signal_label}"]
    )
    result.setdefault("schema_faq", [])

    return result


def translate_post(source_post: dict, source_lang: str, target_lang: str) -> dict:
    """
    원본 포스트(source_lang)를 target_lang으로 번역 + 페르소나 현지화.
    저자, 통화, 절세계좌, 증권사 모두 target_lang 페르소나로 교체.
    """
    target_persona = _load_persona(target_lang)
    target_brief = _persona_brief(target_persona) if target_persona else ""
    target_lp = LANG_PROMPTS.get(target_lang, LANG_PROMPTS["en"])

    src_title = source_post.get("title", "")
    src_html = source_post.get("content_html", "")

    # 면책/저자 바이오는 번역 시 제외 (target에서 다시 주입됨)
    import re as _re

    src_html = _re.sub(
        r'<aside class="author-bio".*?</aside>', "", src_html, flags=_re.DOTALL
    )
    src_html = _re.sub(
        r'<div class="disclaimer".*?</div>', "", src_html, flags=_re.DOTALL
    )

    prompt = f"""You are {target_lp["persona"]}.

{target_brief}

You are translating and LOCALIZING the following blog post from {source_lang} to {target_lp["output_lang"]}.

[Critical: localization rules]
- Replace ALL persona-specific details (name, age, broker, portfolio, currency, tax accounts) with YOUR fixed profile above
- Convert numbers/currency to the target market's local equivalent (e.g., KRW → USD/JPY/VND/IDR)
- Replace Korean ETFs with equivalent target-market ETFs (KODEX → SPY for en, eMAXIS Slim for ja)
- Keep the core argument, tables, and chart references intact
- Do NOT translate literally — adapt for cultural context
- NEVER use: {target_lp["forbidden"]}
- OUTPUT LANGUAGE ENFORCEMENT: Every single character of the output (title, body, tags, keywords, descriptions, image alt text) MUST be in {target_lp["output_lang"]} only. Zero Korean (한글) characters allowed anywhere in the output.

[Source title]
{src_title}

[Source HTML]
{src_html}

[Output format - pure JSON only]
{{"title": "translated localized title", "content_html": "translated localized HTML body", "meta_description": "localized meta", "tags": ["..."], "primary_keyword": "...", "keywords_long_tail": ["..."], "schema_faq": [{{"question": "?", "answer": "..."}}], "content_type": "guide"}}
"""

    raw = _call_llm(prompt)
    result = _parse_json_response(raw, "translate_post")

    # 품질 게이트
    result.setdefault("primary_keyword", source_post.get("primary_keyword", ""))
    result["title"] = _ensure_primary_keyword_in_title(
        result.get("title", ""), result.get("primary_keyword", "")
    )
    ok, issues = _validate_post(result, target_lang)
    if not ok:
        logger.warning(f"번역 품질 게이트 실패 ({target_lang}): {issues}")

    # 한글 오염 감지
    import re as _re
    _korean = _re.compile(r"[\uAC00-\uD7A3]")
    if _korean.search(result.get("title", "")) or _korean.search(result.get("content_html", "")[:500]):
        logger.warning(f"[translate_post] {target_lang} 결과에 한글 감지 — 프롬프트 강화 필요")

    # 언어별 카테고리 주입
    result.setdefault("categories", CATEGORIES_BY_LANG.get(target_lang, ["Investing", "Personal Finance"]))

    # 면책 + 저자 바이오 자동 삽입
    result["content_html"] = _inject_disclaimer(
        result.get("content_html", ""), target_lang
    )
    result.setdefault("content_type", source_post.get("content_type", "guide"))
    result.setdefault("keywords_long_tail", [])
    result.setdefault("schema_faq", [])
    return result


def _normalize_keyword_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9가-힣一-龥ぁ-んァ-ン]", "", text.lower())


def _ensure_primary_keyword_in_title(title: str, primary_keyword: str) -> str:
    if not title or not primary_keyword:
        return title

    normalized_title = _normalize_keyword_for_match(title)
    normalized_keyword = _normalize_keyword_for_match(primary_keyword)
    if normalized_keyword and normalized_keyword in normalized_title:
        return title

    merged = f"{title} | {primary_keyword}".strip()
    return merged[:70].rstrip(" |")


def generate_sns_post(topic: str, platform: str) -> dict:
    """
    SNS 포스트 생성 (Phase 2)

    Returns:
        {text, hashtags}
    """
    char_limits = {
        "twitter": 280,
        "instagram": 2200,
    }
    limit = char_limits.get(platform, 280)

    prompt = f"""당신은 한국 {CONTENT_NICHE} 분야의 SNS 인플루언서입니다.
아래 주제로 {platform} 게시물을 작성해주세요.

주제: {topic}

[작성 규칙]
1. 순수 JSON만 반환하세요. 마크다운 코드블록(```)이나 다른 텍스트 없이 JSON만 출력하세요.
2. 본문은 {limit}자 이내
3. 한국어로 작성, 자연스러운 구어체
4. 이모지 적절히 활용
5. CTA(행동 유도) 포함
6. 관련 해시태그 5~10개

[출력 형식 - 순수 JSON]
{{"text": "게시물 본문", "hashtags": ["#해시태그1", "#해시태그2"]}}
"""

    raw = _call_llm(prompt)
    return _parse_json_response(raw, "sns_post")


def generate_short_script(topic: str) -> dict:
    """
    숏폼 영상 스크립트 생성 (Phase 3)

    Returns:
        {script, title, description}
    """
    prompt = f"""당신은 한국 {CONTENT_NICHE} 분야의 유튜브 크리에이터입니다.
아래 주제로 60초 숏폼 영상 스크립트를 작성해주세요.

주제: {topic}

[작성 규칙]
1. 순수 JSON만 반환하세요. 마크다운 코드블록(```)이나 다른 텍스트 없이 JSON만 출력하세요.
2. 스크립트는 60초 분량 (약 300자)
3. 후킹 → 핵심 정보 → CTA 구조
4. 자연스러운 구어체 한국어
5. 영상 제목은 호기심 유발형
6. 설명문은 200자 이내, 키워드 포함

[출력 형식 - 순수 JSON]
{{"script": "스크립트 전문", "title": "영상 제목", "description": "영상 설명"}}
"""

    raw = _call_llm(prompt)
    return _parse_json_response(raw, "short_script")


def _parse_json_response(raw: str, context: str) -> dict:
    """codex 응답에서 JSON 파싱 (헤더 및 코드블록 제거 포함)"""
    text = raw.strip()
    text = _strip_thinking_output(text)

    # 마크다운 코드블록 제거
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 중괄호 범위 추출 시도 (codex 헤더 제거)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패 ({context}): {e}\n원본 응답:\n{raw[:500]}")

    raise ValueError(f"codex 응답을 JSON으로 파싱할 수 없습니다 ({context})")


def _strip_thinking_output(text: str) -> str:
    """Remove thinking/reasoning wrappers before JSON parsing."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    markers = (
        "Final Answer:",
        "Final:",
        "최종 답변:",
        "최종:",
    )
    for marker in markers:
        idx = text.rfind(marker)
        if idx >= 0:
            text = text[idx + len(marker):].strip()
    return text


# ═══════════════════════════════════════════════════════════════════════════
# Markdown 후처리 — HTML 블록 뒤 빈 줄 + 중첩 <a> 평탄화
# ═══════════════════════════════════════════════════════════════════════════

# Goldmark(Hugo)는 HTML 블록 다음 줄에 빈 줄이 없으면 이어지는 마크다운 파싱을 건너뛴다.
# content_generator 가 출력하는 <div>, <table>, <figure>, <ul>, <ol>, <p> 등 블록 요소 뒤에
# 반드시 \n\n 을 삽입해서 후속 마크다운(## 헤더, 문단, 리스트) 이 정상 렌더되도록 한다.
_BLOCK_CLOSE_TAGS = (
    "div",
    "table",
    "figure",
    "ul",
    "ol",
    "blockquote",
    "pre",
    "section",
    "article",
    "header",
    "footer",
    "aside",
    "nav",
    "details",
    "dl",
)


def fix_html_block_spacing(text: str) -> str:
    """HTML 블록 태그 뒤 빈 줄 강제 + 중첩 <a> 평탄화.

    Idempotent: 이미 빈 줄이 있으면 변경하지 않는다.
    """
    import re

    for tag in _BLOCK_CLOSE_TAGS:
        # </tag> 바로 다음에 한 개의 줄바꿈 + 비어있지 않은 라인이 오면 \n\n 로 바꾼다.
        # 이미 \n\n 이거나 파일 끝이면 건드리지 않는다.
        pattern = re.compile(
            rf"(</{tag}>)\n(?!\n|$)",
            re.IGNORECASE,
        )
        text = pattern.sub(r"\1\n\n", text)

    # 중첩된 <a> 평탄화: <a ...><a ...>TEXT</a></a> → <a ...>TEXT</a>
    # 외부 앵커만 남기고 내부 앵커는 텍스트만 보존.
    nested_pattern = re.compile(
        r"<a(\s+[^>]*)?>\s*<a(\s+[^>]*)?>(.*?)</a>\s*</a>",
        re.IGNORECASE | re.DOTALL,
    )
    # 반복 적용: 3중첩도 가능하므로 더 이상 매치가 없을 때까지
    prev = None
    while prev != text:
        prev = text
        text = nested_pattern.sub(r"<a\1>\3</a>", text)

    return text


# ═══════════════════════════════════════════════════════════════════════════
# E-E-A-T Front Matter 빌더 (YMYL/검색 신뢰도 강화)
# ═══════════════════════════════════════════════════════════════════════════

_EEAT_BASE_URL = "https://investiqs.net"
_EEAT_DEFAULT_AUTHOR = "InvestIQs 편집팀"
_EEAT_DEFAULT_REVIEWER = "편집자 미검토 — AI 자동 발행"
_EEAT_DEFAULT_VERIFIED_BY = "자동화 규칙 검증 시스템 v2.1"
_CONFIDENCE_LEVELS = {"low", "medium", "high", "very_high"}
_EEAT_DEFAULT_DISCLAIMER = (
    "본 글은 정보 제공 목적이며, 투자 결정은 본인 책임입니다. "
    "과거 수익률이 미래 수익을 보장하지 않습니다."
)

# 한글 → 로마자 간이 변환 (외부 의존성 없는 초성+중성+종성 테이블)
_HANGUL_CHO = [
    "g",
    "kk",
    "n",
    "d",
    "tt",
    "r",
    "m",
    "b",
    "pp",
    "s",
    "ss",
    "",
    "j",
    "jj",
    "ch",
    "k",
    "t",
    "p",
    "h",
]
_HANGUL_JUNG = [
    "a",
    "ae",
    "ya",
    "yae",
    "eo",
    "e",
    "yeo",
    "ye",
    "o",
    "wa",
    "wae",
    "oe",
    "yo",
    "u",
    "wo",
    "we",
    "wi",
    "yu",
    "eu",
    "ui",
    "i",
]
_HANGUL_JONG = [
    "",
    "g",
    "kk",
    "gs",
    "n",
    "nj",
    "nh",
    "d",
    "l",
    "lg",
    "lm",
    "lb",
    "ls",
    "lt",
    "lp",
    "lh",
    "m",
    "b",
    "bs",
    "s",
    "ss",
    "ng",
    "j",
    "ch",
    "k",
    "t",
    "p",
    "h",
]


def _romanize_korean(text: str) -> str:
    """한글을 간이 로마자로 변환 (완벽한 표준은 아니지만 URL용으로 충분)."""
    out = []
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            idx = code - 0xAC00
            cho = idx // 588
            jung = (idx % 588) // 28
            jong = idx % 28
            out.append(_HANGUL_CHO[cho] + _HANGUL_JUNG[jung] + _HANGUL_JONG[jong])
        else:
            out.append(ch)
    return "".join(out)


def make_eeat_slug(title: str) -> str:
    """제목을 영문/숫자/하이픈만 포함하는 URL-safe slug로 변환.

    한글은 로마자로 치환. 공백/언더스코어는 하이픈으로. 중복 하이픈 제거.
    """
    import re

    if not title:
        return "untitled"
    romanized = _romanize_korean(title)
    lowered = romanized.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "untitled"


def _default_eeat_faq(title: str, primary_keyword: str = "") -> list:
    """E-E-A-T 기본 FAQ 3종 자동 생성 (키워드 반영)."""
    keyword = primary_keyword or title
    return [
        {
            "q": f"{keyword}이란 무엇인가요?",
            "a": f"{keyword}의 정의와 주요 특징을 본문에서 자세히 설명합니다.",
        },
        {
            "q": f"{keyword}을(를) 처음 시작하려면 어떻게 해야 하나요?",
            "a": "본문의 단계별 가이드를 참고하여 계좌 개설부터 실행까지 진행하세요.",
        },
        {
            "q": f"{keyword} 관련 세금이나 수수료는 어떻게 되나요?",
            "a": "본문의 세금·수수료 섹션에서 구체적인 수치와 사례를 확인할 수 있습니다.",
        },
    ]


def build_eeat_frontmatter(
    title: str,
    slug: str,
    lang: str = "ko",
    meta_description: str = "",
    tags: list = None,
    categories: list = None,
    primary_keyword: str = "",
    author: str = None,
    author_bio: str = None,
    reviewed_by: str = None,
    verified_by: str = None,
    faq: list = None,
    disclaimer: str = None,
    date: str = None,
    lastmod: str = None,
    data_fetched_at: str = None,
    data_source: str = "yfinance (공개 데이터, 최대 15분 지연)",
    ai_generated: bool = True,
    ai_models: str = "Claude/Gemini",
    analysis_confidence: str = "medium",
    confidence_note: str = "",
) -> str:
    """Hugo front matter YAML 문자열을 생성. E-E-A-T 필드 전부 주입.

    Returns:
        "---\n...YAML...\n---" 형식 문자열 (yaml.safe_load 가능)
    """
    from datetime import datetime, timezone

    if analysis_confidence not in _CONFIDENCE_LEVELS:
        raise ValueError(
            f"analysis_confidence must be one of {_CONFIDENCE_LEVELS}, got '{analysis_confidence}'"
        )

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    canonical = f"{_EEAT_BASE_URL}/{lang}/blog/{slug}/"

    fm = {
        "title": title,
        "slug": slug,
        "date": date or now_iso,
        "lastmod": lastmod or now_iso,
        "draft": False,
        "author": author or _EEAT_DEFAULT_AUTHOR,
        "authorBio": author_bio
        or "투자/재테크 전문 에디터 팀. 공시 자료와 실데이터를 기반으로 분석합니다.",
        "reviewedBy": reviewed_by or _EEAT_DEFAULT_REVIEWER,
        "verifiedBy": verified_by or _EEAT_DEFAULT_VERIFIED_BY,
        "description": meta_description or f"{title} — 실데이터 기반 투자 정보",
        "canonicalURL": canonical,
        "tags": tags or [],
        "categories": categories or [],
        "keywords": [primary_keyword] if primary_keyword else (tags or []),
        "faq": faq if faq is not None else _default_eeat_faq(title, primary_keyword),
        "disclaimer": disclaimer or _EEAT_DEFAULT_DISCLAIMER,
        "lang": lang,
        "ai_generated": ai_generated,
        "ai_models": ai_models,
        "data_fetched_at": data_fetched_at or now_iso,
        "data_source": data_source,
        "analysis_confidence": analysis_confidence,
        "confidence_note": confidence_note,
    }

    try:
        import yaml

        yaml_body = yaml.safe_dump(
            fm, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
    except ImportError:
        lines = []
        for k, v in fm.items():
            if isinstance(v, (list, dict)):
                lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
            elif isinstance(v, bool):
                lines.append(f"{k}: {'true' if v else 'false'}")
            else:
                lines.append(f"{k}: {json.dumps(str(v), ensure_ascii=False)}")
        yaml_body = "\n".join(lines) + "\n"

    return f"---\n{yaml_body}---\n"
