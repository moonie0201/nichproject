"""
컴플라이언스 필터 및 면책 자동 주입
"""

import os
import re
from auto_publisher.config import FORBIDDEN_PHRASES

# 미국 주식 전용 전환 (2026-08-08) — 국내 종목/지수/ETF 브랜드 차단.
# 국내 종목 콘텐츠를 발행하지 않는 것이 목적이며, 판정 로직의 단일 출처다.
# 한글 종목명 — 대소문자 개념이 없다.
_DOMESTIC_KO = re.compile(
    r"삼성전자|LG이노텍|SK하이닉스|현대차|기아차|네이버|카카오|셀트리온|포스코"
    r"|코스피|코스닥"
)
# 라틴 표기는 대소문자를 구분한다. 국내 ETF 브랜드는 항상 대문자라
# 'Tiger Global'(미국 헤지펀드), 'tiger woods' 같은 오탐을 피할 수 있다.
# ACE/SOL은 영어 약어·솔라나와 충돌해 제외한다.
_DOMESTIC_LATIN = re.compile(
    r"\bKOSPI\b|\bKOSDAQ\b|\bPOSCO\b"
    r"|\bKODEX\b|\bTIGER\b|\bKBSTAR\b|\bARIRANG\b|\bKINDEX\b"
    r"|\^KS11|\^KQ11|\b\d{6}\.K[SQ]\b"
)

# 자본시장법상 유사투자자문 리스크 — 개별 종목 매수·매도 권유로 읽히는 표현.
# 국내/해외 종목을 가리지 않고 적용된다.
SOLICITATION_PATTERNS = [
    (re.compile(r"절대적으로\s*그렇습니다"), "단정적 확언"),
    (re.compile(r"(지금|당장)\s*(매수|매도|사세요|파세요|사야|팔아야)"), "매매 시점 권유"),
    (re.compile(r"추천도\s*[★☆]{3,}"), "종목 별점 추천"),
    (re.compile(r"(반드시|무조건)\s*(오릅|수익|벌|사)"), "수익 보장성 단정"),
    (re.compile(r"강력\s*(추천|매수)"), "강한 매수 권유"),
    (re.compile(r"\b(must[- ]buy|strong buy|guaranteed returns?)\b", re.I), "영문 매수 권유"),
]


def contains_domestic_equity(text: str) -> str | None:
    """국내 종목/지수 언급이 있으면 매칭 문자열을, 없으면 None을 반환."""
    text = text or ""
    for pattern in (_DOMESTIC_KO, _DOMESTIC_LATIN):
        m = pattern.search(text)
        if m:
            return m.group(0)
    return None


def find_solicitation(text: str) -> list[str]:
    """투자권유로 읽힐 수 있는 표현 목록 반환 (라벨 + 실제 매칭)."""
    hits = []
    for pattern, label in SOLICITATION_PATTERNS:
        m = pattern.search(text or "")
        if m:
            hits.append(f"{label}: {m.group(0).strip()}")
    return hits

DISCLAIMER = {
    "ko": '<div class="disclaimer" style="font-size:0.85em;color:#666;border-top:1px solid #eee;padding-top:1em;margin-top:2em;">본 콘텐츠는 개인 경험과 공개 데이터를 바탕으로 한 정보 공유이며, 특정 금융상품의 매수·매도 권유가 아닙니다. 모든 투자 결정과 책임은 본인에게 있습니다. 본 서비스는 자본시장법상 유사투자자문업으로 신고되지 않은 사업자가 운영하며, 회원제·1:1 자문이 아닌 불특정 다수 정보 공유입니다.</div>',
    "en": '<div class="disclaimer" style="font-size:0.85em;color:#666;border-top:1px solid #eee;padding-top:1em;margin-top:2em;">This content is shared for informational purposes based on personal experience and public data. It is not investment advice or a recommendation to buy or sell any security. All decisions and risks are your own.</div>',
    "ja": '<div class="disclaimer" style="font-size:0.85em;color:#666;border-top:1px solid #eee;padding-top:1em;margin-top:2em;">本コンテンツは個人の経験と公開データに基づく情報提供であり、特定の金融商品の売買を推奨するものではありません。すべての投資判断と責任はご自身にあります。</div>',
    "vi": '<div class="disclaimer" style="font-size:0.85em;color:#666;border-top:1px solid #eee;padding-top:1em;margin-top:2em;">Nội dung này chia sẻ thông tin dựa trên kinh nghiệm cá nhân và dữ liệu công khai, không phải lời khuyên mua hoặc bán bất kỳ sản phẩm tài chính nào. Mọi quyết định và rủi ro thuộc về bạn.</div>',
    "id": '<div class="disclaimer" style="font-size:0.85em;color:#666;border-top:1px solid #eee;padding-top:1em;margin-top:2em;">Konten ini dibagikan untuk informasi berdasarkan pengalaman pribadi dan data publik, bukan saran investasi atau rekomendasi membeli/menjual produk keuangan. Semua keputusan dan risiko adalah milik Anda.</div>',
}


def filter_forbidden_phrases(text: str, lang: str) -> str:
    """금칙어 필터링"""
    for phrase in FORBIDDEN_PHRASES.get(lang, []):
        text = text.replace(phrase, "")
    return text


def inject_disclaimer(html: str, lang: str) -> str:
    """면책 조항 주입"""
    if 'class="disclaimer"' not in html:
        return html + "\n" + DISCLAIMER.get(lang, DISCLAIMER["en"])
    return html


def count_sources(html: str) -> int:
    """출처 개수 확인.

    본문은 [[출처명]](url) 형태의 마크다운 링크와 <a href> 를 함께 쓴다.
    이전에는 [숫자] 각주만 세어, 링크로만 인용한 글이 "출처 0개"로 오탐됐다.
    """
    sources = set()
    sources.update(re.findall(r"\[\d+\]", html or ""))
    # [[라벨]](http...) 및 [라벨](http...)
    sources.update(re.findall(r"\[\[?[^\]]+\]?\]\((https?://[^)]+)\)", html or ""))
    # <a href="http...">
    sources.update(re.findall(r'<a\s[^>]*href="(https?://[^"]+)"', html or "", re.I))
    return len(sources)


def apply_compliance(html: str, lang: str) -> str:
    """전체 컴플라이언스 적용.

    국내 종목 언급과 투자권유성 표현은 발행을 중단시킨다(기본값). 생성 파이프라인에
    재시도 루프가 있어, 차단 시 다른 토픽/재생성으로 넘어간다.
    끄려면 COMPLIANCE_HARD_BLOCK=0.
    """
    html = filter_forbidden_phrases(html, lang)
    html = inject_disclaimer(html, lang)

    hard_block = os.getenv("COMPLIANCE_HARD_BLOCK", "1") == "1"

    domestic = contains_domestic_equity(html)
    if domestic:
        msg = f"국내 종목 언급 감지: '{domestic}' — 미국 주식 전용 정책 위반"
        if hard_block:
            raise ValueError(msg)
        print(f"WARNING: {msg}")

    solicitations = find_solicitation(html)
    if solicitations:
        msg = "투자권유성 표현 감지: " + "; ".join(solicitations)
        if hard_block:
            raise ValueError(msg)
        print(f"WARNING: {msg}")

    # 3개 이상 출처 검사 (경고 로깅)
    source_count = count_sources(html)
    if source_count < 3:
        print(
            f"WARNING: 출처가 3개 미만입니다 (현재: {source_count}개). 컴플라이언스 가이드라인을 준수해주세요."
        )

    return html
