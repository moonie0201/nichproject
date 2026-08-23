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
import re


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

# 카테고리별로 보낼 계산기. 개별 글은 사라질 수 있지만 계산기는 항상 살아 있다.
# 2026-08 실측: 쇼츠 설명문의 블로그 링크 7개 중 5개가 404 였다 (애드센스 심사용
# 축소로 /ko/daily/ 와 /en/ 이 내려가면서). 쇼츠가 유일하게 트래픽이 나오는
# 자산인데(편당 1,716회) 사이트로 오는 통로가 끊겨 있었다.
_CATEGORY_TOOL = {
    "tax":          ("pension-tax-credit",   "연금저축·IRP 세액공제 계산기"),
    "dividend":     ("portfolio-income",     "포트폴리오 인컴 계산기"),
    "etf-analysis": ("etf-fee-calculator",   "ETF 수수료 비교 계산기"),
    "market-wrap":  ("portfolio-rebalance",  "포트폴리오 리밸런싱 계산기"),
    "intraday":     ("portfolio-rebalance",  "포트폴리오 리밸런싱 계산기"),
    "weekly":       ("portfolio-rebalance",  "포트폴리오 리밸런싱 계산기"),
    "crypto":       ("dca-calculator",       "적립식 투자 계산기"),
    "default":      ("dca-calculator",       "적립식 투자 계산기"),
}
_SITE = os.getenv("SITE_BASE_URL", "https://investiqs.net").rstrip("/")


def _is_enabled(env: str, default: bool = True) -> bool:
    val = os.getenv(env, "true" if default else "false").lower()
    return val not in ("false", "0", "no")


def _tool_link(category: str, lang: str = "ko") -> tuple[str, str]:
    slug, label = _CATEGORY_TOOL.get(category, _CATEGORY_TOOL["default"])
    return f"{_SITE}/{lang}/tools/{slug}/", label


_LONGFORM_URL = re.compile(r'https?://(?:www\.|m\.)?(?:youtube\.com|youtu\.be)/\S+')
_LEAD = r'(?:본편 영상|전체 영상|전체 분석|무료 확인|자세히 보기)'
# 유도 문구 + URL 을 한 덩어리로 잡는다. 문구와 화살표는 양쪽 순서가 다 나타난다
# ("무료 확인 👉 https://...", "👉 전체 영상 https://...").
_LEAD_THEN_URL = re.compile(
    rf'[ \t]*[-—·|]?[ \t]*(?:{_LEAD}\s*:?\s*(?:👉|▶|➡)?|(?:👉|▶|➡)\s*(?:{_LEAD})?\s*:?)\s*'
    r'https?://(?:www\.|m\.)?(?:youtube\.com|youtu\.be)/\S+')


def _strip_longform_links(text: str) -> str:
    """본문에서 롱폼 유튜브 링크와, 그 링크를 가리키던 유도 문구를 걷어낸다.

    유도 문구 정리는 URL 이 실제로 지워진 자리에만 적용한다. 문서 전체에
    돌리면 링크가 없는 정상 문장까지 잘린다 — "이번 글의 핵심은 전체 분석"
    이 "이번 글의 핵심은" 이 됐다(Codex 리뷰 2차 지적).
    """
    def cut(m: "re.Match") -> str:
        # URL 앞의 유도 문구까지 한 번에 지운다. 매칭 범위가 URL 주변으로 한정된다.
        return ""

    out = re.sub(_LEAD_THEN_URL, cut, text or "")
    out = _LONGFORM_URL.sub("", out)          # 유도 문구 없이 링크만 있는 경우
    out = re.sub(r'[ \t]+$', '', out, flags=re.M)
    return re.sub(r'\n{3,}', '\n\n', out).rstrip()


def _url_alive(url: str, timeout: int = 5) -> bool:
    """설명문에 넣기 전에 목적지가 살아 있는지 확인한다.

    애드센스 심사용 축소로 /ko/daily/ 와 /en/ 이 내려가면서, 이미 올라간 쇼츠의
    블로그 링크 7개 중 5개가 404 가 됐다. 발행 시점에 존재하던 URL 이라도
    나중에 죽을 수 있으므로 업로드 직전에 한 번 확인한다.
    확인 실패(네트워크 오류 등)는 '살아 있음'으로 본다 — 검증 때문에 링크를
    빠뜨리는 쪽이 더 손해다.
    """
    if os.getenv("SHORTS_VERIFY_LINKS", "1") != "1":
        return True
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, method="HEAD",
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 400
    except urllib.error.HTTPError as e:
        # 404/410 만 '없는 페이지'로 확정한다. 403/405 는 HEAD 를 막는 서버일 뿐
        # 실제로는 살아 있을 수 있어, 링크를 잘못 빼는 쪽이 손해다.
        return e.code not in (404, 410)
    except Exception:
        return True


def enrich_shorts_description(base: str, blog_url: str, category: str,
                              lang: str = "ko") -> str:
    """원본 description 에 CTA + funnel + affiliate + hashtags 추가.

    이미 enrich 된 결과를 다시 호출해도 중복 추가 안 함 (idempotent).

    순서가 중요하다. 예전에는 롱폼 링크 → 블로그 링크 → 구독 CTA 순이라
    구독 유도가 맨 아래 묻혀 있었다. 쇼츠 설명문은 접혀 있어서 앞 두세 줄만
    보이므로, 실측 전환율 0.011%(8.4만 조회 / 구독 9명)의 원인이 된다.
    구독을 맨 위로 올린다.
    """
    if not _is_enabled("SHORTS_CTA_ENABLED", default=True):
        return base

    # LLM 이 만든 본문에도 롱폼 유튜브 링크가 섞여 들어온다(video_script 프롬프트가 요구).
    # 롱폼은 실측 조회수 0~2회라 죽은 목적지이므로 여기서 걷어낸다.
    # 줄 단위로 지우면 안 된다 — 링크가 문장 끝에 붙어 있어 본문까지 날아간다.
    base = _strip_longform_links(base)

    parts = [base.rstrip()]
    seen = base

    def add(line: str) -> None:
        if line and line not in seen:
            parts.append(line)

    # 1) 구독 — 접히기 전에 보여야 한다
    parts.append("")
    for line in _CTA_LINES:
        add(line)

    # 2) 계산기 — 개별 글과 달리 항상 살아 있는 목적지
    tool_url, tool_label = _tool_link(category, lang)
    add(f"🧮 {tool_label}: {tool_url}")

    # 3) 원본 글 — 살아 있을 때만. 롱폼 유튜브 링크는 넣지 않는다.
    #    롱폼은 실측 조회수 0~2회라 보내봐야 죽은 목적지다(143 쇼츠 8.3만 vs 120 롱폼 300).
    #    youtube.com 만 걸러 youtu.be 단축 링크가 새어 나갔다(Codex 리뷰 2차 지적).
    if blog_url and not _LONGFORM_URL.match(blog_url.strip()) and _url_alive(blog_url):
        add(f"📊 자세한 분석: {blog_url}")

    # affiliate (옵트인)
    if _is_enabled("SHORTS_AFFILIATE_ENABLED", default=False):
        affiliate_url = os.getenv("SHORTS_AFFILIATE_URL", "").strip()
        add(f"💰 추천 도서 (쿠팡 파트너스 제휴): {affiliate_url}" if affiliate_url else "")

    # 해시태그
    tags = _CATEGORY_HASHTAGS.get(category, _CATEGORY_HASHTAGS["default"])
    new_tags = [t for t in tags if t not in seen]
    if new_tags:
        parts.append(" ".join(new_tags))

    return "\n".join(parts)
