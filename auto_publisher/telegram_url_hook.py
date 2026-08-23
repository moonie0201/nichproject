"""telegram_url_hook.py — Telegram URL→Content hook mirroring the Discord equivalent.

콘텐츠 URL이 Telegram 메시지에 올라오면 bridge_api로 보내서 blog+Shorts 자동 생성.
완료 시 bridge가 callback_url로 POST → 결과를 원래 chat에 Telegram 메시지로 전송.

환경변수:
  TELEGRAM_URL_HOOK_ENABLED=0   (기본 OFF — 1로 설정해야 동작)
  TELEGRAM_BOT_TOKEN=<token>    (ENABLED=1일 때 필수)
  TELEGRAM_CALLBACK_PORT=8901   (callback 수신 포트, 기본 8901)
  NICHPROJECT_BRIDGE_URL        (기본 http://172.17.0.1:8765)
"""

import json
import logging
import os
import re
import urllib.request

logger = logging.getLogger(__name__)

# ── 환경변수 ──────────────────────────────────────────────────────────────────
_ENABLED = os.getenv("TELEGRAM_URL_HOOK_ENABLED", "0").strip() == "1"
_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_CALLBACK_PORT = int(os.getenv("TELEGRAM_CALLBACK_PORT", "8901"))
_BRIDGE_URL = os.getenv("NICHPROJECT_BRIDGE_URL", "http://172.17.0.1:8765")

# ── URL 감지 패턴 (Discord hook과 동일) ────────────────────────────────────────
_URL_RE = re.compile(r'https?://[^\s<>"\']+')
_DOMAINS = (
    "youtube.com", "youtu.be", "instagram.com", "tiktok.com",
    "naver.com", "mk.co.kr", "chosun.com", "yna.co.kr", "hankyung.com",
    "edaily.co.kr", "sedaily.com", "newspim.com",
)

# job_id → (chat_id, reply_to_message_id)
_CALLBACK_TARGETS: dict[str, tuple] = {}


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_content_urls(text: str) -> list[str]:
    """텍스트에서 콘텐츠 도메인 URL 목록 반환 (Discord hook과 동일 로직)."""
    urls = _URL_RE.findall(text or "")
    return [u for u in urls if any(d in u for d in _DOMAINS)]


def _submit_url(url: str, callback_url: str) -> str | None:
    """bridge에 URL 작업 등록. 반환: job_id 또는 None (Discord hook과 동일 로직)."""
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
        logger.warning(f"[telegram_url_hook] bridge POST 실패: {e}")
        return None


# ── aiohttp callback server ────────────────────────────────────────────────────

async def _handle_callback_done(request):
    """bridge → Telegram 콜백 수신 핸들러 (Discord hook의 _handle_done과 동일 구조)."""
    from aiohttp import web

    try:
        r = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid json")

    job_id = r.get("job_id") or ""
    target = _CALLBACK_TARGETS.pop(job_id, None)
    if not target:
        logger.warning(f"[telegram_url_hook] callback {job_id}: 채널 정보 없음")
        return web.Response(status=200, text="no target")

    chat_id, reply_to_message_id = target
    result = r.get("result") or {}
    status = r.get("status")

    if status == "done":
        blog = result.get("blog_url", "(없음)")
        yt = result.get("youtube_url") or result.get("youtube_error", "(영상 미생성)")
        text = f"✅ 완료\n📝 블로그: {blog}\n🎬 Shorts: {yt}"
    else:
        text = f"❌ 처리 실패: {r.get('error', '')[:200]}"

    await _send_telegram_message(chat_id, text, reply_to_message_id=reply_to_message_id)
    return web.Response(status=200, text="ok")


async def _start_callback_server():
    """aiohttp callback 서버를 _CALLBACK_PORT에서 시작."""
    try:
        from aiohttp import web
    except ImportError:
        logger.warning("[telegram_url_hook] aiohttp 미설치 — callback server 비활성")
        return

    app = web.Application()
    app.router.add_post("/url-content-done", _handle_callback_done)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", _CALLBACK_PORT)
    try:
        await site.start()
        logger.info(f"[telegram_url_hook] callback server listening on :{_CALLBACK_PORT}")
    except Exception as e:
        logger.warning(f"[telegram_url_hook] callback server 시작 실패: {e}")


# ── Telegram API helpers ───────────────────────────────────────────────────────

async def _send_telegram_message(
    chat_id: int | str,
    text: str,
    reply_to_message_id: int | None = None,
) -> None:
    """Telegram sendMessage API 호출 (urllib 사용)."""
    if not _BOT_TOKEN:
        logger.warning("[telegram_url_hook] TELEGRAM_BOT_TOKEN 미설정 — 메시지 전송 불가")
        return
    try:
        payload: dict = {"chat_id": chat_id, "text": text}
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{_BOT_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as e:
        logger.warning(f"[telegram_url_hook] Telegram send 실패: {e}")


# ── Telegram message handler ──────────────────────────────────────────────────

async def _handle_telegram_message(message) -> None:
    """URL 감지 → bridge 제출 + target 등록."""
    text = (
        getattr(message, "text", None)
        or getattr(message, "caption", None)
        or ""
    )
    content_urls = _extract_content_urls(text)
    if not content_urls:
        return

    url = content_urls[0]
    chat_id = message.chat.id
    message_id = message.message_id

    # 처리 시작 알림
    await _send_telegram_message(
        chat_id,
        f"⏳ URL 처리 시작... `{url[:60]}` (blog+Shorts 생성 ~10분 소요)",
        reply_to_message_id=message_id,
    )

    callback_url = f"http://127.0.0.1:{_CALLBACK_PORT}/url-content-done"
    job_id = _submit_url(url, callback_url)

    if job_id:
        _CALLBACK_TARGETS[job_id] = (chat_id, message_id)
        logger.info(f"[telegram_url_hook] job {job_id} 등록 url={url[:80]}")
    else:
        await _send_telegram_message(
            chat_id,
            "❌ 브리지 호출 실패 — 잠시 후 다시 시도해주세요",
            reply_to_message_id=message_id,
        )


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """Telegram URL hook 봇 실행 (long polling).

    python-telegram-bot>=21 가 있으면 사용, 없으면 직접 HTTP long polling 폴백.
    """
    if not _ENABLED:
        logger.info("[telegram_url_hook] TELEGRAM_URL_HOOK_ENABLED != 1 — 종료")
        return

    if not _BOT_TOKEN:
        logger.warning("[telegram_url_hook] TELEGRAM_BOT_TOKEN 미설정 — 종료")
        return

    # python-telegram-bot>=21 시도
    try:
        from telegram.ext import Application, MessageHandler, filters

        _run_with_ptb(Application, MessageHandler, filters)
        return
    except ImportError:
        logger.info("[telegram_url_hook] python-telegram-bot 미설치 — HTTP polling 폴백 사용")

    # 폴백: stdlib urllib long polling
    _run_with_polling()


def _run_with_ptb(Application, MessageHandler, filters) -> None:  # noqa: N803
    """python-telegram-bot>=21 ApplicationBuilder 방식으로 실행."""
    import asyncio
    from telegram.ext import Application as _App

    async def _ptb_main():
        await _start_callback_server()

        app = _App.builder().token(_BOT_TOKEN).build()

        async def on_message(update, context):
            if update.message:
                await _handle_telegram_message(update.message)

        app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, on_message))

        logger.info("[telegram_url_hook] ptb 봇 시작 (long polling)")
        async with app:
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            # run until interrupted
            import signal
            stop_event = asyncio.Event()
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop_event.set)
            await stop_event.wait()
            await app.updater.stop()
            await app.stop()

    asyncio.run(_ptb_main())


def _run_with_polling() -> None:
    """stdlib urllib long polling 폴백 (python-telegram-bot 없을 때)."""
    import asyncio
    import signal
    import time

    _POLL_TIMEOUT = 30

    def _tg_get(method: str, **params) -> dict:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"https://api.telegram.org/bot{_BOT_TOKEN}/{method}?{qs}"
        with urllib.request.urlopen(url, timeout=_POLL_TIMEOUT + 5) as resp:
            return json.loads(resp.read())

    async def _polling_loop():
        await _start_callback_server()
        offset = 0
        logger.info("[telegram_url_hook] stdlib polling 봇 시작")

        stop_event = asyncio.Event()
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)

        while not stop_event.is_set():
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: _tg_get(
                        "getUpdates",
                        offset=offset,
                        timeout=_POLL_TIMEOUT,
                        allowed_updates="message",
                    ),
                )
                updates = result.get("result") or []
                for update in updates:
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    if not msg:
                        continue
                    # minimal duck-typed message proxy
                    class _Msg:
                        text = msg.get("text", "")
                        caption = msg.get("caption", "")
                        message_id = msg["message_id"]

                        class chat:
                            id = msg["chat"]["id"]

                    asyncio.ensure_future(_handle_telegram_message(_Msg()))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[telegram_url_hook] polling 오류: {e}")
                await asyncio.sleep(5)

    asyncio.run(_polling_loop())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
