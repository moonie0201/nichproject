"""SEO validator tests."""
import os
import pytest

from auto_publisher.seo_validator import (
    SEOReport,
    SEOValidationError,
    validate_seo,
)


@pytest.fixture(autouse=True)
def enable_validator(monkeypatch):
    """기본적으로 enabled로 테스트 (env gate 동작은 별도 테스트)."""
    monkeypatch.setenv("SEO_VALIDATOR_ENABLED", "1")


def _body(title_kw: str = "VOO", h2_kw: str = "VOO") -> str:
    return f"""<p>{title_kw} ETF는 미국 S&P500 지수를 추종하는 대표 ETF입니다. {title_kw} 5년 수익률은 우수했습니다.</p>
<h2>{h2_kw} 기본 정보</h2>
<p>{title_kw}는 Vanguard가 운용합니다. 운용보수 0.03%로 매우 저렴합니다.</p>
<h2>{h2_kw} 5년 수익률</h2>
<p>{title_kw} 누적 수익률은 약 80%였습니다.</p>
<h2>{h2_kw} 배당 분석</h2>
<p>{title_kw} 배당수익률은 약 1.3%입니다.</p>
<p>결론: {title_kw}는 장기 보유에 적합합니다.</p>"""


def test_passing_post():
    title = "VOO ETF 5년 수익률과 배당률 완벽 분석 가이드"
    body = _body()
    meta = "VOO ETF의 5년 누적 수익률과 배당률을 분석합니다. Vanguard 대표 ETF의 강점과 약점, 장기 보유 전략까지 함께 살펴봅니다."
    report = validate_seo(title, body, "VOO", meta)
    assert report.hard_violations == [], f"hard violations: {report.hard_violations}"
    assert report.score >= 60.0


def test_missing_primary_keyword_in_title():
    title = "투자 ETF 분석 가이드 — 5년 수익률 비교"
    body = _body()
    meta = "ETF 분석 가이드. 5년 수익률과 배당률을 함께 분석하여 장기 보유 전략을 정리합니다. 초보자도 참고 가능합니다."
    report = validate_seo(title, body, "VOO", meta)
    assert any("미포함" in v for v in report.hard_violations)
    with pytest.raises(SEOValidationError):
        if report.hard_violations:
            raise SEOValidationError(report)


def test_too_many_h1():
    title = "VOO ETF 분석 가이드 완벽 정리 2026"
    body = "# H1 첫번째\n\n# H1 두번째\n\n## H2\nVOO 내용"
    meta = "VOO ETF 분석 가이드. 5년 수익률과 배당률을 정리합니다. 초보자도 참고 가능한 콘텐츠입니다."
    report = validate_seo(title, body, "VOO", meta)
    assert any("H1" in v for v in report.hard_violations)


def test_env_gate_downgrade(monkeypatch):
    """SEO_VALIDATOR_ENABLED=0이면 hard도 soft로 다운그레이드."""
    monkeypatch.setenv("SEO_VALIDATOR_ENABLED", "0")
    title = "투자 가이드"  # VOO 미포함
    body = _body()
    report = validate_seo(title, body, "VOO", "meta")
    assert report.hard_violations == []
    assert any("[downgraded]" in v for v in report.soft_violations)


def test_soft_warnings_collected():
    title = "VOO 짧음"  # 너무 짧음
    body = "<p>VOO 본문 짧음</p>"  # H2 없음
    meta = "짧은 meta"  # 너무 짧음
    report = validate_seo(title, body, "VOO", meta)
    soft_text = " ".join(report.soft_violations)
    assert "title" in soft_text or "H2" in soft_text or "meta_description" in soft_text


def test_score_range():
    title = "VOO ETF 5년 수익률 배당 완벽 분석"
    body = _body()
    meta = "VOO ETF 5년 수익률과 배당률을 분석합니다. Vanguard 대표 ETF의 장기 전략 정리. 초보자 가이드 포함."
    report = validate_seo(title, body, "VOO", meta)
    assert 0.0 <= report.score <= 100.0
    assert isinstance(report.metrics, dict)
    assert "keyword_density_pct" in report.metrics


def test_yaml_block_format():
    report = SEOReport(score=87.5, hard_violations=[], soft_violations=["title 짧음"], metrics={})
    yaml = report.to_yaml_block()
    assert "seo_audit:" in yaml
    assert "score: 87.5" in yaml
    assert "hard_violations: []" in yaml
    assert "title 짧음" in yaml
