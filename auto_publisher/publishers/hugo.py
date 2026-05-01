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

import os

HUGO_BIN = "/tmp/hugo"
HUGO_SITE_DIR = Path("/home/mh/ocstorage/workspace/nichproject/web")


def _content_dir(lang: str = "ko", section: str = "blog") -> Path:
    return HUGO_SITE_DIR / "content" / lang / section


CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_PROJECT_NAME = os.getenv("CLOUDFLARE_PAGES_PROJECT", "invest-korea")


class _HTMLToMarkdown(HTMLParser):
    """stdlib만 사용하는 HTML → Markdown 변환기.
    img는 ![alt](src)로, table/figure/aside/div/script는 raw HTML 유지 (Hugo unsafe=true 활용)
    """

    # raw HTML로 보존할 블록 (Hugo의 unsafe 렌더링이 그대로 통과시킴)
    PRESERVE_TAGS = {
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "caption",
        "colgroup",
        "col",
        "figure",
        "figcaption",
        "aside",
        "div",
        "section",
        "script",
        "style",
        "iframe",
    }

    def __init__(self):
        super().__init__()
        self.result = []
        self._tag_stack = []
        self._preserve_depth = 0  # PRESERVE_TAGS 안에 있을 때 raw 유지

    def _attrs_to_str(self, attrs):
        return "".join(f' {k}="{v}"' for k, v in attrs if v is not None)

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        # 보존 태그는 raw HTML 그대로
        if tag in self.PRESERVE_TAGS:
            self._preserve_depth += 1
            self.result.append(f"<{tag}{self._attrs_to_str(attrs)}>")
            return
        # 보존 블록 안에서는 img 포함 모든 inline 태그를 raw 유지
        # (Hugo가 figure/div 안의 markdown을 처리하지 않으므로 raw HTML 필수)
        if self._preserve_depth > 0:
            self.result.append(f"<{tag}{self._attrs_to_str(attrs)}>")
            return
        # 보존 블록 밖의 img는 마크다운 이미지로 변환
        if tag == "img":
            d = dict(attrs)
            src = d.get("src", "")
            alt = d.get("alt", "")
            self.result.append(f"\n![{alt}]({src})\n")
            return
        # 일반 변환
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
        elif tag == "a":
            d = dict(attrs)
            self._tag_stack[-1] = ("a", d.get("href", ""))

    def handle_startendtag(self, tag, attrs):
        # <img />, <br /> 등 자기 닫는 태그
        if tag == "img":
            self.handle_starttag(tag, attrs)
            return
        if tag == "br":
            self.result.append("\n")
            return
        if self._preserve_depth > 0 or tag in self.PRESERVE_TAGS:
            self.result.append(f"<{tag}{self._attrs_to_str(attrs)} />")

    def handle_endtag(self, tag):
        # 스택에서 제거 (a 튜플 처리 포함)
        if self._tag_stack:
            top = self._tag_stack[-1]
            if (isinstance(top, tuple) and top[0] == tag) or top == tag:
                self._tag_stack.pop()
        # 보존 태그 닫기
        if tag in self.PRESERVE_TAGS:
            self.result.append(f"</{tag}>")
            self._preserve_depth = max(0, self._preserve_depth - 1)
            return
        if self._preserve_depth > 0:
            self.result.append(f"</{tag}>")
            return
        if tag in ("h1", "h2", "h3", "h4", "p", "li", "blockquote"):
            self.result.append("\n")
        elif tag in ("strong", "b"):
            self.result.append("**")
        elif tag in ("em", "i"):
            self.result.append("*")
        elif tag == "code":
            self.result.append("`")
        elif tag == "a":
            # 가장 최근 a 링크 정보가 스택 어딘가에 있었음 (이미 pop됨) → 단순 텍스트만
            pass

    def handle_data(self, data):
        # a 태그 내부면 [text](href) 형식으로 마크다운 링크 변환
        if (
            (not self._preserve_depth)
            and self._tag_stack
            and isinstance(self._tag_stack[-1], tuple)
            and self._tag_stack[-1][0] == "a"
        ):
            href = self._tag_stack[-1][1]
            self.result.append(f"[{data}]({href})")
        else:
            self.result.append(data)

    def get_markdown(self):
        md = "".join(self.result)
        md = re.sub(r"\n{3,}", "\n\n", md)
        return md.strip()


def html_to_markdown(html: str) -> str:
    parser = _HTMLToMarkdown()
    parser.feed(html)
    return parser.get_markdown()


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


def _build_faq_jsonld(schema_faq: list[dict]) -> str:
    """FAQ JSON-LD 스크립트 블록 생성"""
    import json as _json

    entities = [
        {
            "@type": "Question",
            "name": item["question"],
            "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
        }
        for item in schema_faq
        if item.get("question") and item.get("answer")
    ]
    if not entities:
        return ""
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities,
    }
    return f'\n<script type="application/ld+json">\n{_json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>\n'


def _build_article_jsonld(
    title: str,
    description: str,
    lang: str,
    slug: str,
    section: str,
    og_image: str = "",
    today: str = "",
) -> str:
    """Article JSON-LD — author + datePublished + image (E-E-A-T 신호)"""
    import json as _json
    from auto_publisher.content_generator import _load_persona

    # 저자 = 조직(InvestIQs Research). E-E-A-T는 Organization + Publisher로 표현.
    persona = _load_persona(lang)
    author_name = persona.get("name", "InvestIQs Research")
    author_url = f"https://investiqs.net/{lang}/about/"
    author_type = "Organization"

    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": today,
        "dateModified": today,
        "author": {
            "@type": author_type,
            "name": author_name,
            "url": author_url,
        },
        "publisher": {
            "@type": "Organization",
            "name": "InvestIQs",
            "url": "https://investiqs.net/",
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://investiqs.net/{lang}/{section}/{slug}/",
        },
    }
    if og_image:
        article["image"] = (
            f"https://investiqs.net{og_image}" if og_image.startswith("/") else og_image
        )
    return f'\n<script type="application/ld+json">\n{_json.dumps(article, ensure_ascii=False, indent=2)}\n</script>\n'


class HugoPublisher:
    def __init__(
        self, lang: str = "ko", site_dir: Path = HUGO_SITE_DIR, section: str = "blog"
    ):
        self.lang = lang
        self.section = section
        self.content_dir = _content_dir(lang, section)
        self.site_dir = site_dir
        self.content_dir.mkdir(parents=True, exist_ok=True)

    def publish_raw_markdown(
        self,
        content: str,
        slug: str,
        section: str = "daily",
    ) -> dict:
        """미리 완성된 마크다운(frontmatter 포함)을 직접 발행 후 Hugo 빌드 + Cloudflare 배포."""
        target_dir = _content_dir(self.lang, section)
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / f"{slug}.md"
        if filepath.exists():
            import uuid

            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
            filepath = target_dir / f"{slug}.md"
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Hugo raw markdown 저장: {filepath}")

        try:
            result = subprocess.run(
                [HUGO_BIN, "--cleanDestinationDir", "--gc", "--minify"],
                cwd=self.site_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.warning(f"Hugo 빌드 경고: {result.stderr}")
            else:
                logger.info("Hugo 빌드 완료")
        except Exception as e:
            logger.error(f"Hugo 빌드 실패: {e}")

        if CLOUDFLARE_API_TOKEN:
            try:
                env = {**os.environ, "CLOUDFLARE_API_TOKEN": CLOUDFLARE_API_TOKEN}
                deploy = subprocess.run(
                    [
                        "npx",
                        "wrangler",
                        "pages",
                        "deploy",
                        "public",
                        "--project-name",
                        CLOUDFLARE_PROJECT_NAME,
                        "--commit-dirty=true",
                    ],
                    cwd=self.site_dir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
                if deploy.returncode == 0:
                    logger.info("Cloudflare Pages 배포 완료")
                else:
                    logger.warning(f"Cloudflare 배포 경고: {deploy.stderr}")
            except Exception as e:
                logger.error(f"Cloudflare 배포 실패: {e}")

        return {
            "url": f"/{self.lang}/{section}/{slug}/",
            "filepath": str(filepath),
            "slug": slug,
        }

    def publish(
        self,
        title: str,
        content_html: str,
        tags: list[str] = None,
        meta_description: str = "",
        categories: list[str] = None,
        primary_keyword: str = "",
        keywords_long_tail: list[str] = None,
        schema_faq: list[dict] = None,
        content_type: str = "guide",
        ticker: str = "",
        mkt_data: dict = None,
    ) -> dict:
        slug = _slugify(title)
        filename = f"{slug}.md"

        # 3-탭 자동 라우팅: 호출 시 self.section 이 기본값("blog") 이면 콘텐츠 분류기로 결정.
        # 호출자가 명시적으로 다른 section 을 지정한 경우(=daily/weekly/study)는 그대로 사용.
        try:
            from auto_publisher.migrate_content_tabs import classify

            tentative_fm = {
                "title": title,
                "categories": categories or [],
                "schema": "",  # schema_type 은 아래에서 결정되므로 카테고리/제목 기준만 사용
            }
            auto_section = classify(filename, tentative_fm)
            if self.section == "blog":
                # 기본값일 때만 자동 라우팅 적용
                self.section = auto_section
                self.content_dir = _content_dir(self.lang, auto_section)
                self.content_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"section 자동 라우팅 실패, 기본값 유지: {e}")

        filepath = self.content_dir / filename

        # 중복 방지
        if filepath.exists():
            import uuid

            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
            filename = f"{slug}.md"
            filepath = self.content_dir / filename

        tags = tags or []
        from auto_publisher.content_generator import CATEGORIES_BY_LANG

        categories = categories or CATEGORIES_BY_LANG.get(
            self.lang, ["Investing", "Personal Finance"]
        )
        keywords_long_tail = keywords_long_tail or []
        schema_faq = schema_faq or []
        today = date.today().isoformat()

        tags_yaml = "\n".join(f'  - "{t}"' for t in tags)
        cats_yaml = "\n".join(f'  - "{c}"' for c in categories)
        kw_str = (
            ", ".join([primary_keyword] + keywords_long_tail[:8])
            if primary_keyword
            else ", ".join(tags[:8])
        )

        # schema 타입 매핑
        schema_map = {
            "guide": "HowTo",
            "comparison": "Article",
            "analysis": "Article",
            "howto": "HowTo",
        }
        # [수정] JSON-LD 주입을 여기서 제거 (Article/FAQ JSON-LD는 Hugo 템플릿에서 처리)
        schema_type = schema_map.get(content_type, "Article")

        # 차트 생성 및 주입
        category = categories[0] if categories else ("재테크 기초" if self.lang == "ko" else "ETF")
        og_image_path = ""  # OG 이미지로 사용할 첫 차트 경로
        try:
            from auto_publisher.chart_generator import (
                generate_charts,
                generate_analysis_charts,
                inject_charts_into_html,
            )

            if content_type == "analysis" and ticker:
                charts = generate_analysis_charts(
                    slug=slug, ticker=ticker, mkt_data=mkt_data
                )
            else:
                charts = generate_charts(
                    slug=slug, category=category, keywords=tags, lang=self.lang
                )
            if charts:
                content_html = inject_charts_into_html(content_html, charts)
                og_image_path = charts[0].get("path", "")
        except Exception as e:
            logger.warning(f"차트 생성 건너뜀: {e}")

        # 내부 링크 주입 (다국어 + 섹션 + 티커 크로스링크)
        from auto_publisher.link_builder import (
            get_published_links,
            inject_internal_links,
        )

        published_links = get_published_links(lang=self.lang)
        # 현재 포스트에서 티커 추출 (태그 + 키워드)
        import re as _re

        text_for_tickers = (title + " " + " ".join(tags) + " " + (ticker or "")).upper()
        current_tickers = [
            t
            for t in [
                "VOO",
                "SPY",
                "QQQ",
                "QQQM",
                "SCHD",
                "JEPI",
                "JEPQ",
                "VT",
                "VTI",
                "VXUS",
                "BND",
                "TLT",
                "GLD",
                "VYM",
                "SCHG",
                "SOXX",
                "SMH",
                "AAPL",
                "MSFT",
                "NVDA",
                "TSLA",
            ]
            if _re.search(rf"\b{t}\b", text_for_tickers)
        ]
        content_html = inject_internal_links(
            content_html,
            slug,
            published_links,
            current_section=self.section,
            current_tickers=current_tickers,
        )

        content_md = html_to_markdown(content_html)

        # JSON-LD 주입 제거 완료. FAQ는 Hugo에서 별도 처리.
        faq_block = ""

        # OG 이미지 (PaperMod cover) — 차트 있으면 자동 사용
        cover_block = ""
        if og_image_path:
            cover_block = f"""cover:
    image: "{og_image_path}"
    alt: "{title}"
    relative: false
"""

        frontmatter = f"""---
title: "{title}"
date: {today}
lastmod: {today}
draft: false
reviewed: true
description: "{meta_description}"
keywords: "{kw_str}"
primary_keyword: "{primary_keyword}"
schema: "{schema_type}"
toc: true
{cover_block}tags:
{tags_yaml}
categories:
{cats_yaml}
---

"""
        from auto_publisher.content_generator import fix_html_block_spacing

        body = fix_html_block_spacing(content_md + faq_block)
        filepath.write_text(frontmatter + body, encoding="utf-8")
        logger.info(f"Hugo 파일 저장: {filepath}")

        # Hugo 빌드
        try:
            result = subprocess.run(
                [HUGO_BIN, "--cleanDestinationDir", "--gc", "--minify"],
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

        # Cloudflare Pages 자동 배포
        if CLOUDFLARE_API_TOKEN:
            try:
                env = {**os.environ, "CLOUDFLARE_API_TOKEN": CLOUDFLARE_API_TOKEN}
                deploy = subprocess.run(
                    [
                        "npx",
                        "wrangler",
                        "pages",
                        "deploy",
                        "public",
                        "--project-name",
                        CLOUDFLARE_PROJECT_NAME,
                        "--commit-dirty=true",
                    ],
                    cwd=self.site_dir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
                if deploy.returncode == 0:
                    logger.info("Cloudflare Pages 배포 완료")
                else:
                    logger.warning(f"Cloudflare 배포 경고: {deploy.stderr}")
            except Exception as e:
                logger.error(f"Cloudflare 배포 실패: {e}")

        return {
            "url": f"/{self.lang}/{self.section}/{slug}/",
            "filepath": str(filepath),
            "slug": slug,
        }
