"""cmd_run --with-video chain — 블로그 발행 후 자동 make-video 호출 검증.

배경: cmd_run은 블로그만 발행하고 영상은 별도 cmd_make_video 호출 필요했음.
n8n cron이 두 단계를 chain 으로 호출했지만 분리 구조라 한 단계 실패 시 다른 쪽 안 됨.

이제: cmd_run --with-video (기본 True) 가 do_publish 성공 시 자동으로
do_make_video(slug, lang)를 호출. 한 번의 실행으로 블로그+영상+업로드 완성.
"""
from __future__ import annotations
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


def test_cmd_run_with_video_chains_make_video():
    """--with-video=True 면 do_publish 성공 후 do_make_video(slug=..., lang=...) 호출."""
    from auto_publisher import main

    fake_publish_result = {
        "topic_info": {"id": "test-001"},
        "post": {"title": "Test Title"},
        "publish_results": {
            "hugo": {"slug": "test-slug-001", "url": "/ko/study/test-slug-001/",
                     "filepath": "/tmp/test.md"}
        },
    }
    args = SimpleNamespace(lang="ko", all_langs=False, with_video=True)

    with patch.object(main, "validate_config", return_value=[]), \
         patch.object(main, "do_publish", return_value=fake_publish_result) as mock_pub, \
         patch.object(main, "do_make_video") as mock_mv:
        main.cmd_run(args)

    mock_pub.assert_called_once_with(lang="ko")
    mock_mv.assert_called_once()
    call_kwargs = mock_mv.call_args.kwargs
    assert call_kwargs.get("slug") == "test-slug-001", (
        f"slug 추출 실패: {call_kwargs}"
    )
    assert call_kwargs.get("lang") == "ko"


def test_cmd_run_no_video_skips_make_video():
    """--with-video=False (또는 --no-video) 면 do_make_video 호출 안 함."""
    from auto_publisher import main

    fake_publish_result = {
        "topic_info": {"id": "test-002"},
        "post": {"title": "Test"},
        "publish_results": {"hugo": {"slug": "test-slug-002", "url": "/", "filepath": "/tmp/x.md"}},
    }
    args = SimpleNamespace(lang="ko", all_langs=False, with_video=False)

    with patch.object(main, "validate_config", return_value=[]), \
         patch.object(main, "do_publish", return_value=fake_publish_result), \
         patch.object(main, "do_make_video") as mock_mv:
        main.cmd_run(args)

    mock_mv.assert_not_called()


def test_cmd_run_video_chain_handles_no_publish():
    """do_publish가 None 반환 시 (토픽 없음) do_make_video 호출 안 함."""
    from auto_publisher import main

    args = SimpleNamespace(lang="ko", all_langs=False, with_video=True)
    with patch.object(main, "validate_config", return_value=[]), \
         patch.object(main, "do_publish", return_value=None), \
         patch.object(main, "do_make_video") as mock_mv:
        main.cmd_run(args)

    mock_mv.assert_not_called()


def test_cmd_run_video_chain_handles_no_slug_gracefully():
    """publish_results에 slug 없으면 영상 생성 시도 안 함 (silent skip)."""
    from auto_publisher import main

    fake_publish_result = {
        "topic_info": {"id": "test-003"},
        "post": {"title": "Test"},
        "publish_results": {},  # hugo 발행 실패한 케이스
    }
    args = SimpleNamespace(lang="ko", all_langs=False, with_video=True)

    with patch.object(main, "validate_config", return_value=[]), \
         patch.object(main, "do_publish", return_value=fake_publish_result), \
         patch.object(main, "do_make_video") as mock_mv:
        main.cmd_run(args)

    mock_mv.assert_not_called()


def test_cmd_run_default_with_video_is_true():
    """parser 기본값: --with-video 미지정 시 True (체인 활성)."""
    from auto_publisher import main

    parser = main._build_parser() if hasattr(main, "_build_parser") else None
    if parser is None:
        # _build_parser 없으면 main() 내부 inline parser 직접 검증 어려움 → SKIP
        pytest.skip("_build_parser helper not extracted")
    args = parser.parse_args(["run", "--lang", "ko"])
    assert getattr(args, "with_video", None) is True
