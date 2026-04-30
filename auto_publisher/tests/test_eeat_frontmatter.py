"""
E-E-A-T Front Matter 확장 TDD 테스트
- build_eeat_frontmatter() 함수를 대상으로 10개 케이스 검증
- TDD: 이 테스트가 먼저 RED 상태여야 하고, 구현 후 GREEN 이 됨
"""

import re
import yaml
import pytest
from datetime import datetime


# ── 테스트 대상 import ────────────────────────────────────────
from auto_publisher.content_generator import build_eeat_frontmatter, make_eeat_slug


# ── 공통 픽스처 ──────────────────────────────────────────────

@pytest.fixture
def base_input():
    """최소 유효 입력값 — 모든 테스트의 기준선"""
    return dict(
        title="ETF 투자 입문 가이드",
        slug="etf-investment-guide",
        lang="ko",
        meta_description="ETF 투자 방법을 상세히 안내합니다.",
        tags=["ETF", "투자"],
        categories=["재테크 기초"],
        primary_keyword="ETF",
    )


@pytest.fixture
def parsed(base_input):
    """build_eeat_frontmatter 결과를 YAML 파싱한 dict"""
    raw = build_eeat_frontmatter(**base_input)
    # --- 구분자 제거 후 YAML 파싱
    inner = raw.strip().lstrip("-").rstrip("-").strip()
    return yaml.safe_load(inner)


# ── 테스트 1: author 필드 존재 ───────────────────────────────

def test_frontmatter_contains_author(parsed):
    """생성된 YAML front matter에 author 필드가 존재한다."""
    assert "author" in parsed, "author 필드가 front matter에 없음"
    assert parsed["author"], "author 값이 비어있음"


# ── 테스트 2: lastmod ISO 8601 ───────────────────────────────

def test_frontmatter_contains_lastmod_iso(parsed):
    """lastmod 필드가 ISO 8601 형식(YYYY-MM-DDTHH:MM:SS)이다."""
    assert "lastmod" in parsed, "lastmod 필드 없음"
    lastmod_str = str(parsed["lastmod"])
    # datetime 객체 또는 ISO 문자열 양쪽 허용
    try:
        dt = datetime.fromisoformat(lastmod_str)
    except ValueError:
        pytest.fail(f"lastmod '{lastmod_str}'이 ISO 8601 형식이 아님")
    assert dt.year >= 2024, f"lastmod 연도가 비정상: {dt.year}"


# ── 테스트 3: canonicalURL 패턴 ─────────────────────────────

def test_canonical_url_matches_slug(base_input):
    """canonicalURL은 baseURL + lang + blog + slug 패턴이다."""
    slug = "etf-investment-guide"
    raw = build_eeat_frontmatter(**base_input)
    inner = raw.strip().lstrip("-").rstrip("-").strip()
    parsed = yaml.safe_load(inner)

    assert "canonicalURL" in parsed, "canonicalURL 필드 없음"
    url = parsed["canonicalURL"]
    assert url.startswith("https://investiqs.net/"), f"baseURL 불일치: {url}"
    assert "/ko/" in url, f"lang 세그먼트 없음: {url}"
    assert "/blog/" in url, f"/blog/ 경로 없음: {url}"
    assert slug in url, f"slug '{slug}'이 URL에 없음: {url}"


# ── 테스트 4: disclaimer 존재 및 내용 ───────────────────────

def test_disclaimer_present(parsed):
    """disclaimer 필드가 존재하고 '투자 결정은 본인 책임' 문구를 포함한다."""
    assert "disclaimer" in parsed, "disclaimer 필드 없음"
    text = parsed["disclaimer"]
    assert "투자 결정" in text or "본인 책임" in text, (
        f"disclaimer에 필수 문구 없음: {text}"
    )


# ── 테스트 5: faq는 q/a 키를 가진 list ─────────────────────

def test_faq_field_is_list_of_qa(parsed):
    """faq 필드가 list이며 각 항목에 q, a 키가 있다."""
    assert "faq" in parsed, "faq 필드 없음"
    faqs = parsed["faq"]
    assert isinstance(faqs, list), f"faq가 list가 아님: {type(faqs)}"
    assert len(faqs) >= 3, f"faq 항목이 3개 미만: {len(faqs)}"
    for i, item in enumerate(faqs):
        assert "q" in item, f"faq[{i}]에 'q' 키 없음"
        assert "a" in item, f"faq[{i}]에 'a' 키 없음"
        assert item["q"], f"faq[{i}].q가 비어있음"
        assert item["a"], f"faq[{i}].a가 비어있음"


# ── 테스트 6: 기존 faq 유지 ─────────────────────────────────

def test_existing_faq_not_overwritten(base_input):
    """이미 faq가 있으면 덮어쓰지 않고 그대로 유지한다."""
    existing_faq = [
        {"q": "ETF가 뭔가요?", "a": "상장지수펀드입니다."},
        {"q": "어디서 사나요?", "a": "증권사 앱에서 삽니다."},
        {"q": "수수료는?", "a": "0.01%~0.5% 수준입니다."},
    ]
    raw = build_eeat_frontmatter(**base_input, faq=existing_faq)
    inner = raw.strip().lstrip("-").rstrip("-").strip()
    parsed = yaml.safe_load(inner)

    result_faq = parsed["faq"]
    assert result_faq == existing_faq, (
        f"기존 faq가 변경됨: {result_faq}"
    )


# ── 테스트 7: author 기본값 ──────────────────────────────────

def test_author_default_value(base_input):
    """author 파라미터 미지정 시 'InvestIQs 편집팀'이 기본값이다."""
    raw = build_eeat_frontmatter(**base_input)
    inner = raw.strip().lstrip("-").rstrip("-").strip()
    parsed = yaml.safe_load(inner)
    assert parsed["author"] == "InvestIQs 편집팀", (
        f"author 기본값 불일치: {parsed['author']}"
    )


# ── 테스트 8: reviewedBy 필드 존재 ──────────────────────────

def test_reviewed_by_field_present(parsed):
    """YMYL 요구사항: reviewedBy 필드가 존재한다."""
    assert "reviewedBy" in parsed, "reviewedBy 필드 없음 (YMYL 신뢰 지표 필수)"
    assert parsed["reviewedBy"], "reviewedBy 값이 비어있음"


# ── 테스트 9: 한글 제목 → 영문/하이픈 slug ──────────────────

def test_slug_is_english_ascii():
    """한글 제목 입력 시 make_eeat_slug가 영문·숫자·하이픈만 반환한다."""
    korean_title = "ETF 투자 입문 가이드 2026"
    slug = make_eeat_slug(korean_title)
    assert slug, "slug가 비어있음"
    assert re.fullmatch(r"[a-z0-9\-]+", slug), (
        f"slug에 비ASCII 문자 포함: '{slug}'"
    )
    assert "--" not in slug, f"이중 하이픈 포함: '{slug}'"
    assert not slug.startswith("-"), f"slug가 하이픈으로 시작: '{slug}'"
    assert not slug.endswith("-"), f"slug가 하이픈으로 끝남: '{slug}'"


# ── 테스트 10: 기존 호출부 회귀 방지 ────────────────────────

def test_backward_compatible_without_eeat_param(base_input):
    """E-E-A-T 파라미터를 전혀 넘기지 않아도 함수가 정상 동작한다."""
    # 최소 파라미터만 전달 (title, slug만 필수)
    try:
        raw = build_eeat_frontmatter(
            title="간단 제목",
            slug="simple-title",
        )
    except TypeError as e:
        pytest.fail(f"필수 파라미터 오류 (하위 호환 위반): {e}")

    assert raw.startswith("---"), "front matter가 --- 로 시작하지 않음"
    inner = raw.strip().lstrip("-").rstrip("-").strip()
    parsed = yaml.safe_load(inner)
    # 핵심 E-E-A-T 필드들이 기본값으로 존재해야 함
    for field in ("author", "lastmod", "canonicalURL", "disclaimer"):
        assert field in parsed, f"파라미터 생략 시 '{field}' 필드 누락"


# ── 보너스: YAML 유효성 (yaml.safe_load 가능) ───────────────

def test_yaml_parseable(base_input):
    """생성된 front matter 전체가 yaml.safe_load 가능한 유효 YAML이다."""
    raw = build_eeat_frontmatter(**base_input)
    inner = raw.strip().lstrip("-").rstrip("-").strip()
    try:
        data = yaml.safe_load(inner)
    except yaml.YAMLError as e:
        pytest.fail(f"YAML 파싱 실패: {e}")
    assert isinstance(data, dict), "YAML 결과가 dict가 아님"
