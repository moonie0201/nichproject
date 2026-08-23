"""
Integration tests for new bridge_api routes — runs against LIVE bridge.

Run:
    cd /home/mh/ocstorage/workspace/nichproject
    venv/bin/python3 -m pytest n8n/tests/test_bridge_routes.py -v --no-header

All tests are skipped automatically when the bridge is not reachable.
No real publishes, no LLM calls, no side effects.
"""
import os
import pytest
import requests

BRIDGE = os.getenv("BRIDGE_API_URL", "http://172.17.0.1:8765")


def _bridge_alive() -> bool:
    try:
        r = requests.get(f"{BRIDGE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _bridge_alive(), reason="bridge not running"
)


# ---------------------------------------------------------------------------
# 1. GET /health — basic liveness
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_health_returns_ok():
    """GET /health returns HTTP 200 with status=ok."""
    r = requests.get(f"{BRIDGE}/health", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


# ---------------------------------------------------------------------------
# 2. GET /health/full — bot_status field
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_health_full_has_bot_status():
    """GET /health/full contains bot_status with discord/telegram/slack keys."""
    r = requests.get(f"{BRIDGE}/health/full", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "bot_status" in body, "missing bot_status field"
    bs = body["bot_status"]
    assert isinstance(bs, dict), "bot_status must be a dict"
    for key in ("discord_hermes_callback", "telegram_callback", "slack_callback"):
        assert key in bs, f"bot_status missing key '{key}'"
        assert isinstance(bs[key], bool), f"bot_status['{key}'] must be bool"


# ---------------------------------------------------------------------------
# 3. GET /health/full — paperclip_today_cost field
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_health_full_has_paperclip_cost():
    """GET /health/full contains paperclip_today_cost with usd and threshold_usd keys."""
    r = requests.get(f"{BRIDGE}/health/full", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "paperclip_today_cost" in body, "missing paperclip_today_cost field"
    cost = body["paperclip_today_cost"]
    assert isinstance(cost, dict), "paperclip_today_cost must be a dict"
    assert "usd" in cost, "paperclip_today_cost missing 'usd' key"
    assert "threshold_usd" in cost, "paperclip_today_cost missing 'threshold_usd' key"
    assert isinstance(cost["usd"], (int, float)), "'usd' must be numeric"
    assert isinstance(cost["threshold_usd"], (int, float)), "'threshold_usd' must be numeric"


# ---------------------------------------------------------------------------
# 4. POST /url-to-content — returns job_id without side effects
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_url_to_content_returns_job_id():
    """POST /url-to-content with publish_blog=false returns 202 + job_id."""
    payload = {
        "url": "https://investiqs.net/ko/privacy/",
        "publish_blog": False,
        "publish_shorts": False,
    }
    r = requests.post(f"{BRIDGE}/url-to-content", json=payload, timeout=10)
    assert r.status_code in (200, 202), f"expected 200 or 202, got {r.status_code}"
    body = r.json()
    assert "job_id" in body, "response missing 'job_id'"
    assert "status" in body, "response missing 'status'"
    assert isinstance(body["job_id"], str) and body["job_id"], "job_id must be a non-empty string"
    assert body["status"] in ("queued", "pending", "accepted"), (
        f"unexpected status value: {body['status']!r}"
    )


# ---------------------------------------------------------------------------
# 5. GET /url-to-content-status — 404 for unknown job_id
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_url_to_content_status_404_unknown():
    """GET /url-to-content-status with a nonexistent job_id returns 404."""
    r = requests.get(
        f"{BRIDGE}/url-to-content-status",
        params={"job_id": "nonexistent-job-00000000-0000-0000-0000-000000000000"},
        timeout=5,
    )
    assert r.status_code == 404, f"expected 404 for unknown job_id, got {r.status_code}"


# ---------------------------------------------------------------------------
# 6. POST /paperclip/cost-alert-check — returns threshold fields
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_cost_alert_check_returns_threshold():
    """POST /paperclip/cost-alert-check returns today_usd and threshold_usd."""
    r = requests.post(f"{BRIDGE}/paperclip/cost-alert-check", timeout=10)
    assert r.status_code == 200, f"expected 200, got {r.status_code}"
    body = r.json()
    assert "today_usd" in body, "response missing 'today_usd'"
    assert "threshold_usd" in body, "response missing 'threshold_usd'"
    assert isinstance(body["today_usd"], (int, float)), "'today_usd' must be numeric"
    assert isinstance(body["threshold_usd"], (int, float)), "'threshold_usd' must be numeric"


# ---------------------------------------------------------------------------
# 7. POST /paperclip/poll-and-publish — skipped when disabled (default env)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_paperclip_poll_skipped_when_disabled():
    """POST /paperclip/poll-and-publish returns a skipped indicator when PAPERCLIP_PUBLISH_ENABLED=0."""
    r = requests.post(f"{BRIDGE}/paperclip/poll-and-publish", timeout=15)
    assert r.status_code == 200, f"expected 200, got {r.status_code}"
    body = r.json()
    # Bridge env has PAPERCLIP_PUBLISH_ENABLED=0 by default; expect skipped field or
    # processed=0 with a skipped key explaining the reason.
    skipped_str = body.get("skipped", "")
    processed = body.get("processed", None)
    assert skipped_str or processed == 0, (
        "expected 'skipped' field or processed=0 when PAPERCLIP_PUBLISH_ENABLED=0"
    )
    if skipped_str:
        assert "PAPERCLIP_PUBLISH_ENABLED" in str(skipped_str), (
            f"skipped message should mention PAPERCLIP_PUBLISH_ENABLED, got: {skipped_str!r}"
        )
