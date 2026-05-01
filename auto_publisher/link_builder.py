"""
내부 링크 빌더 — 발행된 포스트 목록 읽어 관련 링크 자동 주입
- 다국어 지원: content/{lang}/blog/ + content/{lang}/analysis/
- 블로그 ↔ 분석 포스트 크로스 링크 (같은 티커)
"""

import re
from pathlib import Path

HUGO_CONTENT_ROOT = Path("/home/mh/ocstorage/workspace/nichproject/web/content")


def get_published_links(lang: str = "ko") -> list[dict]:
    """발행된 Hugo 포스트 목록 반환 (title, url, keywords, section, tickers)"""
    links = []
    for section in ("blog", "analysis", "study", "daily", "weekly"):
        section_dir = HUGO_CONTENT_ROOT / lang / section
        if not section_dir.exists():
            continue
        for md_file in section_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue

            title_match = re.search(r'^title:\s*"(.+)"', content, re.MULTILINE)
            if not title_match:
                continue

            title = title_match.group(1)
            slug = md_file.stem
            tags = re.findall(r'^\s+-\s+"(.+)"', content, re.MULTILINE)[:10]
            # 티커 추출 (대문자 알파벳 2~5자리, 정확한 매칭만)
            tickers = []
            text_upper = (title + " " + " ".join(tags)).upper()
            for t in ["VOO", "SPY", "QQQ", "QQQM", "SCHD", "JEPI", "JEPQ", "VT", "VTI",
                     "VXUS", "BND", "TLT", "GLD", "VYM", "SCHG", "SOXX", "SMH",
                     "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]:
                if re.search(rf'\b{t}\b', text_upper):
                    tickers.append(t)

            links.append({
                "title": title, "url": f"/{lang}/{section}/{slug}/",
                "keywords": tags, "section": section, "tickers": tickers,
            })
    return links


def inject_internal_links(content_html: str, current_slug: str,
                          links: list[dict], current_section: str = "blog",
                          current_tickers: list[str] = None) -> str:
    """
    본문 HTML에서 다른 포스트 키워드/티커 발견 시 내부 링크 삽입 (최대 3개)

    우선순위:
    1) 같은 티커의 반대 섹션 포스트 (블로그 ↔ 분석) — "심층분석 보기" 박스
    2) 같은 티커의 동일 섹션 포스트 (관련 글)
    3) 키워드 매칭 일반 포스트
    """
    if not links:
        return content_html

    current_tickers = current_tickers or []
    injected = 0
    used_urls: set[str] = set()

    # ─────────────────────────────────────────────
    # 1) 크로스 섹션 (블로그 → 분석 또는 분석 → 블로그) — 같은 티커
    # ─────────────────────────────────────────────
    cross_section = "analysis" if current_section == "blog" else "blog"
    cross_links = []
    for link in links:
        if link["section"] != cross_section:
            continue
        if link["url"].rstrip("/").endswith(current_slug.rstrip("/")):
            continue
        common_tickers = set(current_tickers) & set(link["tickers"])
        if common_tickers:
            cross_links.append((link, list(common_tickers)[0]))

    if cross_links:
        link, ticker = cross_links[0]
        section_label = "심층 분석" if cross_section == "analysis" else "실전 후기"
        cross_box = (
            f'\n<div class="related-cross-box" style="border:1px solid #e5e7eb;'
            f'border-radius:8px;padding:1em;margin:1.5em 0;background:#f9fafb;">'
            f'<strong>📊 {ticker} {section_label}도 읽어보세요</strong><br>'
            f'<a href="{link["url"]}" style="color:#2563eb;text-decoration:none;">'
            f'→ {link["title"]}</a>'
            f'</div>\n'
        )
        # 첫 번째 H2 닫는 태그 뒤에 삽입
        h2_pos = content_html.find("</h2>")
        if h2_pos != -1:
            pos = h2_pos + len("</h2>")
            content_html = content_html[:pos] + cross_box + content_html[pos:]
            used_urls.add(link["url"])
            injected += 1

    # ─────────────────────────────────────────────
    # 2~3) 키워드/티커 매칭 일반 인라인 링크
    # ─────────────────────────────────────────────
    for link in links:
        if injected >= 3:
            break
        if link["url"].rstrip("/").endswith(current_slug.rstrip("/")):
            continue
        if link["url"] in used_urls:
            continue

        for kw in link["keywords"]:
            if len(kw) < 3:
                continue
            pattern = re.compile(
                r'(?<!["\'/=\w])(' + re.escape(kw) + r')(?!["\'\w])'
            )
            anchor = f'<a href="{link["url"]}">{kw}</a>'
            if anchor in content_html:
                continue
            new_html, n = pattern.subn(anchor, content_html, count=1)
            if n > 0:
                content_html = new_html
                used_urls.add(link["url"])
                injected += 1
                break

    return content_html
