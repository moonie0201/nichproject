"""Pexels Videos API stock B-roll 클라이언트.

split-screen Shorts 의 아래 절반 (1080x960) 에 사용할 무료 stock B-roll mp4
다운로드. AI 생성 대신 사람이 촬영한 실제 stock 영상이라 환각 위험 0.

Pexels API:
- https://api.pexels.com/videos/search?query=...&per_page=N
- API key 등록 (무료): https://www.pexels.com/api/
- 200 req/h, 상업 사용 OK, attribution 권장 (필수 아님)

설계:
- 카테고리별 캐시 풀 운영 (.omc/stock_broll/<category>/*.mp4)
- 캐시 hit 시 네트워크 호출 없이 1개 선택
- API 실패 / key 없으면 None → 호출자가 placeholder 사용
"""
from __future__ import annotations

import logging
import os
import random
from pathlib import Path

logger = logging.getLogger(__name__)


PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
PIXABAY_SEARCH_URL = "https://pixabay.com/api/videos/"


# 카테고리 → Pexels 검색 키워드 매핑
_CATEGORY_QUERIES = {
    "etf-analysis": "stock market chart finance",
    "market-wrap": "stock market trading floor",
    "intraday": "stock ticker financial data",
    "weekly": "business meeting analytics",
    "crypto": "bitcoin cryptocurrency blockchain",
    "tax": "money calculator office",
    "dividend": "money cash flow business",
    "default": "finance business money",
}


def category_to_query(category: str) -> str:
    """카테고리 → Pexels 검색 키워드 (모름 → generic finance)."""
    return _CATEGORY_QUERIES.get(category, _CATEGORY_QUERIES["default"])


def _cache_dir() -> Path:
    base = os.getenv(
        "STOCK_BROLL_CACHE_DIR",
        "/home/mh/ocstorage/workspace/nichproject/.omc/stock_broll",
    )
    return Path(base)


def _select_from_pool(category: str) -> Path | None:
    cdir = _cache_dir() / category
    if not cdir.exists():
        return None
    files = sorted(cdir.glob("*.mp4"))
    if not files:
        return None
    return random.choice(files)


def _pick_best_file(video: dict, target_w: int = 1080, target_h: int = 960) -> str | None:
    """video.video_files 중 1080x960 에 가장 적합한 url 1개 선택.

    선호: 9:16 또는 9:16 가까운 비율, 너무 큰 파일 회피.
    """
    files = video.get("video_files", [])
    if not files:
        return None
    # 점수: 1080+ width 우선, hd 품질 우선
    def score(f):
        w = f.get("width") or 0
        h = f.get("height") or 0
        q_bonus = 100 if f.get("quality") == "hd" else 0
        size_penalty = abs((w * h) - (target_w * target_h * 4))  # 4배 정도가 적당
        return -(size_penalty - q_bonus)
    sorted_files = sorted(files, key=score, reverse=True)
    return sorted_files[0].get("link")


def _download_via_pexels(category: str, duration_sec: float) -> Path | None:
    import httpx

    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not api_key:
        return None

    cdir = _cache_dir() / category
    cdir.mkdir(parents=True, exist_ok=True)

    query = category_to_query(category)
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": 5, "orientation": "portrait"}

    try:
        resp = httpx.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Pexels search 실패 ({category}): {e}")
        return None

    videos = data.get("videos", [])
    if not videos:
        logger.warning(f"Pexels 검색 결과 없음 ({query})")
        return None

    # 첫 번째 비디오의 best file
    pick = videos[0]
    url = _pick_best_file(pick)
    if not url:
        return None

    try:
        dl = httpx.get(url, timeout=120.0)
        dl.raise_for_status()
    except Exception as e:
        logger.warning(f"Pexels mp4 다운로드 실패: {e}")
        return None

    pid = pick.get("id", "unk")
    out = cdir / f"pexels-{pid}.mp4"
    out.write_bytes(dl.content)
    logger.info(f"Pexels B-roll 캐시 저장: {out} ({len(dl.content)//1024} KB)")
    return out


def _download_via_pixabay(category: str, duration_sec: float) -> Path | None:
    """Pixabay Videos API → 카테고리 검색 → 첫 결과 mp4 저장."""
    import httpx

    api_key = os.getenv("PIXABAY_API_KEY", "").strip()
    if not api_key:
        return None

    cdir = _cache_dir() / category
    cdir.mkdir(parents=True, exist_ok=True)

    query = category_to_query(category)
    params = {
        "key": api_key, "q": query,
        "video_type": "all", "per_page": 5,
    }
    try:
        resp = httpx.get(PIXABAY_SEARCH_URL, params=params, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Pixabay search 실패 ({category}): {e}")
        return None

    hits = data.get("hits", [])
    if not hits:
        logger.warning(f"Pixabay 검색 결과 없음 ({query})")
        return None

    # videos.large > medium > small > tiny 우선순위
    pick = hits[0]
    videos = pick.get("videos", {})
    url = None
    for size_key in ("large", "medium", "small", "tiny"):
        v = videos.get(size_key)
        if v and v.get("url"):
            url = v["url"]
            break
    if not url:
        return None

    try:
        dl = httpx.get(url, timeout=120.0)
        dl.raise_for_status()
    except Exception as e:
        logger.warning(f"Pixabay mp4 다운로드 실패: {e}")
        return None

    pid = pick.get("id", "unk")
    out = cdir / f"pixabay-{pid}.mp4"
    out.write_bytes(dl.content)
    logger.info(f"Pixabay B-roll 캐시 저장: {out} ({len(dl.content)//1024} KB)")
    return out


def get_stock_broll(category: str, duration_sec: float = 60.0) -> Path | None:
    """카테고리에 맞는 stock B-roll mp4 경로 반환.

    우선순위:
    1. 캐시 풀 (.omc/stock_broll/<category>/*.mp4)
    2. Pexels API (PEXELS_API_KEY 설정 시)
    3. Pixabay API (PIXABAY_API_KEY 설정 시)
    4. None (호출자 fallback)

    Args:
        category: 'etf-analysis' / 'market-wrap' / 'crypto' / etc.
        duration_sec: 필요한 길이 (정보용 — 트림은 호출자 책임)
    """
    has_pexels = bool(os.getenv("PEXELS_API_KEY", "").strip())
    has_pixabay = bool(os.getenv("PIXABAY_API_KEY", "").strip())

    if not has_pexels and not has_pixabay:
        return None

    # 캐시 우선
    pooled = _select_from_pool(category)
    if pooled is not None:
        return pooled

    # Pexels 우선 시도
    if has_pexels:
        result = _download_via_pexels(category, duration_sec)
        if result is not None:
            return result

    # Pixabay fallback
    if has_pixabay:
        return _download_via_pixabay(category, duration_sec)

    return None
