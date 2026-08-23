"""cmd_run — 토픽 생성 실패 시 다음 토픽 재시도 회귀 테스트.

버그: do_publish가 None 반환 시 즉시 "발행할 토픽이 없습니다"로 종료.
     다음 토픽을 시도하지 않아 48개 미발행 토픽이 있어도 발행 불가.

픽스: cmd_run에 최대 5회 재시도 루프 추가.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch, call


def _args(lang="ko", with_video=False):
    return SimpleNamespace(lang=lang, all_langs=False, with_video=with_video)


def test_cmd_run_retries_on_first_failure():
    """첫 번째 do_publish가 None이면 두 번째 호출로 성공해야 한다."""
    from auto_publisher import main

    fake_result = {
        "topic_info": {"id": "blog-etf-01"},
        "post": {"title": "ETF 투자"},
        "publish_results": {"hugo": {"slug": "etf-투자", "url": "/ko/study/etf/", "filepath": "/tmp/x.md"}},
    }
    side_effects = [None, fake_result]

    with patch.object(main, "validate_config", return_value=[]), \
         patch.object(main, "do_publish", side_effect=side_effects) as mock_pub:
        main.cmd_run(_args())

    assert mock_pub.call_count == 2, (
        f"실패 후 재시도 1회 기대, 실제: {mock_pub.call_count}"
    )


def test_cmd_run_retries_up_to_5_times():
    """최대 5회까지 재시도하고 모두 실패하면 포기한다."""
    from auto_publisher import main

    with patch.object(main, "validate_config", return_value=[]), \
         patch.object(main, "do_publish", return_value=None) as mock_pub:
        main.cmd_run(_args())

    assert mock_pub.call_count == 5, (
        f"최대 5회 재시도 기대, 실제: {mock_pub.call_count}"
    )


def test_cmd_run_stops_retrying_after_success():
    """성공하면 즉시 멈추고 이후 호출 없다."""
    from auto_publisher import main

    fake_result = {
        "topic_info": {"id": "t"},
        "post": {"title": "T"},
        "publish_results": {"hugo": {"slug": "t", "url": "/", "filepath": "/tmp/t.md"}},
    }
    side_effects = [None, None, fake_result]

    with patch.object(main, "validate_config", return_value=[]), \
         patch.object(main, "do_publish", side_effect=side_effects) as mock_pub:
        main.cmd_run(_args())

    assert mock_pub.call_count == 3, (
        f"3번째 성공 시 총 3회 기대, 실제: {mock_pub.call_count}"
    )


def test_cmd_run_original_bug_would_have_failed():
    """회귀 확인: 첫 시도 실패 시 2번째 호출이 존재함을 검증 (구버전은 1번만 호출)."""
    from auto_publisher import main

    call_count = 0
    success_result = {
        "topic_info": {"id": "safe"},
        "post": {"title": "Safe"},
        "publish_results": {"hugo": {"slug": "safe", "url": "/", "filepath": "/tmp/s.md"}},
    }

    def mock_pub(lang):
        nonlocal call_count
        call_count += 1
        return None if call_count == 1 else success_result

    with patch.object(main, "validate_config", return_value=[]), \
         patch.object(main, "do_publish", side_effect=mock_pub):
        main.cmd_run(_args())

    assert call_count >= 2, (
        "첫 실패 후 재시도 없으면 이 테스트 실패 — 구버전 버그 재현"
    )
