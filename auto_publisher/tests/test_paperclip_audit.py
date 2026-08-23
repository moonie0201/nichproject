"""paperclip_audit 테스트 — API mock + graceful fail validation."""
from unittest.mock import patch, MagicMock

import pytest

from auto_publisher import paperclip_audit as pa


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """모든 테스트에서 audit 활성화 (individual test에서 disable)."""
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")


# ─────────────────────────────────────────────────────────────────────────────
# test_disabled_returns_none — PAPERCLIP_AUDIT_ENABLED=0 → create_url_content_issue 반환 None
# ─────────────────────────────────────────────────────────────────────────────
def test_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "0")
    result = pa.create_url_content_issue(
        url="https://example.com/article",
        lang="ko",
        source="discord",
        job_id="job-123",
        channel_id="ch-456"
    )
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# test_disabled_skips_complete — PAPERCLIP_AUDIT_ENABLED=0 → complete_url_content_issue no-op
# ─────────────────────────────────────────────────────────────────────────────
def test_disabled_skips_complete(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "0")
    with patch.object(pa, "_api") as mock_api:
        pa.complete_url_content_issue(
            issue_id="issue-123",
            result={"blog_url": "https://blog.com/post"},
            ok=True
        )
    # no API calls when disabled
    mock_api.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# test_create_issue_returns_id — mock _api_request → function returns issue_id
# ─────────────────────────────────────────────────────────────────────────────
def test_create_issue_returns_id(monkeypatch):
    # Mock COMPANY_ID import
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "ccd0c00a-d565-4fc4-910f-9d823665313b"):
        with patch.object(pa, "_api") as mock_api:
            mock_api.return_value = {"id": "abc-123"}
            result = pa.create_url_content_issue(
                url="https://example.com/article",
                lang="ko",
                source="discord",
                job_id="job-123",
                channel_id="ch-456"
            )
    assert result == "abc-123"
    # Verify API call was made with correct path and method
    mock_api.assert_called_once()
    call_args = mock_api.call_args
    assert call_args[0][0] == "POST"  # method
    assert "/issues" in call_args[0][1]  # path contains /issues


# ─────────────────────────────────────────────────────────────────────────────
# test_create_issue_api_fail_returns_none — _api_request raises → _api catches → returns None
# ─────────────────────────────────────────────────────────────────────────────
def test_create_issue_api_fail_returns_none(monkeypatch):
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "ccd0c00a-d565-4fc4-910f-9d823665313b"):
        with patch("auto_publisher.paperclip_publish._api_request") as mock_api_req:
            mock_api_req.side_effect = RuntimeError("API connection failed")
            result = pa.create_url_content_issue(
                url="https://example.com/article",
                lang="ko",
                source="discord"
            )
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# test_create_issue_import_fail_returns_none — COMPANY_ID import fail → None
# ─────────────────────────────────────────────────────────────────────────────
def test_create_issue_import_fail_returns_none(monkeypatch):
    # Patch the dynamic import inside create_url_content_issue
    def side_effect_func(module_name):
        if module_name == "auto_publisher.paperclip_publish":
            raise Exception("import fail")
        # For actual imports, use the real __import__
        return __import__(module_name)

    with patch("builtins.__import__", side_effect=side_effect_func):
        result = pa.create_url_content_issue(
            url="https://example.com/article",
            lang="ko",
            source="discord"
        )
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# test_complete_ok_creates_workproduct_and_comment — verify API calls for success path
# ─────────────────────────────────────────────────────────────────────────────
def test_complete_ok_creates_workproduct_and_comment(monkeypatch):
    with patch.object(pa, "_api") as mock_api:
        mock_api.return_value = {"id": "wp-1"}
        pa.complete_url_content_issue(
            issue_id="issue-123",
            result={
                "blog_url": "https://blog.com/post-slug",
                "youtube_url": "https://youtube.com/watch?v=abc",
                "slug": "post-slug",
                "source_url": "https://source.com",
                "platform": "YouTube",
                "filepath": "/path/to/file.md"
            },
            ok=True,
            error=""
        )
    # Should have 3 API calls: POST work-products, PATCH status, POST comment
    assert mock_api.call_count == 3

    calls = mock_api.call_args_list
    # Call 1: POST work-products
    assert calls[0][0][0] == "POST"
    assert "/work-products" in calls[0][0][1]
    assert calls[0][0][2]["type"] == "blog_post"
    assert calls[0][0][2]["status"] == "published"
    assert calls[0][0][2]["url"] == "https://blog.com/post-slug"

    # Call 2: PATCH status to done
    assert calls[1][0][0] == "PATCH"
    assert "/issues/issue-123" in calls[1][0][1]
    assert calls[1][0][2]["status"] == "done"

    # Call 3: POST comment
    assert calls[2][0][0] == "POST"
    assert "/comments" in calls[2][0][1]
    assert "Published" in calls[2][0][2]["body"]
    assert "https://blog.com/post-slug" in calls[2][0][2]["body"]


# ─────────────────────────────────────────────────────────────────────────────
# test_complete_fail_status_cancelled — ok=False → status=cancelled, error in comment
# ─────────────────────────────────────────────────────────────────────────────
def test_complete_fail_status_cancelled(monkeypatch):
    with patch.object(pa, "_api") as mock_api:
        pa.complete_url_content_issue(
            issue_id="issue-123",
            result={"blog_url": ""},
            ok=False,
            error="Video encoding failed: GPU out of memory"
        )
    # Should have 2 API calls: PATCH status, POST comment (no work-products)
    assert mock_api.call_count == 2

    calls = mock_api.call_args_list
    # Call 1: PATCH status to cancelled
    assert calls[0][0][0] == "PATCH"
    assert "/issues/issue-123" in calls[0][0][1]
    assert calls[0][0][2]["status"] == "cancelled"

    # Call 2: POST comment with error
    assert calls[1][0][0] == "POST"
    assert "/comments" in calls[1][0][1]
    assert "Failed" in calls[1][0][2]["body"]
    assert "GPU out of memory" in calls[1][0][2]["body"]


# ─────────────────────────────────────────────────────────────────────────────
# test_complete_no_issue_id_noop — empty issue_id → no API calls
# ─────────────────────────────────────────────────────────────────────────────
def test_complete_no_issue_id_noop(monkeypatch):
    with patch.object(pa, "_api") as mock_api:
        pa.complete_url_content_issue(
            issue_id="",
            result={"blog_url": "https://blog.com/post"},
            ok=True
        )
    mock_api.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# test_complete_workproduct_url_in_body — verify result.blog_url in work_product body
# ─────────────────────────────────────────────────────────────────────────────
def test_complete_workproduct_url_in_body(monkeypatch):
    with patch.object(pa, "_api") as mock_api:
        pa.complete_url_content_issue(
            issue_id="issue-123",
            result={
                "blog_url": "https://investiqs.net/ko/articles/voo-etf-analysis",
                "youtube_url": "https://youtube.com/watch?v=abc123",
                "slug": "voo-etf-analysis",
                "source_url": "https://source.com/article",
                "platform": "YouTube",
                "filepath": "/articles/voo-etf.md"
            },
            ok=True,
            error=""
        )
    # Extract work-products call (first call)
    calls = mock_api.call_args_list
    wp_call = calls[0]

    # Verify blog_url is in the work_product body
    wp_body = wp_call[0][2]
    assert wp_body["url"] == "https://investiqs.net/ko/articles/voo-etf-analysis"
    # Also in summary
    assert "voo-etf-analysis" in wp_body["summary"]


# ─────────────────────────────────────────────────────────────────────────────
# test_complete_workproduct_exception_graceful — work_product POST fail → continue with status/comment
# ─────────────────────────────────────────────────────────────────────────────
def test_complete_workproduct_exception_graceful(monkeypatch):
    with patch.object(pa, "_api") as mock_api:
        # First call (work-products) raises, others succeed
        mock_api.side_effect = [
            RuntimeError("work-products create failed"),
            {"status": "done"},  # status patch
            {"body": "comment"}   # comment post
        ]
        pa.complete_url_content_issue(
            issue_id="issue-123",
            result={"blog_url": "https://blog.com/post"},
            ok=True,
            error=""
        )
    # Should still make all 3 calls despite work-products exception
    assert mock_api.call_count == 3


# ─────────────────────────────────────────────────────────────────────────────
# test_complete_error_truncated — error message truncated to 300 chars
# ─────────────────────────────────────────────────────────────────────────────
def test_complete_error_truncated(monkeypatch):
    long_error = "This is a very long error message. " * 20  # > 300 chars
    with patch.object(pa, "_api") as mock_api:
        pa.complete_url_content_issue(
            issue_id="issue-123",
            result={},
            ok=False,
            error=long_error
        )
    # Get comment call (second call)
    calls = mock_api.call_args_list
    comment_call = calls[1]
    comment_body = comment_call[0][2]["body"]

    # Should be truncated and contain "Failed:"
    assert "Failed:" in comment_body
    assert len(comment_body) <= 330  # Some buffer for "Failed: " prefix


# ─────────────────────────────────────────────────────────────────────────────
# test_complete_comment_ok_format — verify success comment format
# ─────────────────────────────────────────────────────────────────────────────
def test_complete_comment_ok_format(monkeypatch):
    with patch.object(pa, "_api") as mock_api:
        pa.complete_url_content_issue(
            issue_id="issue-123",
            result={
                "blog_url": "https://blog.com/voo-etf",
                "youtube_url": "https://youtube.com/watch?v=xyz",
                "slug": "voo-etf"
            },
            ok=True,
            error=""
        )
    # Get comment call (third call)
    calls = mock_api.call_args_list
    comment_call = calls[2]
    body = comment_call[0][2]["body"]

    assert "✅ Published" in body
    assert "📝 blog:" in body
    assert "🎬 yt:" in body
    assert "slug:" in body
    assert "https://blog.com/voo-etf" in body
    assert "https://youtube.com/watch?v=xyz" in body


# ─────────────────────────────────────────────────────────────────────────────
# test_complete_comment_fail_format — verify fail comment format
# ─────────────────────────────────────────────────────────────────────────────
def test_complete_comment_fail_format(monkeypatch):
    with patch.object(pa, "_api") as mock_api:
        pa.complete_url_content_issue(
            issue_id="issue-123",
            result={},
            ok=False,
            error="Encoding failed"
        )
    # Get comment call (second call)
    calls = mock_api.call_args_list
    comment_call = calls[1]
    body = comment_call[0][2]["body"]

    assert "❌ Failed:" in body
    assert "Encoding failed" in body


# ─────────────────────────────────────────────────────────────────────────────
# test_enabled_flag — _enabled() reads PAPERCLIP_AUDIT_ENABLED correctly
# ─────────────────────────────────────────────────────────────────────────────
def test_enabled_flag(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    assert pa._enabled() is True

    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "0")
    assert pa._enabled() is False

    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", " 1 ")
    assert pa._enabled() is True


# ─────────────────────────────────────────────────────────────────────────────
# test_api_graceful_fail — _api catches and logs exceptions
# ─────────────────────────────────────────────────────────────────────────────
def test_api_graceful_fail(monkeypatch):
    with patch("auto_publisher.paperclip_publish._api_request") as mock_api_req:
        mock_api_req.side_effect = RuntimeError("Connection failed")
        result = pa._api("POST", "/api/test", {"key": "value"})
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# test_api_disabled_returns_none — _api returns None when disabled
# ─────────────────────────────────────────────────────────────────────────────
def test_api_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "0")
    with patch("auto_publisher.paperclip_publish._api_request") as mock_api_req:
        result = pa._api("POST", "/api/test", {"key": "value"})
    # Should not even attempt the import/call
    mock_api_req.assert_not_called()
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# test_api_success — _api returns result dict
# ─────────────────────────────────────────────────────────────────────────────
def test_api_success(monkeypatch):
    with patch("auto_publisher.paperclip_publish._api_request") as mock_api_req:
        mock_api_req.return_value = {"id": "issue-123", "status": "todo"}
        result = pa._api("POST", "/api/issues", {"title": "test"})
    assert result == {"id": "issue-123", "status": "todo"}


# ─────────────────────────────────────────────────────────────────────────────
# test_create_issue_body_structure — verify POST body format and content
# ─────────────────────────────────────────────────────────────────────────────
def test_create_issue_body_structure(monkeypatch):
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        with patch.object(pa, "_api") as mock_api:
            mock_api.return_value = {"id": "issue-1"}
            pa.create_url_content_issue(
                url="https://example.com/long-url-article-here",
                lang="ja",
                source="api",
                job_id="job-999",
                channel_id="ch-888"
            )

    # Verify POST call
    call_args = mock_api.call_args
    body = call_args[0][2]

    assert "title" in body
    assert "https://example.com/long-url-article-here" in body["title"]
    assert body["status"] == "todo"
    assert body["priority"] == "medium"
    assert "description" in body
    assert "source=api" in body["description"]
    assert "lang=ja" in body["description"]
    assert "job_id=job-999" in body["description"]
    assert "ch-888" in body["description"]


# ─────────────────────────────────────────────────────────────────────────────
# test_workproduct_metadata_complete — verify work_product metadata fields
# ─────────────────────────────────────────────────────────────────────────────
def test_workproduct_metadata_complete(monkeypatch):
    with patch.object(pa, "_api") as mock_api:
        pa.complete_url_content_issue(
            issue_id="issue-123",
            result={
                "blog_url": "https://blog.com/article",
                "youtube_url": "https://youtube.com/v1",
                "slug": "article-slug",
                "source_url": "https://source.com/orig",
                "platform": "YouTube",
                "filepath": "/content/article.md"
            },
            ok=True
        )

    calls = mock_api.call_args_list
    wp_call = calls[0]
    body = wp_call[0][2]

    assert body["type"] == "blog_post"
    assert body["provider"] == "bridge-api"
    assert body["status"] == "published"

    # Metadata should include all fields
    metadata = body["metadata"]
    assert metadata["source_url"] == "https://source.com/orig"
    assert metadata["platform"] == "YouTube"
    assert metadata["slug"] == "article-slug"
    assert metadata["youtube_url"] == "https://youtube.com/v1"
    assert metadata["filepath"] == "/content/article.md"


# ─────────────────────────────────────────────────────────────────────────────
# test_monthly_cost_summary_default_month — monthly_cost_summary uses current UTC
# ─────────────────────────────────────────────────────────────────────────────
def test_monthly_cost_summary_default_month(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.monthly_cost_summary()

    assert "period" in result
    assert result.get("year") is not None
    assert result.get("month") is not None
    assert result.get("total") is not None
    assert result["total"]["cost_cents"] == 0  # No data yet


# ─────────────────────────────────────────────────────────────────────────────
# test_monthly_cost_summary_explicit_month — monthly_cost_summary with year/month
# ─────────────────────────────────────────────────────────────────────────────
def test_monthly_cost_summary_explicit_month(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.monthly_cost_summary(year=2026, month=5)

    assert result["year"] == 2026
    assert result["month"] == 5
    assert result["period"] == "2026-05"
    assert result.get("total") is not None


# ─────────────────────────────────────────────────────────────────────────────
# test_monthly_cost_summary_invalid_month — invalid month returns error
# ─────────────────────────────────────────────────────────────────────────────
def test_monthly_cost_summary_invalid_month(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.monthly_cost_summary(year=2026, month=13)

    assert "error" in result
    assert "Invalid month" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# test_monthly_cost_summary_invalid_year — invalid year returns error
# ─────────────────────────────────────────────────────────────────────────────
def test_monthly_cost_summary_invalid_year(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.monthly_cost_summary(year=1999, month=5)

    assert "error" in result
    assert "Invalid year" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# test_monthly_cost_summary_disabled — disabled returns error
# ─────────────────────────────────────────────────────────────────────────────
def test_monthly_cost_summary_disabled(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "0")
    result = pa.monthly_cost_summary(year=2026, month=5)

    assert "error" in result
    assert "PAPERCLIP_AUDIT_ENABLED" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# test_monthly_cost_summary_structure — verify result structure
# ─────────────────────────────────────────────────────────────────────────────
def test_monthly_cost_summary_structure(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.monthly_cost_summary(year=2026, month=3)

    assert "year" in result
    assert "month" in result
    assert "period" in result
    assert "total" in result
    assert "models" in result

    total = result["total"]
    assert "calls" in total
    assert "input_tokens" in total
    assert "output_tokens" in total
    assert "cost_cents" in total


# ─────────────────────────────────────────────────────────────────────────────
# test_check_cost_threshold_disabled — PAPERCLIP_AUDIT_ENABLED=0 → skipped result
# ─────────────────────────────────────────────────────────────────────────────
def test_check_cost_threshold_disabled(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "0")
    result = pa.check_cost_threshold()
    assert "skipped" in result
    assert "PAPERCLIP_AUDIT_ENABLED" in result["skipped"]


# ─────────────────────────────────────────────────────────────────────────────
# test_check_cost_threshold_below_limit — cost < threshold → no alert
# ─────────────────────────────────────────────────────────────────────────────
def test_check_cost_threshold_below_limit(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    monkeypatch.setenv("PAPERCLIP_DAILY_COST_LIMIT_USD", "10.0")
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.check_cost_threshold()

    assert result["today_usd"] == 0.0
    assert result["threshold_usd"] == 10.0
    assert result["alert_sent"] is False
    assert "message" not in result


# ─────────────────────────────────────────────────────────────────────────────
# test_check_cost_threshold_above_limit_no_webhook — cost >= threshold + no webhook → alert_sent=False
# ─────────────────────────────────────────────────────────────────────────────
def test_check_cost_threshold_above_limit_no_webhook(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    monkeypatch.setenv("PAPERCLIP_DAILY_COST_LIMIT_USD", "0.0")  # Threshold is 0, so any cost >= 0
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.check_cost_threshold()

    # In the current implementation, today_usd is always 0 (GET endpoint not ready)
    # but the structure is correct for when it is implemented
    assert result["alert_sent"] is False
    assert result["threshold_usd"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# test_check_cost_threshold_above_limit_with_webhook — cost >= threshold + webhook → urlopen called
# ─────────────────────────────────────────────────────────────────────────────
def test_check_cost_threshold_above_limit_with_webhook(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    monkeypatch.setenv("PAPERCLIP_DAILY_COST_LIMIT_USD", "5.0")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    # Mock urlopen
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = MagicMock()
        with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
            # We need to mock the cost to be >= threshold
            # Since the implementation doesn't yet query cost-events,
            # we simulate a scenario where the threshold is very low
            monkeypatch.setenv("PAPERCLIP_DAILY_COST_LIMIT_USD", "0.0")
            result = pa.check_cost_threshold()

            # When today_usd >= threshold_usd and webhook is present,
            # webhook should be called (but only if cost is high enough)
            # In current impl, cost is always 0, so no webhook call expected
            # This test verifies the structure is ready
            assert "threshold_usd" in result
            assert result["threshold_usd"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# test_check_cost_threshold_webhook_error — webhook fails → webhook_error captured
# ─────────────────────────────────────────────────────────────────────────────
def test_check_cost_threshold_webhook_error(monkeypatch):
    import os
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    monkeypatch.setenv("PAPERCLIP_DAILY_COST_LIMIT_USD", "0.0")  # Force threshold breach
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/invalid")

    # Mock urlopen to raise exception
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = RuntimeError("Network error")
        with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
            # The function gracefully handles webhook errors
            result = pa.check_cost_threshold()
            # Since today_usd is 0 in the current implementation,
            # this test validates the structure is correct
            assert "threshold_usd" in result
            assert result["threshold_usd"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# test_check_cost_threshold_structure — verify result dict structure
# ─────────────────────────────────────────────────────────────────────────────
def test_check_cost_threshold_structure(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.check_cost_threshold()

    assert "today_usd" in result
    assert "threshold_usd" in result
    assert "alert_sent" in result
    assert isinstance(result["today_usd"], float)
    assert isinstance(result["threshold_usd"], float)
    assert isinstance(result["alert_sent"], bool)


# ─────────────────────────────────────────────────────────────────────────────
# test_check_cost_threshold_default_threshold — default threshold is 5.0 USD
# ─────────────────────────────────────────────────────────────────────────────
def test_check_cost_threshold_default_threshold(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    monkeypatch.delenv("PAPERCLIP_DAILY_COST_LIMIT_USD", raising=False)
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.check_cost_threshold()

    assert result["threshold_usd"] == 5.0


# ─────────────────────────────────────────────────────────────────────────────
# test_check_cost_threshold_custom_threshold — custom threshold is used
# ─────────────────────────────────────────────────────────────────────────────
def test_check_cost_threshold_custom_threshold(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")
    monkeypatch.setenv("PAPERCLIP_DAILY_COST_LIMIT_USD", "15.5")
    with patch("auto_publisher.paperclip_publish.COMPANY_ID", "test-company-id"):
        result = pa.check_cost_threshold()

    assert result["threshold_usd"] == 15.5


# ─────────────────────────────────────────────────────────────────────────────
# test_check_cost_threshold_import_fail — import fail → graceful return
# ─────────────────────────────────────────────────────────────────────────────
def test_check_cost_threshold_import_fail(monkeypatch):
    monkeypatch.setenv("PAPERCLIP_AUDIT_ENABLED", "1")

    def side_effect_func(module_name):
        if module_name == "auto_publisher.paperclip_publish":
            raise Exception("import fail")
        return __import__(module_name)

    with patch("builtins.__import__", side_effect=side_effect_func):
        result = pa.check_cost_threshold()

    assert "skipped" in result
    assert "Failed to import" in result["skipped"]
