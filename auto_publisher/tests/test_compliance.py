import pytest
from auto_publisher.compliance import apply_compliance, count_sources


def test_filter_forbidden_phrases():
    # 간단한 금칙어 필터 테스트 (ko)
    html = "이것은 완벽 가이드입니다."
    filtered = apply_compliance(html, "ko")
    assert "완벽 가이드" not in filtered


def test_inject_disclaimer():
    # 면책 조항 주입 테스트
    html = "<p>투자 내용</p>"
    injected = apply_compliance(html, "ko")
    assert 'class="disclaimer"' in injected


def test_count_sources():
    # 출처 개수 테스트
    html = "내용 1 [1] 내용 2 [2] 내용 3 [3]"
    assert count_sources(html) == 3

    html_low = "내용 1 [1]"
    assert count_sources(html_low) == 1
