"""3-탭(투자공부/일일시황/주간시황) 콘텐츠 마이그레이션 — TDD 테스트.

핵심 함수:
- classify(filename, frontmatter) -> "study" | "daily" | "weekly"
- add_alias(content, old_url) -> 새 content (idempotent)
- migrate_one(md_path, dry_run, content_root) -> {moved, from, to, tab, alias_added}
- migrate_all(content_root, dry_run) -> [results...]
"""

from pathlib import Path
import shutil
import textwrap
import pytest


# ── 1. classify() ─────────────────────────────────────────────

def test_classify_intraday_prefix():
    from auto_publisher.migrate_content_tabs import classify
    assert classify("intraday-some-slug.md", {"title": "..."}) == "daily"


def test_classify_news_article_schema():
    from auto_publisher.migrate_content_tabs import classify
    fm = {"title": "VOO 분석", "schema": "NewsArticle", "categories": []}
    assert classify("voo-analysis.md", fm) == "daily"


def test_classify_title_contains_jangjung():
    from auto_publisher.migrate_content_tabs import classify
    fm = {"title": "2026년 4월 26일 미국 증시 장중", "categories": []}
    assert classify("foo.md", fm) == "daily"


def test_classify_title_contains_magam():
    from auto_publisher.migrate_content_tabs import classify
    fm = {"title": "2026년 4월 23일 미국 증시 마감", "categories": []}
    assert classify("foo.md", fm) == "daily"


def test_classify_title_contains_jugan():
    from auto_publisher.migrate_content_tabs import classify
    fm = {"title": "주간 시황 정리", "categories": []}
    assert classify("foo.md", fm) == "weekly"


def test_classify_categories_dailymarket():
    from auto_publisher.migrate_content_tabs import classify
    fm = {"title": "...", "categories": ["시장분석", "데일리마켓"]}
    assert classify("foo.md", fm) == "daily"


def test_classify_categories_misuk_jeungsi():
    from auto_publisher.migrate_content_tabs import classify
    fm = {"title": "어떤 분석", "categories": ["미국증시"]}
    assert classify("foo.md", fm) == "daily"


def test_classify_etf_guide_default_to_study():
    from auto_publisher.migrate_content_tabs import classify
    fm = {"title": "ETF 투자 입문 가이드", "categories": ["재테크 기초"], "schema": "Article"}
    assert classify("etf-guide.md", fm) == "study"


def test_classify_voo_analysis_default_to_study():
    from auto_publisher.migrate_content_tabs import classify
    # 분석 글이지만 schema 가 Article 이고 제목에 시황 키워드 없음
    fm = {"title": "VOO 5년 수익률 분석", "categories": ["ETF 데이터 분석"]}
    assert classify("voo-5y.md", fm) == "study"


# ── 2. add_alias() ─────────────────────────────────────────────

def test_add_alias_to_frontmatter_without_aliases_field():
    from auto_publisher.migrate_content_tabs import add_alias
    content = textwrap.dedent("""\
        ---
        title: "Hello"
        date: 2026-04-01
        ---

        본문
    """)
    out = add_alias(content, "/ko/blog/hello/")
    assert "aliases:" in out
    assert "/ko/blog/hello/" in out


def test_add_alias_preserves_existing_aliases():
    from auto_publisher.migrate_content_tabs import add_alias
    content = textwrap.dedent("""\
        ---
        title: "Hello"
        aliases:
          - /old-url-1/
        ---

        본문
    """)
    out = add_alias(content, "/ko/blog/hello/")
    assert "/old-url-1/" in out
    assert "/ko/blog/hello/" in out


def test_add_alias_skips_duplicate():
    from auto_publisher.migrate_content_tabs import add_alias
    content = textwrap.dedent("""\
        ---
        title: "Hello"
        aliases:
          - /ko/blog/hello/
        ---
        본문
    """)
    out = add_alias(content, "/ko/blog/hello/")
    # 중복 추가되지 않아야 함
    assert out.count("/ko/blog/hello/") == 1


# ── 3. migrate_one() — 임시 디렉토리 ─────────────────────────

@pytest.fixture
def tmp_content_root(tmp_path):
    """임시 web/content 디렉토리 구조 생성."""
    root = tmp_path / "content"
    (root / "ko" / "blog").mkdir(parents=True)
    return root


def _write_md(path: Path, frontmatter_lines: list[str], body: str = "본문"):
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = "\n".join(frontmatter_lines)
    path.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")


def test_migrate_one_moves_file_to_study(tmp_content_root):
    from auto_publisher.migrate_content_tabs import migrate_one
    src = tmp_content_root / "ko" / "blog" / "etf-guide.md"
    _write_md(src, [
        'title: "ETF 투자 입문 가이드"',
        'categories:',
        '  - "재테크 기초"',
    ])
    result = migrate_one(src, content_root=tmp_content_root, dry_run=False)
    new_path = tmp_content_root / "ko" / "study" / "etf-guide.md"
    assert result["tab"] == "study"
    assert result["moved"] is True
    assert new_path.exists()
    assert not src.exists()


def test_migrate_one_moves_intraday_to_daily(tmp_content_root):
    from auto_publisher.migrate_content_tabs import migrate_one
    src = tmp_content_root / "ko" / "blog" / "intraday-foo.md"
    _write_md(src, ['title: "장중 시황 X"'])
    result = migrate_one(src, content_root=tmp_content_root, dry_run=False)
    assert result["tab"] == "daily"
    assert (tmp_content_root / "ko" / "daily" / "intraday-foo.md").exists()


def test_migrate_one_dry_run_does_not_move(tmp_content_root):
    from auto_publisher.migrate_content_tabs import migrate_one
    src = tmp_content_root / "ko" / "blog" / "etf-guide.md"
    _write_md(src, ['title: "ETF 가이드"'])
    result = migrate_one(src, content_root=tmp_content_root, dry_run=True)
    assert src.exists(), "dry_run 인데 원본이 삭제됨"
    assert not (tmp_content_root / "ko" / "study" / "etf-guide.md").exists()
    assert result["tab"] == "study"
    assert result["moved"] is False


def test_migrate_one_inserts_alias_to_old_blog_path(tmp_content_root):
    from auto_publisher.migrate_content_tabs import migrate_one
    src = tmp_content_root / "ko" / "blog" / "etf-guide.md"
    _write_md(src, ['title: "ETF 가이드"'])
    migrate_one(src, content_root=tmp_content_root, dry_run=False)
    new_content = (tmp_content_root / "ko" / "study" / "etf-guide.md").read_text(encoding="utf-8")
    assert "aliases:" in new_content
    assert "/ko/blog/etf-guide/" in new_content


def test_migrate_one_idempotent(tmp_content_root):
    from auto_publisher.migrate_content_tabs import migrate_one, migrate_all
    src = tmp_content_root / "ko" / "blog" / "etf-guide.md"
    _write_md(src, ['title: "ETF 가이드"'])
    # 1차 마이그레이션
    migrate_one(src, content_root=tmp_content_root, dry_run=False)
    moved_path = tmp_content_root / "ko" / "study" / "etf-guide.md"
    first_content = moved_path.read_text(encoding="utf-8")
    # 2차 — 이미 study/ 에 있으니 noop
    results = migrate_all(content_root=tmp_content_root, dry_run=False)
    second_content = moved_path.read_text(encoding="utf-8")
    assert first_content == second_content, "두 번째 실행 시 내용이 변경됨"


# ── 4. migrate_all() ────────────────────────────────────────────

def test_migrate_all_processes_multiple_files(tmp_content_root):
    from auto_publisher.migrate_content_tabs import migrate_all
    blog = tmp_content_root / "ko" / "blog"
    _write_md(blog / "etf-guide.md", ['title: "ETF 가이드"'])
    _write_md(blog / "intraday-x.md", ['title: "장중 시황"'])
    _write_md(blog / "weekly-recap.md", ['title: "주간 리캡"'])

    results = migrate_all(content_root=tmp_content_root, dry_run=False)
    tabs = sorted(r["tab"] for r in results)
    assert tabs == ["daily", "study", "weekly"]
    assert (tmp_content_root / "ko" / "study" / "etf-guide.md").exists()
    assert (tmp_content_root / "ko" / "daily" / "intraday-x.md").exists()
    assert (tmp_content_root / "ko" / "weekly" / "weekly-recap.md").exists()


def test_migrate_all_skips_already_migrated(tmp_content_root):
    """blog/ 가 비어 있고 study/ 등에 이미 있으면 noop."""
    from auto_publisher.migrate_content_tabs import migrate_all
    already = tmp_content_root / "ko" / "study" / "old.md"
    _write_md(already, ['title: "이미 옮겨진 글"'])
    results = migrate_all(content_root=tmp_content_root, dry_run=False)
    # blog/ 에 파일 없으니 결과는 0개
    assert len([r for r in results if r.get("moved")]) == 0


def test_migrate_all_handles_multiple_languages(tmp_content_root):
    from auto_publisher.migrate_content_tabs import migrate_all
    for lang in ("ko", "en"):
        _write_md(
            tmp_content_root / lang / "blog" / f"guide-{lang}.md",
            ['title: "guide"', 'categories:', '  - "tutorial"'],
        )
    results = migrate_all(content_root=tmp_content_root, dry_run=False)
    assert (tmp_content_root / "ko" / "study" / "guide-ko.md").exists()
    assert (tmp_content_root / "en" / "study" / "guide-en.md").exists()
