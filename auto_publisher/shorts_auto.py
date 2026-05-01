"""Shorts 자동 생성 — 가장 최근 발행된 글로 /make-video 호출.

n8n cron 이 정해진 시간에 호출하면, 이 모듈이:
1. content_root/{lang}/{blog,study,daily,weekly}/ 디렉토리를 스캔
2. mtime 이 가장 최근 인 .md 파일 식별
3. video_cache 에서 이미 영상화된 slug 는 옵션으로 제외
4. {slug, section, lang, path} 반환

bridge_api.py 가 이 결과로 run_make_video(slug, lang) 호출.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_SECTIONS = ("blog", "study", "daily", "weekly")


def find_latest_publishable_slug(
    content_root: Path,
    lang: str = "ko",
    sections: tuple[str, ...] = DEFAULT_SECTIONS,
    skip_sections: tuple[str, ...] = (),
    already_done_slugs: set[str] | None = None,
) -> dict | None:
    """주어진 lang 의 blog/study/daily/weekly 디렉토리에서 mtime 최신 글 찾기.

    Returns:
        {"slug": str, "section": str, "lang": str, "path": Path, "mtime": float}
        없으면 None.
    """
    content_root = Path(content_root)
    already_done = already_done_slugs or set()

    candidates: list[tuple[float, str, Path]] = []
    for section in sections:
        if section in skip_sections:
            continue
        section_dir = content_root / lang / section
        if not section_dir.is_dir():
            continue
        for md in section_dir.glob("*.md"):
            slug = md.stem
            if slug in already_done:
                continue
            try:
                mtime = md.stat().st_mtime
            except OSError:
                continue
            candidates.append((mtime, section, md))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    mtime, section, path = candidates[0]
    return {
        "slug": path.stem,
        "section": section,
        "lang": lang,
        "path": path,
        "mtime": mtime,
    }


def list_videoed_slugs(video_cache_dir: Path) -> set[str]:
    """이미 영상이 생성된 slug 목록 (video_cache/<slug>/ 디렉토리 존재)."""
    video_cache_dir = Path(video_cache_dir)
    if not video_cache_dir.is_dir():
        return set()
    return {p.name for p in video_cache_dir.iterdir() if p.is_dir()}
