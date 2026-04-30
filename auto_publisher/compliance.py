"""
컴플라이언스 필터 및 면책 자동 주입
"""

import re
from auto_publisher.config import FORBIDDEN_PHRASES

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
    """출처 개수 확인 (대략적인 인용구 패턴 [숫자] 검색)"""
    citations = re.findall(r"\[\d+\]", html)
    return len(set(citations))


def apply_compliance(html: str, lang: str) -> str:
    """전체 컴플라이언스 적용"""
    html = filter_forbidden_phrases(html, lang)
    html = inject_disclaimer(html, lang)

    # 3개 이상 출처 검사 (경고 로깅)
    source_count = count_sources(html)
    if source_count < 3:
        print(
            f"WARNING: 출처가 3개 미만입니다 (현재: {source_count}개). 컴플라이언스 가이드라인을 준수해주세요."
        )

    return html
