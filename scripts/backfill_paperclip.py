"""published_history*.json → Paperclip issue backfill (idempotent).

각 history entry당 Paperclip issue 1건 생성.
- status: done
- title: [<job_type>] <lang> <yyyy-mm-dd> <slug-preview>
- description: 원본 published_at + URL + section + source
- work_product: type=blog_post, url=원본 URL
- 추적 파일: auto_publisher/data/paperclip_backfill.json (URL → issue_id 매핑)

사용:
    venv/bin/python3 scripts/backfill_paperclip.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/mh/ocstorage/workspace/nichproject")
DATA = ROOT / "auto_publisher" / "data"
MARKER = DATA / "paperclip_backfill.json"
PAPERCLIP_BASE = "http://127.0.0.1:3100"
COMPANY_ID = "ccd0c00a-d565-4fc4-910f-9d823665313b"


def _api(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(PAPERCLIP_BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read() or "{}")
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"HTTP {e.code}: {body_text[:200]}") from e


def _infer_job_type(section: str, url: str, lang: str) -> str:
    """section/URL 패턴에서 job_type 추정."""
    url_lc = (url or "").lower()
    if section == "daily" or "daily" in url_lc:
        if "intraday" in url_lc:
            return "market-intraday"
        return "market-wrap"
    if section == "weekly" or "weekly" in url_lc:
        return "market-weekly"
    if section == "study":
        return "blog-pillar"
    if section == "blog":
        return "blog"
    return f"history-{section or 'unknown'}"


def _slug_preview(url: str) -> str:
    """URL에서 slug 미리보기 추출 (60자 이내)."""
    if not url:
        return ""
    name = url.rsplit("/", 1)[-1].replace(".md", "")
    return name[:60]


def _load_marker() -> dict:
    if MARKER.exists():
        try:
            return json.loads(MARKER.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_marker(marker: dict):
    DATA.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_candidates() -> list[dict]:
    """source != paperclip 인 모든 entry 수집 + dedupe by URL."""
    seen_urls: set[str] = set()
    candidates: list[dict] = []
    for f in sorted(DATA.glob("published_history*.json")):
        try:
            data = json.load(open(f))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        fname_lang = f.stem.replace("published_history_", "")
        if fname_lang == "published_history":
            fname_lang = "all"
        for e in data:
            if not isinstance(e, dict):
                continue
            if e.get("source") == "paperclip":
                continue  # already in Paperclip
            url = e.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            candidates.append({
                "url": url,
                "published_at": e.get("published_at") or e.get("timestamp", ""),
                "lang": e.get("lang") or fname_lang,
                "section": e.get("section") or "unknown",
                "topic_id": e.get("topic_id", ""),
                "source": e.get("source", "raw"),
                "_history_file": f.name,
            })
    return candidates


def create_issue_for_entry(entry: dict, dry_run: bool = False) -> str | None:
    """Paperclip issue 생성. 반환: issue_id."""
    job_type = _infer_job_type(entry["section"], entry["url"], entry["lang"])
    slug = _slug_preview(entry["url"])
    pub_date = (entry["published_at"] or "")[:10]
    lang = entry["lang"]

    title = f"[{job_type}] {lang} {pub_date} {slug}"[:120]
    desc = (
        f"backfill from history\n"
        f"url={entry['url']}\n"
        f"published_at={entry['published_at']}\n"
        f"lang={lang}\n"
        f"section={entry['section']}\n"
        f"original_topic_id={entry.get('topic_id','')}\n"
        f"source={entry.get('source','raw')}\n"
        f"history_file={entry.get('_history_file','')}"
    )

    if dry_run:
        return f"DRY-{slug[:30]}"

    # 1. Issue 생성 (done status)
    issue_body = {
        "title": title,
        "description": desc,
        "status": "todo",  # in_progress requires assignee; will PATCH to done after
        "priority": "low",
    }
    try:
        issue = _api("POST", f"/api/companies/{COMPANY_ID}/issues", issue_body)
        issue_id = issue.get("id") if isinstance(issue, dict) else None
    except Exception as e:
        print(f"    issue 생성 실패: {e}", file=sys.stderr)
        return None
    if not issue_id:
        return None

    # 2. Work product 추가 (url은 public URL, status는 'archived'=완료)
    raw_url = entry["url"]
    # 로컬 path → public URL 변환
    if raw_url.startswith("/home/mh/"):
        # /home/mh/.../web/content/{lang}/{section}/{slug}.md → https://investiqs.net/{lang}/{section}/{slug}/
        try:
            after_content = raw_url.split("/web/content/", 1)[1]  # "{lang}/{section}/{slug}.md"
            parts = after_content.rsplit(".md", 1)[0]
            public_url = f"https://investiqs.net/{parts}/"
        except Exception:
            public_url = f"https://investiqs.net/{lang}/"
    elif raw_url.startswith("http"):
        public_url = raw_url
    else:
        public_url = f"https://investiqs.net/{lang}/"

    try:
        wp_body = {
            "type": "document",
            "provider": "backfill",
            "title": slug[:120],
            "status": "archived",  # historical published post
            "url": public_url,
            "summary": f"backfill from {entry.get('_history_file')}",
            "metadata": {
                "original_published_at": entry["published_at"],
                "lang": lang,
                "section": entry["section"],
                "source": entry.get("source", "raw"),
                "original_path": raw_url,
            },
        }
        _api("POST", f"/api/issues/{issue_id}/work-products", wp_body)
    except Exception as e:
        print(f"    work_product 실패: {e}", file=sys.stderr)

    # 3. Status → done
    try:
        _api("PATCH", f"/api/issues/{issue_id}", {"status": "done"})
    except Exception as e:
        print(f"    status patch 실패: {e}", file=sys.stderr)

    return issue_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 후보만 표시")
    parser.add_argument("--limit", type=int, default=0, help="최대 N개만 (0=전체)")
    parser.add_argument("--throttle", type=float, default=0.2, help="요청 간 sleep (초)")
    args = parser.parse_args()

    marker = _load_marker()
    candidates = collect_candidates()
    pending = [c for c in candidates if c["url"] not in marker]

    print(f"총 후보: {len(candidates)} (이미 백필됨: {len(candidates)-len(pending)}, 신규: {len(pending)})")

    if args.limit and len(pending) > args.limit:
        pending = pending[:args.limit]
        print(f"  → limit 적용: {len(pending)}만 처리")

    if args.dry_run:
        print("--- dry-run 샘플 5건 ---")
        for c in pending[:5]:
            jt = _infer_job_type(c["section"], c["url"], c["lang"])
            print(f"  [{jt}] {c['lang']} {c['published_at'][:10]} → {_slug_preview(c['url'])[:50]}")
        return

    success = 0
    failed = 0
    for i, entry in enumerate(pending, 1):
        issue_id = create_issue_for_entry(entry, dry_run=False)
        if issue_id:
            marker[entry["url"]] = {
                "issue_id": issue_id,
                "backfilled_at": datetime.now().isoformat(),
            }
            success += 1
            if i % 10 == 0:
                print(f"  {i}/{len(pending)} (성공 {success}, 실패 {failed})")
                _save_marker(marker)  # 진행 중 주기적으로 저장
        else:
            failed += 1
        if args.throttle > 0:
            time.sleep(args.throttle)

    _save_marker(marker)
    print(f"\n완료: 성공 {success} / 실패 {failed} / 전체 {len(pending)}")
    print(f"marker file: {MARKER}")


if __name__ == "__main__":
    main()
