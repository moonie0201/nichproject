"""
n8n Bridge API — n8n이 로컬 Python 스크립트를 HTTP로 호출하기 위한 브리지
포트: 8765
"""

import os
import sys
import json
import fcntl
import subprocess
import threading
import time
import uuid
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

WORKSPACE = Path("/home/mh/ocstorage/workspace")
NICHPROJECT = WORKSPACE / "nichproject"
VENV_PYTHON = str(NICHPROJECT / "venv/bin/python3")

# 환경 변수 로드
sys.path.insert(0, str(NICHPROJECT))
os.chdir(NICHPROJECT)

from dotenv import load_dotenv
load_dotenv(WORKSPACE / ".env")
load_dotenv(NICHPROJECT / ".env", override=True)

from auto_publisher.dynamic_topics import inject_dynamic_topics


BRIDGE_LOCKFILE = NICHPROJECT / "n8n" / ".bridge_api.lock"
BRIDGE_LOCK_HANDLE = None


def acquire_bridge_lock() -> None:
    """중복 bridge 실행을 막는다."""
    global BRIDGE_LOCK_HANDLE
    BRIDGE_LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = BRIDGE_LOCKFILE.open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("n8n Bridge API already running; exiting duplicate process.")
        sys.exit(0)
    lock_handle.write(str(os.getpid()))
    lock_handle.flush()
    BRIDGE_LOCK_HANDLE = lock_handle


def run_auto_publish(lang: str = "ko") -> dict:
    """auto_publisher 실행 — 콘텐츠 생성 + Hugo 빌드 + CF 배포"""
    result = subprocess.run(
        [VENV_PYTHON, "-m", "auto_publisher.main", "run", "--lang", lang],
        cwd=NICHPROJECT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    lines = result.stdout.strip().split("\n")
    title = next((l.replace("  제목: ", "") for l in lines if "제목:" in l), "")
    return {
        "success": result.returncode == 0,
        "title": title,
        "output": result.stdout[-1000:],
        "error": result.stderr[-500:] if result.returncode != 0 else "",
    }


def get_market_analysis() -> dict:
    """OKX 봇 백테스트 캐시에서 최신 시장 분석 읽기"""
    cache_dir = WORKSPACE / ".backtest_cache"
    backtest_results = WORKSPACE / ".backtest_results"

    signals = {}

    # 최신 캐시 파일 읽기
    if cache_dir.exists():
        files = sorted(cache_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        if files:
            try:
                data = json.loads(files[0].read_text())
                signals["backtest"] = {"file": files[0].name, "data": str(data)[:500]}
            except Exception:
                pass

    # bot_out.log에서 최근 시그널 읽기
    log_file = WORKSPACE / "bot_out.log"
    if log_file.exists():
        lines = log_file.read_text(errors="ignore").split("\n")
        recent = [l for l in lines[-200:] if any(k in l for k in ["SIGNAL", "BUY", "SELL", "LONG", "SHORT", "position"])]
        signals["recent_signals"] = recent[-10:]

    return {"success": True, "signals": signals}


def get_topic_queue() -> dict:
    """토픽 큐 상태 조회"""
    result = subprocess.run(
        [VENV_PYTHON, "-m", "auto_publisher.main", "topics"],
        cwd=NICHPROJECT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {"success": result.returncode == 0, "output": result.stdout}


def publish_market_post() -> dict:
    """시장 분석 데이터 → InvestIQs 리서치 애널리스트 AI 포스트 생성 + Hugo 발행"""
    import logging
    import requests as req
    from auto_publisher.content_generator import _load_persona, _persona_brief, _inject_disclaimer
    from auto_publisher.content_verifier import verify_two_stage

    log = logging.getLogger(__name__)

    # 1) 시장 신호 수집
    market = get_market_analysis()
    signals = market.get("signals", {})
    recent = signals.get("recent_signals", [])
    signal_text = "\n".join(recent[-10:]) if recent else "데이터 없음"

    # 2) OpenRouter로 블로그 포스트 생성
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "OPENROUTER_API_KEY 없음"}

    from datetime import date
    today = date.today().strftime("%Y년 %m월 %d일")

    # 애널리스트 페르소나 로드
    persona = _load_persona("ko")
    persona_block = _persona_brief(persona)

    def _build_prompt(retry_issues: str = "") -> str:
        retry_section = ""
        if retry_issues:
            retry_section = f"\n[이전 시도 문제점 — 반드시 수정]\n{retry_issues}\n"

        return f"""{persona_block}

당신은 InvestIQs Research 소속 전문 리서치 애널리스트입니다.
아래 오늘의 시장 신호 데이터를 바탕으로 3인칭 리서치 노트 형식의 블로그 글을 작성해주세요.
{retry_section}
날짜: {today}
시장 신호:
{signal_text}

[작성 규칙]
1. 순수 JSON만 반환하세요. 마크다운 코드블록(```)이나 다른 텍스트 없이 JSON만 출력하세요.
2. 제목은 SEO 최적화 (30~50자), 날짜 포함
3. 본문은 HTML 형식으로 2500자 이상
4. H2, H3 태그로 구조화
5. 3인칭 리서치 노트 톤 — '내가', '제가', '저는' 등 1인칭 절대 금지
6. 데이터, 흐름, 패턴 중심의 분석적 서술
7. 구체적 수치와 근거 포함
8. 마지막에 FAQ 섹션 (3개 Q&A)
9. 태그는 "데이터 분석", "시장 흐름" 등 애널리스트 스타일 사용

[출력 형식]
{{"title": "제목", "content_html": "<h2>...</h2>...", "meta_description": "메타설명", "tags": ["데이터 분석", "시장 흐름", "암호화폐", "패턴 분석"]}}"""

    def _call_gemini(prompt: str) -> dict:
        resp = req.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "google/gemini-2.0-flash-001", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 6000},
            timeout=120,
        )
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("```"))
        return json.loads(raw)

    # 1차 시도
    try:
        post = _call_gemini(_build_prompt())
    except Exception as e:
        return {"success": False, "error": f"AI 생성 실패: {e}"}

    # 3) 2단계 검증
    vr = verify_two_stage(post, source_data=None, lang="ko", min_len=2500)
    if not vr.get("ok"):
        retry_issues = vr.get("retry_prompt", "검증 실패")
        log.warning(f"publish_market_post: 1차 검증 실패 — {retry_issues}. 재시도...")
        try:
            post = _call_gemini(_build_prompt(retry_issues=retry_issues))
            vr2 = verify_two_stage(post, source_data=None, lang="ko", min_len=2500)
            if not vr2.get("ok"):
                log.warning(f"publish_market_post: 2차 검증도 실패 — 그대로 진행. {vr2.get('retry_prompt', '')}")
        except Exception as e:
            log.warning(f"publish_market_post: 재시도 실패 — {e}. 1차 결과로 진행.")

    # 4) 상단 규제 배너 + 면책 조항 삽입
    html = post.get("content_html", "")
    top_banner = (
        '<div class="reg-banner" style="background:#fff3cd;border:1px solid #ffc107;'
        'border-radius:6px;padding:0.8em 1em;margin:0 0 1.5em 0;font-size:0.9em;color:#664d03;">'
        '<strong>⚠️ 정보 제공용 데이터 분석</strong><br>'
        '본 글은 공개 시장 데이터와 AI 분석을 정리한 정보 콘텐츠입니다. '
        '투자 권유나 매매 추천이 아닙니다. '
        '모든 투자 결정과 손익은 본인 책임입니다.'
        '</div>\n'
    )
    if 'class="reg-banner"' not in html:
        html = top_banner + html
    post["content_html"] = _inject_disclaimer(html, "ko")

    # 5) 태그 / 카테고리 보정
    tags = post.get("tags", [])
    analyst_tags = {"데이터 분석", "시장 흐름"}
    for t in analyst_tags:
        if t not in tags:
            tags.append(t)
    post["tags"] = tags

    # 6) Hugo 발행
    result = subprocess.run(
        [VENV_PYTHON, "-c", f"""
import sys; sys.path.insert(0, '{NICHPROJECT}')
from auto_publisher.publishers.hugo import HugoPublisher
p = HugoPublisher()
r = p.publish(
    title={json.dumps(post['title'])},
    content_html={json.dumps(post['content_html'])},
    tags={json.dumps(post.get('tags', []))},
    meta_description={json.dumps(post.get('meta_description', ''))},
    categories={json.dumps(['시장 데이터 분석'])},
)
print(r['url'])
"""],
        capture_output=True, text=True, timeout=180,
    )

    return {
        "success": result.returncode == 0,
        "title": post.get("title", ""),
        "url": result.stdout.strip(),
        "error": result.stderr[-300:] if result.returncode != 0 else "",
    }


def run_publish_us_market_wrap(dry_run: bool = False, force: bool = False, lang: str = "ko") -> dict:
    """매일 아침 '미국 증시 마감' 포스트 자동 생성 + Hugo 발행."""
    from auto_publisher import market_wrap
    from auto_publisher.content_generator import make_eeat_slug
    from pathlib import Path

    snapshot = market_wrap.fetch_us_market_snapshot()

    if snapshot.get("is_us_market_holiday") and not force:
        return {
            "success": True,
            "skipped": True,
            "reason": "us_market_holiday",
            "date_kst": snapshot.get("date_kst"),
        }

    md = market_wrap.build_markdown(snapshot, lang=lang)
    if lang == "ko":
        title = market_wrap._build_title(snapshot)
    else:
        from auto_publisher.i18n_market import get_i18n, date_label
        from auto_publisher.market_wrap import _parse_kst_date, _format_pct, _format_price
        i18n = get_i18n(lang)
        spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
        qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
        d = _parse_kst_date(snapshot.get("date_kst", ""))
        title = i18n["title_pattern_wrap"].format(
            date=date_label(lang, d),
            spy_pct=_format_pct(spy["pct"]) if spy else "",
            qqq_pct=_format_pct(qqq["pct"]) if qqq else "",
            spy_price=_format_price(spy["price"]) if spy else "",
        )
    slug = make_eeat_slug(title)

    compliance = check_compliance(
        {"title": title, "html": md}, lang=lang, channel="blog"
    )
    if not compliance.get("ok"):
        return {
            "success": False,
            "error": "compliance_violation",
            "violations": compliance.get("violations", []),
            "title": title,
        }

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "title": title,
            "slug": slug,
            "len": len(md),
            "narrative_hint": snapshot.get("narrative_hint"),
        }

    # 실제 파일 저장 + Hugo 빌드 + CF 배포
    content_dir = NICHPROJECT / "web" / "content" / lang / "daily"
    content_dir.mkdir(parents=True, exist_ok=True)
    filepath = content_dir / f"{slug}.md"
    filepath.write_text(md, encoding="utf-8")

    # Hugo 빌드
    build = subprocess.run(
        ["hugo", "--cleanDestinationDir", "--gc", "--minify"],
        cwd=str(NICHPROJECT / "web"),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if build.returncode != 0:
        return {
            "success": False,
            "error": "hugo_build_failed",
            "stderr": build.stderr[-500:],
            "file": str(filepath),
        }

    # Cloudflare Pages 배포
    deploy_env = os.environ.copy()
    deploy = subprocess.run(
        ["npx", "wrangler", "pages", "deploy", "public", "--project-name", "invest-korea"],
        cwd=str(NICHPROJECT / "web"),
        capture_output=True,
        text=True,
        timeout=300,
        env=deploy_env,
    )

    return {
        "success": deploy.returncode == 0,
        "title": title,
        "slug": slug,
        "url": f"/{lang}/daily/{slug}/",
        "file": str(filepath),
        "hugo_stdout_tail": build.stdout[-300:] if build.stdout else "",
        "deploy_stdout_tail": deploy.stdout[-300:] if deploy.stdout else "",
        "deploy_error": deploy.stderr[-300:] if deploy.returncode != 0 else "",
    }


def run_publish_us_market_weekly(dry_run: bool = False, force: bool = False, lang: str = "ko") -> dict:
    """매주 토요일 09:00 KST '미국 증시 주간' 포스트 자동 생성 + Hugo 발행."""
    from auto_publisher import market_weekly
    from auto_publisher.content_generator import make_eeat_slug

    snapshot = market_weekly.fetch_weekly_snapshot()
    md = market_weekly.build_weekly_markdown(snapshot, lang=lang)
    if lang == "ko":
        title = market_weekly._build_weekly_title(snapshot)
    else:
        from auto_publisher.i18n_market import get_i18n
        from auto_publisher.market_wrap import _format_pct
        i18n = get_i18n(lang)
        spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
        qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
        title = i18n["title_pattern_weekly"].format(
            label=snapshot.get("week_label", ""),
            spy_pct=_format_pct(spy["pct_5d"]) if spy else "",
            qqq_pct=_format_pct(qqq["pct_5d"]) if qqq else "",
        )
    slug = "weekly-" + make_eeat_slug(title)

    compliance = check_compliance(
        {"title": title, "html": md}, lang=lang, channel="blog"
    )
    if not compliance.get("ok"):
        return {
            "success": False,
            "error": "compliance_violation",
            "violations": compliance.get("violations", []),
            "title": title,
        }

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "title": title,
            "slug": slug,
            "len": len(md),
            "narrative_hint": snapshot.get("narrative_hint"),
            "week_label": snapshot.get("week_label"),
        }

    content_dir = NICHPROJECT / "web" / "content" / lang / "weekly"
    content_dir.mkdir(parents=True, exist_ok=True)
    filepath = content_dir / f"{slug}.md"
    filepath.write_text(md, encoding="utf-8")

    build = subprocess.run(
        ["hugo", "--cleanDestinationDir", "--gc", "--minify"],
        cwd=str(NICHPROJECT / "web"),
        capture_output=True, text=True, timeout=120,
    )
    if build.returncode != 0:
        return {"success": False, "error": "hugo_build_failed",
                "stderr": build.stderr[-500:], "file": str(filepath)}

    deploy = subprocess.run(
        ["npx", "wrangler", "pages", "deploy", "public", "--project-name", "invest-korea"],
        cwd=str(NICHPROJECT / "web"),
        capture_output=True, text=True, timeout=300,
        env=os.environ.copy(),
    )
    return {
        "success": deploy.returncode == 0,
        "title": title,
        "slug": slug,
        "url": f"/{lang}/weekly/{slug}/",
        "file": str(filepath),
        "deploy_error": deploy.stderr[-300:] if deploy.returncode != 0 else "",
    }


def run_shorts_auto_latest(lang: str = "ko", privacy: str = "public", dry_run: bool = False) -> dict:
    """가장 최근 발행 글을 찾아 /make-video 자동 호출.

    이미 영상화된 slug 는 video_cache 디렉토리 기준으로 제외.
    """
    from auto_publisher.shorts_auto import find_latest_publishable_slug, list_videoed_slugs

    content_root = NICHPROJECT / "web" / "content"
    video_cache = WORKSPACE / ".omc" / "video_cache"
    done = list_videoed_slugs(video_cache)

    target = find_latest_publishable_slug(
        content_root=content_root, lang=lang, already_done_slugs=done
    )
    if not target:
        return {
            "success": True,
            "skipped": True,
            "reason": "no_publishable_slug",
            "lang": lang,
            "already_done_count": len(done),
        }

    slug = target["slug"]
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "slug": slug,
            "section": target["section"],
            "lang": lang,
            "path": str(target["path"]),
        }

    video_result = run_make_video(slug=slug, lang=lang, privacy=privacy)
    return {
        "success": video_result.get("success", False),
        "slug": slug,
        "section": target["section"],
        "lang": lang,
        "video_result": video_result,
    }


def run_publish_us_market_intraday(dry_run: bool = False, force: bool = False, lang: str = "ko") -> dict:
    """미국장 개장 30분 후 장중 시황 포스트 자동 생성 + Hugo 발행."""
    from auto_publisher import market_intraday
    from auto_publisher.content_generator import make_eeat_slug

    snapshot = market_intraday.fetch_intraday_snapshot()

    if snapshot.get("is_us_market_holiday") and not force:
        return {
            "success": True,
            "skipped": True,
            "reason": "us_market_not_in_session",
            "date_kst": snapshot.get("date_kst"),
        }

    md = market_intraday.build_intraday_markdown(snapshot, lang=lang)
    if lang == "ko":
        title = market_intraday._build_intraday_title(snapshot)
    else:
        from auto_publisher.i18n_market import get_i18n, date_label
        from auto_publisher.market_wrap import _parse_kst_date, _format_pct, _format_price
        i18n = get_i18n(lang)
        spy = next((i for i in snapshot["indices"] if i["ticker"] == "SPY"), None)
        qqq = next((i for i in snapshot["indices"] if i["ticker"] == "QQQ"), None)
        d = _parse_kst_date(snapshot.get("date_kst", ""))
        title = i18n["title_pattern_intraday"].format(
            date=date_label(lang, d),
            spy_pct=_format_pct(spy["pct_from_open"]) if spy else "",
            qqq_pct=_format_pct(qqq["pct_from_open"]) if qqq else "",
            spy_price=_format_price(spy["current"]) if spy else "",
        )
    slug = "intraday-" + make_eeat_slug(title)

    compliance = check_compliance(
        {"title": title, "html": md}, lang=lang, channel="blog"
    )
    if not compliance.get("ok"):
        return {
            "success": False,
            "error": "compliance_violation",
            "violations": compliance.get("violations", []),
            "title": title,
        }

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "title": title,
            "slug": slug,
            "len": len(md),
            "narrative_hint": snapshot.get("narrative_hint"),
            "gap": snapshot.get("gap"),
        }

    content_dir = NICHPROJECT / "web" / "content" / lang / "daily"
    content_dir.mkdir(parents=True, exist_ok=True)
    filepath = content_dir / f"{slug}.md"
    filepath.write_text(md, encoding="utf-8")

    build = subprocess.run(
        ["hugo", "--cleanDestinationDir", "--gc", "--minify"],
        cwd=str(NICHPROJECT / "web"),
        capture_output=True, text=True, timeout=120,
    )
    if build.returncode != 0:
        return {"success": False, "error": "hugo_build_failed",
                "stderr": build.stderr[-500:], "file": str(filepath)}

    deploy = subprocess.run(
        ["npx", "wrangler", "pages", "deploy", "public", "--project-name", "invest-korea"],
        cwd=str(NICHPROJECT / "web"),
        capture_output=True, text=True, timeout=300,
        env=os.environ.copy(),
    )
    return {
        "success": deploy.returncode == 0,
        "title": title,
        "slug": slug,
        "url": f"/{lang}/daily/{slug}/",
        "file": str(filepath),
        "deploy_error": deploy.stderr[-300:] if deploy.returncode != 0 else "",
    }


def run_analyze(ticker: str = "VOO", lang: str = "ko") -> dict:
    """AI 분석 포스트 생성 + Hugo 발행"""
    result = subprocess.run(
        [VENV_PYTHON, "-m", "auto_publisher.main", "analyze", "--ticker", ticker, "--lang", lang],
        cwd=NICHPROJECT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    lines = result.stdout.strip().split("\n")
    url = next((l.split("URL: ")[-1] for l in lines if "URL:" in l), "")
    title = next((l.split("제목: ")[-1] for l in lines if "제목:" in l), "")
    signal = next((l.split("—")[-1].strip() for l in lines if "분석 완료" in l), "")
    return {
        "success": result.returncode == 0,
        "ticker": ticker,
        "signal": signal,
        "title": title,
        "url": url,
        "error": result.stderr[-500:] if result.returncode != 0 else "",
    }


def run_translate(source_lang: str = "ko", target_lang: str = "en") -> dict:
    """번역+현지화 발행"""
    result = subprocess.run(
        [VENV_PYTHON, "-m", "auto_publisher.main", "translate", "--from", source_lang, "--to", target_lang],
        cwd=NICHPROJECT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return {
        "success": result.returncode == 0,
        "output": result.stdout[-500:],
        "error": result.stderr[-300:] if result.returncode != 0 else "",
    }


def run_dynamic_scan() -> dict:
    """매일 새벽 시장 이벤트 스캔 → 토픽 큐에 우선순위 토픽 자동 추가"""
    try:
        added = inject_dynamic_topics("ko")
        return {"success": True, "added": added}
    except Exception as e:
        return {"success": False, "error": str(e)}


_VIDEO_JOBS: dict[str, dict] = {}


def _run_video_job(job_id: str, slug: str, lang: str, privacy: str) -> None:
    _VIDEO_JOBS[job_id]["status"] = "running"
    try:
        result = run_make_video(slug, lang, privacy)
        _VIDEO_JOBS[job_id].update({"status": "done", "result": result, "finished_at": time.time()})
    except Exception as e:
        _VIDEO_JOBS[job_id].update({"status": "failed", "error": str(e), "finished_at": time.time()})


def run_make_video(slug: str = "", lang: str = "ko",
                   privacy: str = "public") -> dict:
    """블로그 slug → 롱폼+쇼츠 영상 생성 + YouTube 업로드"""
    if not slug:
        # slug 없으면 가장 최근 발행된 lang 포스트 사용
        from auto_publisher.shorts_auto import find_latest_publishable_slug
        content_root = NICHPROJECT / "web" / "content"
        latest = find_latest_publishable_slug(content_root=content_root, lang=lang)
        if latest:
            slug = latest["slug"]
    if not slug:
        return {"success": False, "error": "slug 없고 최근 포스트도 없음"}
    result = subprocess.run(
        [VENV_PYTHON, "-m", "auto_publisher.main", "make-video",
         "--slug", slug, "--lang", lang, "--privacy", privacy],
        cwd=NICHPROJECT,
        capture_output=True,
        text=True,
        timeout=int(os.getenv("MAKE_VIDEO_TIMEOUT_SEC", "1500")),
    )
    return {
        "success": result.returncode == 0,
        "slug": slug,
        "output": result.stdout[-1500:],
        "error": result.stderr[-500:] if result.returncode != 0 else "",
    }


def run_refresh_market_cache() -> dict:
    """매일 새벽 watched ticker 데이터 일괄 fetch + 검증 → market-cache.json 저장.
    이후 모든 포스트 생성은 캐시에서 읽음 → yfinance 부하/오류 최소화."""
    result = subprocess.run(
        [VENV_PYTHON, "-m", "auto_publisher.market_cache"],
        cwd=NICHPROJECT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return {
        "success": result.returncode == 0,
        "summary": result.stdout[-1500:],
        "error": result.stderr[-500:] if result.returncode != 0 else "",
    }


ROUTES = {
    "/publish-market": publish_market_post,
    "/market": get_market_analysis,
    "/topics": get_topic_queue,
    "/refresh-market-cache": run_refresh_market_cache,
    "/analyze": lambda: run_analyze(),
    "/dynamic-scan": run_dynamic_scan,
}

# Phase 2 준비용 스텁 — 추후 크리덴셜 발급/기능 구현 완료 시 점진 활성화.
# 지금은 200 + {stub: true} 로 응답하여 n8n 워크플로우가 404로 깨지지 않게 한다.
STUB_ROUTES = {
    # Benchmark YouTube Tracker
    "/benchmark/save", "/benchmark/weekly-report",
    # Comment Auto Reply
    "/comments/filter", "/comments/classify-intent", "/comments/gpt-reply",
    "/youtube/post-comment-reply", "/youtube/moderate-comment",
    # Comparison Content
    "/comparison/pick-pair", "/comparison/generate", "/backtest/run",
    # Cross Platform Post
    "/cross-post/generate", "/x/post-thread", "/reels/build", "/instagram/upload-reel",
    # Keyword Rank Monitor (GSC)
    "/gsc/fetch", "/gsc/diff", "/gsc/save-snapshot",
    # KPI Weekly Dashboard
    "/kpi/blog-pv", "/kpi/youtube", "/kpi/newsletter",
    "/kpi/compute-health", "/kpi/save-snapshot",
    # News React Shorts
    "/rss/poll", "/shorts/generate-script",
    # Newsletter Weekly
    "/newsletter/curate-weekly", "/newsletter/build", "/newsletter/log",
    # Weekly Dividend Report (Tistory 2중 발행)
    "/dividend-report", "/publish-tistory",
}


def stub_response(path: str) -> dict:
    return {
        "success": True,
        "stub": True,
        "implemented": False,
        "endpoint": path,
        "note": "미구현 스텁입니다. 기능 완성 시 실제 응답으로 대체됩니다.",
    }

FORBIDDEN_PHRASES = [
    "원금보장", "원금 보장",
    "확실한 수익", "확실한수익",
    "100% 수익", "100%수익",
    "리딩방", "종목 추천방", "종목추천방",
    "무료 리딩", "무료리딩",
    "단타 매매 프로그램",
    "절대 손실 없음", "손실 없음",
]
DISCLAIMER_KEYWORDS = [
    # ko
    "투자 참고", "투자는 본인 책임", "본인 책임",
    "면책", "정보 제공 목적", "정보제공 목적",
    # en
    "informational only", "not investment advice", "your own responsibility",
    "past performance does not guarantee", "no warranty",
    # ja
    "投資判断", "本人の責任", "情報提供を目的", "投資助言ではありません",
    # vi
    "không phải tư vấn đầu tư", "trách nhiệm của bạn", "chỉ mang tính",
    # id
    "bukan saran investasi", "tanggung jawab Anda", "hanya untuk informasi",
]
INVESTMENT_TRIGGERS = [
    # ko
    "투자", "ETF", "배당", "주식", "코인", "수익률", "종목",
    # en (case-insensitive matched after lower())
    "stock", "stocks", "etf", "etfs", "dividend", "yield", "ticker",
    # ja
    "株", "投資", "配当", "利回り",
    # vi
    "cổ phiếu", "đầu tư", "lợi nhuận",
    # id
    "saham", "investasi", "dividen",
]


def check_compliance(content: dict, lang: str = "ko", channel: str = "blog") -> dict:
    """콘텐츠 금칙어/면책 검증."""
    title = (content or {}).get("title", "") or ""
    html = (content or {}).get("html", "") or ""
    text = f"{title}\n{html}"
    violations = []
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            violations.append({
                "type": "forbidden_phrase",
                "severity": "high",
                "phrase": phrase,
                "rule": "자본시장법 위반 가능 표현",
            })
    text_lower = text.lower()
    is_investment_content = any(t.lower() in text_lower for t in INVESTMENT_TRIGGERS)
    has_disclaimer = any(d.lower() in text_lower for d in DISCLAIMER_KEYWORDS)
    if is_investment_content and not has_disclaimer:
        violations.append({
            "type": "missing_disclaimer",
            "severity": "warning",
            "rule": "투자 콘텐츠는 면책 조항 필요",
        })
    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "lang": lang,
        "channel": channel,
    }


def generate_monthly_dividend(symbols=None, lang: str = "ko", force_timeout: bool = False) -> dict:
    """월배당 ETF 리포트 markdown 생성 (스텁: 실제 LLM 호출은 추후 연결)."""
    syms = symbols or ["SCHD", "JEPI", "JEPQ"]
    if force_timeout:
        return {"success": False, "error": "timeout", "symbols": syms}
    title = f"월배당 ETF 리포트: {', '.join(syms)}"
    preview_lines = [f"- {s}: 월 배당금 / 분배율 / 총수익률 분석" for s in syms]
    content_preview = (
        f"# {title}\n\n"
        + "\n".join(preview_lines)
        + "\n\n본 글은 정보 제공 목적이며, 투자 결정은 본인 책임입니다."
    )
    return {
        "success": True,
        "title": title,
        "content_preview": content_preview,
        "symbols": syms,
        "lang": lang,
    }


def deep_health() -> dict:
    """서비스별 확장 헬스체크."""
    import shutil
    services = {}
    services["openrouter"] = {
        "configured": bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("GOOGLE_API_KEY")),
    }
    try:
        total, used, free = shutil.disk_usage(str(NICHPROJECT))
        services["disk"] = {
            "free_gb": round(free / (1024**3), 2),
            "used_pct": round(used / total * 100, 1),
        }
    except Exception as e:
        services["disk"] = {"error": str(e)}
    services["auto_publisher"] = {
        "module_path": str(NICHPROJECT / "auto_publisher"),
        "exists": (NICHPROJECT / "auto_publisher" / "main.py").exists(),
    }
    return {
        "status": "ok",
        "services": services,
    }


class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 로그 조용히

    def _read_json_body(self):
        """POST body를 JSON으로 파싱. 비어있거나 실패 시 None."""
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return None
        try:
            raw = self.rfile.read(length).decode("utf-8")
            if not raw.strip():
                return None
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return None

    def _check_auth(self) -> bool:
        token = os.getenv("BRIDGE_TOKEN", "")
        if not token:
            return True  # 토큰 미설정 시 내부망 신뢰
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {token}"

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        path = parsed.path
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if path != "/health" and not self._check_auth():
            self._respond(401, {"error": "Unauthorized"})
            return

        if path == "/health":
            if params.get("deep") in ("true", "1", "yes"):
                self._respond(200, deep_health())
            else:
                self._respond(200, {"status": "ok"})
            return
        if path == "/publish":
            try:
                if params.get("dry_run") in ("true", "1", "yes"):
                    self._respond(200, {"success": True, "dry_run": True, "endpoint": "/publish"})
                    return
                lang = params.get("lang", "ko")
                result = run_auto_publish(lang=lang)
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/analyze":
            try:
                ticker = params.get("ticker", "VOO")
                lang = params.get("lang", "ko")
                result = run_analyze(ticker=ticker, lang=lang)
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/translate":
            try:
                src = params.get("from", "ko")
                tgt = params.get("to", "en")
                self._respond(200, run_translate(src, tgt))
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/publish-us-market-wrap":
            try:
                dry_run = params.get("dry_run") in ("true", "1", "yes")
                force = params.get("force") in ("true", "1", "yes")
                lang = params.get("lang", "ko")
                self._respond(200, run_publish_us_market_wrap(dry_run=dry_run, force=force, lang=lang))
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/publish-us-market-intraday":
            try:
                dry_run = params.get("dry_run") in ("true", "1", "yes")
                force = params.get("force") in ("true", "1", "yes")
                lang = params.get("lang", "ko")
                self._respond(200, run_publish_us_market_intraday(dry_run=dry_run, force=force, lang=lang))
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/shorts/auto-latest":
            try:
                lang = params.get("lang", "ko")
                privacy = params.get("privacy", "public")
                dry_run = params.get("dry_run") in ("true", "1", "yes")
                self._respond(200, run_shorts_auto_latest(lang=lang, privacy=privacy, dry_run=dry_run))
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/publish-us-market-weekly":
            try:
                dry_run = params.get("dry_run") in ("true", "1", "yes")
                force = params.get("force") in ("true", "1", "yes")
                lang = params.get("lang", "ko")
                self._respond(200, run_publish_us_market_weekly(dry_run=dry_run, force=force, lang=lang))
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/make-video":
            try:
                slug = params.get("slug", "")
                lang = params.get("lang", "ko")
                privacy = params.get("privacy", "public")
                self._respond(200, run_make_video(slug, lang, privacy))
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/prediction-accuracy":
            try:
                from auto_publisher.prediction_tracker import PredictionTracker
                tracker = PredictionTracker()
                summary = tracker.accuracy_summary()
                pending = tracker.pending_verification()
                self._respond(200, {
                    "success": True,
                    "summary": summary,
                    "pending_count": len(pending),
                })
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/make-video-status":
            job_id = params.get("job_id", "")
            if not job_id or job_id not in _VIDEO_JOBS:
                self._respond(404, {"error": "job_id not found"})
                return
            self._respond(200, _VIDEO_JOBS[job_id])
            return
        if path in ROUTES:
            try:
                result = ROUTES[path]()
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path in STUB_ROUTES:
            self._respond(200, stub_response(path))
            return
        self._respond(404, {"error": "Not found", "routes": list(ROUTES.keys()) + ["/health"]})

    def do_POST(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path

        if not self._check_auth():
            self._respond(401, {"error": "Unauthorized"})
            return

        if path == "/compliance/check":
            body = self._read_json_body()
            if body is None:
                self._respond(400, {"error": "missing or invalid JSON body"})
                return
            try:
                result = check_compliance(
                    body.get("content", {}),
                    lang=body.get("lang", "ko"),
                    channel=body.get("channel", "blog"),
                )
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"ok": False, "error": str(e)})
            return

        if path == "/publish-us-market-wrap":
            body = self._read_json_body() or {}
            try:
                result = run_publish_us_market_wrap(
                    dry_run=bool(body.get("dry_run", False)),
                    force=bool(body.get("force", False)),
                    lang=body.get("lang", "ko"),
                )
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return

        if path == "/publish-us-market-intraday":
            body = self._read_json_body() or {}
            try:
                result = run_publish_us_market_intraday(
                    dry_run=bool(body.get("dry_run", False)),
                    force=bool(body.get("force", False)),
                    lang=body.get("lang", "ko"),
                )
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return

        if path == "/publish-us-market-weekly":
            body = self._read_json_body() or {}
            try:
                result = run_publish_us_market_weekly(
                    dry_run=bool(body.get("dry_run", False)),
                    force=bool(body.get("force", False)),
                    lang=body.get("lang", "ko"),
                )
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return

        if path == "/generate/monthly-dividend":
            body = self._read_json_body() or {}
            try:
                result = generate_monthly_dividend(
                    symbols=body.get("symbols"),
                    lang=body.get("lang", "ko"),
                    force_timeout=bool(body.get("force_timeout", False)),
                )
                self._respond(200, result)
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
            return

        if path == "/make-video":
            body = self._read_json_body() or {}
            slug = body.get("slug", "")
            lang = body.get("lang", "ko")
            privacy = body.get("privacy", "public")
            job_id = str(uuid.uuid4())
            _VIDEO_JOBS[job_id] = {"status": "queued", "slug": slug, "started_at": time.time()}
            threading.Thread(
                target=_run_video_job, args=(job_id, slug, lang, privacy), daemon=True
            ).start()
            self._respond(202, {"job_id": job_id, "status": "queued",
                                 "poll": f"/make-video-status?job_id={job_id}"})
            return

        # Phase 2 스텁 라우트
        if path in STUB_ROUTES:
            # body 가 있으면 JSON 파싱 시도하되 실패해도 스텁 응답 유지
            self._read_json_body()
            self._respond(200, stub_response(path))
            return

        # fallback: GET과 동일 처리 (기존 동작 보존)
        self.do_GET()

    def _respond(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    acquire_bridge_lock()
    port = int(os.getenv("BRIDGE_PORT", "8765"))
    server = HTTPServer(("127.0.0.1", port), BridgeHandler)
    print(f"n8n Bridge API running on http://127.0.0.1:{port}")
    print(f"Routes: {list(ROUTES.keys()) + ['/health']}")
    server.serve_forever()
