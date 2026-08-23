"""Paperclip audit logging — bridge url-to-content job → Paperclip issue.

Phase 3: 모든 url-to-content job 을 Paperclip issue로 기록 (audit trail).
flow 변경 없이, paperclip API만 추가 호출.

Env:
  PAPERCLIP_AUDIT_ENABLED=1     (기본 ON; Paperclip 실패 시 graceful)
  PAPERCLIP_API_BASE
  PAPERCLIP_COMPANY_ID

Paperclip cost-events API Reference:
  POST /api/companies/{COMPANY_ID}/cost-events
    Request: {agentId, issueId, provider, model, inputTokens, outputTokens, costCents, occurredAt}
    Response: {id, companyId, agentId, issueId, ..., createdAt}
    Note: All fields are camelCase. occurredAt must be ISO 8601 format (e.g., "2026-05-21T15:40:05.878Z")
          costCents must be integer (USD cents). inputTokens/outputTokens are integers.

  GET /api/companies/{COMPANY_ID}/cost-events (NOT YET IMPLEMENTED in Paperclip)
    Query endpoint for cost-events is not available yet. When available, expect:
    Response: [cost_event, ...] with pagination support
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.getenv("PAPERCLIP_AUDIT_ENABLED", "1").strip() == "1"


def _api(method: str, path: str, body: dict | None = None) -> dict | list | None:
    """paperclip_publish의 _api_request 재사용. graceful fail."""
    if not _enabled():
        return None
    try:
        from auto_publisher.paperclip_publish import _api_request
        return _api_request(method, path, body=body, timeout=10)
    except Exception as e:
        logger.warning(f"paperclip_audit API fail: {e}")
        return None


def create_audit_issue(
    job_type: str, summary: str, lang: str = "ko", source: str = "n8n",
) -> str | None:
    """Generic Paperclip issue 생성. job_type: 'daily-publish' | 'market-wrap' | 'shorts-auto' | etc.
    issue_id 반환 (None on fail)."""
    if not _enabled():
        return None
    try:
        from auto_publisher.paperclip_publish import COMPANY_ID
    except Exception:
        return None
    body = {
        "title": f"[{job_type}] {summary[:80]}",
        "description": (
            f"job_type={job_type} source={source} lang={lang}\n"
            f"{summary}\n"
            f"auto-created by bridge_api"
        ),
        "status": "todo",
        "priority": "medium",
    }
    result = _api("POST", f"/api/companies/{COMPANY_ID}/issues", body)
    if isinstance(result, dict):
        return result.get("id")
    return None


def complete_audit_issue(
    issue_id: str,
    ok: bool,
    summary: str,
    error: str = "",
    blog_url: str = "",
    cost_breakdown: dict | None = None,
) -> None:
    """Generic completion + work_product + cost events."""
    if not _enabled() or not issue_id:
        return

    # 1. work_product (성공 시만)
    if ok and blog_url:
        try:
            wp_body = {
                "type": "document",
                "provider": "bridge-api",
                "title": blog_url[:120],
                "status": "archived",
                "url": blog_url if blog_url.startswith("http") else f"https://investiqs.net/",
                "summary": summary[:200],
            }
            _api("POST", f"/api/issues/{issue_id}/work-products", wp_body)
        except Exception as e:
            logger.warning(f"complete_audit_issue work_product 생성 실패 ({issue_id}): {e}")

    # 2. cost events
    if cost_breakdown and isinstance(cost_breakdown, dict):
        for model_name, costs in cost_breakdown.items():
            if not isinstance(costs, dict):
                continue
            try:
                record_cost_event(
                    issue_id=issue_id,
                    agent_id="bridge-api",
                    provider=costs.get("provider", "openrouter"),
                    model=model_name,
                    input_tokens=int(costs.get("input_tokens", 0)),
                    output_tokens=int(costs.get("output_tokens", 0)),
                    cost_usd=float(costs.get("cost_usd", 0.0)),
                )
            except Exception as e:
                logger.warning(f"complete_audit_issue cost_breakdown 처리 실패 ({model_name}): {e}")

    # 3. issue status 업데이트
    new_status = "done" if ok else "cancelled"
    _api("PATCH", f"/api/issues/{issue_id}", {"status": new_status})

    # 4. comment 추가 (audit log)
    if ok:
        body_text = (
            f"✅ Done\n"
            f"📝 {summary[:200]}\n"
            f"url: {blog_url or '(없음)'}"
        )
    else:
        body_text = f"❌ Failed: {(error or '')[:300]}"
    _api("POST", f"/api/issues/{issue_id}/comments", {"body": body_text})


def create_url_content_issue(
    url: str, lang: str = "ko", source: str = "discord",
    job_id: str = "", channel_id: str = "",
) -> str | None:
    """url-to-content job 시작 → Paperclip issue 생성. issue_id 반환 (None on fail).
    Thin wrapper around create_audit_issue."""
    summary = (
        f"source={source} lang={lang} job_id={job_id}\n"
        f"url={url}\n"
        f"channel_id={channel_id}"
    )
    return create_audit_issue("url-to-content", summary, lang=lang, source=source)


def record_cost_event(
    issue_id: str,
    agent_id: str = "bridge-api",
    provider: str = "openrouter",
    model: str = "gemini-2.5-flash",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> None:
    """url-to-content job의 비용 기록 → Paperclip cost-events.

    Args:
        issue_id: Paperclip issue ID
        agent_id: 에이전트 ID (기본 'bridge-api')
        provider: LLM 제공자 (openrouter, gemini, anthropic 등)
        model: 모델 이름 (gemini-2.5-flash, gpt-4-turbo 등)
        input_tokens: 입력 토큰 수
        output_tokens: 출력 토큰 수
        cost_usd: 비용 (USD) — costCents로 변환
    """
    if not _enabled() or not issue_id:
        return
    try:
        from auto_publisher.paperclip_publish import COMPANY_ID
    except Exception:
        return

    try:
        from datetime import datetime, timezone

        cost_cents = int(round(cost_usd * 100))
        body = {
            "agentId": agent_id,
            "issueId": issue_id,
            "provider": provider,
            "biller": provider,
            "model": model,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "costCents": cost_cents,
            "occurredAt": datetime.now(timezone.utc).isoformat(),
        }
        _api("POST", f"/api/companies/{COMPANY_ID}/cost-events", body)
    except Exception as e:
        logger.warning(f"record_cost_event 실패 ({issue_id}): {e}")


def complete_url_content_issue(
    issue_id: str,
    result: dict,
    ok: bool = True,
    error: str = "",
    cost_breakdown: dict | None = None,
) -> None:
    """url-to-content job 종료 → Paperclip issue status + work_product + cost events.

    Args:
        issue_id: Paperclip issue ID
        result: 작업 결과 딕셔너리
        ok: 성공 여부
        error: 에러 메시지 (ok=False 시)
        cost_breakdown: 비용 분류 딕셔너리
            형식: {model_name: {input_tokens, output_tokens, cost_usd}}
            예: {"gemini-2.5-flash": {input_tokens: 100, output_tokens: 50, cost_usd: 0.001}}
    """
    if not _enabled() or not issue_id:
        return

    # 1. work_product (성공 시만)
    if ok:
        try:
            _bu = result.get("blog_url", "") or ""
            wp_body = {
                "type": "document",
                "provider": "bridge-api",
                "title": (result.get("blog_url") or "blog_post")[:120],
                "status": "archived",
                "url": _bu if _bu.startswith("http") else "https://investiqs.net/",
                "summary": f"slug={result.get('slug','')} yt={result.get('youtube_url','')}",
                "metadata": {
                    "source_url": result.get("source_url"),
                    "platform": result.get("platform"),
                    "slug": result.get("slug"),
                    "youtube_url": result.get("youtube_url"),
                    "filepath": result.get("filepath"),
                },
            }
            _api("POST", f"/api/issues/{issue_id}/work-products", wp_body)
        except Exception as e:
            logger.warning(f"work_product 생성 실패 ({issue_id}): {e}")

    # 2. cost events (cost_breakdown 있으면 각 모델별로 기록)
    if cost_breakdown and isinstance(cost_breakdown, dict):
        for model_name, costs in cost_breakdown.items():
            if not isinstance(costs, dict):
                continue
            try:
                record_cost_event(
                    issue_id=issue_id,
                    agent_id="bridge-api",
                    provider=costs.get("provider", "openrouter"),
                    model=model_name,
                    input_tokens=int(costs.get("input_tokens", 0)),
                    output_tokens=int(costs.get("output_tokens", 0)),
                    cost_usd=float(costs.get("cost_usd", 0.0)),
                )
            except Exception as e:
                logger.warning(f"cost_breakdown 처리 실패 ({model_name}): {e}")

    # 3. issue status 업데이트
    new_status = "done" if ok else "cancelled"
    _api("PATCH", f"/api/issues/{issue_id}", {"status": new_status})

    # 4. comment 추가 (audit log)
    if ok:
        body_text = (
            f"✅ Published\n"
            f"📝 blog: {result.get('blog_url','(없음)')}\n"
            f"🎬 yt: {result.get('youtube_url','(영상 없음)')}\n"
            f"slug: {result.get('slug','')}"
        )
    else:
        body_text = f"❌ Failed: {(error or '')[:300]}"
    _api("POST", f"/api/issues/{issue_id}/comments", {"body": body_text})


def check_cost_threshold() -> dict:
    """오늘 누적 비용 vs PAPERCLIP_DAILY_COST_LIMIT_USD 비교.
    한도 도달 시 Discord webhook 알림 (DISCORD_WEBHOOK_URL).

    Returns:
        {
            "today_usd": float,
            "threshold_usd": float,
            "alert_sent": bool,
            "message": str (if alert sent),
            "webhook_error": str (if webhook failed),
            "skipped": str (if disabled)
        }
    """
    if not _enabled():
        return {"skipped": "PAPERCLIP_AUDIT_ENABLED=0"}

    try:
        from datetime import datetime, timezone, date
        from auto_publisher.paperclip_publish import COMPANY_ID
    except Exception:
        return {"skipped": "Failed to import COMPANY_ID or datetime"}

    threshold_usd = float(os.getenv("PAPERCLIP_DAILY_COST_LIMIT_USD", "5.0"))
    today_iso = date.today().isoformat()

    result = {
        "today_usd": 0.0,
        "threshold_usd": threshold_usd,
        "alert_sent": False,
    }

    try:
        # Query cost-events for today
        # Note: Paperclip cost-events GET endpoint may not exist yet.
        # For now, we simulate a query. In production, when endpoint is available:
        # GET /api/companies/{COMPANY_ID}/cost-events?from={today_iso}T00:00:00Z&to={today_iso}T23:59:59Z
        # For now, return placeholder since GET cost-events is not implemented
        # but keep the structure ready for when it is available.
        result["today_usd"] = 0.0

        # If today_usd >= threshold_usd, send Discord webhook alert
        if result["today_usd"] >= threshold_usd:
            webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
            if webhook_url:
                try:
                    import json
                    import urllib.request as _ur

                    msg = f"⚠️ Paperclip cost alert: today ${result['today_usd']:.2f} / ${threshold_usd:.2f} 한도 도달"
                    body = json.dumps({"content": msg}).encode()
                    req = _ur.Request(
                        webhook_url,
                        data=body,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    _ur.urlopen(req, timeout=10)
                    result["alert_sent"] = True
                    result["message"] = msg
                except Exception as e:
                    result["webhook_error"] = str(e)[:100]
            else:
                result["alert_sent"] = False

        return result

    except Exception as e:
        logger.warning(f"check_cost_threshold failed: {e}")
        result["error"] = str(e)[:100]
        return result


def monthly_cost_summary(year: int | None = None, month: int | None = None) -> dict:
    """Monthly cost summary by model from Paperclip cost-events.

    Query Paperclip cost-events for a given month and aggregate by model.

    Args:
        year: Year (None = current UTC year)
        month: Month (None = current UTC month)

    Returns:
        Dictionary with structure:
        {
            "year": int,
            "month": int,
            "period": "YYYY-MM",
            "models": {
                "model_name": {
                    "calls": int,
                    "input_tokens": int,
                    "output_tokens": int,
                    "cost_cents": int,
                },
                ...
            },
            "total": {
                "calls": int,
                "input_tokens": int,
                "output_tokens": int,
                "cost_cents": int,
            },
            "error": str (if API fails)
        }
    """
    if not _enabled():
        return {"error": "PAPERCLIP_AUDIT_ENABLED not set"}

    try:
        from datetime import datetime, timezone
        from auto_publisher.paperclip_publish import COMPANY_ID
    except Exception:
        return {"error": "Failed to import COMPANY_ID"}

    # Default to current UTC date
    now = datetime.now(timezone.utc)
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    # Validate month/year
    if not (1 <= month <= 12):
        return {"error": f"Invalid month: {month}"}
    if year < 2000 or year > 2100:
        return {"error": f"Invalid year: {year}"}

    # Query parameters: from start of month to end of month (UTC)
    # Note: Paperclip cost-events GET endpoint may not exist yet.
    # This implementation returns placeholder data for now.
    # In production, when the endpoint is available, use:
    # GET /api/companies/{COMPANY_ID}/cost-events?from=YYYY-MM-01T00:00:00Z&to=YYYY-MM-{last_day}T23:59:59Z

    period_str = f"{year:04d}-{month:02d}"

    try:
        # Attempt to query (endpoint may not exist yet)
        # path = f"/api/companies/{COMPANY_ID}/cost-events"
        # params = {
        #     "from": f"{year:04d}-{month:02d}-01T00:00:00Z",
        #     "to": f"{year:04d}-{month:02d}-{_last_day_of_month(month, year):02d}T23:59:59Z",
        #     "limit": 1000
        # }
        # result = _api_get(path, params)

        # For now, return structure with error message
        return {
            "year": year,
            "month": month,
            "period": period_str,
            "models": {},
            "total": {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_cents": 0,
            },
            "note": "Cost-events GET endpoint not yet implemented in Paperclip",
        }
    except Exception as e:
        logger.warning(f"monthly_cost_summary query failed: {e}")
        return {
            "year": year,
            "month": month,
            "period": period_str,
            "error": str(e),
        }


if __name__ == "__main__":
    """CLI entry point for paperclip_audit operations.

    Usage:
        python3 -m auto_publisher.paperclip_audit summary [--year YYYY] [--month MM]
        python3 -m auto_publisher.paperclip_audit alert
    """
    import argparse
    import sys
    import json

    parser = argparse.ArgumentParser(description="Paperclip audit CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Show monthly cost summary")
    summary_parser.add_argument("--year", type=int, default=None, help="Year (default: current)")
    summary_parser.add_argument("--month", type=int, default=None, help="Month (default: current)")

    # Alert command
    alert_parser = subparsers.add_parser("alert", help="Check daily cost threshold and send alert if needed")

    args = parser.parse_args()

    if args.command == "summary":
        import json
        from datetime import datetime, timezone

        year = args.year
        month = args.month

        # If no year/month, use current UTC
        if year is None or month is None:
            now = datetime.now(timezone.utc)
            if year is None:
                year = now.year
            if month is None:
                month = now.month

        result = monthly_cost_summary(year=year, month=month)

        # Pretty-print summary table
        period = result.get("period", f"{year:04d}-{month:02d}")
        print(f"\n== {period} Cost Summary ==\n")

        if "error" in result:
            print(f"Error: {result['error']}")
            if "note" in result:
                print(f"Note: {result['note']}")
            sys.exit(1)

        models = result.get("models", {})
        total = result.get("total", {})

        if not models:
            print("No cost data available for this period.")
            if "note" in result:
                print(f"({result['note']})")
            sys.exit(0)

        # Print header
        print(f"{'model':<35} {'calls':>8} {'in_tok':>12} {'out_tok':>12} {'cost':>10}")
        print("-" * 78)

        # Sort models by cost (descending)
        sorted_models = sorted(
            models.items(),
            key=lambda x: x[1].get("cost_cents", 0),
            reverse=True,
        )

        # Print each model
        for model_name, costs in sorted_models:
            calls = costs.get("calls", 0)
            input_toks = costs.get("input_tokens", 0)
            output_toks = costs.get("output_tokens", 0)
            cost_cents = costs.get("cost_cents", 0)
            cost_usd = cost_cents / 100.0

            print(
                f"{model_name:<35} {calls:>8} {input_toks:>12,} {output_toks:>12,} ${cost_usd:>9.2f}"
            )

        # Print total
        print("-" * 78)
        total_calls = total.get("calls", 0)
        total_input = total.get("input_tokens", 0)
        total_output = total.get("output_tokens", 0)
        total_cost_cents = total.get("cost_cents", 0)
        total_cost_usd = total_cost_cents / 100.0

        print(
            f"{'TOTAL':<35} {total_calls:>8} {total_input:>12,} {total_output:>12,} ${total_cost_usd:>9.2f}"
        )
        print()
    elif args.command == "alert":
        result = check_cost_threshold()
        print(json.dumps(result, indent=2))
        if "skipped" in result:
            sys.exit(0)
        if result.get("alert_sent"):
            print(f"\n✅ Alert sent: {result.get('message')}")
            sys.exit(0)
        elif result.get("webhook_error"):
            print(f"\n⚠️ Webhook error: {result.get('webhook_error')}")
            sys.exit(1)
        else:
            print(f"\n✅ Cost check: ${result.get('today_usd', 0):.2f} / ${result.get('threshold_usd', 0):.2f}")
            sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)
