"""SEO 검증기 — 발행 전 콘텐츠 SEO 품질 게이트.

Hard 위반: H1 count != 1, primary_keyword 미포함 in title → 발행 차단
Soft 위반: 길이/밀도/구조 권장사항 미달 → 경고만, frontmatter에 audit 결과 기록

Env gate: SEO_VALIDATOR_ENABLED=1 (기본 OFF). OFF면 hard도 soft 취급.

사용:
    from auto_publisher.seo_validator import validate_seo, SEOValidationError
    report = validate_seo(title, body_md, primary_keyword, meta_description)
    if report.hard_violations:
        raise SEOValidationError(report)
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from auto_publisher.content_generator import _normalize_keyword_for_match

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
SEO_FAILURES_PATH = DATA_DIR / "seo_failures.json"


@dataclass
class SEOReport:
    score: float
    hard_violations: list[str] = field(default_factory=list)
    soft_violations: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def to_yaml_block(self) -> str:
        lines = ["seo_audit:"]
        lines.append(f"  score: {self.score:.1f}")
        if self.hard_violations:
            lines.append("  hard_violations:")
            for v in self.hard_violations:
                lines.append(f"    - {json.dumps(v, ensure_ascii=False)}")
        else:
            lines.append("  hard_violations: []")
        if self.soft_violations:
            lines.append("  soft_violations:")
            for v in self.soft_violations:
                lines.append(f"    - {json.dumps(v, ensure_ascii=False)}")
        else:
            lines.append("  soft_violations: []")
        return "\n".join(lines) + "\n"


class SEOValidationError(Exception):
    def __init__(self, report: SEOReport):
        self.report = report
        super().__init__(f"SEO hard fail: {report.hard_violations}")


_H1_RE = re.compile(r"^#\s+.+$|<h1[^>]*>", re.MULTILINE | re.IGNORECASE)
_H2_RE = re.compile(r"^##\s+.+$|<h2[^>]*>(.*?)</h2>", re.MULTILINE | re.IGNORECASE | re.DOTALL)
_H3_RE = re.compile(r"^###\s+.+$|<h3[^>]*>(.*?)</h3>", re.MULTILINE | re.IGNORECASE | re.DOTALL)
_HEADING_TEXT_RE = re.compile(r"<h([23])[^>]*>(.*?)</h\1>|^(#{2,3})\s+(.+)$", re.MULTILINE | re.IGNORECASE | re.DOTALL)
_IMG_RE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
_ALT_RE = re.compile(r'\balt\s*=\s*"([^"]*)"', re.IGNORECASE)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(s: str) -> str:
    return _WS_RE.sub(" ", _TAG_STRIP_RE.sub(" ", s)).strip()


def _heading_texts(body: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for m in _HEADING_TEXT_RE.finditer(body):
        if m.group(2):
            out.append((int(m.group(1)), _strip_html(m.group(2)).strip()))
        elif m.group(3):
            out.append((len(m.group(3)), m.group(4).strip()))
    return out


def _count_keyword_occurrences(plain_text: str, keyword_norm: str) -> int:
    if not keyword_norm:
        return 0
    text_norm = _normalize_keyword_for_match(plain_text)
    if not text_norm:
        return 0
    return text_norm.count(keyword_norm)


def validate_seo(
    title: str,
    body_md: str,
    primary_keyword: str,
    meta_description: str,
) -> SEOReport:
    title = title or ""
    body_md = body_md or ""
    primary_keyword = primary_keyword or ""
    meta_description = meta_description or ""

    hard: list[str] = []
    soft: list[str] = []
    metrics: dict = {}

    title_norm = _normalize_keyword_for_match(title)
    kw_norm = _normalize_keyword_for_match(primary_keyword)

    # Hard 1: H1 count
    h1_count = len(_H1_RE.findall(body_md))
    metrics["h1_count"] = h1_count
    if h1_count != 1:
        # Hugo가 title을 H1로 렌더하므로 body 내 H1 없는 것이 정상.
        # H1 == 0 정상, > 1 만 hard. H1 == 1 도 정상.
        if h1_count > 1:
            hard.append(f"본문에 H1 {h1_count}개 (1개 이하 권장; Hugo가 title을 H1으로 렌더)")

    # Hard 2: primary_keyword in title
    if not kw_norm:
        soft.append("primary_keyword 비어있음")
    elif kw_norm not in title_norm:
        hard.append(f"primary_keyword '{primary_keyword}' title에 미포함")

    # Soft: title length
    metrics["title_length"] = len(title)
    if not (30 <= len(title) <= 60):
        soft.append(f"title 길이 {len(title)}자 (30-60 권장)")

    # Soft: meta_description length
    metrics["meta_description_length"] = len(meta_description)
    if not (120 <= len(meta_description) <= 160):
        soft.append(f"meta_description 길이 {len(meta_description)}자 (120-160 권장)")

    # Soft: H2 count >= 3
    h2_matches = re.findall(r"^##\s+|<h2[^>]*>", body_md, re.MULTILINE | re.IGNORECASE)
    h2_count = len(h2_matches)
    metrics["h2_count"] = h2_count
    if h2_count < 3:
        soft.append(f"H2 {h2_count}개 (3+ 권장)")

    # Soft: keyword density 0.5%-2.5% (정규화 텍스트 기준)
    plain = _strip_html(body_md)
    plain_norm = _normalize_keyword_for_match(plain)
    plain_total_chars = max(len(plain_norm), 1)
    kw_occ = _count_keyword_occurrences(plain, kw_norm)
    density = (kw_occ * max(len(kw_norm), 1) / plain_total_chars) * 100 if kw_norm else 0.0
    metrics["keyword_occurrences"] = kw_occ
    metrics["keyword_density_pct"] = round(density, 3)
    if kw_norm:
        if density < 0.5:
            soft.append(f"키워드 밀도 {density:.2f}% (0.5%+ 권장)")
        elif density > 2.5:
            soft.append(f"키워드 밀도 {density:.2f}% (2.5%- 권장, 과다)")

    # Soft: primary_kw in first 100 chars + last 100 chars
    if kw_norm:
        first100 = _normalize_keyword_for_match(plain[:300])  # 정규화 후 길이 줄어드므로 여유
        last100 = _normalize_keyword_for_match(plain[-300:])
        if kw_norm not in first100:
            soft.append("primary_keyword 첫 단락 미포함")
        if kw_norm not in last100:
            soft.append("primary_keyword 마지막 단락 미포함")

    # Soft: primary_kw in >= 3 H2/H3 headings
    if kw_norm:
        headings = _heading_texts(body_md)
        h_with_kw = sum(1 for _, t in headings if kw_norm in _normalize_keyword_for_match(t))
        metrics["headings_with_keyword"] = h_with_kw
        metrics["total_h2_h3"] = len(headings)
        if h_with_kw < 3 and len(headings) >= 3:
            soft.append(f"H2/H3 중 primary_keyword 포함 {h_with_kw}개 (3+ 권장)")

    # Soft: img alt 누락
    imgs = _IMG_RE.findall(body_md)
    metrics["img_count"] = len(imgs)
    missing_alt = 0
    for attrs in imgs:
        m = _ALT_RE.search(attrs)
        if not m or not m.group(1).strip():
            missing_alt += 1
    metrics["img_missing_alt"] = missing_alt
    if missing_alt:
        soft.append(f"img alt 누락 {missing_alt}/{len(imgs)}건")

    # Score: hard 1건당 -50, soft 1건당 -8, base 100
    score = max(0.0, 100.0 - 50.0 * len(hard) - 8.0 * len(soft))
    metrics["hard_count"] = len(hard)
    metrics["soft_count"] = len(soft)

    # env gate: SEO_VALIDATOR_ENABLED=0 → hard 강제 다운그레이드
    if os.getenv("SEO_VALIDATOR_ENABLED", "0").strip() != "1" and hard:
        soft.extend([f"[downgraded] {v}" for v in hard])
        hard = []

    return SEOReport(score=score, hard_violations=hard, soft_violations=soft, metrics=metrics)


def record_seo_failure(topic_id: str, slug: str, lang: str, report: SEOReport, retry_count: int) -> None:
    """Hard fail 시 manual review 큐에 기록."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    if SEO_FAILURES_PATH.exists():
        try:
            entries = json.loads(SEO_FAILURES_PATH.read_text(encoding="utf-8"))
        except Exception:
            entries = []
    from datetime import datetime, timezone
    entries.append({
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "topic_id": topic_id,
        "slug": slug,
        "lang": lang,
        "retry_count": retry_count,
        "score": report.score,
        "hard_violations": report.hard_violations,
        "soft_violations": report.soft_violations,
        "metrics": report.metrics,
    })
    SEO_FAILURES_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.warning(f"SEO fail recorded: topic={topic_id} retry={retry_count} score={report.score:.1f}")
