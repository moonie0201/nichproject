"""
n8n Bridge API — n8n이 로컬 Python 스크립트를 HTTP로 호출하기 위한 브리지
포트: 8765
"""

import os
import sys
import json
import contextlib
import fcntl
import logging
import ipaddress
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

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
from auto_publisher.config import SUPPORTED_LANGUAGES


ADSENSE_REVIEW_FLAG = NICHPROJECT / ".adsense_review"


def _review_mode_block() -> dict | None:
    """애드센스 심사 모드면 발행을 막는 skip 응답을, 아니면 None 을 돌려준다.

    심사 중 자동 발행은 "manual review or curation 없는 대량 생성"이라는
    위반 신호를 실시간으로 강화한다(survey/04-adsense-approval.md).

    토글은 파일 존재 여부다:
        켜기 : touch .adsense_review
        끄기 : rm .adsense_review
    n8n 워크플로우를 건드리지 않고 발행 경로 한 곳에서 흡수하므로,
    승인 후 파일만 지우면 즉시 원복된다.
    """
    if not ADSENSE_REVIEW_FLAG.exists():
        return None
    return {
        "success": True,
        "skipped": True,
        "reason": "애드센스 심사 모드 — 자동 발행 중단 중 (.adsense_review 삭제 시 재개)",
    }


def _lang_retired(lang: str) -> dict | None:
    """발행 중단된 언어면 skip 응답을, 아니면 None 을 돌려준다.

    n8n 워크플로우 27개가 여전히 lang=ja/vi/id 로 호출하므로, 워크플로우를
    일일이 고치는 대신 여기서 no-op 으로 흡수한다.
    심사 모드일 때는 언어와 무관하게 전부 막는다.
    """
    blocked = _review_mode_block()
    if blocked:
        return {**blocked, "lang": lang}
    if lang in SUPPORTED_LANGUAGES:
        return None
    return {
        "success": True,
        "skipped": True,
        "lang": lang,
        "reason": f"{lang} 발행 중단 (활성 언어: {', '.join(SUPPORTED_LANGUAGES)})",
    }


def _atomic_write(path: Path, text: str) -> None:
    """같은 임시파일에 쓰고 rename 한다.

    intraday(22:30)와 wrap(07:30)이 같은 us-daily.md 를 쓴다. 스케줄은 안 겹치지만
    수동 트리거가 겹치면 write_text 는 반쯤 쓰인 파일을 남긴다(Codex 리뷰 지적).
    os.replace 는 같은 파일시스템 안에서 원자적이라 온전한 하나가 남는다.

    tmp 이름에 PID 만 쓰면 안 된다 — 서버가 ThreadingHTTPServer 라 동시 요청이
    같은 프로세스의 다른 스레드로 들어오고, 그러면 두 호출이 같은 tmp 를 공유해
    한쪽이 replace 한 뒤 다른 쪽이 FileNotFoundError 를 낸다(Codex 리뷰 2차 지적).
    mkstemp 로 호출마다 고유 이름을 받는다.
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# hugo 는 --cleanDestinationDir 로 web/public 을 통째로 갈아엎고, 바로 그 디렉터리를
# wrangler 가 배포한다. 세 발행 경로(wrap/weekly/intraday)가 이걸 공유하므로,
# 동시에 돌면 한쪽 빌드가 다른 쪽 배포 중인 public/ 을 지운다(Codex 리뷰 2차 지적).
# 쓰기→빌드→배포 전체를 직렬화한다. 프로세스 안(ThreadingHTTPServer)과 밖(cron/CLI)
# 양쪽을 막아야 해서 스레드 락과 파일 락을 같이 쓴다.
_BUILD_LOCK = threading.Lock()
_BUILD_LOCK_FILE = NICHPROJECT / "web" / ".hugo_build.lock"
# flock 은 블로킹 대기에 타임아웃을 못 걸어서 폴링한다. 간격은 테스트에서 줄인다.
_BUILD_LOCK_POLL_SEC = 1.0


@contextlib.contextmanager
def _build_lock(timeout: int = 600):
    """빌드+배포 구간을 프로세스 안팎에서 직렬화한다.

    timeout 은 두 락의 **합계** 대기 시간이다. 스레드 락을 `with` 로 잡으면
    거기서 무기한 대기해 timeout 계약이 깨진다(Codex 리뷰 3차 지적) —
    데드라인을 하나 만들어 양쪽이 나눠 쓴다.
    """
    deadline = time.monotonic() + timeout
    if not _BUILD_LOCK.acquire(timeout=timeout):
        raise TimeoutError(f"hugo 빌드 락(스레드) 대기 {timeout}s 초과")
    try:
        _BUILD_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_BUILD_LOCK_FILE, "w") as fh:
            while True:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    # 남은 시간을 넘겨 자지 않는다. 고정 sleep(1) 이면 남은 시간이
                    # 0.1s 여도 1s 를 자서, 성공도 실패도 계약을 최대 1s 초과한다
                    # (Codex 리뷰 3차 지적).
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError(f"hugo 빌드 락(파일) 대기 {timeout}s 초과")
                    time.sleep(min(_BUILD_LOCK_POLL_SEC, remaining))
                    # 잔 뒤 재시도 전에 다시 확인한다 — 자는 동안 만료됐을 수 있다.
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"hugo 빌드 락(파일) 대기 {timeout}s 초과")
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    finally:
        _BUILD_LOCK.release()


ADSENSE_OVERLAY = NICHPROJECT / "web" / "hugo.adsense.toml"


def _hugo_config_args() -> list[str]:
    """심사 모드면 축소 overlay 를 얹어서 빌드한다.

    overlay 는 만들어 놓고 아무도 쓰지 않았다. 그래서 `.adsense_review` 를 지우는
    순간 다음 발행이 전체 사이트(약 3,900 페이지)를 다시 빌드해 배포하면서
    축소를 통째로 되돌리게 돼 있었다. 되돌리기가 조용해서 더 위험했다.
    """
    if not ADSENSE_REVIEW_FLAG.exists():
        return []
    if not ADSENSE_OVERLAY.exists():
        # fail-open 하면 안 된다. overlay 가 없다고 조용히 plain 빌드로 넘어가면
        # 심사 중에 en 과 축소 대상 글이 전부 배포된다 — 막으려던 바로 그 사고다
        # (Codex 리뷰 4차 지적).
        raise FileNotFoundError(
            f"심사 모드인데 축소 overlay 가 없다: {ADSENSE_OVERLAY}. "
            "overlay 를 복구하거나 .adsense_review 를 지워라."
        )
    return ["--config", "hugo.toml,hugo.adsense.toml"]


def _build_and_deploy(filepath: Path, md: str) -> tuple[dict | None, str]:
    """대시보드 쓰기 → hugo 빌드 → Cloudflare 배포.

    반환: (빌드 실패 시 오류 dict / 아니면 None, 배포 오류 문자열).
    배포 실패는 치명적이지 않다 — 파일은 이미 커밋됐고 다음 발행에서 다시 나간다.
    """
    with _build_lock():
        # 설정을 먼저 확정한다. 파일부터 쓰면 overlay 누락으로 터졌을 때
        # 빌드는 막혀도 대시보드 파일은 이미 바뀐 채로 남는다(Codex 리뷰 5차 지적).
        hugo_config_args = _hugo_config_args()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(filepath, md)
        build = subprocess.run(
            ["hugo", "--cleanDestinationDir", "--gc", "--minify", *hugo_config_args],
            cwd=str(NICHPROJECT / "web"),
            capture_output=True, text=True, timeout=120,
        )
        if build.returncode != 0:
            return {"success": False, "error": "hugo_build_failed",
                    "stderr": build.stderr[-500:], "file": str(filepath)}, ""
        deploy = subprocess.run(
            ["npx", "wrangler", "pages", "deploy", "public", "--project-name", "invest-korea"],
            cwd=str(NICHPROJECT / "web"),
            capture_output=True, text=True, timeout=300, env=os.environ.copy(),
        )
    return None, (deploy.stderr[-300:] if deploy.returncode != 0 else "")


def _market_dashboard_path(lang: str, kind: str) -> Path:
    """시황이 쓸 고정 경로를 돌려준다.

    예전에는 발행 때마다 날짜 slug 로 새 URL 을 만들어 ko 기준 84편이 쌓였고,
    전부 noindex 라 색인 가치는 0 인데 도메인 품질 평균만 끌어내렸다.
    이제 시황은 갱신되는 대시보드 한 장으로 유지한다. kind 는 us-daily / us-weekly.
    """
    return NICHPROJECT / "web" / "content" / lang / "market" / f"{kind}.md"


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
    if skip := _lang_retired(lang):
        return skip
    stdout, stderr, returncode = _popen_stream(
        [VENV_PYTHON, "-m", "auto_publisher.main", "run", "--lang", lang],
        cwd=NICHPROJECT,
        timeout_sec=int(os.getenv("RUN_PUBLISH_TIMEOUT_SEC", "600")),
    )
    lines = stdout.strip().split("\n")
    title = next((l.replace("  제목: ", "") for l in lines if "제목:" in l), "")
    return {
        "success": returncode == 0,
        "title": title,
        "output": stdout[-1000:],
        "error": stderr[-500:] if returncode != 0 else "",
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
    # Hugo 발행 경로다. 한국어 전용이라 언어 인자가 없어 가드에서 빠져 있었다
    # (Codex 리뷰 지적 — 2차).
    if skip := _lang_retired("ko"):
        return skip

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

    # 2) LLM으로 블로그 포스트 생성 (OpenRouter 1차, Gemini CLI 폴백)
    api_key = os.getenv("OPENROUTER_API_KEY", "")

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

    def _call_market_llm(prompt: str) -> dict:
        # 1차: OpenRouter
        if api_key:
            try:
                resp = req.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "google/gemini-2.0-flash-001", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": int(os.getenv("OPENROUTER_MAX_TOKENS", "2000"))},
                    timeout=120,
                )
                _resp_data = resp.json()
                if "choices" not in _resp_data:
                    _err = _resp_data.get("error", {})
                    raise RuntimeError(f"OpenRouter error: {_err.get('message', str(_resp_data))[:200]}")
                raw = _resp_data["choices"][0]["message"]["content"].strip()
                if raw.startswith("```"):
                    raw = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("```"))
                return json.loads(raw)
            except Exception as e:
                log.warning(f"OpenRouter failed: {e}, falling back to gemini CLI")

        # 2차: Gemini CLI fallback
        import subprocess
        gemini_model = os.getenv("GEMINI_CLI_MODEL", "gemini-2.5-flash")
        result = subprocess.run(
            ["gemini", "-m", gemini_model, "-p", prompt],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Both OpenRouter + Gemini CLI failed: {result.stderr[:300]}")
        raw = result.stdout.strip()
        if raw.startswith("```"):
            raw = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("```"))
        return json.loads(raw)

    # 1차 시도
    try:
        post = _call_market_llm(_build_prompt())
    except Exception as e:
        return {"success": False, "error": f"AI 생성 실패: {e}"}

    # 3) 2단계 검증
    vr = verify_two_stage(post, source_data=None, lang="ko", min_len=2500)
    if not vr.get("ok"):
        retry_issues = vr.get("retry_prompt", "검증 실패")
        log.warning(f"publish_market_post: 1차 검증 실패 — {retry_issues}. 재시도...")
        try:
            post = _call_market_llm(_build_prompt(retry_issues=retry_issues))
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
    if skip := _lang_retired(lang):
        return skip
    audit_id = None
    try:
        from auto_publisher.paperclip_audit import create_audit_issue, complete_audit_issue
        audit_id = create_audit_issue("market-wrap", f"lang={lang}", lang=lang, source="n8n")
    except Exception:
        pass

    from auto_publisher import market_wrap
    from auto_publisher.content_generator import make_eeat_slug
    from pathlib import Path

    def _finish(result: dict) -> dict:
        try:
            if audit_id:
                complete_audit_issue(
                    audit_id,
                    ok=bool(result.get("success")),
                    summary=str(result)[:200],
                    error=result.get("error", "") or result.get("deploy_error", ""),
                    blog_url=result.get("url", ""),
                )
        except Exception:
            pass
        return result

    snapshot = market_wrap.fetch_us_market_snapshot()

    if snapshot.get("is_us_market_holiday") and not force:
        return _finish({
            "success": True,
            "skipped": True,
            "reason": "us_market_holiday",
            "date_kst": snapshot.get("date_kst"),
        })

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
        return _finish({
            "success": False,
            "error": "compliance_violation",
            "violations": compliance.get("violations", []),
            "title": title,
        })

    if dry_run:
        return _finish({
            "success": True,
            "dry_run": True,
            "title": title,
            "slug": slug,
            "len": len(md),
            "narrative_hint": snapshot.get("narrative_hint"),
        })

    # 실제 파일 저장 + Hugo 빌드 + CF 배포
    filepath = _market_dashboard_path(lang, "us-daily")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    err, deploy_error = _build_and_deploy(filepath, md)
    if err:
        return _finish(err)

    return _finish({
        "success": True,
        "title": title,
        "slug": slug,
        "url": f"/{lang}/market/us-daily/",
        "file": str(filepath),
        "deploy_error": deploy_error,
    })


def run_publish_us_market_weekly(dry_run: bool = False, force: bool = False, lang: str = "ko") -> dict:
    """매주 토요일 09:00 KST '미국 증시 주간' 포스트 자동 생성 + Hugo 발행."""
    if skip := _lang_retired(lang):
        return skip
    audit_id = None
    try:
        from auto_publisher.paperclip_audit import create_audit_issue, complete_audit_issue
        audit_id = create_audit_issue("market-weekly", f"lang={lang}", lang=lang, source="n8n")
    except Exception:
        pass

    from auto_publisher import market_weekly
    from auto_publisher.content_generator import make_eeat_slug

    def _finish(result: dict) -> dict:
        try:
            if audit_id:
                complete_audit_issue(
                    audit_id,
                    ok=bool(result.get("success")),
                    summary=str(result)[:200],
                    error=result.get("error", "") or result.get("deploy_error", ""),
                    blog_url=result.get("url", ""),
                )
        except Exception:
            pass
        return result

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
        return _finish({
            "success": False,
            "error": "compliance_violation",
            "violations": compliance.get("violations", []),
            "title": title,
        })

    if dry_run:
        return _finish({
            "success": True,
            "dry_run": True,
            "title": title,
            "slug": slug,
            "len": len(md),
            "narrative_hint": snapshot.get("narrative_hint"),
            "week_label": snapshot.get("week_label"),
        })

    filepath = _market_dashboard_path(lang, "us-weekly")
    err, deploy_error = _build_and_deploy(filepath, md)
    if err:
        return _finish(err)
    return _finish({
        "success": True,
        "title": title,
        "slug": slug,
        "url": f"/{lang}/market/us-weekly/",
        "file": str(filepath),
        "deploy_error": deploy_error,
    })


def run_shorts_auto_latest(lang: str = "ko", privacy: str = "public", dry_run: bool = False) -> dict:
    """가장 최근 발행 글을 찾아 /make-video 자동 호출.

    이미 영상화된 slug 는 video_cache 디렉토리 기준으로 제외.
    """
    if skip := _lang_retired(lang):
        return skip
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
    if skip := _lang_retired(lang):
        return skip
    audit_id = None
    try:
        from auto_publisher.paperclip_audit import create_audit_issue, complete_audit_issue
        audit_id = create_audit_issue("market-intraday", f"lang={lang}", lang=lang, source="n8n")
    except Exception:
        pass

    from auto_publisher import market_intraday
    from auto_publisher.content_generator import make_eeat_slug

    def _finish(result: dict) -> dict:
        try:
            if audit_id:
                complete_audit_issue(
                    audit_id,
                    ok=bool(result.get("success")),
                    summary=str(result)[:200],
                    error=result.get("error", "") or result.get("deploy_error", ""),
                    blog_url=result.get("url", ""),
                )
        except Exception:
            pass
        return result

    snapshot = market_intraday.fetch_intraday_snapshot()

    if snapshot.get("is_us_market_holiday") and not force:
        return _finish({
            "success": True,
            "skipped": True,
            "reason": "us_market_not_in_session",
            "date_kst": snapshot.get("date_kst"),
        })

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
        return _finish({
            "success": False,
            "error": "compliance_violation",
            "violations": compliance.get("violations", []),
            "title": title,
        })

    if dry_run:
        return _finish({
            "success": True,
            "dry_run": True,
            "title": title,
            "slug": slug,
            "len": len(md),
            "narrative_hint": snapshot.get("narrative_hint"),
            "gap": snapshot.get("gap"),
        })

    # 장중 시황도 같은 대시보드를 갱신한다. 아침에는 전 세션 마감, 저녁에는 당일 장중이
    # 올라가므로 시간순으로도 "현재 시장 상태" 한 장으로 일관된다.
    filepath = _market_dashboard_path(lang, "us-daily")
    err, deploy_error = _build_and_deploy(filepath, md)
    if err:
        return _finish(err)
    return _finish({
        "success": True,
        "title": title,
        "slug": slug,
        "url": f"/{lang}/market/us-daily/",
        "file": str(filepath),
        "deploy_error": deploy_error,
    })


def run_analyze(ticker: str = "VOO", lang: str = "ko") -> dict:
    """AI 분석 포스트 생성 + Hugo 발행"""
    if skip := _lang_retired(lang):
        return skip
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
    # 번역은 목적 언어로 새 글을 만드는 발행 경로다. 은퇴 언어로의 번역과
    # 심사 모드를 모두 여기서 막는다. (Codex 리뷰 지적 — 이 경로가 무방비였다)
    if skip := _lang_retired(target_lang):
        return skip
    stdout, stderr, returncode = _popen_stream(
        [VENV_PYTHON, "-m", "auto_publisher.main", "translate", "--from", source_lang, "--to", target_lang],
        cwd=NICHPROJECT,
        timeout_sec=int(os.getenv("TRANSLATE_TIMEOUT_SEC", "600")),
    )
    return {
        "success": returncode == 0,
        "output": stdout[-500:],
        "error": stderr[-300:] if returncode != 0 else "",
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


_URL_JOBS: dict[str, dict] = {}


def _validate_url_to_content_url(url: str) -> tuple[bool, str]:
    """Return whether URL is actionable enough to create editorial work."""
    if not url:
        return False, "url is required"
    if any(ch.isspace() for ch in url):
        return False, "url contains whitespace"

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, "url must use http or https"
    if not parsed.hostname:
        return False, "url host is missing"

    host = parsed.hostname.rstrip(".").lower()
    placeholder_hosts = {
        "ex",
        "example",
        "example.com",
        "example.net",
        "example.org",
        "test",
        "localhost",
    }
    if host in placeholder_hosts:
        return False, f"placeholder host is not actionable: {host}"

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip:
        if not ip.is_global:
            return False, f"non-public host is not actionable: {host}"
        return True, ""

    labels = host.split(".")
    if len(labels) < 2 or any(not label for label in labels):
        return False, f"host must be a fully qualified public name: {host}"
    if len(labels[-1]) < 2:
        return False, f"host has an invalid top-level domain: {host}"

    return True, ""


def _cancel_url_to_content_job(job_id: str, url: str, reason: str, callback_url: str = "") -> dict:
    finished_at = time.time()
    _URL_JOBS[job_id] = {
        "status": "cancelled",
        "url": url,
        "error": "invalid_url",
        "reason": reason,
        "started_at": finished_at,
        "finished_at": finished_at,
        "callback_url": callback_url,
    }
    logger.warning(f"url-to-content job {job_id} rejected: {reason}")
    return {
        "success": False,
        "job_id": job_id,
        "status": "cancelled",
        "error": "invalid_url",
        "reason": reason,
        "poll": f"/url-to-content-status?job_id={job_id}",
    }


def _run_url_to_content_job(
    job_id: str, url: str, lang: str, publish_blog: bool, publish_shorts: bool,
    callback_url: str = "",
) -> None:
    """URL → blog post + (optional) YouTube Shorts. Discord에서 호출.
    완료 시 callback_url 지정되면 POST.
    Paperclip audit: 시작 시 issue 생성, 종료 시 status + work_product 업데이트.
    """
    # URL → 블로그 글 + 쇼츠를 만드는 발행 경로다. 심사 모드·은퇴 언어를 여기서도 막는다.
    # (Codex 리뷰 지적 — 이 경로가 무방비여서 심사 중에도 신규 글이 나갈 수 있었다)
    if skip := _lang_retired(lang):
        _URL_JOBS[job_id].update(status="skipped", result=skip, finished_at=time.time())
        logger.info(f"url-to-content job {job_id} skipped: {skip.get('reason')}")
        _notify_url_job(job_id, callback_url)
        return

    _URL_JOBS[job_id]["status"] = "running"
    cost_breakdown: dict = {}
    # Paperclip audit issue (graceful — 실패해도 job 계속)
    try:
        from auto_publisher.paperclip_audit import create_url_content_issue
        audit_issue_id = create_url_content_issue(url, lang, source="bridge", job_id=job_id)
        if audit_issue_id:
            _URL_JOBS[job_id]["paperclip_issue_id"] = audit_issue_id
    except Exception as e:
        logger.warning(f"paperclip audit 생성 skip: {e}")
        audit_issue_id = None
    try:
        # 1. URL 콘텐츠 추출
        from auto_publisher.url_fetcher import fetch_url_content
        content = fetch_url_content(url)
        _URL_JOBS[job_id]["fetched"] = {
            "title": content["title"], "platform": content["platform"], "text_len": len(content["text"])
        }

        result: dict = {"source_url": url, "platform": content["platform"]}

        # 2. 블로그 생성 + 발행
        if publish_blog:
            from auto_publisher.content_generator import generate_blog_post
            # 토픽 = URL 제목, 키워드 = 제목에서 추출 가능한 의미있는 단어 + 핵심
            topic = content["title"]
            # 키워드: 제목 + 단순 분할 (LLM이 알아서 best primary 결정)
            keywords = [topic] + topic.split()[:5]
            post = generate_blog_post(
                topic=topic, keywords=keywords, lang=lang, category="시장분석",
                external_context=content["text"],
            )
            # 비용 추정 (post-hoc)
            try:
                from auto_publisher.token_estimator import estimate_call
                import os as _os
                primary = _os.getenv("LLM_PRIMARY_BACKEND", "gemini")
                if primary == "gemini":
                    model = _os.getenv("GEMINI_CLI_MODEL", "gemini-3.1-pro-preview")
                elif primary == "claude":
                    model = _os.getenv("CLAUDE_CLI_MODEL", "claude-haiku-4-5")
                else:
                    model = primary
                full_response = post.get("content_html", "") + post.get("meta_description", "")
                rough_prompt_estimate = content["text"][:3000] + content["title"]
                breakdown = estimate_call(rough_prompt_estimate, full_response, model)
                cost_breakdown[model] = breakdown
            except Exception as _ce:
                logger.warning(f"cost estimation 실패: {_ce}")

            from auto_publisher.publishers.hugo import HugoPublisher
            publisher = HugoPublisher(lang=lang)
            hugo_result = publisher.publish(
                title=post["title"],
                content_html=post["content_html"],
                tags=post.get("tags", []),
                meta_description=post.get("meta_description", ""),
                categories=["시장분석", "재테크"],
                primary_keyword=post.get("primary_keyword", ""),
                keywords_long_tail=post.get("keywords_long_tail", []),
                schema_faq=post.get("schema_faq", []),
                content_type=post.get("content_type", "guide"),
                howto_steps=post.get("howto_steps", []),
            )
            result["blog_url"] = f"https://investiqs.net{hugo_result.get('url','')}"
            result["filepath"] = hugo_result.get("filepath", "")
            result["slug"] = hugo_result.get("slug", "")

            # 3. Shorts 생성
            if publish_shorts and result.get("slug"):
                try:
                    video_res = run_make_video(result["slug"], lang, "public")
                    result["youtube_url"] = (video_res or {}).get("short_url") or (video_res or {}).get("youtube_url", "")
                except Exception as e:
                    logger.warning(f"url-to-content shorts 실패: {e}")
                    result["youtube_error"] = str(e)[:200]

        _URL_JOBS[job_id].update({"status": "done", "result": result, "finished_at": time.time()})
    except Exception as e:
        logger.error(f"url-to-content job {job_id} 실패: {e}", exc_info=True)
        _URL_JOBS[job_id].update({"status": "cancelled", "error": str(e)[:300], "finished_at": time.time()})

    # Paperclip audit 종료 — status + work_product + comment
    if audit_issue_id:
        try:
            from auto_publisher.paperclip_audit import complete_url_content_issue
            job_state = _URL_JOBS[job_id]
            complete_url_content_issue(
                audit_issue_id,
                result=job_state.get("result") or {},
                ok=(job_state.get("status") == "done"),
                error=job_state.get("error", ""),
                cost_breakdown=cost_breakdown or None,
            )
        except Exception as e:
            logger.warning(f"paperclip audit 종료 실패: {e}")

    _notify_url_job(job_id, callback_url)


def _notify_url_job(job_id: str, callback_url: str) -> None:
    """callback_url 호출 (성공/실패/skip 무관 알림).

    호출자가 어떤 경로로 끝나든 완료 통지는 나가야 한다 — 심사모드 skip 이
    이 통지를 건너뛰어 Discord 쪽이 영원히 대기했다(Codex 리뷰 2차 지적).
    """
    if not callback_url:
        return
    try:
        import urllib.request as _ur
        payload = json.dumps({
            "job_id": job_id,
            "status": _URL_JOBS[job_id].get("status"),
            "result": _URL_JOBS[job_id].get("result", {}),
            "error": _URL_JOBS[job_id].get("error", ""),
        }, ensure_ascii=False, default=str).encode("utf-8")
        req = _ur.Request(
            callback_url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _ur.urlopen(req, timeout=10) as resp:
            resp.read()
        logger.info(f"url-to-content callback 전송 완료: {callback_url}")
    except Exception as cb_err:
        logger.warning(f"callback_url POST 실패 ({callback_url}): {cb_err}")


def _popen_stream(cmd: list, cwd, timeout_sec: int) -> tuple[str, str, int]:
    """subprocess.Popen으로 실행하며 stdout을 sys.stdout에 실시간 스트림하고 캡처도 반환.

    Returns: (stdout_captured, stderr_captured, returncode)
    """
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output_lines = []
    try:
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            output_lines.append(line)
        proc.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise
    return "".join(output_lines), "", proc.returncode


def run_make_video(slug: str = "", lang: str = "ko",
                   privacy: str = "public") -> dict:
    """블로그 slug → 롱폼+쇼츠 영상 생성 + YouTube 업로드"""
    if skip := _lang_retired(lang):
        return skip
    if not slug:
        # slug 없으면 가장 최근 발행된 lang 포스트 사용
        from auto_publisher.shorts_auto import find_latest_publishable_slug
        content_root = NICHPROJECT / "web" / "content"
        latest = find_latest_publishable_slug(content_root=content_root, lang=lang)
        if latest:
            slug = latest["slug"]
    if not slug:
        return {"success": False, "error": "slug 없고 최근 포스트도 없음"}
    stdout, stderr, returncode = _popen_stream(
        [VENV_PYTHON, "-m", "auto_publisher.main", "make-video",
         "--slug", slug, "--lang", lang, "--privacy", privacy],
        cwd=NICHPROJECT,
        timeout_sec=int(os.getenv("MAKE_VIDEO_TIMEOUT_SEC", "1800")),
    )
    return {
        "success": returncode == 0,
        "slug": slug,
        "output": stdout[-1500:],
        "error": stderr[-500:] if returncode != 0 else "",
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


_BRIDGE_START_TIME = time.time()


def health_full() -> dict:
    """확장 헬스체크 — 토큰, 발행 이력, 프로세스, 디스크, GPU 포함."""
    import shutil

    result: dict = {"status": "ok"}

    # uptime
    result["bridge_uptime_sec"] = int(time.time() - _BRIDGE_START_TIME)

    # TikTok token
    tiktok_path = NICHPROJECT / ".tiktok_secrets" / "token.json"
    tiktok_info: dict = {"exists": tiktok_path.exists()}
    if tiktok_path.exists():
        try:
            tok = json.loads(tiktok_path.read_text())
            expires_at = tok.get("expires_at") or tok.get("expires_in")
            if expires_at:
                expires_in_sec = int(float(expires_at) - time.time())
                tiktok_info["expires_in_sec"] = expires_in_sec
                tiktok_info["warning"] = "expires soon" if expires_in_sec < 3600 else None
        except Exception:
            pass
    result["tiktok_token"] = tiktok_info

    # YouTube token
    yt_path = NICHPROJECT / ".youtube_secrets" / "token.json"
    result["youtube_token"] = {"exists": yt_path.exists()}

    # last_published — merges all published_history*.json (통합 + lang suffix)
    from glob import glob as _glob_hist
    from datetime import datetime as _dt
    import re as _re_hist

    def _entry_ts(entry: dict) -> float:
        raw = entry.get("timestamp") or entry.get("published_at") or entry.get("date") or ""
        if not raw:
            return 0.0
        try:
            return _dt.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    def _iter_history():
        base = NICHPROJECT / "auto_publisher" / "data"
        for hp in _glob_hist(str(base / "published_history*.json")):
            m = _re_hist.search(r"published_history(?:_([a-z]{2}))?\.json$", hp)
            lang_from_file = m.group(1) if m and m.group(1) else None
            try:
                data = json.loads(open(hp).read())
            except Exception:
                continue
            iterator = data if isinstance(data, list) else (
                [{**(v if isinstance(v, dict) else {}), "timestamp": v.get("timestamp", k) if isinstance(v, dict) else k}
                 for k, v in data.items()] if isinstance(data, dict) else []
            )
            for e in iterator:
                if not isinstance(e, dict):
                    continue
                if lang_from_file and not e.get("lang"):
                    e = {**e, "lang": lang_from_file}
                yield e

    last_published: dict = {}
    try:
        latest = max(_iter_history(), key=_entry_ts, default=None)
        if latest:
            last_published = {
                "timestamp": latest.get("timestamp") or latest.get("published_at") or latest.get("date"),
                "slug": latest.get("slug"),
                "lang": latest.get("lang"),
            }
    except Exception:
        pass
    result["last_published"] = last_published

    # n8n running (Docker 컨테이너 우선, 직접 프로세스 폴백)
    def _check_n8n() -> bool:
        try:
            r = subprocess.run(
                ["docker", "ps", "-q", "--filter", "name=n8n"],
                capture_output=True, text=True, timeout=5,
            )
            if r.stdout.strip():
                return True
        except Exception:
            pass
        try:
            r = subprocess.run(
                ["pgrep", "-f", "n8n"],
                capture_output=True, text=True, timeout=5,
            )
            if r.stdout.strip():
                return True
        except Exception:
            pass
        return False

    result["n8n_running"] = _check_n8n()

    # tunnel active
    try:
        tunnel_out = subprocess.run(
            ["pgrep", "-f", "cloudflared.*investiqs"],
            capture_output=True, text=True, timeout=5,
        )
        result["tunnel_active"] = tunnel_out.returncode == 0
    except Exception:
        result["tunnel_active"] = False

    # stuck processes (auto_publisher.main make-video running >= 1800s)
    stuck = []
    try:
        ps_out = subprocess.run(
            ["ps", "-eo", "pid,etimes,args", "--no-headers"],
            capture_output=True, text=True, timeout=5,
        )
        for line in ps_out.stdout.splitlines():
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            pid_str, elapsed_str, cmd = parts
            if "auto_publisher" in cmd and "make-video" in cmd:
                try:
                    elapsed = int(elapsed_str)
                    if elapsed >= 1800:
                        stuck.append({"pid": int(pid_str), "cmd": cmd[:120], "elapsed_sec": elapsed})
                except ValueError:
                    pass
    except Exception:
        pass
    result["stuck_processes"] = stuck

    # disk usage
    try:
        df_out = subprocess.run(
            ["df", "/", "--output=pcent"],
            capture_output=True, text=True, timeout=5,
        )
        lines = [l.strip() for l in df_out.stdout.splitlines() if l.strip()]
        pct_str = lines[-1].rstrip("%")
        result["disk_usage_percent"] = float(pct_str)
    except Exception:
        result["disk_usage_percent"] = None

    # GPU utilization
    try:
        gpu_out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if gpu_out.returncode == 0:
            gpu_vals = [float(v.strip()) for v in gpu_out.stdout.splitlines() if v.strip()]
            result["gpu_utilization_percent"] = gpu_vals[0] if len(gpu_vals) == 1 else gpu_vals
        else:
            result["gpu_utilization_percent"] = None
    except Exception:
        result["gpu_utilization_percent"] = None

    # 활성 n8n 워크플로우 수 — alpine n8n 컨테이너에 sqlite3 바이너리 없으므로 docker cp 후 호스트에서 읽음
    def _active_workflows():
        import tempfile, sqlite3 as _sql, os as _os
        tmp_path = None
        try:
            tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
            tmp_path = tf.name
            tf.close()
            r = subprocess.run(
                ["docker", "cp", "n8n-n8n-1:/home/node/.n8n/database.sqlite", tmp_path],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode != 0:
                return None
            conn = _sql.connect(tmp_path)
            row = conn.execute("SELECT COUNT(*) FROM workflow_entity WHERE active=1").fetchone()
            conn.close()
            return int(row[0]) if row else None
        except Exception:
            return None
        finally:
            if tmp_path:
                try: _os.unlink(tmp_path)
                except Exception: pass

    # 최근 24h 발행 수 — 모든 published_history*.json 합산
    def _recent_publish_count():
        try:
            since = _dt.now().timestamp() - 86400
            return sum(1 for e in _iter_history() if _entry_ts(e) > since)
        except Exception:
            return None

    # 마지막 영상 생성 시각 — NICHPROJECT 기준 (WORKSPACE 였던 버그 수정)
    def _last_video():
        try:
            from glob import glob
            from os.path import getmtime
            videos = glob(str(NICHPROJECT / ".omc" / "video_cache" / "*" / "short.mp4"))
            if not videos:
                return None
            latest = max(videos, key=getmtime)
            return _dt.fromtimestamp(getmtime(latest)).isoformat()
        except Exception:
            return None

    result["active_workflows"] = _active_workflows()
    result["recent_24h_publish_count"] = _recent_publish_count()
    result["last_video_generated"] = _last_video()

    # bot_status — TCP port listening checks
    def _bot_listening(port: int) -> bool:
        """Check if a TCP port is listening on 127.0.0.1."""
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            res = s.connect_ex(("127.0.0.1", port))
            return res == 0
        finally:
            s.close()

    result["bot_status"] = {
        "discord_hermes_callback": _bot_listening(8900),
        "telegram_callback": _bot_listening(8901),
        "slack_callback": _bot_listening(8902),
    }

    # paperclip_today_cost — fetch today's cost from audit module
    paperclip_today = {"usd": None, "alert_sent": False}
    try:
        from auto_publisher.paperclip_audit import check_cost_threshold
        cost_result = check_cost_threshold()
        if "today_usd" in cost_result:
            paperclip_today["usd"] = cost_result["today_usd"]
            paperclip_today["threshold_usd"] = cost_result.get("threshold_usd")
            paperclip_today["alert_sent"] = cost_result.get("alert_sent", False)
    except Exception:
        pass
    result["paperclip_today_cost"] = paperclip_today

    return result


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
                tiktok_warn = False
                tiktok_path = NICHPROJECT / ".tiktok_secrets" / "token.json"
                if tiktok_path.exists():
                    try:
                        tok = json.loads(tiktok_path.read_text())
                        expires_at = tok.get("expires_at") or tok.get("expires_in")
                        if expires_at:
                            tiktok_warn = int(float(expires_at) - time.time()) < 3600
                    except Exception:
                        pass
                self._respond(200, {"status": "warning" if tiktok_warn else "ok"})
            return
        if path == "/health/full":
            if not self._check_auth():
                self._respond(401, {"error": "Unauthorized"})
                return
            try:
                self._respond(200, health_full())
            except Exception as e:
                self._respond(500, {"status": "error", "error": str(e)})
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
        if path == "/url-to-content-status":
            job_id = params.get("job_id", "")
            if not job_id or job_id not in _URL_JOBS:
                self._respond(404, {"error": "job_id not found"})
                return
            self._respond(200, _URL_JOBS[job_id])
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
        if path == "/tiktok-callback":
            try:
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(self.path).query)
                code = (qs.get("code") or [""])[0]
                err = (qs.get("error") or [""])[0]
                if err:
                    self._respond(400, {"success": False, "error": err, "description": (qs.get("error_description") or [""])[0]})
                    return
                if not code:
                    self._respond(400, {"success": False, "error": "missing code parameter"})
                    return
                from auto_publisher.video_uploader import tiktok_auth_setup
                tiktok_auth_setup(code=code)
                html = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'><title>TikTok 인증 완료</title>"
                    "<style>body{font-family:system-ui,sans-serif;background:#0f172a;color:#fff;padding:60px;text-align:center}h1{color:#22c55e}</style></head>"
                    "<body><h1>✅ TikTok 토큰 발급 완료</h1><p>이 창을 닫아도 됩니다.</p></body></html>"
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._respond(500, {"success": False, "error": str(e)})
            return
        if path == "/instagram/auth-test":
            try:
                import urllib.request as _ureq
                access_token = os.getenv("META_ACCESS_TOKEN", "")
                if not access_token:
                    self._respond(400, {"success": False, "error": "META_ACCESS_TOKEN 미설정"})
                    return
                me_url = f"https://graph.facebook.com/v21.0/me?access_token={access_token}"
                with _ureq.urlopen(_ureq.Request(me_url, method="GET"), timeout=15) as _r:
                    me_data = json.loads(_r.read().decode())
                if "id" in me_data and "name" in me_data:
                    self._respond(200, {"success": True, "id": me_data["id"], "name": me_data["name"]})
                else:
                    self._respond(200, {"success": False, "response": me_data})
            except Exception as e:
                self._respond(500, {"success": False, "error": str(e)})
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

        if path == "/paperclip/poll-and-publish":
            # Paperclip work_product(type=blog_post, status=ready) 폴링 + 발행
            body = self._read_json_body() or {}
            max_items = int(body.get("max_items", 5))
            try:
                from auto_publisher.paperclip_publish import poll_and_publish
                result = poll_and_publish(max_items=max_items)
                self._respond(200, result)
            except Exception as e:
                logger.error(f"paperclip poll-and-publish 실패: {e}", exc_info=True)
                self._respond(500, {"success": False, "error": str(e)[:200]})
            return

        if path == "/paperclip/cost-alert-check":
            # Daily cost threshold check (23:00 KST n8n cron)
            try:
                from auto_publisher.paperclip_audit import check_cost_threshold
                result = check_cost_threshold()
                self._respond(200, result)
            except Exception as e:
                logger.error(f"cost-alert-check 실패: {e}", exc_info=True)
                self._respond(500, {"success": False, "error": str(e)[:200]})
            return

        if path == "/url-to-content":
            # URL → blog post + (optional) YouTube Shorts. Async job.
            body = self._read_json_body() or {}
            url = (body.get("url") or "").strip()
            if not url:
                self._respond(400, {"error": "url 필수"})
                return
            lang = body.get("lang", "ko")
            publish_blog = bool(body.get("publish_blog", True))
            publish_shorts = bool(body.get("publish_shorts", True))
            callback_url = (body.get("callback_url") or "").strip()
            job_id = body.get("job_id") or str(uuid.uuid4())
            valid_url, invalid_reason = _validate_url_to_content_url(url)
            if not valid_url:
                self._respond(422, _cancel_url_to_content_job(job_id, url, invalid_reason, callback_url))
                return
            _URL_JOBS[job_id] = {"status": "queued", "url": url, "started_at": time.time(),
                                 "callback_url": callback_url}
            threading.Thread(
                target=_run_url_to_content_job,
                args=(job_id, url, lang, publish_blog, publish_shorts, callback_url),
                daemon=True,
            ).start()
            self._respond(202, {
                "job_id": job_id, "status": "queued",
                "poll": f"/url-to-content-status?job_id={job_id}",
            })
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


def _start_health_alerter_thread() -> None:
    """30분 간격 health 점검 + Discord 알림 (background daemon).

    - HEALTH_ALERTER_ENABLED=false 면 run_health_check 자체에서 no-op
    - HEALTH_ALERTER_INTERVAL_SEC 으로 간격 조정 (default 1800초)
    - bridge_api crash 시 alert 도 죽음 → 별도 시스템 cron 추가 권장
    """
    from auto_publisher.health_alerter import run_health_check
    repo = Path("/home/mh/ocstorage/workspace/nichproject")
    interval_sec = int(os.getenv("HEALTH_ALERTER_INTERVAL_SEC", "1800"))

    def _loop():
        while True:
            time.sleep(interval_sec)
            try:
                run_health_check(
                    token_file=repo / ".tiktok_secrets" / "token.json",
                    history_file=repo / "auto_publisher" / "data" / "published_history.json",
                )
            except Exception as e:
                print(f"[health_alerter] loop error: {e}", flush=True)

    t = threading.Thread(target=_loop, daemon=True, name="health_alerter")
    t.start()
    print(f"[bridge] health_alerter thread 시작 (interval={interval_sec}s)", flush=True)


if __name__ == "__main__":
    acquire_bridge_lock()
    _start_health_alerter_thread()
    port = int(os.getenv("BRIDGE_PORT", "8765"))
    bind_host = os.getenv("BRIDGE_BIND_HOST", "127.0.0.1")
    # ThreadingHTTPServer: 동시 요청 처리 (단일스레드 HTTPServer는 cron 충돌 시 ECONNABORTED 유발)
    server = ThreadingHTTPServer((bind_host, port), BridgeHandler)
    print(f"n8n Bridge API running on http://{bind_host}:{port}")
    print(f"Routes: {list(ROUTES.keys()) + ['/health']}")
    server.serve_forever()
