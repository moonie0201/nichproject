"""paperclip_publish 테스트 — API mock + validation hooks."""
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from auto_publisher import paperclip_publish as pp


@pytest.fixture(autouse=True)
def env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("PAPERCLIP_PUBLISH_ENABLED", "1")
    monkeypatch.setenv("PAPERCLIP_PUBLISH_DRY_RUN", "1")
    monkeypatch.setenv("PAPERCLIP_PUBLISH_COMPLIANCE", "0")
    monkeypatch.setenv("PAPERCLIP_PUBLISH_SEO", "0")
    monkeypatch.setenv("PAPERCLIP_PUBLISH_DAILY_LIMIT", "10")
    # 격리된 history dir
    monkeypatch.setattr(pp, "DATA_DIR", tmp_path)


def _make_wp(**overrides) -> dict:
    base = {
        "issue_id": "iss-1",
        "issue_identifier": "NIC-100",
        "issue_title": "test issue",
        "workproduct_id": "wp-1",
        "title": "VOO ETF 5년 수익률과 배당률 완벽 분석",
        "status": "ready",
        "metadata": {
            "lang": "ko",
            "category": "etf",
            "primary_keyword": "VOO ETF 분석",
            "body": "# VOO ETF 분석\n\n" + ("이것은 충분히 긴 본문입니다. " * 200),
        },
        "summary": "VOO ETF 5년 수익률 분석",
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
def test_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_PUBLISH_ENABLED", "0")
    assert pp.find_pending_blog_workproducts() == []
    r = pp.poll_and_publish()
    assert r["processed"] == 0
    assert "PAPERCLIP_PUBLISH_ENABLED" in r["skipped"]


def test_find_pending_filters_correctly():
    issues_resp = [
        {"id": "iss-1", "identifier": "NIC-1", "title": "A", "hiddenAt": None, "cancelledAt": None},
        {"id": "iss-2", "identifier": "NIC-2", "title": "B", "hiddenAt": "2026-01-01", "cancelledAt": None},
    ]
    wps_for_1 = [
        {"id": "wp-a", "type": "blog_post", "status": "ready", "title": "A blog", "metadata": {"lang": "ko"}},
        {"id": "wp-b", "type": "blog_post", "status": "draft", "title": "A draft", "metadata": {}},
        {"id": "wp-c", "type": "code_review", "status": "ready", "title": "C", "metadata": {}},
    ]
    def fake_get(path, params=None):
        if "/work-products" in path: return wps_for_1
        return issues_resp
    with patch.object(pp, "_api_get", side_effect=fake_get):
        cands = pp.find_pending_blog_workproducts()
    assert len(cands) == 1
    assert cands[0]["workproduct_id"] == "wp-a"


def test_publish_one_dry_run_passes_all_gates():
    wp = _make_wp()
    with patch.object(pp, "_check_keyword_duplicate", return_value=False):
        r = pp.publish_one(wp)
    assert r["success"] is True
    assert r["dry_run"] is True
    assert r["html_len"] > 2000


def test_publish_rejects_missing_title():
    wp = _make_wp(title="")
    with patch.object(pp, "_api_post") as post, patch.object(pp, "_api_patch") as patch_:
        r = pp.publish_one(wp)
    assert r["success"] is False
    assert "title" in r["reason"]
    assert r["hard"] is True


def test_publish_rejects_disallowed_category():
    wp = _make_wp(metadata={**_make_wp()["metadata"], "category": "gambling"})
    with patch.object(pp, "_api_post"), patch.object(pp, "_api_patch"):
        r = pp.publish_one(wp)
    assert r["success"] is False
    assert "allowlist" in r["reason"]


def test_publish_rejects_short_body():
    wp = _make_wp(metadata={**_make_wp()["metadata"], "body": "짧은 본문"})
    with patch.object(pp, "_api_post"), patch.object(pp, "_api_patch"):
        r = pp.publish_one(wp)
    assert r["success"] is False
    assert "body markdown" in r["reason"] or "too short" in r["reason"]


def test_publish_rejects_duplicate_primary_keyword():
    wp = _make_wp()
    with patch.object(pp, "_check_keyword_duplicate", return_value=True), \
         patch.object(pp, "_api_post"), patch.object(pp, "_api_patch"):
        r = pp.publish_one(wp)
    assert r["success"] is False
    assert "duplicate" in r["reason"]


def test_publish_soft_rejects_daily_limit(monkeypatch):
    """daily limit 도달 시 hard=False (재시도 가능, blocked 안 됨)."""
    monkeypatch.setenv("PAPERCLIP_PUBLISH_DAILY_LIMIT", "1")
    wp = _make_wp()
    with patch.object(pp, "_check_keyword_duplicate", return_value=False), \
         patch.object(pp, "_count_today_paperclip_publishes", return_value=5), \
         patch.object(pp, "_api_post"), patch.object(pp, "_api_patch") as patch_:
        r = pp.publish_one(wp)
    assert r["success"] is False
    assert "daily limit" in r["reason"]
    assert r["hard"] is False
    # blocked status 호출 안 됨
    patch_.assert_not_called()


def test_publish_compliance_violation(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_PUBLISH_COMPLIANCE", "1")
    wp = _make_wp()
    with patch.object(pp, "_check_keyword_duplicate", return_value=False), \
         patch.object(pp, "_run_compliance", return_value=(False, "투자 권유 표현 감지")), \
         patch.object(pp, "_api_post"), patch.object(pp, "_api_patch"):
        r = pp.publish_one(wp)
    assert r["success"] is False
    assert "compliance" in r["reason"]


def test_poll_and_publish_aggregates(monkeypatch):
    wps = [_make_wp(workproduct_id=f"wp-{i}") for i in range(3)]
    with patch.object(pp, "find_pending_blog_workproducts", return_value=wps), \
         patch.object(pp, "_check_keyword_duplicate", return_value=False):
        r = pp.poll_and_publish(max_items=5)
    assert r["processed"] == 3
    assert r["succeeded"] == 3
    assert r["candidates_total"] == 3


def test_poll_max_items_limits():
    wps = [_make_wp(workproduct_id=f"wp-{i}") for i in range(10)]
    with patch.object(pp, "find_pending_blog_workproducts", return_value=wps), \
         patch.object(pp, "_check_keyword_duplicate", return_value=False):
        r = pp.poll_and_publish(max_items=3)
    assert r["processed"] == 3
    assert r["candidates_total"] == 10


def test_fetch_body_from_comment_fallback():
    """metadata.body 없을 때 comments에서 본문 fetch."""
    wp = _make_wp(metadata={"lang": "ko", "category": "etf"})  # no body
    comments_resp = [
        {"id": "c1", "body": "old comment", "createdAt": "2026-01-01"},
        {"id": "c2", "body": "newest markdown body " * 100, "createdAt": "2026-05-01"},
    ]
    with patch.object(pp, "_api_get", return_value=comments_resp):
        body = pp._fetch_body_markdown(wp)
    assert "newest markdown body" in body


def test_count_today_paperclip_publishes(tmp_path, monkeypatch):
    monkeypatch.setattr(pp, "DATA_DIR", tmp_path)
    today_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entries = [
        {"source": "paperclip", "published_at": today_iso, "url": "/a"},
        {"source": "paperclip", "published_at": today_iso, "url": "/b"},
        {"source": "auto", "published_at": today_iso, "url": "/c"},
        {"source": "paperclip", "published_at": "2020-01-01T00:00:00+00:00", "url": "/old"},
    ]
    import json
    (tmp_path / "published_history_ko.json").write_text(json.dumps(entries))
    assert pp._count_today_paperclip_publishes() == 2
