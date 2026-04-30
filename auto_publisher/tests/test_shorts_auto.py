"""Shorts 자동 생성 — 가장 최근 발행 글로 /make-video 호출 — TDD."""

from pathlib import Path
import pytest


@pytest.fixture
def tmp_content(tmp_path):
    """임시 web/content/ko/{blog,study,daily,weekly}/ 트리."""
    base = tmp_path / "web" / "content" / "ko"
    for sec in ("blog", "study", "daily", "weekly"):
        (base / sec).mkdir(parents=True)
    return base


def _touch(path: Path, mtime_offset: int = 0):
    """파일 생성 + mtime 조정 (offset 초)."""
    import time
    path.write_text("---\ntitle: test\n---\n", encoding="utf-8")
    if mtime_offset:
        ts = time.time() + mtime_offset
        import os
        os.utime(path, (ts, ts))


def test_pick_latest_returns_most_recent(tmp_content):
    """find_latest_publishable_slug() 가 가장 최신 mtime 의 slug 를 반환."""
    from auto_publisher.shorts_auto import find_latest_publishable_slug

    _touch(tmp_content / "study" / "old-guide.md", mtime_offset=-3600)
    _touch(tmp_content / "daily" / "newer-wrap.md", mtime_offset=-60)
    _touch(tmp_content / "weekly" / "newest-weekly.md", mtime_offset=-10)

    result = find_latest_publishable_slug(content_root=tmp_content.parent.parent / "content", lang="ko")
    assert result is not None
    assert result["slug"] == "newest-weekly"
    assert result["section"] == "weekly"


def test_pick_latest_skips_section(tmp_content):
    """skip_sections 옵션으로 특정 section 제외."""
    from auto_publisher.shorts_auto import find_latest_publishable_slug

    _touch(tmp_content / "study" / "guide.md", mtime_offset=-3600)
    _touch(tmp_content / "daily" / "wrap.md", mtime_offset=-60)

    result = find_latest_publishable_slug(
        content_root=tmp_content.parent.parent / "content",
        lang="ko",
        skip_sections=("daily",),
    )
    assert result["slug"] == "guide"
    assert result["section"] == "study"


def test_pick_latest_returns_none_when_empty(tmp_content):
    from auto_publisher.shorts_auto import find_latest_publishable_slug
    result = find_latest_publishable_slug(
        content_root=tmp_content.parent.parent / "content", lang="ko",
    )
    assert result is None


def test_pick_latest_only_includes_specified_lang(tmp_content):
    """다른 lang 디렉토리는 무시."""
    from auto_publisher.shorts_auto import find_latest_publishable_slug
    en_base = tmp_content.parent / "en" / "study"
    en_base.mkdir(parents=True)
    _touch(en_base / "english-guide.md", mtime_offset=-1)
    _touch(tmp_content / "study" / "korean-guide.md", mtime_offset=-3600)
    result = find_latest_publishable_slug(
        content_root=tmp_content.parent.parent / "content", lang="ko",
    )
    assert result["slug"] == "korean-guide"


def test_pick_latest_excludes_recently_videoed(tmp_content):
    """이미 video_cache 에 있는 slug 는 제외 옵션."""
    from auto_publisher.shorts_auto import find_latest_publishable_slug

    _touch(tmp_content / "study" / "already-done.md", mtime_offset=-10)
    _touch(tmp_content / "study" / "fresh.md", mtime_offset=-3600)

    # already_done_slugs 인자에 already-done 만 들어있으면 fresh 가 선택됨
    result = find_latest_publishable_slug(
        content_root=tmp_content.parent.parent / "content",
        lang="ko",
        already_done_slugs={"already-done"},
    )
    assert result["slug"] == "fresh"


def test_pick_latest_prefers_blog_when_newest(tmp_path):
    """blog 섹션이 가장 최신이면 영상 자동 대상에 포함된다."""
    from auto_publisher.shorts_auto import find_latest_publishable_slug

    base = tmp_path / "web" / "content" / "ko"
    for sec in ("blog", "study", "daily", "weekly"):
        (base / sec).mkdir(parents=True)

    _touch(base / "daily" / "older.md", mtime_offset=-3600)
    _touch(base / "blog" / "newest-blog.md", mtime_offset=-10)

    result = find_latest_publishable_slug(content_root=tmp_path / "web" / "content", lang="ko")
    assert result is not None
    assert result["slug"] == "newest-blog"
    assert result["section"] == "blog"
