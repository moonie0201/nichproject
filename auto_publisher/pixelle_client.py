"""Pixelle-Video REST API 클라이언트 — split-screen Shorts 의 B-roll 수신.

Pixelle FastAPI (기본 http://localhost:8866) 를 호출하여 1080x960 모션 비디오
(B-roll) 을 받아온다. 캐시 hit 시 네트워크 호출 없이 디렉토리의 mp4 1개 선택.

설계:
- API 다운/에러 시 None 반환 → 호출자는 ffmpeg 단독 fallback (정적 placeholder).
- 카테고리별 캐시 풀 운영: .omc/pixelle_cache/broll/<category>/*.mp4
- PIXELLE_ENABLED=false 면 즉시 None (개발/디버깅 모드).
"""
from __future__ import annotations

import logging
import os
import random
from pathlib import Path

logger = logging.getLogger(__name__)


def _cache_dir() -> Path:
    base = os.getenv(
        "PIXELLE_BROLL_CACHE_DIR",
        "/home/mh/ocstorage/workspace/nichproject/.omc/pixelle_cache/broll",
    )
    return Path(base)


def _is_enabled() -> bool:
    return os.getenv("PIXELLE_ENABLED", "true").lower() not in ("false", "0", "no")


def _api_base() -> str:
    return os.getenv("PIXELLE_API_URL", "http://localhost:8866").rstrip("/")


def _select_from_pool(category: str) -> Path | None:
    """캐시 디렉토리의 mp4 중 1개 선택 (랜덤). 없으면 None."""
    cdir = _cache_dir() / category
    if not cdir.exists():
        return None
    files = sorted(cdir.glob("*.mp4"))
    if not files:
        return None
    return random.choice(files)


def _generate_via_api(category: str, duration_sec: float) -> Path | None:
    """Pixelle API 호출하여 B-roll mp4 생성 + 캐시 저장. 실패 시 None."""
    import httpx

    cdir = _cache_dir() / category
    cdir.mkdir(parents=True, exist_ok=True)

    body = {
        "topic": f"{category} financial b-roll abstract motion",
        "template": "1080x1920/image_default.html",
        "duration_sec": duration_sec,
    }
    api_url = _api_base()
    try:
        resp = httpx.post(
            f"{api_url}/api/video/generate/sync",
            json=body,
            timeout=600.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Pixelle API 실패 ({category}): {e}")
        return None

    video_url = data.get("video_url")
    if not video_url:
        logger.warning(f"Pixelle 응답에 video_url 없음: {data}")
        return None

    # mp4 다운로드
    full_url = video_url if video_url.startswith("http") else f"{api_url}{video_url}"
    try:
        dl = httpx.get(full_url, timeout=120.0)
        dl.raise_for_status()
    except Exception as e:
        logger.warning(f"Pixelle mp4 다운로드 실패: {e}")
        return None

    # 캐시에 저장 — 다음 호출은 hit
    existing = list(cdir.glob("*.mp4"))
    out = cdir / f"broll-{len(existing)+1:03d}.mp4"
    out.write_bytes(dl.content)
    logger.info(f"Pixelle B-roll 캐시 저장: {out} ({len(dl.content)//1024} KB)")
    return out


def get_broll(category: str, duration_sec: float = 60.0) -> Path | None:
    """카테고리에 맞는 B-roll mp4 경로 반환. 없으면 Pixelle API 호출. 실패 시 None.

    Args:
        category: 영상 카테고리 (예: 'etf-analysis', 'market-wrap', 'crypto')
        duration_sec: 필요한 길이 (캐시 풀 영상은 트림 또는 루프로 맞춤)

    Returns:
        Path: 생성/선택된 mp4 (1080x960 권장)
        None: PIXELLE_ENABLED=false 또는 API 실패 (호출자 fallback 처리)
    """
    if not _is_enabled():
        return None

    # 캐시 hit 우선
    pooled = _select_from_pool(category)
    if pooled is not None:
        return pooled

    # 캐시 miss → API 호출
    return _generate_via_api(category, duration_sec)
