"""topic_manager.get_next_topic — 영구 실패 토픽 정상 큐 제외 회귀 테스트.

버그: attempts >= 3 인 failed 토픽이 step-1(재시도 큐)에서는 건너뛰지만
     step-2(정상 큐)에서는 그대로 선택되어 무한 반복 실패.

픽스: get_next_topic step-2 루프에 permanently_failed_ids 필터 추가.
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ── 픽스처 ──────────────────────────────────────────────

TOPIC_JEPQ = {
    "id": "dyn-jepq-div-2026-05-01",
    "topic": "JEPQ 배당 발표",
    "keywords": ["JEPQ", "JEPQ 배당"],
    "category": "배당 이벤트",
    "type": "blog",
    "priority": "urgent",
}

TOPIC_SAFE = {
    "id": "blog-etf-safe",
    "topic": "ETF 투자 기초",
    "keywords": ["ETF", "ETF 투자"],
    "category": "기초",
    "type": "blog",
}


def _make_topic_manager(tmp_path, topics, history=None, failed=None):
    from auto_publisher.topic_manager import TopicManager
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "topics_ko.json").write_text(json.dumps(topics), encoding="utf-8")
    (data_dir / "published_history_ko.json").write_text(json.dumps(history or []), encoding="utf-8")
    (data_dir / "failed_topics_ko.json").write_text(json.dumps(failed or []), encoding="utf-8")
    (data_dir / "published_history.json").write_text(json.dumps([]), encoding="utf-8")

    tm = TopicManager.__new__(TopicManager)
    tm.lang = "ko"
    tm.auto_refill = False
    tm.topics_file = data_dir / "topics_ko.json"
    tm.history_file = data_dir / "published_history_ko.json"
    tm.failed_file = data_dir / "failed_topics_ko.json"
    return tm


# ── 테스트 ──────────────────────────────────────────────

def test_permanently_failed_topic_skipped_in_normal_queue(tmp_path):
    """attempts=3 인 토픽은 정상 큐(step-2)에서 선택되면 안 된다."""
    failed = [{"topic_id": TOPIC_JEPQ["id"], "attempts": 3,
               "first_failed_at": "2026-05-08T00:59:00",
               "last_failed_at": "2026-05-08T00:59:00",
               "last_reason": "JSON 파싱 실패"}]
    tm = _make_topic_manager(tmp_path, [TOPIC_JEPQ, TOPIC_SAFE], failed=failed)

    with patch.object(tm, "_get_global_recent_primary_keywords", return_value=[]), \
         patch.object(tm, "_get_recent_published_topics", return_value=[]), \
         patch("auto_publisher.topic_manager.EventCalendar") as MockCal:
        MockCal.return_value.get_upcoming_event.return_value = None
        result = tm.get_next_topic("blog")

    assert result is not None, "발행 가능한 토픽이 있어야 한다"
    assert result["id"] != TOPIC_JEPQ["id"], (
        f"attempts=3 인 JEPQ 가 선택되면 안 됨: {result['id']}"
    )
    assert result["id"] == TOPIC_SAFE["id"], (
        f"SAFE 토픽이 선택돼야 함: {result['id']}"
    )


def test_failed_topic_with_attempts_lt_3_is_retried_first(tmp_path):
    """attempts < 3 인 failed 토픽은 step-1(재시도 우선)에서 선택된다."""
    failed = [{"topic_id": TOPIC_JEPQ["id"], "attempts": 1,
               "first_failed_at": "2026-05-08T00:59:00",
               "last_failed_at": "2026-05-08T00:59:00",
               "last_reason": "일시적 오류"}]
    tm = _make_topic_manager(tmp_path, [TOPIC_JEPQ, TOPIC_SAFE], failed=failed)

    with patch.object(tm, "_get_global_recent_primary_keywords", return_value=[]), \
         patch.object(tm, "_get_recent_published_topics", return_value=[]), \
         patch("auto_publisher.topic_manager.EventCalendar") as MockCal:
        MockCal.return_value.get_upcoming_event.return_value = None
        result = tm.get_next_topic("blog")

    assert result is not None
    assert result["id"] == TOPIC_JEPQ["id"], (
        f"attempts=1 인 JEPQ 가 재시도 우선 선택돼야 함: {result['id']}"
    )


def test_no_available_topic_when_all_permanently_failed(tmp_path):
    """모든 토픽이 permanently failed 이면 None 반환."""
    failed = [
        {"topic_id": TOPIC_JEPQ["id"], "attempts": 3,
         "first_failed_at": "2026-05-08T00:00:00", "last_failed_at": "2026-05-08T00:00:00",
         "last_reason": "실패"},
        {"topic_id": TOPIC_SAFE["id"], "attempts": 5,
         "first_failed_at": "2026-05-08T00:00:00", "last_failed_at": "2026-05-08T00:00:00",
         "last_reason": "실패"},
    ]
    tm = _make_topic_manager(tmp_path, [TOPIC_JEPQ, TOPIC_SAFE], failed=failed)

    with patch.object(tm, "_get_global_recent_primary_keywords", return_value=[]), \
         patch.object(tm, "_get_recent_published_topics", return_value=[]), \
         patch("auto_publisher.topic_manager.EventCalendar") as MockCal:
        MockCal.return_value.get_upcoming_event.return_value = None
        result = tm.get_next_topic("blog")

    assert result is None
