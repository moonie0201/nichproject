"""쇼츠 description 보강 — CTA + 롱폼 funnel + affiliate.

목적:
- 롱폼 블로그 링크 (RPM 5배 차이 → 시청자 유입)
- 쿠팡파트너스 affiliate (선택적)
- 구독/알림 CTA
- 카테고리별 해시태그

ENV 토글:
- SHORTS_CTA_ENABLED (default true)
- SHORTS_AFFILIATE_ENABLED (default false — 명시적으로 켜야 함)
- SHORTS_AFFILIATE_URL (예: https://link.coupang.com/a/XXX)
"""
from __future__ import annotations

import os


_CATEGORY_HASHTAGS = {
    "etf-analysis": ["#ETF", "#투자", "#운용보수", "#shorts"],
    "market-wrap": ["#미국증시", "#마감", "#주식", "#shorts"],
    "intraday": ["#장중", "#실시간", "#주식", "#shorts"],
    "weekly": ["#주간정리", "#증시", "#주식", "#shorts"],
    "crypto": ["#bitcoin", "#비트코인", "#crypto", "#암호화폐", "#shorts"],
    "tax": ["#세금", "#절세", "#재테크", "#shorts"],
    "dividend": ["#배당", "#배당주", "#투자", "#shorts"],
    "default": ["#투자", "#재테크", "#주식", "#shorts"],
}

_CTA_LINES = [
    "🔔 구독 + 알림 설정으로 매일 시장 분석 받아보세요",
]


def _is_enabled(env: str, default: bool = True) -> bool:
    val = os.getenv(env, "true" if default else "false").lower()
    return val not in ("false", "0", "no")


def enrich_shorts_description(base: str, blog_url: str, category: str) -> str:
    """원본 description 에 CTA + funnel + affiliate + hashtags 추가.

    이미 enrich 된 결과를 다시 호출해도 중복 추가 안 함 (idempotent).
    """
    if not _is_enabled("SHORTS_CTA_ENABLED", default=True):
        return base

    parts = [base.rstrip()]
    seen = base

    # 롱폼 블로그 링크 (funnel)
    if blog_url and blog_url not in seen:
        parts.append(f"\n📊 자세한 분석: {blog_url}")

    # affiliate (옵트인)
    if _is_enabled("SHORTS_AFFILIATE_ENABLED", default=False):
        affiliate_url = os.getenv("SHORTS_AFFILIATE_URL", "").strip()
        if affiliate_url and affiliate_url not in seen:
            parts.append(f"💰 추천 도서 (쿠팡 파트너스 제휴): {affiliate_url}")

    # CTA
    for line in _CTA_LINES:
        if line not in seen:
            parts.append(line)

    # 해시태그
    tags = _CATEGORY_HASHTAGS.get(category, _CATEGORY_HASHTAGS["default"])
    new_tags = [t for t in tags if t not in seen]
    if new_tags:
        parts.append(" ".join(new_tags))

    return "\n".join(parts)
