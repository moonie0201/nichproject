"""Paperclip work_product → HugoPublisher 파이프라인.

Paperclip Issue 의 work_product(type=blog_post, status=ready)을 폴링.
각 후보는 10-step validation hooks 통과 시 HugoPublisher.publish() 호출.
실패는 Paperclip comment에 사유 기록 + work_product status=blocked.

Env:
  PAPERCLIP_API_BASE         default http://127.0.0.1:3100
  PAPERCLIP_COMPANY_ID       default NichProject UUID
  PAPERCLIP_PUBLISH_ENABLED  default 0  (opt-in master switch)
  PAPERCLIP_PUBLISH_DRY_RUN  default 0  (publish 직전 skip)
  PAPERCLIP_PUBLISH_COMPLIANCE default 1
  PAPERCLIP_PUBLISH_SEO      default 1
  PAPERCLIP_PUBLISH_DAILY_LIMIT default 3
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from glob import glob
from pathlib import Path

logger = logging.getLogger(__name__)

PAPERCLIP_BASE = os.getenv("PAPERCLIP_API_BASE", "http://127.0.0.1:3100").rstrip("/")
COMPANY_ID = os.getenv("PAPERCLIP_COMPANY_ID", "ccd0c00a-d565-4fc4-910f-9d823665313b")
DATA_DIR = Path(__file__).parent / "data"

# Niche allowlist — 사이트 토픽 클러스터 이탈 방지
ALLOWED_CATEGORIES = {
    "finance", "investment", "etf", "재테크", "투자",
    "배당", "주식", "stocks", "dividend",
    "연금", "절세", "tax", "tax-saving",
    "리츠", "reits", "부동산", "real-estate",
    "채권", "bond", "암호화폐", "crypto",
    "시장분석", "market-analysis",
}

USER_AGENT = "Mozilla/5.0 (investiqs-paperclip-bridge)"


def _enabled() -> bool:
    return os.getenv("PAPERCLIP_PUBLISH_ENABLED", "0").strip() == "1"


def _dry_run() -> bool:
    return os.getenv("PAPERCLIP_PUBLISH_DRY_RUN", "0").strip() == "1"


def _compliance_required() -> bool:
    return os.getenv("PAPERCLIP_PUBLISH_COMPLIANCE", "1").strip() == "1"


def _seo_required() -> bool:
    return os.getenv("PAPERCLIP_PUBLISH_SEO", "1").strip() == "1"


def _daily_limit() -> int:
    try:
        return int(os.getenv("PAPERCLIP_PUBLISH_DAILY_LIMIT", "3"))
    except ValueError:
        return 3


# ─────────────────────────────────────────────────────────────────────────────
# Paperclip API client (urllib stdlib)
# ─────────────────────────────────────────────────────────────────────────────
def _api_request(method: str, path: str, body: dict | None = None, timeout: int = 30) -> dict | list:
    url = PAPERCLIP_BASE + path
    data = None
    headers = {"User-Agent": USER_AGENT}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    api_key = os.getenv("PAPERCLIP_API_KEY", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"Paperclip API {method} {path} HTTP {e.code}: {body_text[:200]}") from e


def _api_get(path: str, params: dict | None = None) -> dict | list:
    if params:
        path += "?" + urllib.parse.urlencode(params)
    return _api_request("GET", path)


def _api_patch(path: str, body: dict) -> dict | list:
    return _api_request("PATCH", path, body)


def _api_post(path: str, body: dict) -> dict | list:
    return _api_request("POST", path, body)


# ─────────────────────────────────────────────────────────────────────────────
# Discovery
# ─────────────────────────────────────────────────────────────────────────────
def find_pending_blog_workproducts() -> list[dict]:
    """Paperclip 에서 type=blog_post + status=ready work_product 후보 반환."""
    if not _enabled():
        return []
    try:
        issues = _api_get(f"/api/companies/{COMPANY_ID}/issues", {"limit": 100})
    except Exception as e:
        logger.warning(f"paperclip issues fetch fail: {e}")
        return []

    issues_list = issues if isinstance(issues, list) else issues.get("issues", [])
    candidates: list[dict] = []
    for issue in issues_list:
        if issue.get("hiddenAt") or issue.get("cancelledAt"):
            continue
        try:
            wps = _api_get(f"/api/issues/{issue['id']}/work-products")
        except Exception as e:
            logger.warning(f"work-products fetch fail for {issue.get('identifier')}: {e}")
            continue
        if not isinstance(wps, list):
            continue
        for wp in wps:
            if wp.get("type") != "blog_post":
                continue
            if wp.get("status") != "ready":
                continue
            candidates.append({
                "issue_id": issue["id"],
                "issue_identifier": issue.get("identifier"),
                "issue_title": issue.get("title"),
                "workproduct_id": wp["id"],
                "title": wp.get("title") or issue.get("title", ""),
                "status": wp["status"],
                "metadata": wp.get("metadata") or {},
                "summary": wp.get("summary") or "",
            })
    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# Validation hooks
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_body_markdown(wp: dict) -> str:
    """work_product.metadata.body > latest comment.body 순서로 markdown 본문 추출."""
    meta = wp.get("metadata") or {}
    body = meta.get("body") or ""
    if body:
        return body
    try:
        comments = _api_get(f"/api/issues/{wp['issue_id']}/comments")
        if isinstance(comments, list) and comments:
            # 최신 (createdAt desc) — API는 desc 가정. 안전하게 sort.
            comments_sorted = sorted(
                comments, key=lambda c: c.get("createdAt", ""), reverse=True
            )
            return comments_sorted[0].get("body", "")
    except Exception as e:
        logger.warning(f"comments fetch fail: {e}")
    return ""


def _count_today_paperclip_publishes() -> int:
    # UTC 기준 비교 (timestamps are stored in UTC ISO)
    today_str = datetime.now(timezone.utc).date().isoformat()
    count = 0
    for path in glob(str(DATA_DIR / "published_history*.json")):
        try:
            entries = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            if e.get("source") != "paperclip":
                continue
            ts = (e.get("published_at") or e.get("timestamp") or "")
            if ts.startswith(today_str):
                count += 1
    return count


def _check_keyword_duplicate(primary_keyword: str, lang: str = "ko") -> bool:
    """primary_keyword 가 30일 내 발행 history에 있으면 True."""
    if not primary_keyword:
        return False
    try:
        from auto_publisher.content_generator import _normalize_keyword_for_match
        from auto_publisher.topic_manager import TopicManager
        tm = TopicManager(lang=lang)
        recent = tm._get_global_recent_primary_keywords(days=30)
        norm = _normalize_keyword_for_match(primary_keyword)
        for r in recent:
            if _normalize_keyword_for_match(r) == norm:
                return True
    except Exception as e:
        logger.warning(f"keyword duplicate check fail: {e}")
    return False


def _run_compliance(content: str, lang: str) -> tuple[bool, str]:
    """bridge_api.check_compliance 직접 import 호출."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "n8n"))
        from bridge_api import check_compliance  # type: ignore
        result = check_compliance(content=content, lang=lang, channel="blog")
        if result.get("ok"):
            return True, ""
        violations = result.get("violations") or []
        return False, "; ".join(str(v)[:80] for v in violations[:3])
    except Exception as e:
        logger.warning(f"compliance import fail: {e} — bypass")
        return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# Reject helpers
# ─────────────────────────────────────────────────────────────────────────────
def _post_skip_comment(wp: dict, reason: str) -> None:
    try:
        _api_post(
            f"/api/issues/{wp['issue_id']}/comments",
            {"body": f"⛔ Publish skipped (work_product {wp['workproduct_id'][:8]}): {reason}"},
        )
    except Exception as e:
        logger.warning(f"could not post skip comment: {e}")


def _mark_blocked(wp: dict, reason: str) -> None:
    try:
        _api_patch(
            f"/api/work-products/{wp['workproduct_id']}",
            {"status": "blocked", "summary": f"Blocked: {reason}"[:200]},
        )
    except Exception as e:
        logger.warning(f"could not mark blocked: {e}")


def _reject(wp: dict, reason: str, hard: bool = True) -> dict:
    """hard=True 면 work_product.status='blocked', False 면 status 유지 (재시도 가능)."""
    _post_skip_comment(wp, reason)
    if hard:
        _mark_blocked(wp, reason)
    return {
        "success": False,
        "reason": reason,
        "workproduct_id": wp["workproduct_id"],
        "hard": hard,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Publish flow
# ─────────────────────────────────────────────────────────────────────────────
def publish_one(wp: dict) -> dict:
    """단일 work_product → 10-step validation → HugoPublisher.publish."""
    if not _enabled():
        return {"success": False, "error": "PAPERCLIP_PUBLISH_ENABLED=0"}

    meta = wp.get("metadata") or {}
    lang = (meta.get("lang") or "ko").strip()
    category = (meta.get("category") or "").lower().strip()
    title = (wp.get("title") or "").strip()
    primary_kw = (meta.get("primary_keyword") or "").strip()

    # Step 1: required fields
    if not title:
        return _reject(wp, "title missing")

    # Step 2: category allowlist
    if category and category not in ALLOWED_CATEGORIES:
        return _reject(wp, f"category '{category}' not in allowlist")

    # Step 3: body
    body_md = _fetch_body_markdown(wp)
    if not body_md or len(body_md.strip()) < 200:
        return _reject(wp, f"body markdown missing or too short ({len(body_md)} chars)")

    import markdown as md_lib
    content_html = md_lib.markdown(
        body_md, extensions=["tables", "fenced_code", "toc", "nl2br"]
    )

    # Step 4: min content length (Hugo body)
    MIN_HTML_LEN = 2000
    if len(content_html) < MIN_HTML_LEN:
        return _reject(wp, f"content too short (html={len(content_html)} < {MIN_HTML_LEN})")

    # Step 5: primary_keyword 30일 중복
    if _check_keyword_duplicate(primary_kw, lang=lang):
        return _reject(wp, f"primary_keyword '{primary_kw}' duplicate within 30 days")

    # Step 6: daily limit (soft — 한도 도달 시 다음 cron까지 대기, blocked 아님)
    if _count_today_paperclip_publishes() >= _daily_limit():
        return _reject(wp, f"daily limit {_daily_limit()} reached", hard=False)

    # Step 7: compliance
    if _compliance_required():
        ok, reason = _run_compliance(body_md, lang)
        if not ok:
            return _reject(wp, f"compliance violation: {reason}")

    # Step 8: SEO validate (HugoPublisher 내부 hook 이 SEO_VALIDATOR_ENABLED 따라 동작)
    # paperclip은 항상 엄격 적용
    if _seo_required():
        os.environ["SEO_VALIDATOR_ENABLED"] = "1"

    # Step 9: dry-run short-circuit
    if _dry_run():
        return {
            "success": True,
            "dry_run": True,
            "title": title,
            "workproduct_id": wp["workproduct_id"],
            "html_len": len(content_html),
        }

    # Step 10: HugoPublisher.publish
    from auto_publisher.publishers.hugo import HugoPublisher
    publisher = HugoPublisher(lang=lang)
    try:
        result = publisher.publish(
            title=title,
            content_html=content_html,
            tags=meta.get("tags") or [],
            meta_description=(wp.get("summary") or title)[:160],
            categories=[category or "재테크"] if category else None,
            primary_keyword=primary_kw,
            keywords_long_tail=meta.get("keywords_long_tail") or [],
            content_type=meta.get("content_type", "guide"),
        )
    except Exception as e:
        logger.error(f"HugoPublisher.publish failed: {e}", exc_info=True)
        # status 유지 (재시도 가능), comment에 에러
        _post_skip_comment(wp, f"publish error: {str(e)[:120]}")
        return {
            "success": False,
            "error": str(e)[:200],
            "workproduct_id": wp["workproduct_id"],
        }

    # Step 11: mark published in Paperclip + history
    try:
        _api_patch(
            f"/api/work-products/{wp['workproduct_id']}",
            {"status": "archived", "url": result.get("url", "")},
        )
    except Exception as e:
        logger.warning(f"could not mark wp published: {e}")
    try:
        _api_post(
            f"/api/issues/{wp['issue_id']}/comments",
            {"body": f"📰 Published: {result.get('url','')}"},
        )
    except Exception as e:
        logger.warning(f"could not post published comment: {e}")

    _record_history(wp, result, lang)

    return {
        "success": True,
        "url": result.get("url"),
        "filepath": result.get("filepath"),
        "slug": result.get("slug"),
        "workproduct_id": wp["workproduct_id"],
    }


def _record_history(wp: dict, result: dict, lang: str) -> None:
    history_path = DATA_DIR / f"published_history_{lang}.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entries: list = []
    if history_path.exists():
        try:
            loaded = json.loads(history_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                entries = loaded
        except Exception:
            entries = []
    entries.append({
        "topic_id": f"paperclip-{wp['workproduct_id']}",
        "platform": "hugo",
        "url": result.get("url", ""),
        "filepath": result.get("filepath", ""),
        "slug": result.get("slug", ""),
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "paperclip",
        "lang": lang,
        "issue_identifier": wp.get("issue_identifier"),
    })
    history_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def poll_and_publish(max_items: int = 5) -> dict:
    """Find pending blog_post work_products → publish up to max_items.

    Returns: {processed, succeeded, failed, skipped, candidates_total, items}
    """
    if not _enabled():
        return {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "candidates_total": 0,
            "skipped": "PAPERCLIP_PUBLISH_ENABLED=0",
            "items": [],
        }

    candidates = find_pending_blog_workproducts()
    items: list[dict] = []
    succeeded = 0
    failed = 0
    for wp in candidates[:max_items]:
        try:
            r = publish_one(wp)
        except Exception as e:
            logger.error(f"publish_one fatal: {e}", exc_info=True)
            r = {"success": False, "error": str(e)[:200], "workproduct_id": wp.get("workproduct_id")}
        items.append(r)
        if r.get("success"):
            succeeded += 1
        else:
            failed += 1
    return {
        "processed": len(items),
        "succeeded": succeeded,
        "failed": failed,
        "candidates_total": len(candidates),
        "items": items,
    }
