"""
Hugo Publisher — content/blog/ 에 마크다운 파일 저장 후 빌드
"""

import logging
import re
import subprocess
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

logger = logging.getLogger(__name__)

HUGO_BIN = "/tmp/hugo"
HUGO_CONTENT_DIR = Path("/home/mh/ocstorage/workspace/nichproject/web/content/blog")
HUGO_SITE_DIR = Path("/home/mh/ocstorage/workspace/nichproject/web")


class _HTMLToMarkdown(HTMLParser):
    """stdlib만 사용하는 간단한 HTML → Markdown 변환기"""

    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "br", "hr", "blockquote"}
    INLINE_TAGS = {"strong", "b", "em", "i", "code"}

    def __init__(self):
        super().__init__()
        self.result = []
        self._tag_stack = []

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        if tag in ("h1", "h2"):
            self.result.append("\n## ")
        elif tag == "h3":
            self.result.append("\n### ")
        elif tag == "h4":
            self.result.append("\n#### ")
        elif tag == "p":
            self.result.append("\n")
        elif tag == "li":
            self.result.append("\n- ")
        elif tag == "br":
            self.result.append("\n")
        elif tag == "hr":
            self.result.append("\n---\n")
        elif tag in ("strong", "b"):
            self.result.append("**")
        elif tag in ("em", "i"):
            self.result.append("*")
        elif tag == "code":
            self.result.append("`")
        elif tag == "blockquote":
            self.result.append("\n> ")

    def handle_endtag(self, tag):
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()
        if tag in ("h1", "h2", "h3", "h4", "p", "li", "blockquote"):
            self.result.append("\n")
        elif tag in ("strong", "b"):
            self.result.append("**")
        elif tag in ("em", "i"):
            self.result.append("*")
        elif tag == "code":
            self.result.append("`")

    def handle_data(self, data):
        self.result.append(data)

    def get_markdown(self):
        md = "".join(self.result)
        md = re.sub(r'\n{3,}', '\n\n', md)
        return md.strip()


def html_to_markdown(html: str) -> str:
    parser = _HTMLToMarkdown()
    parser.feed(html)
    return parser.get_markdown()


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug[:80]


class HugoPublisher:
    def __init__(self, content_dir: Path = HUGO_CONTENT_DIR, site_dir: Path = HUGO_SITE_DIR):
        self.content_dir = content_dir
        self.site_dir = site_dir
        self.content_dir.mkdir(parents=True, exist_ok=True)

    def publish(self, title: str, content_html: str, tags: list[str] = None,
                meta_description: str = "", categories: list[str] = None) -> dict:
        slug = _slugify(title)
        filename = f"{slug}.md"
        filepath = self.content_dir / filename

        # 중복 방지
        if filepath.exists():
            import uuid
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
            filename = f"{slug}.md"
            filepath = self.content_dir / filename

        tags = tags or []
        categories = categories or ["투자", "재테크"]
        today = date.today().isoformat()

        tags_yaml = "\n".join(f'  - "{t}"' for t in tags)
        cats_yaml = "\n".join(f'  - "{c}"' for c in categories)

        content_md = html_to_markdown(content_html)

        frontmatter = f"""---
title: "{title}"
date: {today}
draft: false
description: "{meta_description}"
tags:
{tags_yaml}
categories:
{cats_yaml}
---

"""
        filepath.write_text(frontmatter + content_md, encoding="utf-8")
        logger.info(f"Hugo 파일 저장: {filepath}")

        # Hugo 빌드
        try:
            result = subprocess.run(
                [HUGO_BIN],
                cwd=self.site_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                logger.info("Hugo 빌드 완료")
            else:
                logger.warning(f"Hugo 빌드 경고: {result.stderr}")
        except Exception as e:
            logger.error(f"Hugo 빌드 실패: {e}")

        return {
            "url": f"/{slug}/",
            "filepath": str(filepath),
            "slug": slug,
        }
