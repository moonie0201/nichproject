"""금칙어 정책 — 삭제가 아니라 탐지 후 재생성.

기존 결함: compliance.filter_forbidden_phrases 가 금칙어를 본문에서 통째로
삭제했다. 한국어는 조사가 남아 문장이 무너졌다.
    "연말정산 완벽 가이드를 다음과 같이 정리했습니다."
    → "연말정산 를  정리했습니다."
역설적으로 이 처리가 글을 더 AI 티 나게 만들었고, content_verifier 가 이미
같은 금칙어를 검사해 재생성을 트리거하므로 삭제는 이득 없이 손상만 남겼다.
"""

import pytest

from auto_publisher.compliance import apply_compliance, find_forbidden_phrases
from auto_publisher.config import FORBIDDEN_PHRASES


SENTENCES = [
    "이렇게 계산하면 환급액은 148만 5천 원입니다.",
    "연말정산 완벽 가이드를 다음과 같이 정리했습니다.",
    "저희는 이런 식으로 한도를 배분합니다.",
    "결론적으로 IRP 한도를 먼저 채우는 편이 유리합니다.",
]


@pytest.mark.parametrize("text", SENTENCES)
def test_pipeline_no_longer_mutilates_sentences(text):
    """발행 경로가 문장을 건드리면 안 된다. 조사만 남는 붕괴가 재발하면 안 된다."""
    assert text in apply_compliance(text, "ko")


def test_orphaned_particle_regression():
    """가장 심했던 사례 — 조사 '를'만 남던 문장."""
    out = apply_compliance("연말정산 완벽 가이드를 다음과 같이 정리했습니다.", "ko")
    assert "연말정산 를" not in out


def test_apply_compliance_still_injects_disclaimer():
    assert 'class="disclaimer"' in apply_compliance("<p>본문</p>", "ko")


def test_detection_still_reports_phrases():
    """삭제는 안 하지만 탐지는 되어야 검증 계층이 재생성을 걸 수 있다."""
    hits = find_forbidden_phrases("결론적으로 정리하면 다음과 같이 됩니다.", "ko")
    assert "결론적으로" in hits
    assert "다음과 같이" in hits


def test_clean_text_reports_nothing():
    assert find_forbidden_phrases("연금저축 납입 한도는 연 600만 원입니다.", "ko") == []


# --- 1인칭 정책: 지어낸 개인 경험은 막고, 발행 주체 목소리는 허용 ---

def test_fabricated_personal_experience_still_banned():
    """AI 생성임을 공개한 사이트에서 '제가 직접 해봤다'는 사실이 아니다."""
    for w in ("내가", "제가", "저는"):
        assert w in FORBIDDEN_PHRASES["ko"], w


def test_publisher_voice_is_allowed():
    """'저희는'은 발행 주체의 참인 진술이므로 막지 않는다."""
    assert "저희는" not in FORBIDDEN_PHRASES["ko"]


def test_fabricated_persona_stays_banned():
    for w in ("이재훈", "34세 직장인"):
        assert w in FORBIDDEN_PHRASES["ko"], w


def test_ordinary_korean_connectives_unbanned():
    """'이렇게', '이런 식으로'는 AI 특유 표현이 아니라 일반 한국어다."""
    for w in ("이렇게", "이런 식으로"):
        assert w not in FORBIDDEN_PHRASES["ko"], w


def test_verifier_catches_cliches_that_deletion_used_to_hide():
    """삭제로 감추던 클리셰를 검증기가 잡아 재생성시켜야 한다."""
    from auto_publisher.content_verifier import FORBIDDEN_IN_BODY
    for w in ("살펴보겠습니다", "알아보겠습니다", "다음과 같이", "마치며"):
        assert w in FORBIDDEN_IN_BODY["ko"], w
