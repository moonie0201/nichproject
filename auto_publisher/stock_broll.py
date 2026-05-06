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
import time
from pathlib import Path

logger = logging.getLogger(__name__)


PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
PIXABAY_SEARCH_URL = "https://pixabay.com/api/videos/"


# 카테고리 → Pexels 검색 키워드 매핑
# 정책: 데이터/차트/추상 키워드 중심으로 사람 얼굴 클로즈업 빈도 ↓
# (Pexels API 는 negative keyword 미지원이라 검색어 자체를 추상화)
_CATEGORY_QUERIES = {
    "etf-analysis": "stock chart graph data finance",
    "market-wrap": "stock market screen ticker display",
    "intraday": "stock ticker chart financial data",
    "weekly": "business analytics dashboard data",
    "crypto": "bitcoin cryptocurrency blockchain digital",
    "tax": "money calculator finance numbers",
    "dividend": "money cash flow finance graph",
    "default": "finance business chart data",
}


def category_to_query(category: str) -> str:
    """카테고리 → Pexels 검색 키워드 (모름 → generic finance)."""
    return _CATEGORY_QUERIES.get(category, _CATEGORY_QUERIES["default"])


# slug 키워드 → 카테고리 매핑 (우선순위 위에서 아래로)
_SLUG_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    (("etf", "voo", "spy", "qqq", "tqqq", "schd", "vti", "운용보수", "추적오차"), "etf-analysis"),
    (("bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "비트코인", "이더리움", "코인"), "crypto"),
    (("dividend", "배당"), "dividend"),
    (("market-close", "market_close", "market-wrap", "market_wrap", "종가", "마감"), "market-wrap"),
    (("intraday", "장중", "실시간"), "intraday"),
    (("weekly", "주간"), "weekly"),
    (("tax", "세금", "절세", "소득세", "연말정산", "환급"), "tax"),
]


def slug_to_category(slug: str) -> str:
    """slug 키워드 → 카테고리 자동 추론. 매칭 안되면 'default'."""
    if not slug:
        return "default"
    s = slug.lower()
    for keywords, category in _SLUG_PATTERNS:
        if any(kw in s for kw in keywords):
            return category
    return "default"


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
    pick = random.choice(files)
    # LRU 보호: 사용한 파일의 atime/mtime 갱신
    now = time.time()
    try:
        os.utime(pick, (now, now))
    except OSError:
        pass
    return pick


def _evict_oldest_if_over_limit(cdir: Path) -> None:
    """카테고리 디렉토리 mp4 개수가 STOCK_BROLL_MAX_PER_CATEGORY 초과 시
    가장 오래 안 쓴 파일부터 삭제. 0/음수면 무제한 (no-op)."""
    try:
        max_per = int(os.getenv("STOCK_BROLL_MAX_PER_CATEGORY", "10"))
    except ValueError:
        max_per = 10
    if max_per <= 0:
        return
    files = list(cdir.glob("*.mp4"))
    if len(files) <= max_per:
        return
    files.sort(key=lambda p: p.stat().st_atime)
    for old in files[: len(files) - max_per]:
        try:
            old.unlink()
            logger.info(f"LRU evict: {old.name} (cat={cdir.name})")
        except OSError as e:
            logger.warning(f"LRU evict 실패 {old}: {e}")


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

    # 검색 결과 중 random 선택 (다양성 확보, 같은 영상 반복 방지)
    pick = random.choice(videos)
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
    _evict_oldest_if_over_limit(cdir)
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

    # 검색 결과 중 random 선택 (다양성 확보)
    pick = random.choice(hits)
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
    _evict_oldest_if_over_limit(cdir)
    return out


def get_broll_pool(category: str, n: int = 5) -> list[Path]:
    """카테고리 캐시 풀에서 random N개 (중복 없음) B-roll mp4 반환.

    부족하면 가용한 만큼만 반환 (no exception).
    캐시 비어있으면 빈 리스트.

    split-screen Shorts 의 17초 ladder 전환에 사용.
    """
    if n <= 0:
        return []
    cdir = _cache_dir() / category
    if not cdir.exists():
        return []
    files = sorted(cdir.glob("*.mp4"))
    if not files:
        return []
    pick_count = min(n, len(files))
    picks = random.sample(files, pick_count)
    # 사용 표시: atime 갱신 (LRU 보호)
    now = time.time()
    for p in picks:
        try:
            os.utime(p, (now, now))
        except OSError:
            pass
    return picks


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
