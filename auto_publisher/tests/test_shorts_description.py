"""쇼츠 description CTA + affiliate 보강 회귀 테스트.

목적: YouTube/TikTok 쇼츠 description 자동 보강
- 롱폼 블로그 링크 (RPM 5배 차이 활용)
- 쿠팡파트너스 affiliate (선택적)
- CTA (구독/알림)

ENV 토글:
- SHORTS_CTA_ENABLED (default true)
- SHORTS_AFFILIATE_ENABLED (default false, 명시적으로 켜야 함)
- SHORTS_AFFILIATE_URL (쿠팡파트너스 링크)
- SHORTS_BLOG_BASE_URL (롱폼 funnel 도메인)
"""
from __future__ import annotations
from unittest.mock import patch
import pytest


def test_enrich_adds_blog_link_when_url_provided(monkeypatch):
    """blog_url 주면 description 끝에 '자세한 분석' 라인 추가."""
    monkeypatch.setenv("SHORTS_CTA_ENABLED", "true")
    from auto_publisher.shorts_description import enrich_shorts_description
    out = enrich_shorts_description(
        base="ETF 운용보수 0.03% vs 0.5% 30년 복리 시뮬레이션",
        blog_url="https://investiqs.net/ko/study/etf-운용보수/",
        category="etf-analysis",
    )
    assert "investiqs.net" in out
    assert "ETF 운용보수" in out  # 원본 보존
    assert out.startswith("ETF 운용보수")  # 원본이 첫 줄


def test_enrich_adds_cta_phrases(monkeypatch):
    """SHORTS_CTA_ENABLED=true 이면 구독/알림 CTA 포함."""
    monkeypatch.setenv("SHORTS_CTA_ENABLED", "true")
    from auto_publisher.shorts_description import enrich_shorts_description
    out = enrich_shorts_description(base="설명", blog_url="", category="default")
    # 구독/팔로우/알림 중 하나는 들어있어야 함
    assert any(kw in out for kw in ("구독", "알림", "팔로우", "Follow", "Subscribe"))


def test_enrich_disabled_returns_base(monkeypatch):
    """SHORTS_CTA_ENABLED=false 면 원본 그대로 반환."""
    monkeypatch.setenv("SHORTS_CTA_ENABLED", "false")
    monkeypatch.setenv("SHORTS_AFFILIATE_ENABLED", "false")
    from auto_publisher.shorts_description import enrich_shorts_description
    base = "원본 설명"
    out = enrich_shorts_description(base=base, blog_url="https://x", category="any")
    assert out == base


def test_enrich_includes_affiliate_when_explicitly_enabled(monkeypatch):
    """SHORTS_AFFILIATE_ENABLED=true + URL 있으면 affiliate 줄 추가."""
    monkeypatch.setenv("SHORTS_CTA_ENABLED", "true")
    monkeypatch.setenv("SHORTS_AFFILIATE_ENABLED", "true")
    monkeypatch.setenv("SHORTS_AFFILIATE_URL", "https://link.coupang.com/a/test123")
    from auto_publisher.shorts_description import enrich_shorts_description
    out = enrich_shorts_description(base="설명", blog_url="", category="etf-analysis")
    assert "coupang" in out.lower() or "쿠팡" in out
    assert "test123" in out


def test_enrich_skips_affiliate_when_disabled(monkeypatch):
    """SHORTS_AFFILIATE_ENABLED=false (default) 이면 affiliate 줄 없음 (default 켜지 않음)."""
    monkeypatch.setenv("SHORTS_CTA_ENABLED", "true")
    monkeypatch.delenv("SHORTS_AFFILIATE_ENABLED", raising=False)
    monkeypatch.delenv("SHORTS_AFFILIATE_URL", raising=False)
    from auto_publisher.shorts_description import enrich_shorts_description
    out = enrich_shorts_description(base="설명", blog_url="", category="etf-analysis")
    assert "coupang" not in out.lower()
    assert "쿠팡" not in out


def test_enrich_includes_hashtags_for_category(monkeypatch):
    """카테고리별 해시태그 포함."""
    monkeypatch.setenv("SHORTS_CTA_ENABLED", "true")
    from auto_publisher.shorts_description import enrich_shorts_description
    etf_out = enrich_shorts_description(base="x", blog_url="", category="etf-analysis")
    crypto_out = enrich_shorts_description(base="x", blog_url="", category="crypto")
    # ETF / 비트코인 관련 해시태그 차별화
    assert "#shorts" in etf_out
    assert "#ETF" in etf_out or "#etf" in etf_out.lower()
    assert "#bitcoin" in crypto_out.lower() or "#비트코인" in crypto_out or "#crypto" in crypto_out.lower()


def test_enrich_no_blog_url_skips_blog_line(monkeypatch):
    """blog_url 비어있으면 블로그 링크 줄 추가 안 함."""
    monkeypatch.setenv("SHORTS_CTA_ENABLED", "true")
    from auto_publisher.shorts_description import enrich_shorts_description
    out = enrich_shorts_description(base="설명", blog_url="", category="default")
    assert "investiqs.net" not in out  # 강제로 도메인 안 끼워넣음


def test_enrich_idempotent(monkeypatch):
    """이미 enriched description 다시 enrich 호출해도 중복 추가 안 함."""
    monkeypatch.setenv("SHORTS_CTA_ENABLED", "true")
    from auto_publisher.shorts_description import enrich_shorts_description
    once = enrich_shorts_description(
        base="설명", blog_url="https://investiqs.net/ko/post/x", category="default")
    twice = enrich_shorts_description(
        base=once, blog_url="https://investiqs.net/ko/post/x", category="default")
    # 두 번 호출했어도 #shorts 가 1번만
    assert twice.count("#shorts") == 1
    assert twice.count("investiqs.net/ko/post/x") <= 1
