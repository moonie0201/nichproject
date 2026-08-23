"""
컴플라이언스 필터 및 면책 자동 주입
"""

import os
import re
from functools import lru_cache
from auto_publisher.config import FORBIDDEN_PHRASES

# 국내 개별 종목 차단 (2026-08-08 도입, 2026-08-21 범위 축소).
# 판정 로직의 단일 출처다.
#
# 자본시장법이 규제하는 것은 '특정 종목'의 매매 권유다. 따라서 차단 대상은
# 국내 개별 종목뿐이며, 아래 둘은 차단하지 않는다:
#   - 지수(코스피/코스닥/KOSPI/KOSDAQ/^KS11): 특정 종목이 아니라 시장 서술이다.
#     이걸 막으면 "미국장 마감 후 아시아 증시가 열린다" 같은 일반 서술조차 못 한다.
#   - 국내 상장 ETF(KODEX/TIGER 등): 분산 상품이라 개별 종목 권유에 해당하지 않는다.
#
# 한글 종목명 — 대소문자 개념이 없다.
_DOMESTIC_KO = re.compile(
    # 시총 상위 종목은 시황 글에 자연스럽게 섞여 들어오므로 빠짐없이 열거한다.
    r"삼성전자|삼성SDI|삼성바이오로직스|삼성물산"
    r"|LG이노텍|LG전자|LG화학|LG에너지솔루션"
    r"|SK하이닉스|SK이노베이션|현대차|현대모비스|기아차"
    r"|셀트리온|포스코|한화에어로스페이스|HD현대"
    r"|네이버\s*주가|카카오\s*주가"
)
# 라틴 표기는 대소문자를 구분한다.
_DOMESTIC_LATIN = re.compile(
    r"\bPOSCO\b|\bNAVER\b|\b(?P<code>\d{6})\.K[SQ]\b"
)


@lru_cache(maxsize=1)
def _kr_etf_codes() -> frozenset[str]:
    """국내 ETF 종목코드 허용 목록.

    ETF 와 개별 종목은 같은 6자리 체계를 써서 정규식만으로는 구분이 안 된다.
    "ETF 는 허용" 이라고 문서에 써놓고 069500.KS(KODEX 200) 를 차단하고 있었다 —
    데이터 수집 경로(_fetch_korean_etf_data)가 실제로 .KS 티커를 만들어
    본문에 넣으므로, 정상 ETF 글이 발행 단계에서 ValueError 로 죽었다
    (Codex 리뷰 2차 지적).

    목록은 content_generator.KOREAN_ETF_CODES 단일 출처를 그대로 쓴다.
    순환 import 를 피하려고 호출 시점에 가져온다.
    """
    try:
        from auto_publisher.content_generator import KOREAN_ETF_CODES
        return frozenset(KOREAN_ETF_CODES.values())
    except Exception:
        return frozenset()

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
    """국내 개별 종목 언급이 있으면 매칭 문자열을, 없으면 None을 반환.

    지수와 국내 상장 ETF 는 대상이 아니다. 위 정규식 주석 참조.
    """
    text = text or ""
    if m := _DOMESTIC_KO.search(text):
        return m.group(0)
    for m in _DOMESTIC_LATIN.finditer(text):
        if m.group("code") and m.group("code") in _kr_etf_codes():
            continue  # 허용 목록에 있는 국내 ETF
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


def find_forbidden_phrases(text: str, lang: str) -> list[str]:
    """금칙어가 있으면 목록을 돌려준다. 지우지 않는다.

    예전에는 `text.replace(phrase, "")` 로 통째로 삭제했는데, 한국어는 조사가
    남아 문장이 무너졌다:
        "연말정산 완벽 가이드를 다음과 같이 정리했습니다."
        → "연말정산 를  정리했습니다."
    역설적으로 이 처리가 글을 더 "AI 티 나게" 만들어 애드센스가 잡는 신호를
    스스로 키웠다. 게다가 content_verifier 가 이미 같은 금칙어를 검사해
    재생성을 트리거하므로, 삭제는 이득 없이 손상만 남기는 단계였다.

    탐지 결과는 검증 계층이 재생성 프롬프트로 넘긴다.
    """
    text = text or ""
    return [p for p in FORBIDDEN_PHRASES.get(lang, [])
            if _phrase_pattern(p).search(text)]


@lru_cache(maxsize=256)
def _phrase_pattern(phrase: str) -> "re.Pattern":
    """금칙어를 단어 경계에 붙여 컴파일한다.

    부분문자열로 검사하면 정상 한국어가 걸린다 — "문제가"/"경제가" 안에 "제가",
    "국내가" 안에 "내가" 가 들어 있다. 이대로 검증에 연결하면 멀쩡한 글이
    재생성 루프를 돈다.

    한국어는 \b 가 안 통한다(공백으로 단어를 안 끊음). 충돌은 전부 앞쪽에서
    난다 — "경제가"의 뒤 두 글자가 "제가"다. 그래서 앞만 막는다.
    뒤는 열어둬야 한다: 금칙어에 조사·어미가 붙는 게 정상이라
    ("완벽 가이드입니다", "총정리하면") 뒤까지 막으면 이번엔 놓친다.
    """
    if re.search(r"[가-힣]", phrase):
        return re.compile(rf"(?<![가-힣]){re.escape(phrase)}")
    return re.compile(rf"\b{re.escape(phrase)}\b", re.I)


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
    # 금칙어는 여기서 지우지 않는다. content_verifier 가 검사해 재생성을 트리거한다.
    # (삭제하면 조사가 남아 문장이 무너진다 — find_forbidden_phrases 주석 참조)
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
