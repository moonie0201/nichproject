"""Google Trends KR (RSS) 신호로 토픽 우선순위 강화.

Google Trends Daily RSS (https://trends.google.com/trending/rss?geo=KR) 파싱.
pytrends 라이브러리는 2025년부터 404 — RSS는 여전히 동작.

토픽 자동생성 시 트렌딩 키워드를 시드에 주입 + 생성된 토픽 점수화 → 정렬.
실패해도 graceful degradation (빈 리스트 반환, 기존 동작 유지).

Env gate: TRENDS_KR_ENABLED=1 (기본 ON)
캐시: data/trends_cache.json, TTL 6h, stale-on-error
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
CACHE_PATH = DATA_DIR / "trends_cache.json"
TTL_SECONDS = 6 * 3600
TRENDS_RSS_URL = "https://trends.google.com/trending/rss?geo=KR"
USER_AGENT = "Mozilla/5.0 (compatible; InvestIQs-trends/1.0)"


def _enabled() -> bool:
    return os.getenv("TRENDS_KR_ENABLED", "1").strip() == "1"


def _load_cache() -> tuple[float, list[tuple[str, float]]]:
    if not CACHE_PATH.exists():
        return 0.0, []
    try:
        raw = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        ts = float(raw.get("fetched_at", 0))
        items = [(str(it[0]), float(it[1])) for it in raw.get("items", [])]
        return ts, items
    except Exception as e:
        logger.warning(f"trends_cache load fail: {e}")
        return 0.0, []


def _save_cache(items: list[tuple[str, float]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"fetched_at": time.time(), "items": [[k, v] for k, v in items]}
    CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _traffic_to_score(approx_traffic: str) -> float:
    """approx_traffic 문자열을 0-100 점수로 변환.

    예: "10M+" → 100, "1M+" → 95, "500K+" → 90, "100K+" → 85,
        "50K+" → 80, "10K+" → 75, "5K+" → 70, "1K+" → 60,
        "500+" → 50, "200+" → 40, "100+" → 30
    """
    if not approx_traffic:
        return 0.0
    s = approx_traffic.strip().upper().replace(",", "").replace("+", "")
    m = re.match(r"(\d+(?:\.\d+)?)\s*([KMB]?)", s)
    if not m:
        return 0.0
    num = float(m.group(1))
    unit = m.group(2)
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(unit, 1)
    n = num * multiplier
    # 로그 스케일 매핑
    import math
    if n <= 0:
        return 0.0
    # 100=30점, 1K=60점, 100K=85점, 10M=100점 (log10(100)=2 → 30, log10(1e7)=7 → 100)
    score = max(0.0, min(100.0, (math.log10(n) - 2) * 14 + 30))
    return round(score, 1)


def _parse_rss(xml_text: str) -> list[tuple[str, float]]:
    """RSS XML → [(title, score)] 정렬은 RSS 등장 순 (Google이 보낸 순)."""
    items: list[tuple[str, float]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning(f"trends RSS parse fail: {e}")
        return items
    ns = {"ht": "https://trends.google.com/trending/rss"}
    for item in root.iter("item"):
        title_el = item.find("title")
        traffic_el = item.find("ht:approx_traffic", ns)
        if title_el is None or not (title_el.text or "").strip():
            continue
        title = title_el.text.strip()
        traffic = (traffic_el.text or "").strip() if traffic_el is not None else ""
        score = _traffic_to_score(traffic)
        items.append((title, score))
    return items


def fetch_trending_finance_keywords_kr() -> list[tuple[str, float]]:
    """KR 트렌딩 키워드 [(keyword, score 0-100)] 반환.

    캐시 6h TTL. 실패 시 stale 캐시 반환 (없으면 빈 리스트).
    Disabled 시 즉시 빈 리스트.
    """
    if not _enabled():
        return []

    ts, cached = _load_cache()
    if cached and (time.time() - ts) < TTL_SECONDS:
        return cached

    try:
        req = urllib.request.Request(TRENDS_RSS_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        items = _parse_rss(body)
        if items:
            _save_cache(items)
            return items
        logger.warning("trends RSS returned empty; using stale cache")
        return cached
    except Exception as e:
        logger.warning(f"trends RSS fetch fail (stale fallback): {e}")
        return cached


def score_topic_by_trends(title: str, keywords: list[tuple[str, float]]) -> float:
    """토픽 제목과 트렌딩 키워드 유사도 최대값 (0-100).

    부분 매치(키워드가 title 안에 등장) → 트렌드 점수 그대로.
    그 외 약한 유사도는 50점 만점으로 환산.
    """
    if not title or not keywords:
        return 0.0
    title_lower = title.lower()
    best = 0.0
    for kw, trend_score in keywords:
        kw_lower = kw.lower()
        if kw_lower and kw_lower in title_lower:
            best = max(best, trend_score)
            continue
        ratio = SequenceMatcher(None, title_lower, kw_lower).ratio()
        best = max(best, ratio * 50.0)
    return round(best, 2)
