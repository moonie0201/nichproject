"""URL → 콘텐츠 추출 (YouTube/Instagram/TikTok/뉴스 기사).

목적: Discord에 올라온 URL을 받아 블로그+영상 생성 파이프라인으로 흘려보내기 위한 콘텐츠 수집.

지원:
- YouTube/Shorts: youtube-transcript-api (자막) + yt-dlp metadata
- Instagram Reels / TikTok: yt-dlp (캡션 + metadata)
- 뉴스/일반 기사: trafilatura

반환 표준 형식:
    {
        "title": str,
        "text": str,           # 본문 (200자 이상)
        "platform": str,       # youtube/instagram/tiktok/article/unknown
        "thumbnail_url": str,
        "source_url": str,
        "fetched_at": str (ISO),
    }
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_YT_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})")


def _detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "instagram.com" in host:
        return "instagram"
    if "tiktok.com" in host:
        return "tiktok"
    return "article"


def _extract_youtube_id(url: str) -> str | None:
    m = _YT_RE.search(url)
    return m.group(1) if m else None


def _fetch_youtube(url: str) -> dict:
    """YouTube/Shorts → 자막 + 메타. transcript-api primary, yt-dlp 메타 보조."""
    vid = _extract_youtube_id(url)
    if not vid:
        raise RuntimeError(f"YouTube video id 추출 실패: {url}")

    title = ""
    thumb = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"
    transcript_text = ""

    # 1. 자막 (한국어 우선, 영어 폴백) — youtube-transcript-api v1+ instance API
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        try:
            fetched = api.fetch(vid, languages=["ko"])
        except Exception:
            fetched = api.fetch(vid, languages=["en", "ko", "ja"])
        # FetchedTranscript: iterable of FetchedTranscriptSnippet (has .text attr) or dict
        segments = []
        for seg in fetched:
            if hasattr(seg, "text"):
                segments.append(seg.text)
            elif isinstance(seg, dict):
                segments.append(seg.get("text", ""))
        transcript_text = " ".join(segments).strip()
    except Exception as e:
        logger.warning(f"YouTube transcript 실패 ({vid}): {e}")

    # 2. 메타 (yt-dlp)
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "") or title
            if info.get("thumbnail"):
                thumb = info["thumbnail"]
            if not transcript_text:
                # description 폴백
                desc = info.get("description") or ""
                if len(desc) > 100:
                    transcript_text = desc
    except Exception as e:
        logger.warning(f"yt-dlp 메타 추출 실패: {e}")

    if not transcript_text or len(transcript_text) < 100:
        raise RuntimeError(f"YouTube 텍스트 추출 실패 또는 너무 짧음 ({len(transcript_text)}자)")

    return {
        "title": title or f"YouTube {vid}",
        "text": transcript_text,
        "platform": "youtube",
        "thumbnail_url": thumb,
        "source_url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _fetch_yt_dlp_generic(url: str, platform: str) -> dict:
    """Instagram/TikTok 등 yt-dlp 지원 플랫폼."""
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise RuntimeError(f"yt-dlp 추출 실패 ({platform}): {e}") from e

    title = (info.get("title") or info.get("description") or "")[:120].strip()
    description = info.get("description") or ""
    # Instagram/TikTok 의 description = 캡션
    text = description if len(description) >= 100 else title
    if not text or len(text) < 50:
        raise RuntimeError(f"{platform} 캡션 너무 짧음 ({len(text)}자)")

    return {
        "title": title or f"{platform} 콘텐츠",
        "text": text,
        "platform": platform,
        "thumbnail_url": info.get("thumbnail") or "",
        "source_url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _fetch_article(url: str) -> dict:
    """뉴스/블로그 기사 — trafilatura."""
    try:
        import trafilatura
    except ImportError as e:
        raise RuntimeError(f"trafilatura 미설치: {e}") from e

    downloaded = trafilatura.fetch_url(url, no_ssl=True)
    if not downloaded:
        raise RuntimeError(f"기사 다운로드 실패: {url}")
    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )
    if not text or len(text) < 200:
        raise RuntimeError(f"기사 본문 추출 실패 또는 너무 짧음 ({len(text or '')}자)")

    # 제목 추출 — metadata
    title = ""
    try:
        meta = trafilatura.extract_metadata(downloaded)
        if meta and meta.title:
            title = meta.title
    except Exception:
        pass

    if not title:
        # text 첫 줄 폴백
        title = text.split("\n")[0][:120]

    return {
        "title": title,
        "text": text,
        "platform": "article",
        "thumbnail_url": "",
        "source_url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def fetch_url_content(url: str) -> dict:
    """URL → 표준 콘텐츠 dict.

    실패: RuntimeError.
    """
    if not url or not url.strip():
        raise RuntimeError("빈 URL")
    url = url.strip()

    platform = _detect_platform(url)
    logger.info(f"url_fetcher: platform={platform} url={url[:80]}")

    if platform == "youtube":
        return _fetch_youtube(url)
    if platform in ("instagram", "tiktok"):
        return _fetch_yt_dlp_generic(url, platform)
    return _fetch_article(url)
