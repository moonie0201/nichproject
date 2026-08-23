"""trends_kr 테스트 — RSS 파싱/캐시/실패 fallback/점수 계산."""
import io
import json
import time
from unittest.mock import patch, MagicMock

import pytest

from auto_publisher import trends_kr


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0">
  <channel>
    <item>
      <title>삼성전자</title>
      <ht:approx_traffic>500K+</ht:approx_traffic>
    </item>
    <item>
      <title>VOO ETF</title>
      <ht:approx_traffic>10K+</ht:approx_traffic>
    </item>
    <item>
      <title>비트코인</title>
      <ht:approx_traffic>200+</ht:approx_traffic>
    </item>
  </channel>
</rss>
"""


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """각 테스트마다 격리된 캐시 파일."""
    cache = tmp_path / "trends_cache.json"
    monkeypatch.setattr(trends_kr, "CACHE_PATH", cache)
    monkeypatch.setattr(trends_kr, "DATA_DIR", tmp_path)
    monkeypatch.setenv("TRENDS_KR_ENABLED", "1")


def _mock_response(body: str):
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8")
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("TRENDS_KR_ENABLED", "0")
    assert trends_kr.fetch_trending_finance_keywords_kr() == []


def test_score_exact_match():
    keywords = [("VOO", 100.0), ("SCHD", 90.0)]
    score = trends_kr.score_topic_by_trends("VOO ETF 분석", keywords)
    assert score == 100.0


def test_score_no_match():
    keywords = [("zzzzzzz", 100.0)]
    score = trends_kr.score_topic_by_trends("VOO ETF 분석", keywords)
    assert score < 50.0


def test_score_empty_inputs():
    assert trends_kr.score_topic_by_trends("", [("VOO", 100.0)]) == 0.0
    assert trends_kr.score_topic_by_trends("VOO", []) == 0.0


def test_traffic_to_score():
    assert trends_kr._traffic_to_score("100+") < trends_kr._traffic_to_score("1K+")
    assert trends_kr._traffic_to_score("1K+") < trends_kr._traffic_to_score("100K+")
    assert trends_kr._traffic_to_score("100K+") < trends_kr._traffic_to_score("10M+")
    assert trends_kr._traffic_to_score("") == 0.0


def test_rss_parse():
    items = trends_kr._parse_rss(SAMPLE_RSS)
    assert len(items) == 3
    assert items[0][0] == "삼성전자"
    assert items[1][0] == "VOO ETF"
    # 500K+가 200+ 보다 점수 높아야 함
    assert items[0][1] > items[2][1]


def test_cache_within_ttl_returns_cached():
    trends_kr._save_cache([("VOO", 95.0), ("SCHD", 80.0)])
    with patch("urllib.request.urlopen") as mock_open:
        result = trends_kr.fetch_trending_finance_keywords_kr()
        mock_open.assert_not_called()
    assert result == [("VOO", 95.0), ("SCHD", 80.0)]


def test_cache_expired_triggers_fetch():
    trends_kr._save_cache([("OLD", 50.0)])
    raw = json.loads(trends_kr.CACHE_PATH.read_text())
    raw["fetched_at"] = time.time() - (trends_kr.TTL_SECONDS + 100)
    trends_kr.CACHE_PATH.write_text(json.dumps(raw))

    with patch("urllib.request.urlopen", return_value=_mock_response(SAMPLE_RSS)):
        result = trends_kr.fetch_trending_finance_keywords_kr()
    assert len(result) == 3
    assert any("삼성전자" in kw for kw, _ in result)


def test_fetch_failure_returns_stale_cache():
    trends_kr._save_cache([("STALE", 70.0)])
    raw = json.loads(trends_kr.CACHE_PATH.read_text())
    raw["fetched_at"] = time.time() - (trends_kr.TTL_SECONDS + 100)
    trends_kr.CACHE_PATH.write_text(json.dumps(raw))

    with patch("urllib.request.urlopen", side_effect=Exception("HTTP 404")):
        result = trends_kr.fetch_trending_finance_keywords_kr()
    assert result == [("STALE", 70.0)]


def test_fetch_failure_no_cache_returns_empty():
    with patch("urllib.request.urlopen", side_effect=Exception("network down")):
        result = trends_kr.fetch_trending_finance_keywords_kr()
    assert result == []
