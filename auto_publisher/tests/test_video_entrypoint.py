from pathlib import Path
from types import SimpleNamespace

import pytest


def test_resolve_video_source_prefers_known_sections(tmp_path):
    from auto_publisher.main import resolve_video_source

    content_root = tmp_path / "web" / "content"
    blog = content_root / "ko" / "blog"
    daily = content_root / "ko" / "daily"
    blog.mkdir(parents=True)
    daily.mkdir(parents=True)

    slug = "latest-post"
    (daily / f"{slug}.md").write_text("daily", encoding="utf-8")

    resolved = resolve_video_source(slug=slug, lang="ko", content_root=content_root)
    assert resolved == (
        str(daily / f"{slug}.md"),
        "daily",
        f"https://investiqs.net/ko/daily/{slug}/",
    )


def test_resolve_video_source_returns_none_when_missing(tmp_path):
    from auto_publisher.main import resolve_video_source

    content_root = tmp_path / "web" / "content"
    (content_root / "ko" / "blog").mkdir(parents=True)
    assert resolve_video_source("missing", lang="ko", content_root=content_root) is None


def test_cmd_make_video_exits_nonzero_on_failure(monkeypatch, capsys):
    from auto_publisher import main

    monkeypatch.setattr(main, "do_make_video", lambda **_: None)

    with pytest.raises(SystemExit) as exc:
        main.cmd_make_video(SimpleNamespace(slug="missing", lang="ko", no_upload=True, privacy="private"))

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "[YouTube] 실패" in captured.out
