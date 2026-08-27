"""애드센스 심사 모드 — 발행 경로 전면 차단 토글.

심사 중 자동 발행은 "manual review or curation 없는 대량 생성"이라는
위반 신호를 실시간으로 강화한다(survey/04-adsense-approval.md).
n8n 워크플로우를 건드리지 않고 bridge 한 곳에서 흡수한다.
"""

import pytest

import n8n.bridge_api as api


# 사이트 발행 경로 — 심사 중 전부 차단돼야 한다.
# 영상 경로(run_shorts_auto_latest, run_make_video)는 2026-08-28 부터 예외:
# 심사관이 보는 건 investiqs.net 이지 유튜브가 아니고, 쇼츠는 이미 라이브에
# 있는 글만 소재로 쓴다. 아래 test_youtube_channel_passes_review_mode 참조.
PUBLISH_ENTRYPOINTS = [
    ("run_auto_publish", {"lang": "ko"}),
    ("run_publish_us_market_wrap", {"lang": "ko"}),
    ("run_publish_us_market_weekly", {"lang": "ko"}),
    ("run_publish_us_market_intraday", {"lang": "ko"}),
]


@pytest.fixture
def review_on(monkeypatch, tmp_path):
    flag = tmp_path / ".adsense_review"
    flag.write_text("on", encoding="utf-8")
    monkeypatch.setattr(api, "ADSENSE_REVIEW_FLAG", flag)
    return flag


@pytest.fixture
def review_off(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "ADSENSE_REVIEW_FLAG", tmp_path / "absent")


@pytest.mark.parametrize("fn_name,kwargs", PUBLISH_ENTRYPOINTS)
def test_every_publish_entrypoint_is_blocked(review_on, fn_name, kwargs):
    """블로그·시황·쇼츠·영상 어느 경로로도 발행이 나가면 안 된다."""
    result = getattr(api, fn_name)(**kwargs)
    assert result["skipped"] is True, fn_name
    assert result["success"] is True, "실패가 아니라 정상 skip 이어야 워크플로우가 오류로 안 뜬다"
    assert "심사" in result["reason"]


def test_flag_absent_restores_publishing(review_off):
    """플래그를 지우면 즉시 원복된다 — 승인 후 되돌리기가 파일 삭제 하나로 끝나야 한다."""
    assert api._review_mode_block() is None
    assert api._lang_retired("ko") is None


def test_retired_language_guard_survives_review_mode(review_off):
    """심사 모드를 꺼도 은퇴 언어 차단은 그대로 유지된다."""
    assert api._lang_retired("ja")["skipped"] is True


def test_review_mode_blocks_supported_language_too(review_on):
    """심사 모드에서는 활성 언어(ko/en)도 막아야 의미가 있다."""
    for lang in ("ko", "en"):
        assert api._lang_retired(lang)["skipped"] is True, lang


def test_youtube_channel_passes_review_mode(review_on):
    """심사 중에도 유튜브 채널은 통과한다 — 사이트는 안 바뀌므로.

    실제 영상 생성 경로에 들어가면 테스트가 5분씩 돌므로 가드 함수
    수준에서만 확인한다. run_make_video / run_shorts_auto_latest 가
    channel="youtube" 로 호출하는 건 소스 검사로 잠근다.
    """
    assert api._review_mode_block(channel="youtube") is None
    assert api._lang_retired("ko", channel="youtube") is None
    # 은퇴 언어 차단은 채널과 무관하게 유지돼야 한다
    assert api._lang_retired("ja", channel="youtube")["skipped"] is True

    import inspect
    for fn_name in ("run_make_video", "run_shorts_auto_latest"):
        src = inspect.getsource(getattr(api, fn_name))
        assert 'channel="youtube"' in src, f"{fn_name} 이 youtube 채널로 호출하지 않는다"


# --- 발행 경로 전수 검사 (Codex 리뷰 2차 지적:
#     함수명을 손으로 열거하면 새 경로가 추가될 때 반드시 빠진다.
#     실제로 run_analyze / run_translate / _run_url_to_content_job /
#     publish_market_post 가 이렇게 새어 나갔다) ---

# 발행 = 콘텐츠 파일을 쓰거나 영상을 업로드하는 동작.
_PUBLISH_MARKERS = (
    "_atomic_write", "write_text", "_build_and_deploy", "hugo_publish",
    "publish_post", "upload_video", "make-video", "auto_publisher.main",
    "wrangler", "HugoPublisher", "run_make_video(",
)
# 발행이 아닌데 마커에 걸리는 것들 — 이유를 남긴다.
_NOT_PUBLISHING = {
    "run_refresh_market_cache": "market-cache.json 갱신만 — 콘텐츠 아님",
    "_atomic_write": "쓰기 헬퍼 자체",
    "_build_and_deploy": "빌드/배포 헬퍼 — 호출자(wrap/weekly/intraday)가 이미 가드함",
    "_run_video_job": "run_make_video 로 그대로 위임 — 가드는 그쪽에 있음",
    "_save_url_job": "잡 상태 파일",
    "get_topic_queue": "auto_publisher.main topics — 큐 조회(읽기)만",
    "health_full": "stuck 프로세스 감시 — 문자열이 주석 안에 있음",
}


def _publishing_functions():
    import inspect
    import n8n.bridge_api as api

    for name, fn in vars(api).items():
        if not inspect.isfunction(fn) or fn.__module__ != api.__name__:
            continue
        if name in _NOT_PUBLISHING:
            continue
        try:
            src = inspect.getsource(fn)
        except OSError:
            continue
        code = _executable_source(src)
        if any(m in code for m in _PUBLISH_MARKERS):
            yield name, code


def _executable_source(src: str) -> str:
    """주석과 독스트링을 걷어낸 소스.

    다른 문자열 리터럴은 남긴다 — subprocess argv 의 "auto_publisher.main",
    "make-video" 같은 게 바로 발행 마커라, 문자열을 통째로 지우면 탐지가 무너진다
    (실제로 11개 → 6개로 떨어지는 걸 확인했다).
    """
    import ast
    import textwrap

    tree = ast.parse(textwrap.dedent(src))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef, ast.Module)) and ast.get_docstring(node):
            node.body = node.body[1:]
    return ast.unparse(tree)


def _has_guard_call(src: str) -> bool:
    """`_lang_retired(...)` / `_review_mode_block(...)` 를 **호출**하는지 확인.

    문자열 검사로는 독스트링이나 로그 메시지 안의 이름도 가드로 오인된다
    (Codex 리뷰 3차 지적). AST 로 실제 Call 노드만 센다.
    """
    import ast
    import textwrap

    for node in ast.walk(ast.parse(textwrap.dedent(src))):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in ("_lang_retired", "_review_mode_block")):
            return True
    return False


def test_every_publishing_route_is_guarded():
    """콘텐츠를 쓰는 모든 함수가 _lang_retired 가드를 통과하는지 소스로 확인."""
    missing = [name for name, code in _publishing_functions()
               if not _has_guard_call(code)]
    assert not missing, (
        f"가드 없는 발행 경로: {missing}. "
        "발행이 아니라면 _NOT_PUBLISHING 에 이유와 함께 등록하라."
    )


def test_detector_actually_finds_something():
    """탐지기가 0건을 반환하면 위 테스트는 항상 통과한다 — 무의미해진다."""
    found = [n for n, _ in _publishing_functions()]
    assert len(found) >= 6, f"발행 경로를 {len(found)}개만 찾았다 — 마커가 낡았다: {found}"


# --- _atomic_write 동시성 (Codex 리뷰 2차: PID tmp 는 스레드 간 공유된다) ---

def test_atomic_write_survives_concurrent_threads(tmp_path):
    """ThreadingHTTPServer 라 같은 프로세스의 여러 스레드가 같은 파일을 쓴다.

    이 테스트가 실제로 잡아낸 것: tempfile 모듈 레벨 import 누락(NameError).
    """
    import threading
    import n8n.bridge_api as api

    target = tmp_path / "us-daily.md"
    errors: list[str] = []

    def writer(n: int) -> None:
        try:
            for _ in range(30):
                api._atomic_write(target, f"content-{n}\n" * 500)
        except Exception as e:      # noqa: BLE001 — 어떤 예외든 실패로 본다
            errors.append(repr(e))

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"동시 쓰기 실패: {errors[:3]}"
    # 반쯤 섞인 파일이 아니라 어느 한 writer 의 내용 전체여야 한다.
    assert len(set(target.read_text().splitlines())) == 1
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "us-daily.md"]
    assert not leftovers, f"tmp 파일이 남았다: {leftovers}"


def test_build_lock_serializes():
    """hugo --cleanDestinationDir 가 공용 web/public 을 갈아엎으므로 겹치면 안 된다."""
    import threading
    import time
    import n8n.bridge_api as api

    order: list[tuple[str, int]] = []

    def job(n: int) -> None:
        with api._build_lock(timeout=30):
            order.append(("in", n))
            time.sleep(0.05)
            order.append(("out", n))

    threads = [threading.Thread(target=job, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # in/out 이 짝지어 번갈아 나와야 한다. 겹쳤다면 in,in 이 연달아 나온다.
    assert all(order[i][0] == "in" and order[i + 1][0] == "out"
               for i in range(0, len(order), 2)), order


def test_build_lock_respects_total_timeout(tmp_path, monkeypatch):
    """timeout 은 스레드 락 + 파일 락의 **합계** 여야 한다.

    폴링 sleep 이 남은 시간을 무시하면 성공도 실패도 계약을 초과한다
    (Codex 리뷰 3차 지적: 남은 시간 0.1s 에도 1s 를 자던 문제).
    """
    import fcntl
    import multiprocessing
    import time
    import n8n.bridge_api as api

    lock_file = tmp_path / ".hugo_build.lock"
    monkeypatch.setattr(api, "_BUILD_LOCK_FILE", lock_file)

    ready = multiprocessing.Event()
    release = multiprocessing.Event()

    def hold(path: str) -> None:
        with open(path, "w") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            ready.set()
            release.wait(30)

    # 파일 락은 같은 프로세스에서 재획득이 되므로 별도 프로세스로 잡아야 한다.
    holder = multiprocessing.Process(target=hold, args=(str(lock_file),))
    holder.start()
    try:
        assert ready.wait(10), "락 홀더가 시작되지 않았다"

        timeout = 0.5
        start = time.monotonic()
        with pytest.raises(TimeoutError):
            with api._build_lock(timeout=timeout):
                pass
        elapsed = time.monotonic() - start
    finally:
        release.set()
        holder.join(10)

    # 폴링 간격(1.0s)이 timeout(0.5s)보다 크다. 남은 시간을 안 지키면 1s 이상 걸린다.
    assert elapsed < timeout + 0.3, f"timeout 계약 초과: {elapsed:.2f}s > {timeout}s"


def test_build_lock_releases_thread_lock_on_file_timeout(tmp_path, monkeypatch):
    """파일 락 타임아웃으로 빠져나가도 스레드 락은 풀려야 한다.

    안 풀리면 이후 모든 발행이 영구 데드락에 빠진다.
    """
    import fcntl
    import multiprocessing
    import n8n.bridge_api as api

    lock_file = tmp_path / ".hugo_build.lock"
    monkeypatch.setattr(api, "_BUILD_LOCK_FILE", lock_file)

    ready = multiprocessing.Event()
    release = multiprocessing.Event()

    def hold(path: str) -> None:
        with open(path, "w") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            ready.set()
            release.wait(30)

    holder = multiprocessing.Process(target=hold, args=(str(lock_file),))
    holder.start()
    try:
        assert ready.wait(10)
        with pytest.raises(TimeoutError):
            with api._build_lock(timeout=0.3):
                pass
    finally:
        release.set()
        holder.join(10)

    assert api._BUILD_LOCK.acquire(timeout=1), "스레드 락이 안 풀렸다 — 영구 데드락"
    api._BUILD_LOCK.release()


# --- 심사 overlay 배선 (Codex 리뷰 4차 지적:
#     설정 파일만 검사하면 --config 연결을 지워도 테스트가 전부 통과한다) ---

def test_hugo_config_args_by_flag(tmp_path, monkeypatch):
    """플래그 유무에 따라 --config 가 붙고 빠져야 한다."""
    import n8n.bridge_api as api

    flag = tmp_path / ".adsense_review"
    overlay = tmp_path / "hugo.adsense.toml"
    overlay.write_text("ignoreFiles = []\n", encoding="utf-8")
    monkeypatch.setattr(api, "ADSENSE_REVIEW_FLAG", flag)
    monkeypatch.setattr(api, "ADSENSE_OVERLAY", overlay)

    assert api._hugo_config_args() == [], "평상시엔 overlay 를 얹으면 안 된다"

    flag.write_text("on", encoding="utf-8")
    assert api._hugo_config_args() == ["--config", "hugo.toml,hugo.adsense.toml"]


def test_missing_overlay_in_review_mode_fails_loudly(tmp_path, monkeypatch):
    """fail-open 이면 심사 중에 축소 대상 글이 전부 배포된다."""
    import n8n.bridge_api as api

    flag = tmp_path / ".adsense_review"
    flag.write_text("on", encoding="utf-8")
    monkeypatch.setattr(api, "ADSENSE_REVIEW_FLAG", flag)
    monkeypatch.setattr(api, "ADSENSE_OVERLAY", tmp_path / "없는파일.toml")

    with pytest.raises(FileNotFoundError):
        api._hugo_config_args()


@pytest.mark.parametrize("review_mode,expect_config", [(True, True), (False, False)])
def test_build_command_carries_config_flag(tmp_path, monkeypatch, review_mode, expect_config):
    """실제 hugo 명령줄에 --config 가 실리는지 확인한다.

    _build_and_deploy 안의 호출부(`*_hugo_config_args()`)를 지우면 이 테스트가 깨진다.
    """
    import n8n.bridge_api as api

    flag = tmp_path / ".adsense_review"
    overlay = tmp_path / "hugo.adsense.toml"
    overlay.write_text("ignoreFiles = []\n", encoding="utf-8")
    if review_mode:
        flag.write_text("on", encoding="utf-8")
    monkeypatch.setattr(api, "ADSENSE_REVIEW_FLAG", flag)
    monkeypatch.setattr(api, "ADSENSE_OVERLAY", overlay)
    monkeypatch.setattr(api, "_BUILD_LOCK_FILE", tmp_path / ".hugo_build.lock")

    calls: list[list[str]] = []

    class _Done:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, *a, **k):
        calls.append(list(cmd))
        return _Done()

    monkeypatch.setattr(api.subprocess, "run", fake_run)

    err, _ = api._build_and_deploy(tmp_path / "out" / "us-daily.md", "본문")
    assert err is None

    hugo_cmd = next(c for c in calls if c and c[0] == "hugo")
    has_config = "--config" in hugo_cmd
    assert has_config is expect_config, hugo_cmd
    if expect_config:
        assert hugo_cmd[hugo_cmd.index("--config") + 1] == "hugo.toml,hugo.adsense.toml"


def test_missing_overlay_aborts_before_touching_files(tmp_path, monkeypatch):
    """overlay 누락으로 터질 때 대시보드 파일이 바뀌면 안 된다.

    설정 확인이 쓰기보다 뒤에 있으면 빌드는 막혀도 파일은 이미 갈아엎힌다
    (Codex 리뷰 5차 지적).
    """
    import n8n.bridge_api as api

    flag = tmp_path / ".adsense_review"
    flag.write_text("on", encoding="utf-8")
    monkeypatch.setattr(api, "ADSENSE_REVIEW_FLAG", flag)
    monkeypatch.setattr(api, "ADSENSE_OVERLAY", tmp_path / "없는파일.toml")
    monkeypatch.setattr(api, "_BUILD_LOCK_FILE", tmp_path / ".hugo_build.lock")

    calls: list[list[str]] = []
    monkeypatch.setattr(api.subprocess, "run",
                        lambda cmd, *a, **k: calls.append(list(cmd)))

    target = tmp_path / "out" / "us-daily.md"
    with pytest.raises(FileNotFoundError):
        api._build_and_deploy(target, "새 본문")

    assert not target.exists(), "터졌는데 대시보드 파일이 쓰였다"
    assert not target.parent.exists(), "디렉터리도 만들면 안 된다"
    assert calls == [], f"hugo/wrangler 가 실행됐다: {calls}"


def test_existing_dashboard_untouched_when_overlay_missing(tmp_path, monkeypatch):
    """이미 있는 대시보드도 덮어쓰면 안 된다."""
    import n8n.bridge_api as api

    flag = tmp_path / ".adsense_review"
    flag.write_text("on", encoding="utf-8")
    monkeypatch.setattr(api, "ADSENSE_REVIEW_FLAG", flag)
    monkeypatch.setattr(api, "ADSENSE_OVERLAY", tmp_path / "없는파일.toml")
    monkeypatch.setattr(api, "_BUILD_LOCK_FILE", tmp_path / ".hugo_build.lock")
    monkeypatch.setattr(api.subprocess, "run",
                        lambda *a, **k: pytest.fail("빌드가 실행되면 안 된다"))

    target = tmp_path / "us-daily.md"
    target.write_text("기존 본문", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        api._build_and_deploy(target, "새 본문")

    assert target.read_text(encoding="utf-8") == "기존 본문"
