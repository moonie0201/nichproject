"""url_fetcher 테스트 — platform 감지 + mock fetcher."""
from unittest.mock import patch, MagicMock

import pytest

from auto_publisher import url_fetcher as uf


def test_detect_platform():
    assert uf._detect_platform("https://www.youtube.com/watch?v=abc12345678") == "youtube"
    assert uf._detect_platform("https://youtu.be/abc12345678") == "youtube"
    assert uf._detect_platform("https://www.youtube.com/shorts/abc12345678") == "youtube"
    assert uf._detect_platform("https://instagram.com/reel/xxx") == "instagram"
    assert uf._detect_platform("https://tiktok.com/@user/video/123") == "tiktok"
    assert uf._detect_platform("https://news.naver.com/article/xxx") == "article"


def test_extract_youtube_id():
    assert uf._extract_youtube_id("https://youtube.com/watch?v=ABC12345678") == "ABC12345678"
    assert uf._extract_youtube_id("https://youtu.be/XYZ98765432") == "XYZ98765432"
    assert uf._extract_youtube_id("https://youtube.com/shorts/AAA00000000") == "AAA00000000"
    assert uf._extract_youtube_id("https://example.com/no-vid") is None


def test_fetch_empty_url_raises():
    with pytest.raises(RuntimeError, match="빈 URL"):
        uf.fetch_url_content("")


def test_fetch_youtube_with_transcript():
    """YouTube transcript mock — v1 instance API (fetch)."""
    fake_segments = [MagicMock(text=f"문장 {i}") for i in range(50)]
    with patch("youtube_transcript_api.YouTubeTranscriptApi") as mock_yt_cls, \
         patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_yt_inst = MagicMock()
        mock_yt_inst.fetch.return_value = fake_segments
        mock_yt_cls.return_value = mock_yt_inst
        mock_inst = MagicMock()
        mock_inst.extract_info.return_value = {
            "title": "VOO ETF 5년 분석 영상",
            "thumbnail": "https://i.ytimg.com/vi/abc/hqdefault.jpg",
        }
        mock_ydl.return_value.__enter__.return_value = mock_inst
        r = uf.fetch_url_content("https://youtube.com/watch?v=ABC12345678")
    assert r["platform"] == "youtube"
    assert "VOO" in r["title"]
    assert "문장 0" in r["text"]
    assert len(r["text"]) > 100


def test_fetch_youtube_transcript_fail_falls_back_to_description():
    """자막 추출 실패 → yt-dlp description 폴백."""
    long_desc = "이 영상은 VOO ETF에 대한 분석입니다. " * 20
    with patch("youtube_transcript_api.YouTubeTranscriptApi") as mock_yt_cls, \
         patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_yt_inst = MagicMock()
        mock_yt_inst.fetch.side_effect = Exception("no transcript")
        mock_yt_cls.return_value = mock_yt_inst
        mock_inst = MagicMock()
        mock_inst.extract_info.return_value = {
            "title": "VOO Analysis",
            "description": long_desc,
            "thumbnail": "",
        }
        mock_ydl.return_value.__enter__.return_value = mock_inst
        r = uf.fetch_url_content("https://youtu.be/ABC12345678")
    assert r["text"].startswith("이 영상은 VOO ETF")


def test_fetch_youtube_id_extract_fail():
    with pytest.raises(RuntimeError, match="video id"):
        uf._fetch_youtube("https://youtube.com/no-id-here")


def test_fetch_instagram_caption():
    long_caption = "VOO 5년 수익률은 87.5% 였습니다. " * 10
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_inst = MagicMock()
        mock_inst.extract_info.return_value = {
            "title": "투자 인플루언서 IG",
            "description": long_caption,
            "thumbnail": "https://cdn.ig/thumb.jpg",
        }
        mock_ydl.return_value.__enter__.return_value = mock_inst
        r = uf.fetch_url_content("https://instagram.com/reel/CXX/")
    assert r["platform"] == "instagram"
    assert "VOO" in r["text"]


def test_fetch_instagram_short_caption_raises():
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_inst = MagicMock()
        mock_inst.extract_info.return_value = {"title": "x", "description": "짧음"}
        mock_ydl.return_value.__enter__.return_value = mock_inst
        with pytest.raises(RuntimeError, match="짧음"):
            uf.fetch_url_content("https://instagram.com/reel/X/")


def test_fetch_article():
    fake_html = "<html><head><title>VOO 분석</title></head><body>" + ("VOO ETF 분석 본문. " * 100) + "</body></html>"
    fake_extract = "VOO ETF 분석 본문. " * 100
    fake_meta = MagicMock(title="VOO 분석 제목")
    with patch("trafilatura.fetch_url", return_value=fake_html), \
         patch("trafilatura.extract", return_value=fake_extract), \
         patch("trafilatura.extract_metadata", return_value=fake_meta):
        r = uf.fetch_url_content("https://news.naver.com/article/xxx")
    assert r["platform"] == "article"
    assert r["title"] == "VOO 분석 제목"
    assert len(r["text"]) > 200


def test_fetch_article_no_content_raises():
    with patch("trafilatura.fetch_url", return_value="<html></html>"), \
         patch("trafilatura.extract", return_value=""):
        with pytest.raises(RuntimeError, match="추출 실패"):
            uf.fetch_url_content("https://example.com/article")
