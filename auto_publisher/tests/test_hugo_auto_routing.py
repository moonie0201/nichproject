"""HugoPublisher 의 3-탭 자동 라우팅 동작 — TDD 테스트.

기본값 section="blog" 일 때, classify() 결과로 study/daily/weekly 자동 결정.
호출자가 명시적으로 daily/weekly/study 를 지정하면 그대로 유지.
"""

from pathlib import Path
import pytest


@pytest.fixture
def tmp_site(tmp_path, monkeypatch):
    """임시 Hugo site_dir 로 격리."""
    from auto_publisher.publishers import hugo as hugo_module
    site = tmp_path / "site"
    (site / "content" / "ko").mkdir(parents=True)
    monkeypatch.setattr(hugo_module, "HUGO_SITE_DIR", site)
    monkeypatch.setattr(hugo_module, "_content_dir",
                        lambda lang="ko", section="blog": site / "content" / lang / section)
    # subprocess.run (hugo build) 을 no-op stub
    import subprocess
    real_run = subprocess.run
    def fake_run(*args, **kwargs):
        class R: returncode = 0; stdout = ""; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    return site


def _make_pub(tmp_site, section="blog"):
    from auto_publisher.publishers.hugo import HugoPublisher
    return HugoPublisher(lang="ko", site_dir=tmp_site, section=section)


def test_default_section_routes_etf_guide_to_study(tmp_site, monkeypatch):
    """제목이 가이드성이고 카테고리가 일반 → study/ 로 자동."""
    # link_builder/chart_generator 호출 회피
    import auto_publisher.publishers.hugo as hp
    monkeypatch.setattr("auto_publisher.chart_generator.generate_charts", lambda **kw: [])
    monkeypatch.setattr("auto_publisher.chart_generator.inject_charts_into_html", lambda html, c: html)
    monkeypatch.setattr("auto_publisher.link_builder.get_published_links", lambda lang: [])
    monkeypatch.setattr("auto_publisher.link_builder.inject_internal_links", lambda html, links, *args, **kwargs: html)

    pub = _make_pub(tmp_site, section="blog")
    result = pub.publish(
        title="ETF 투자 입문 가이드",
        content_html="<p>ETF 기본 개념...</p>",
        categories=["재테크 기초"],
        tags=["ETF"],
        primary_keyword="ETF",
    )
    assert "study" in str(result.get("filepath", "")) or pub.section == "study"
    # 파일이 study/ 디렉토리에 들어갔는지
    assert (tmp_site / "content" / "ko" / "study").exists()


def test_default_section_routes_market_close_to_daily(tmp_site, monkeypatch):
    """제목에 '마감' 포함 → daily/ 로 자동."""
    monkeypatch.setattr("auto_publisher.chart_generator.generate_charts", lambda **kw: [])
    monkeypatch.setattr("auto_publisher.chart_generator.inject_charts_into_html", lambda html, c: html)
    monkeypatch.setattr("auto_publisher.link_builder.get_published_links", lambda lang: [])
    monkeypatch.setattr("auto_publisher.link_builder.inject_internal_links", lambda html, links, *args, **kwargs: html)

    pub = _make_pub(tmp_site, section="blog")
    pub.publish(
        title="2026년 4월 27일 미국 증시 마감 분석",
        content_html="<p>...</p>",
        categories=["시장분석", "미국증시"],
        tags=["SPY"],
    )
    assert pub.section == "daily"


def test_explicit_section_overrides_auto_routing(tmp_site, monkeypatch):
    """호출자가 section='study' 로 지정하면 자동 라우팅 안 함."""
    monkeypatch.setattr("auto_publisher.chart_generator.generate_charts", lambda **kw: [])
    monkeypatch.setattr("auto_publisher.chart_generator.inject_charts_into_html", lambda html, c: html)
    monkeypatch.setattr("auto_publisher.link_builder.get_published_links", lambda lang: [])
    monkeypatch.setattr("auto_publisher.link_builder.inject_internal_links", lambda html, links, *args, **kwargs: html)

    pub = _make_pub(tmp_site, section="study")
    pub.publish(
        title="2026년 4월 27일 미국 증시 마감 분석",  # 제목에 '마감' 있어도
        content_html="<p>...</p>",
        categories=["시장분석"],
    )
    # 명시적 study 가 유지되어야 함 (auto routing 으로 daily 가 되면 안 됨)
    assert pub.section == "study"
