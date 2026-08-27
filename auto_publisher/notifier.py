"""
Discord Webhook 알림 — 발행 완료 후 embed 전송
DISCORD_WEBHOOK_URL 환경변수 필요
"""

import json
import logging
import os
from datetime import date
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

SIGNAL_EMOJI = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
LANG_LABELS = {
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
    "vi": "Tiếng Việt",
    "id": "Bahasa Indonesia",
}


def notify_discord(
    title: str,
    url: str,
    ticker: str = "",
    signal: str = "",
    description: str = "",
    lang: str = "ko",
    post_type: str = "blog",  # "blog" | "analysis"
) -> bool:
    if not DISCORD_WEBHOOK_URL:
        logger.debug("DISCORD_WEBHOOK_URL 없음, 알림 건너뜀")
        return False

    base_url = "https://investiqs.net"
    full_url = f"{base_url}{url}" if url.startswith("/") else url
    today = date.today().strftime("%Y-%m-%d")
    lang_label = LANG_LABELS.get(lang, lang)

    if post_type == "analysis" and ticker:
        emoji = SIGNAL_EMOJI.get(signal.upper(), "📊")
        embed_title = f"{emoji} [{ticker}] {signal.upper()} — AI 투자 분석"
        color = 0x2ECC71 if signal.upper() == "BUY" else (0xE74C3C if signal.upper() == "SELL" else 0xF1C40F)
    else:
        embed_title = f"📝 새 포스트 발행"
        color = 0x3498DB

    embed = {
        "title": embed_title,
        "description": f"**{title}**\n{description[:200] if description else ''}",
        "url": full_url,
        "color": color,
        "fields": [
            {"name": "언어", "value": lang_label, "inline": True},
            {"name": "날짜", "value": today, "inline": True},
        ],
        "footer": {"text": "InvestIQs — investiqs.net"},
    }
    if ticker:
        embed["fields"].insert(0, {"name": "티커", "value": ticker, "inline": True})

    # urllib 로 보내면 Discord 앞단 Cloudflare 가 403 을 돌려준다 — 같은
    # 페이로드·헤더로 curl/requests 는 204 다. urllib 의 TLS 지문이 봇으로
    # 분류되는 알려진 케이스라, requests 로 보낸다. (2026-08-28 실측)
    try:
        import requests
        resp = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"embeds": [embed]},
            headers={"User-Agent": "InvestIQsBot/1.0"},
            timeout=10,
        )
        if resp.status_code in (200, 204):
            logger.info(f"Discord 알림 전송 완료: {title}")
            return True
        logger.warning(f"Discord 응답 {resp.status_code}: {resp.text[:120]}")
        return False
    except Exception as e:
        logger.warning(f"Discord 알림 실패: {e}")
        return False
