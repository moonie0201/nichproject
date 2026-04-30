"""HTML 블록 뒤 빈 줄 강제 + 중첩 <a> 수정 포스트프로세서 TDD 테스트.

Goldmark(Hugo) 파서는 HTML 블록 바로 다음 줄에 빈 줄이 없으면 마크다운 파싱을 건너뛴다.
콘텐츠 생성기가 출력하는 <div>, <table> 등 블록 레벨 HTML 뒤에 반드시 `\\n\\n` 을 삽입해야 한다.

또한 content_generator의 자동 내부링크 삽입이 이미 <a> 안에 또 <a>를 넣는 버그가 있다.
중첩된 <a> 는 outer만 남기고 inner anchor는 텍스트로 변환한다.
"""

import pytest

from auto_publisher.content_generator import fix_html_block_spacing


# ── 1. HTML 블록 뒤 빈 줄 삽입 ─────────────────────────────────

def test_div_followed_by_header_gets_blank_line():
    raw = (
        "<div class=\"summary-box\"><ul><li>현재가: $653</li></ul></div>\n"
        "## 핵심 지표 요약\n"
    )
    out = fix_html_block_spacing(raw)
    assert "</div>\n\n## 핵심 지표 요약" in out, (
        f"</div> 뒤에 빈 줄이 삽입되지 않음:\n{out}"
    )


def test_table_followed_by_paragraph_gets_blank_line():
    raw = (
        "<table><tr><th>A</th></tr><tr><td>1</td></tr></table>\n"
        "동일 지수형 ETF인 SPY와 IVV를 함께 놓고 보면...\n"
    )
    out = fix_html_block_spacing(raw)
    assert "</table>\n\n동일 지수형 ETF" in out


def test_figure_followed_by_text_gets_blank_line():
    raw = (
        "<figure class=\"chart-figure\"><img src=\"x.png\"></figure>\n"
        "아래 3개 차트는 같은 숫자를\n"
    )
    out = fix_html_block_spacing(raw)
    assert "</figure>\n\n아래 3개 차트" in out


def test_ul_followed_by_markdown_list():
    raw = (
        "<ul><li>x</li></ul>\n"
        "- 리스크1\n"
        "- 리스크2\n"
    )
    out = fix_html_block_spacing(raw)
    assert "</ul>\n\n- 리스크1" in out


# ── 2. 이미 빈 줄이 있으면 변경 없음 (idempotency) ───────────

def test_already_spaced_html_block_not_changed():
    raw = (
        "<div>hello</div>\n"
        "\n"
        "## 이미 정상\n"
    )
    out = fix_html_block_spacing(raw)
    # 함수는 이미 빈 줄이 있으면 새로 추가하지 않아야 한다
    assert out.count("</div>\n\n") == 1
    assert "</div>\n\n\n" not in out, "빈 줄이 중복 삽입됨"


def test_function_is_idempotent():
    raw = "<table></table>\n다음 문단\n"
    once = fix_html_block_spacing(raw)
    twice = fix_html_block_spacing(once)
    assert once == twice, "함수 두 번 적용 시 결과가 달라짐"


# ── 3. 인라인 HTML (중간에 나오는) 은 건드리지 않음 ─────────

def test_inline_html_in_paragraph_preserved():
    raw = "문장 안에 <strong>강조</strong>와 링크 <a href=\"/x\">여기</a> 가 있음\n"
    out = fix_html_block_spacing(raw)
    assert out == raw, f"인라인 HTML이 수정됨:\n기대: {raw}\n실제: {out}"


# ── 4. 중첩 <a> 태그 정리 ───────────────────────────────────

def test_nested_anchor_flattened():
    raw = '<figcaption><a href="/ko/blog/outer/"><a href="/ko/blog/inner/">VOO</a></a> 차트</figcaption>'
    out = fix_html_block_spacing(raw)
    # 외부 링크만 유지, 내부 <a>는 제거되고 텍스트만 남아야 함
    # 허용: <figcaption><a href="/ko/blog/outer/">VOO</a> 차트</figcaption>
    # 또는: 내부 링크 유지하고 외부 제거도 가능, 중요한 건 중첩 제거
    assert "<a href=" in out, "최소 하나의 <a> 는 유지되어야 함"
    # 중첩이 제거되었는지 확인: 첫 <a> 이후 `</a>` 전에 또 다른 <a href=" 가 나오면 안 됨
    import re
    nested = re.search(r'<a\s+[^>]*>\s*<a\s+[^>]*>', out)
    assert nested is None, f"중첩 <a> 여전히 존재:\n{out}"


def test_non_nested_anchor_preserved():
    raw = '<p>문장 <a href="/x">링크</a> 끝.</p>'
    out = fix_html_block_spacing(raw)
    assert '<a href="/x">링크</a>' in out


# ── 5. 실제 VOO 포스트의 문제 구간 회귀 테스트 ──────────────

def test_real_case_summary_box_to_header():
    """실제 라이브 페이지에서 발견된 렌더링 버그 재현."""
    raw = (
        "<div class=\"summary-box\"><ul>"
        "<li>현재가: $653.14</li>"
        "<li>P/E: 28.2</li>"
        "</ul></div>\n"
        "## 핵심 지표 요약\n"
        "\n"
        "<figure class=\"chart-figure\"><img src=\"/images/x/price-history.png\"></figure>\n"
        "아래 3개 차트는 같은 숫자를 다른 각도로 보여준다.\n"
    )
    out = fix_html_block_spacing(raw)
    # 두 군데 모두 빈 줄 보장
    assert "</div>\n\n## 핵심 지표 요약" in out
    assert "</figure>\n\n아래 3개 차트" in out
