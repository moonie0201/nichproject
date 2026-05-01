"""3-탭 (투자공부 / 일일시황 / 주간시황) 콘텐츠 구조 마이그레이션.

기존 `web/content/{lang}/blog/<slug>.md` 글을 분류해서
`web/content/{lang}/{study|daily|weekly}/<slug>.md` 로 이동하고,
원래 URL 보존을 위해 frontmatter `aliases` 에 `/lang/blog/<slug>/` 를 추가한다.

핵심: idempotent — 두 번 실행해도 안전.

CLI:
    python3 -m auto_publisher.migrate_content_tabs --dry-run
    python3 -m auto_publisher.migrate_content_tabs
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# 분류
# ─────────────────────────────────────────────────────────────────

DAILY_TITLE_KEYWORDS = ("장중", "마감", "개장")
WEEKLY_TITLE_KEYWORDS = ("주간", "주말")
DAILY_CATEGORY_KEYWORDS = ("데일리마켓", "일일시황", "미국증시")
WEEKLY_CATEGORY_KEYWORDS = ("주간시황", "위클리")


def classify(filename: str, frontmatter: dict) -> str:
    """파일명/frontmatter 로부터 탭(study|daily|weekly) 분류."""
    name = (filename or "").lower()
    if name.startswith("intraday-"):
        return "daily"

    schema = (frontmatter or {}).get("schema") or ""
    if schema == "NewsArticle":
        return "daily"

    cats = frontmatter.get("categories") or []
    if isinstance(cats, str):
        cats = [cats]
    cats_str = " ".join(str(c) for c in cats)

    title = str(frontmatter.get("title") or "")

    if any(w in cats_str for w in DAILY_CATEGORY_KEYWORDS):
        return "daily"
    if any(w in title for w in DAILY_TITLE_KEYWORDS):
        return "daily"
    if any(w in title for w in WEEKLY_TITLE_KEYWORDS):
        return "weekly"
    if any(w in cats_str for w in WEEKLY_CATEGORY_KEYWORDS):
        return "weekly"
    return "study"


# ─────────────────────────────────────────────────────────────────
# Frontmatter 파싱 (간이) + alias 삽입
# ─────────────────────────────────────────────────────────────────

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _split_frontmatter(content: str) -> tuple[str, str]:
    """(frontmatter_block_with_fences, body) 반환. frontmatter 없으면 ('', content)."""
    m = _FM_RE.match(content)
    if not m:
        return "", content
    return m.group(0), content[m.end():]


def _parse_frontmatter_simple(fm_block: str) -> dict:
    """가벼운 YAML 파서. yaml 라이브러리 있으면 사용, 없으면 라인 기반 파싱."""
    if not fm_block:
        return {}
    inner = fm_block.strip().strip("-").strip()
    try:
        import yaml
        data = yaml.safe_load(inner)
        return data if isinstance(data, dict) else {}
    except Exception:
        # fallback: 라인 기반 (title, schema, categories list 만)
        result: dict = {}
        current_key = None
        current_list: list = []
        for line in inner.splitlines():
            if not line.strip():
                continue
            if line.startswith("  - "):
                if current_key:
                    val = line[4:].strip().strip('"').strip("'")
                    current_list.append(val)
                    result[current_key] = current_list
                continue
            m = re.match(r"^([\w-]+)\s*:\s*(.*)$", line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                # list start
                current_key = key
                current_list = []
                result[key] = current_list
            else:
                current_key = None
                current_list = []
                val = val.strip('"').strip("'")
                result[key] = val
        return result


def add_alias(content: str, old_url: str) -> str:
    """frontmatter 의 aliases 에 old_url 추가. 이미 있으면 그대로 반환."""
    fm_block, body = _split_frontmatter(content)
    if not fm_block:
        # frontmatter 없음 — 새로 만들어 추가
        return f"---\naliases:\n  - {old_url}\n---\n{content}"

    inner = fm_block.strip().strip("-").strip()
    lines = inner.splitlines()

    # aliases 섹션 위치 찾기
    alias_start = -1
    alias_end = -1  # exclusive
    for i, line in enumerate(lines):
        if alias_start == -1 and re.match(r"^aliases\s*:", line):
            alias_start = i
            # 다음 라인부터 list 항목 (들여쓰기 시작 또는 같은 줄에 inline)
            # 같은 줄에 inline 인 경우: aliases: ["/x", "/y"]
            after_colon = line.split(":", 1)[1].strip()
            if after_colon and after_colon.startswith("["):
                # inline list
                alias_end = i + 1
                if old_url in after_colon:
                    return content
                # 단순화: inline → 멀티라인으로 변환
                items = [x.strip().strip('"').strip("'")
                         for x in after_colon.strip("[]").split(",") if x.strip()]
                if old_url in items:
                    return content
                items.append(old_url)
                new_block = ["aliases:"] + [f"  - {it}" for it in items]
                lines[i:i + 1] = new_block
                alias_end = i + len(new_block)
            else:
                # 멀티라인 list 시작 — 이어지는 `  - ` 라인 수집
                j = i + 1
                while j < len(lines) and lines[j].startswith("  - "):
                    if lines[j][4:].strip().strip('"').strip("'") == old_url:
                        return content  # 이미 있음
                    j += 1
                alias_end = j
            break

    if alias_start == -1:
        # aliases 필드 없음 → frontmatter 끝에 추가
        new_lines = lines + ["aliases:", f"  - {old_url}"]
    else:
        # 멀티라인 list 끝에 추가
        new_lines = lines[:alias_end] + [f"  - {old_url}"] + lines[alias_end:]

    new_inner = "\n".join(new_lines).strip()
    new_fm = f"---\n{new_inner}\n---\n"
    return new_fm + body


# ─────────────────────────────────────────────────────────────────
# Migrate
# ─────────────────────────────────────────────────────────────────

def migrate_one(md_path: Path, content_root: Path, dry_run: bool = False) -> dict:
    """파일 1개 분류 + 이동 + alias 추가. blog/ 안에 있어야만 이동.

    Returns:
        {moved, from, to, tab, alias_added, dry_run}
    """
    md_path = Path(md_path)
    content_root = Path(content_root)

    raw = md_path.read_text(encoding="utf-8")
    fm_block, _body = _split_frontmatter(raw)
    fm = _parse_frontmatter_simple(fm_block)

    tab = classify(md_path.name, fm)

    # 현재 위치가 blog/ 가 아니면 이미 마이그레이션 됨 → noop
    try:
        rel = md_path.relative_to(content_root)
    except ValueError:
        return {"moved": False, "from": str(md_path), "to": "", "tab": tab,
                "alias_added": False, "dry_run": dry_run, "reason": "outside_content_root"}

    parts = rel.parts
    if len(parts) < 3 or parts[1] != "blog":
        return {"moved": False, "from": str(md_path), "to": str(md_path),
                "tab": tab, "alias_added": False, "dry_run": dry_run,
                "reason": "not_in_blog"}

    lang = parts[0]
    slug = md_path.stem
    new_dir = content_root / lang / tab
    new_path = new_dir / md_path.name
    old_url = f"/{lang}/blog/{slug}/"

    if dry_run:
        return {
            "moved": False, "from": str(md_path), "to": str(new_path),
            "tab": tab, "alias_added": False, "dry_run": True,
        }

    # alias 추가 → 새 위치로 이동
    new_content = add_alias(raw, old_url)
    new_dir.mkdir(parents=True, exist_ok=True)
    new_path.write_text(new_content, encoding="utf-8")
    if md_path.resolve() != new_path.resolve():
        md_path.unlink()

    return {
        "moved": True, "from": str(md_path), "to": str(new_path),
        "tab": tab, "alias_added": True, "dry_run": False,
    }


def migrate_all(content_root: Path, dry_run: bool = False) -> list[dict]:
    """모든 언어의 blog/ 디렉토리를 순회하며 이동."""
    content_root = Path(content_root)
    results = []
    if not content_root.exists():
        return results
    for lang_dir in sorted(content_root.iterdir()):
        if not lang_dir.is_dir():
            continue
        blog_dir = lang_dir / "blog"
        if not blog_dir.is_dir():
            continue
        for md_file in sorted(blog_dir.glob("*.md")):
            try:
                results.append(migrate_one(md_file, content_root=content_root, dry_run=dry_run))
            except Exception as e:
                logger.error(f"migrate failed {md_file}: {e}")
                results.append({"moved": False, "from": str(md_file), "error": str(e)})
    return results


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(description="3-tab content migration (study/daily/weekly)")
    parser.add_argument("--dry-run", action="store_true", help="실제 이동 없이 계획만 출력")
    parser.add_argument(
        "--content-root",
        default="/home/mh/ocstorage/workspace/nichproject/web/content",
        help="Hugo content/ 디렉토리",
    )
    args = parser.parse_args(argv)

    results = migrate_all(Path(args.content_root), dry_run=args.dry_run)
    by_tab: dict[str, int] = {}
    moved = 0
    for r in results:
        tab = r.get("tab", "?")
        by_tab[tab] = by_tab.get(tab, 0) + 1
        action = "PLAN" if args.dry_run else ("MOVED" if r.get("moved") else "skip")
        print(f"  [{action}] {tab}: {Path(r['from']).name}  →  {Path(r['to']).name if r.get('to') else '-'}")
        if r.get("moved"):
            moved += 1
    total = len(results)
    print(f"\n총 {total}개 분석. 이동: {moved}. 탭별 분포: {by_tab}")
    if args.dry_run:
        print("(--dry-run 이라 실제 이동은 하지 않았습니다.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
