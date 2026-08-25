#!/usr/bin/env python3
"""Build and optionally send the InvestIQs weekly Stibee newsletter.

The script intentionally stays dependency-light so it can run from cron, n8n,
or a local shell in the Hugo repository.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


KST = timezone(timedelta(hours=9))
DEFAULT_CONTENT_DIRS = (
    "web/content/ko/daily",
    "web/content/ko/study",
    "web/content/ko/blog",
)
DEFAULT_OUTPUT_DIR = "newsletter/out"
DEFAULT_HUGO_ARCHIVE_DIR = "web/content/ko/newsletter"
SITE_BASE_URL = os.getenv("NEWSLETTER_SITE_BASE_URL", "https://investiqs.net").rstrip("/")
DISCLAIMER = (
    "본 뉴스레터는 정보 제공 목적이며 특정 금융상품의 매수·매도 권유가 아닙니다. "
    "투자 판단과 책임은 독자 본인에게 있습니다."
)


@dataclass
class Post:
    title: str
    description: str
    date: datetime
    path: str
    url: str
    section: str
    tags: list[str]
    body_excerpt: str


@dataclass
class NewsletterIssue:
    subject: str
    preview: str
    generated_at: str
    period_start: str
    period_end: str
    posts: list[Post]
    markdown: str
    html: str


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", raw, re.DOTALL)
    if not match:
        return {}, raw

    frontmatter: dict[str, Any] = {}
    lines = match.group(1).splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            idx += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            values: list[str] = []
            idx += 1
            while idx < len(lines) and lines[idx].startswith("  - "):
                values.append(clean_scalar(lines[idx][4:].strip()))
                idx += 1
            frontmatter[key] = values
            continue
        frontmatter[key] = clean_scalar(value)
        idx += 1
    return frontmatter, match.group(2)


def clean_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [clean_scalar(part.strip()) for part in value[1:-1].split(",") if part.strip()]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value


def parse_date(value: Any, fallback_path: Path) -> datetime:
    if isinstance(value, str) and value:
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=KST)
        except ValueError:
            pass
    return datetime.fromtimestamp(fallback_path.stat().st_mtime, tz=KST)


def slug_to_url(path: Path, root: Path) -> str:
    rel = path.relative_to(root / "web" / "content")
    parts = list(rel.parts)
    filename = parts[-1]
    slug = filename[:-3] if filename.endswith(".md") else filename
    if slug == "_index":
        slug = ""
    parts[-1] = slug
    clean_parts = [part for part in parts if part]
    return "/" + "/".join(clean_parts).strip("/") + "/"


def strip_markdown(markdown: str) -> str:
    text = re.sub(r"<[^>]+>", " ", markdown)
    text = re.sub(r"!\[[^\]]*]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*_`|~-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def excerpt(text: str, limit: int = 180) -> str:
    clean = strip_markdown(text)
    if len(clean) <= limit:
        return clean
    return clean[:limit].rsplit(" ", 1)[0] + "..."


def load_posts(root: Path, content_dirs: list[str], days: int, limit: int) -> list[Post]:
    cutoff = datetime.now(KST) - timedelta(days=days)
    posts: list[Post] = []
    for content_dir in content_dirs:
        base = root / content_dir
        if not base.exists():
            continue
        for path in base.rglob("*.md"):
            if path.name == "_index.md":
                continue
            raw = path.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(raw)
            post_date = parse_date(frontmatter.get("date") or frontmatter.get("lastmod"), path)
            if post_date < cutoff:
                continue
            draft = str(frontmatter.get("draft", "false")).lower() == "true"
            if draft:
                continue
            tags = frontmatter.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            section = path.relative_to(root / "web" / "content" / "ko").parts[0]
            posts.append(
                Post(
                    title=str(frontmatter.get("title") or path.stem),
                    description=str(frontmatter.get("description") or excerpt(body, 140)),
                    date=post_date,
                    path=str(path.relative_to(root)),
                    url=slug_to_url(path, root),
                    section=section,
                    tags=[str(tag) for tag in tags],
                    body_excerpt=excerpt(body),
                )
            )
    posts.sort(key=lambda post: post.date, reverse=True)
    return posts[:limit]


def group_posts(posts: list[Post]) -> dict[str, list[Post]]:
    grouped: dict[str, list[Post]] = {"daily": [], "study": [], "blog": [], "other": []}
    for post in posts:
        grouped.setdefault(post.section, grouped["other"]).append(post)
    return grouped


def build_issue(posts: list[Post], days: int) -> NewsletterIssue:
    now = datetime.now(KST)
    period_start = now - timedelta(days=days)
    subject = f"재테크 선배의 편지: 이번 주 투자 체크포인트 {len(posts)}개"
    preview = posts[0].description[:90] if posts else "이번 주 InvestIQs 신규 콘텐츠 요약"
    grouped = group_posts(posts)

    lines = [
        f"# {subject}",
        "",
        f"발행일: {now.strftime('%Y-%m-%d %H:%M KST')}",
        "",
        "안녕하세요. 이번 주 InvestIQs에서 발행한 투자·절세 콘텐츠를 핵심만 추려 보냈습니다.",
        "",
    ]
    for section, label in (
        ("daily", "시장 브리핑"),
        ("study", "심층 분석"),
        ("blog", "기초 가이드"),
        ("other", "추천 콘텐츠"),
    ):
        section_posts = grouped.get(section) or []
        if not section_posts:
            continue
        lines.extend([f"## {label}", ""])
        for post in section_posts:
            tags = f" · {' / '.join(post.tags[:3])}" if post.tags else ""
            lines.extend(
                [
                    f"### [{post.title}]({SITE_BASE_URL}{post.url})",
                    f"- 날짜: {post.date.astimezone(KST).strftime('%Y-%m-%d')}{tags}",
                    f"- 요약: {post.description or post.body_excerpt}",
                    f"- 읽기: {SITE_BASE_URL}{post.url}",
                    "",
                ]
            )

    lines.extend(["---", "", DISCLAIMER, ""])
    markdown = "\n".join(lines)
    html_body = markdown_to_email_html(markdown)
    return NewsletterIssue(
        subject=subject,
        preview=preview,
        generated_at=now.isoformat(),
        period_start=period_start.date().isoformat(),
        period_end=now.date().isoformat(),
        posts=posts,
        markdown=markdown,
        html=html_body,
    )


def markdown_to_email_html(markdown: str) -> str:
    html_lines = [
        '<div style="font-family:Arial,Helvetica,sans-serif;line-height:1.65;color:#1f2937;max-width:680px;margin:0 auto;">'
    ]
    in_list = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if line == "---":
            html_lines.append('<hr style="border:none;border-top:1px solid #e5e7eb;margin:28px 0;">')
            continue
        if line.startswith("# "):
            html_lines.append(f"<h1>{inline_markdown(line[2:])}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{inline_markdown(line[3:])}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{inline_markdown(line[4:])}</h3>")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{inline_markdown(line[2:])}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{inline_markdown(line)}</p>")
    if in_list:
        html_lines.append("</ul>")
    html_lines.append("</div>")
    return "\n".join(html_lines)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(
        r"\[([^\]]+)]\(([^)]+)\)",
        r'<a href="\2" style="color:#2563eb;text-decoration:none;">\1</a>',
        escaped,
    )


def write_outputs(root: Path, issue: NewsletterIssue, output_dir: str) -> dict[str, str]:
    out_dir = root / output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(KST).strftime("%Y-%m-%d")
    base = out_dir / f"weekly-{stamp}"

    md_path = base.with_suffix(".md")
    html_path = base.with_suffix(".html")
    json_path = base.with_suffix(".json")
    csv_path = base.with_suffix(".csv")

    md_path.write_text(issue.markdown, encoding="utf-8")
    html_path.write_text(issue.html, encoding="utf-8")
    post_payload = []
    for post in issue.posts:
        payload = asdict(post)
        payload["date"] = post.date.astimezone(KST).isoformat()
        post_payload.append(payload)
    json_path.write_text(
        json.dumps(
            {
                "subject": issue.subject,
                "preview": issue.preview,
                "generated_at": issue.generated_at,
                "period_start": issue.period_start,
                "period_end": issue.period_end,
                "posts": post_payload,
                "markdown": issue.markdown,
                "html": issue.html,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["title", "date", "section", "url", "description"])
        writer.writeheader()
        for post in issue.posts:
            writer.writerow(
                {
                    "title": post.title,
                    "date": post.date.astimezone(KST).date().isoformat(),
                    "section": post.section,
                    "url": f"{SITE_BASE_URL}{post.url}",
                    "description": post.description,
                }
            )
    return {
        "markdown": str(md_path),
        "html": str(html_path),
        "json": str(json_path),
        "csv": str(csv_path),
    }


def publish_hugo_archive(root: Path, issue: NewsletterIssue, archive_dir: str) -> str:
    target_dir = root / archive_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(KST).strftime("%Y-%m-%d")
    target = target_dir / f"weekly-{stamp}.md"
    frontmatter = "\n".join(
        [
            "---",
            f'title: "{issue.subject}"',
            f'date: {datetime.now(KST).isoformat()}',
            "draft: false",
            'type: "newsletter"',
            f'description: "{issue.preview}"',
            "---",
            "",
        ]
    )
    target.write_text(frontmatter + issue.markdown, encoding="utf-8")
    return str(target)


def send_to_stibee(issue: NewsletterIssue) -> dict[str, Any]:
    api_key = os.getenv("STIBEE_API_KEY")
    list_id = os.getenv("STIBEE_LIST_ID")
    if not api_key or not list_id:
        raise RuntimeError("STIBEE_API_KEY and STIBEE_LIST_ID are required for --send-stibee")

    endpoint = os.getenv(
        "STIBEE_CAMPAIGN_ENDPOINT",
        f"https://api.stibee.com/v1/lists/{list_id}/campaigns",
    )
    payload = {
        "subject": issue.subject,
        "previewText": issue.preview,
        "content": issue.html,
        "senderName": os.getenv("STIBEE_SENDER_NAME", "InvestIQs Weekly"),
        "senderEmail": os.getenv("STIBEE_SENDER_EMAIL", "weekly@investiqs.com"),
        "sendTimeType": os.getenv("STIBEE_SEND_TIME_TYPE", "draft"),
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "AccessToken": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return {"status": response.status, "body": json.loads(body) if body else {}}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Stibee API error {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Stibee API connection failed: {exc.reason}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Curate Hugo posts into a weekly Stibee newsletter.")
    parser.add_argument("--root", default=".", help="Project root containing web/content")
    parser.add_argument("--days", type=int, default=7, help="Lookback window for recent posts")
    parser.add_argument("--limit", type=int, default=8, help="Maximum posts to include")
    parser.add_argument("--content-dir", action="append", dest="content_dirs", help="Content dir to scan")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--publish-hugo", action="store_true", help="Write archive page into Hugo content")
    parser.add_argument("--hugo-archive-dir", default=DEFAULT_HUGO_ARCHIVE_DIR)
    parser.add_argument("--send-stibee", action="store_true", help="Create/send a Stibee campaign")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    content_dirs = args.content_dirs or list(DEFAULT_CONTENT_DIRS)
    posts = load_posts(root, content_dirs, args.days, args.limit)
    issue = build_issue(posts, args.days)
    outputs = write_outputs(root, issue, args.output_dir)
    result: dict[str, Any] = {
        "success": True,
        "post_count": len(posts),
        "subject": issue.subject,
        "outputs": outputs,
    }
    if args.publish_hugo:
        result["hugo_archive"] = publish_hugo_archive(root, issue, args.hugo_archive_dir)
    if args.send_stibee:
        result["stibee"] = send_to_stibee(issue)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
