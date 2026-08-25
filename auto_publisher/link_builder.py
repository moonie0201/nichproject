"""
내부 링크 빌더 — 발행된 포스트 목록 읽어 관련 링크 자동 주입
- 다국어 지원: content/{lang}/blog/ + content/{lang}/analysis/
- 블로그 ↔ 분석 포스트 크로스 링크 (같은 티커)
- 점수 기반 후보 정렬 (티커 겹침 + 태그 Jaccard + recency)
"""

import re
from datetime import date, datetime
from pathlib import Path

HUGO_CONTENT_ROOT = Path("/home/mh/ocstorage/workspace/nichproject/web/content")

TICKER_VOCAB = [
    "VOO", "SPY", "QQQ", "QQQM", "SCHD", "JEPI", "JEPQ", "VT", "VTI",
    "VXUS", "BND", "TLT", "GLD", "VYM", "SCHG", "SOXX", "SMH",
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "TQQQ", "SQQQ",
    "DIA", "IVV", "VEA", "VWO", "AGG", "LQD", "HYG",
]


def _extract_date(content: str) -> date | None:
    m = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    except Exception:
        return None


def _extract_primary_keyword(content: str) -> str:
    m = re.search(r'^primary_keyword:\s*"(.+)"', content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def get_published_links(lang: str = "ko") -> list[dict]:
    """발행된 Hugo 포스트 목록 반환 (title, url, keywords, section, tickers, date, primary_keyword)"""
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
            text_upper = (title + " " + " ".join(tags)).upper()
            tickers = [t for t in TICKER_VOCAB if re.search(rf'\b{t}\b', text_upper)]

            links.append({
                "title": title,
                "url": f"/{lang}/{section}/{slug}/",
                "keywords": tags,
                "section": section,
                "tickers": tickers,
                "date": _extract_date(content),
                "primary_keyword": _extract_primary_keyword(content),
            })
    return links


def _recency_score(post_date: date | None, today: date | None = None) -> float:
    """발행일 기반 0-1 점수. 7일 이내 1.0, 30일 0.5, 90일 0.2, 그 외 0.0."""
    if not post_date:
        return 0.0
    today = today or date.today()
    age_days = max((today - post_date).days, 0)
    if age_days <= 7: return 1.0
    if age_days <= 30: return 0.5
    if age_days <= 90: return 0.2
    return 0.0


def _link_score(
    candidate: dict,
    current_tickers: list[str],
    current_keywords: list[str],
    current_primary_kw: str,
) -> float:
    """후보 링크 점수 (높을수록 우선). 0-100."""
    cand_tickers = set(candidate.get("tickers") or [])
    cand_keywords = set(k.lower() for k in (candidate.get("keywords") or []))
    cur_t = set(current_tickers or [])
    cur_k = set(k.lower() for k in (current_keywords or []))

    # 티커 겹침: 0-40점 (강한 신호)
    ticker_overlap = len(cur_t & cand_tickers)
    ticker_score = min(40.0, ticker_overlap * 25.0)

    # 태그 Jaccard: 0-30점
    if cur_k and cand_keywords:
        intersection = cur_k & cand_keywords
        union = cur_k | cand_keywords
        jaccard = len(intersection) / max(len(union), 1)
        tag_score = min(30.0, jaccard * 60.0)
    else:
        tag_score = 0.0

    # Recency: 0-20점
    rec_score = _recency_score(candidate.get("date")) * 20.0

    # primary_keyword 매칭 보너스: 10점
    cand_pk = (candidate.get("primary_keyword") or "").lower()
    pk_bonus = 10.0 if cand_pk and cand_pk == (current_primary_kw or "").lower() else 0.0

    return ticker_score + tag_score + rec_score + pk_bonus


_TAG_SPLIT = re.compile(r"(<[^>]*>)")


def _sub_in_text_only(pattern: "re.Pattern", anchor: str, html: str) -> tuple[str, int]:
    """태그 밖 텍스트에서만 1회 치환한다. 반환: (결과, 치환 수).

    예전에는 `pattern.subn(anchor, html, count=1)` 로 문서 전체에 돌렸다.
    룩비하인드 `(?<!["\\'/=\\w])` 로 속성 안을 피하려 했지만, 슬러그처럼
    앞 글자가 하이픈이면 그냥 통과한다:
        href="/ko/study/irp-세액공제-한도-.../"
                        ^ 여기 '세액공제' 가 치환돼 href 값이 마크업으로 깨졌다
        → href="/ko/study/irp-<a href="">세액공제</a>-한도-.../"
    실제로 5개 언어 16개 파일이 이렇게 망가졌다. 태그와 텍스트를 갈라
    텍스트 조각에서만 치환하고, 이미 <a> 안이면 건너뛴다(중첩 앵커 금지).
    """
    parts = _TAG_SPLIT.split(html)
    depth = 0
    for i, part in enumerate(parts):
        if part.startswith("<"):
            low = part.lower()
            if low.startswith("<a") and not low.startswith("</a"):
                depth += 1
            elif low.startswith("</a"):
                depth = max(0, depth - 1)
            continue
        if depth:                      # 이미 링크 안 — 중첩 금지
            continue
        new, n = pattern.subn(anchor, part, count=1)
        if n:
            parts[i] = new
            return "".join(parts), 1
    return html, 0


def inject_internal_links(
    content_html: str,
    current_slug: str,
    links: list[dict],
    current_section: str = "blog",
    current_tickers: list[str] = None,
    current_keywords: list[str] = None,
    current_primary_keyword: str = "",
    max_links: int = 5,
) -> str:
    """
    본문 HTML에서 관련 포스트 링크 자동 주입 (점수 기반 정렬, 최대 max_links개).

    Strategy:
    1) 크로스 섹션 (blog↔analysis 같은 티커) — "심층 분석" 박스 (최대 1)
    2) 점수 기반 인라인 키워드 링크 (티커 + 태그 Jaccard + recency + primary_keyword 매치)
    3) 자기 자신/이미 링크된 URL/현재 primary_keyword 앵커 회피
    """
    if not links:
        return content_html

    current_tickers = current_tickers or []
    current_keywords = current_keywords or []
    current_pk_norm = (current_primary_keyword or "").lower().strip()
    injected = 0
    used_urls: set[str] = set()
    used_anchors: set[str] = set()

    # 자기 자신 제거
    candidates = [
        l for l in links
        if not l["url"].rstrip("/").endswith(current_slug.rstrip("/"))
    ]

    # 1) 크로스 섹션 박스 (최대 1)
    cross_section = "analysis" if current_section == "blog" else "blog"
    cross_links = []
    for link in candidates:
        if link["section"] != cross_section:
            continue
        common_tickers = set(current_tickers) & set(link.get("tickers") or [])
        if common_tickers:
            cross_links.append((link, list(common_tickers)[0]))
    if cross_links:
        # 가장 최근 발행 + 점수 높은 것 우선
        cross_links.sort(
            key=lambda lt: _link_score(lt[0], current_tickers, current_keywords, current_primary_keyword),
            reverse=True,
        )
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
        h2_pos = content_html.find("</h2>")
        if h2_pos != -1:
            pos = h2_pos + len("</h2>")
            content_html = content_html[:pos] + cross_box + content_html[pos:]
            used_urls.add(link["url"])
            injected += 1

    # 2) 인라인 키워드 링크 — 점수 정렬
    scored = [
        (_link_score(l, current_tickers, current_keywords, current_primary_keyword), l)
        for l in candidates
        if l["url"] not in used_urls
    ]
    scored.sort(key=lambda x: x[0], reverse=True)

    for score, link in scored:
        if injected >= max_links:
            break
        if score < 5.0:  # 점수 너무 낮으면 스킵 (스팸 링크 방지)
            continue
        if link["url"] in used_urls:
            continue

        # 앵커 텍스트 후보: keywords + primary_keyword
        anchor_candidates = []
        if link.get("primary_keyword"):
            anchor_candidates.append(link["primary_keyword"])
        anchor_candidates.extend(link.get("keywords") or [])

        for kw in anchor_candidates:
            if not kw or len(kw) < 3:
                continue
            kw_norm = kw.lower().strip()
            # 현재 글의 primary_keyword와 같은 앵커 회피 (자기-키워드 카니발 방지)
            if kw_norm == current_pk_norm:
                continue
            if kw_norm in used_anchors:
                continue
            pattern = re.compile(
                r'(?<!["\'/=\w])(' + re.escape(kw) + r')(?!["\'\w])'
            )
            anchor = f'<a href="{link["url"]}">{kw}</a>'
            if anchor in content_html:
                continue
            new_html, n = _sub_in_text_only(pattern, anchor, content_html)
            if n > 0:
                content_html = new_html
                used_urls.add(link["url"])
                used_anchors.add(kw_norm)
                injected += 1
                break

    return content_html
