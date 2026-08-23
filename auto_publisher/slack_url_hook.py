"""slack_url_hook.py — Slack URL→Content hook mirroring the Telegram equivalent.

콘텐츠 URL이 Slack 메시지에 올라오면 bridge_api로 보내서 blog+Shorts 자동 생성.
완료 시 bridge가 callback_url로 POST → 결과를 원래 채널에 Slack reply로 전송.

환경변수:
  SLACK_URL_HOOK_ENABLED=0     (기본 OFF — 1로 설정해야 동작)
  SLACK_BOT_TOKEN=xoxb-...    (ENABLED=1일 때 필수)
  SLACK_APP_TOKEN=xapp-...    (Socket Mode 필수)
  SLACK_CALLBACK_PORT=8902    (callback 수신 포트, 기본 8902)
  NICHPROJECT_BRIDGE_URL      (기본 http://172.17.0.1:8765)
"""

import json
import logging
import os
import re
import urllib.request

logger = logging.getLogger(__name__)

# ── 환경변수 ──────────────────────────────────────────────────────────────────
_ENABLED = os.getenv("SLACK_URL_HOOK_ENABLED", "0").strip() == "1"
_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "").strip()
_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "").strip()
_CALLBACK_PORT = int(os.getenv("SLACK_CALLBACK_PORT", "8902"))
_BRIDGE_URL = os.getenv("NICHPROJECT_BRIDGE_URL", "http://172.17.0.1:8765")

# ── URL 감지 패턴 (Telegram hook과 동일) ──────────────────────────────────────
_URL_RE = re.compile(r'https?://[^\s<>"\']+')
_DOMAINS = (
    "youtube.com", "youtu.be", "instagram.com", "tiktok.com",
    "naver.com", "mk.co.kr", "chosun.com", "yna.co.kr", "hankyung.com",
    "edaily.co.kr", "sedaily.com", "newspim.com",
)

# job_id → (channel_id, thread_ts)  thread_ts는 원본 메시지 ts (reply용)
_CALLBACK_TARGETS: dict[str, tuple] = {}


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_content_urls(text: str) -> list[str]:
    """텍스트에서 콘텐츠 도메인 URL 목록 반환 (Telegram hook과 동일 로직)."""
    # Slack은 URL을 <https://...> 또는 <https://...|label> 형태로 감싼다 → 풀기
    text = re.sub(r'<(https?://[^|>]+)(?:\|[^>]*)?>',
                  lambda m: m.group(1), text or "")
    urls = _URL_RE.findall(text)
    return [u for u in urls if any(d in u for d in _DOMAINS)]


def _submit_url(url: str, callback_url: str) -> str | None:
    """bridge에 URL 작업 등록. 반환: job_id 또는 None (Telegram hook과 동일 로직)."""
    try:
        payload = json.dumps({
            "url": url,
            "lang": "ko",
            "publish_blog": True,
            "publish_shorts": True,
            "callback_url": callback_url,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{_BRIDGE_URL}/url-to-content",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            r = json.loads(resp.read())
        return r.get("job_id")
    except Exception as e:
        logger.warning(f"[slack_url_hook] bridge POST 실패: {e}")
        return None


# ── aiohttp callback server ────────────────────────────────────────────────────

async def _handle_callback_done(request):
    """bridge → Slack 콜백 수신 핸들러 (Telegram hook의 _handle_callback_done과 동일 구조)."""
    from aiohttp import web

    try:
        r = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid json")

    job_id = r.get("job_id") or ""
    target = _CALLBACK_TARGETS.pop(job_id, None)
    if not target:
        logger.warning(f"[slack_url_hook] callback {job_id}: 채널 정보 없음")
        return web.Response(status=200, text="no target")

    channel_id, thread_ts = target
    result = r.get("result") or {}
    status = r.get("status")

    if status == "done":
        blog = result.get("blog_url", "(없음)")
        yt = result.get("youtube_url") or result.get("youtube_error", "(영상 미생성)")
        text = f"✅ 완료\n📝 블로그: {blog}\n🎬 Shorts: {yt}"
    else:
        text = f"❌ 처리 실패: {r.get('error', '')[:200]}"

    await _post_slack_message(channel_id, text, thread_ts=thread_ts)
    return web.Response(status=200, text="ok")


async def _start_callback_server():
    """aiohttp callback 서버를 _CALLBACK_PORT에서 시작."""
    try:
        from aiohttp import web
    except ImportError:
        logger.warning("[slack_url_hook] aiohttp 미설치 — callback server 비활성")
        return

    app = web.Application()
    app.router.add_post("/url-content-done", _handle_callback_done)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", _CALLBACK_PORT)
    try:
        await site.start()
        logger.info(f"[slack_url_hook] callback server listening on :{_CALLBACK_PORT}")
    except Exception as e:
        logger.warning(f"[slack_url_hook] callback server 시작 실패: {e}")


# ── Slack API helpers ──────────────────────────────────────────────────────────

async def _post_slack_message(
    channel: str,
    text: str,
    thread_ts: str | None = None,
) -> None:
    """Slack chat.postMessage API 호출.

    slack_sdk 있으면 AsyncWebClient 사용, 없으면 urllib 직접 호출.
    thread_ts 지정 시 해당 메시지 스레드에 reply.
    """
    if not _BOT_TOKEN:
        logger.warning("[slack_url_hook] SLACK_BOT_TOKEN 미설정 — 메시지 전송 불가")
        return

    # slack_sdk AsyncWebClient 시도
    try:
        from slack_sdk.web.async_client import AsyncWebClient

        client = AsyncWebClient(token=_BOT_TOKEN)
        kwargs: dict = {"channel": channel, "text": text}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        await client.chat_postMessage(**kwargs)
        return
    except ImportError:
        pass  # 폴백으로 내려감
    except Exception as e:
        logger.warning(f"[slack_url_hook] slack_sdk send 실패: {e}")
        return

    # 폴백: urllib 직접 호출
    try:
        payload: dict = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_BOT_TOKEN}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as e:
        logger.warning(f"[slack_url_hook] Slack send 실패: {e}")


# ── Slack event handler ────────────────────────────────────────────────────────

async def _handle_slack_event(event: dict) -> None:
    """message 이벤트 처리: bot 멘션 확인 → URL 감지 → bridge 제출."""
    # bot 자신의 메시지는 무시
    if event.get("bot_id") or event.get("subtype"):
        return

    text = event.get("text") or ""
    channel = event.get("channel") or ""
    ts = event.get("ts") or ""

    # 멘션 필수: <@U...> 패턴이 없으면 무시
    if not re.search(r'<@[UW][A-Z0-9]+>', text):
        return

    content_urls = _extract_content_urls(text)
    if not content_urls:
        return

    url = content_urls[0]

    # 처리 시작 알림 (원본 ts를 thread_ts로 → 스레드 reply)
    await _post_slack_message(
        channel,
        f"⏳ URL 처리 시작... `{url[:60]}` (blog+Shorts 생성 ~10분 소요)",
        thread_ts=ts,
    )

    callback_url = f"http://127.0.0.1:{_CALLBACK_PORT}/url-content-done"
    job_id = _submit_url(url, callback_url)

    if job_id:
        _CALLBACK_TARGETS[job_id] = (channel, ts)
        logger.info(f"[slack_url_hook] job {job_id} 등록 url={url[:80]}")
    else:
        await _post_slack_message(
            channel,
            "❌ 브리지 호출 실패 — 잠시 후 다시 시도해주세요",
            thread_ts=ts,
        )


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """Slack URL hook 봇 실행 (Socket Mode).

    slack_sdk>=3.27 가 있으면 SocketModeClient 사용, 없으면 경고 후 종료.
    Telegram hook과 달리 Slack은 Socket Mode(App-Level Token)가 필요하므로
    HTTP polling 폴백 없음.
    """
    if not _ENABLED:
        logger.info("[slack_url_hook] SLACK_URL_HOOK_ENABLED != 1 — 종료")
        return

    if not _BOT_TOKEN:
        logger.warning("[slack_url_hook] SLACK_BOT_TOKEN 미설정 — 종료")
        return

    if not _APP_TOKEN:
        logger.warning("[slack_url_hook] SLACK_APP_TOKEN 미설정 — Socket Mode 불가, 종료")
        return

    try:
        from slack_sdk.socket_mode import SocketModeClient  # noqa: F401
    except ImportError:
        logger.warning(
            "[slack_url_hook] slack_sdk 미설치 — "
            "`pip install slack-sdk>=3.27` 후 재시도. 종료."
        )
        return

    _run_with_socket_mode()


def _run_with_socket_mode() -> None:
    """slack_sdk SocketModeClient (async) 방식으로 실행."""
    import asyncio
    import signal

    async def _socket_main():
        from slack_sdk.socket_mode.aiohttp import SocketModeClient
        from slack_sdk.web.async_client import AsyncWebClient

        await _start_callback_server()

        web_client = AsyncWebClient(token=_BOT_TOKEN)
        sm_client = SocketModeClient(
            app_token=_APP_TOKEN,
            web_client=web_client,
        )

        async def _on_event(client, req):
            """SocketModeClient events_api 핸들러."""
            from slack_sdk.socket_mode.response import SocketModeResponse

            # ACK 먼저
            await client.send_socket_mode_response(
                SocketModeResponse(envelope_id=req.envelope_id)
            )

            payload = req.payload or {}
            event = payload.get("event") or {}
            if event.get("type") == "message":
                await _handle_slack_event(event)

        sm_client.socket_mode_request_listeners.append(_on_event)

        logger.info("[slack_url_hook] Socket Mode 봇 시작")
        await sm_client.connect()

        stop_event = asyncio.Event()
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)

        await stop_event.wait()
        await sm_client.close()
        logger.info("[slack_url_hook] 봇 종료")

    asyncio.run(_socket_main())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
