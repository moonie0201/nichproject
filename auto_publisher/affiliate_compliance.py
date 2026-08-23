"""
Affiliate broker compliance — 자본시장법 §11 준수
- ko: FSC 인가 브로커만 허용
- en/ja/vi/id: global broker 허용
- 모든 lang: 미신고 외국 거래소 referral 차단
"""

from __future__ import annotations

import re

# ── 한국 FSC 인가 브로커 화이트리스트 ─────────────────────────────────────
KR_BROKERS: list[str] = [
    "키움증권",
    "토스증권",
    "한국투자증권",
    "미래에셋증권",
    "삼성증권",
    "NH투자증권",
    "KB증권",
    "신한투자증권",
    "하나증권",
    "카카오페이증권",
]

# ── 글로벌 브로커 허용 목록 (en/ja/vi/id) ─────────────────────────────────
GLOBAL_BROKERS: list[str] = [
    "eToro",
    "Webull",
    "Schwab",
    "Vanguard",
    "Fidelity",
    "Interactive Brokers",
    "Robinhood",
    "M1 Finance",
]

# ── 모든 언어에서 referral 완전 차단할 미신고 외국 거래소 ──────────────────
BLOCKED_CRYPTO_EXCHANGES: list[str] = [
    "Binance",
    "OKX",
    "Bybit",
    "Bitget",
    "MEXC",
    "KuCoin",
    "Gate.io",
    "Kraken",
]

# referral/가입 유도 인접 키워드
_REFERRAL_KW_KO = re.compile(
    r"가입|계좌\s*개설|추천|링크|레퍼럴|클릭|등록|referral|sign.?up|open.?account",
    re.IGNORECASE,
)
_REFERRAL_KW_GLOBAL = re.compile(
    r"sign.?up|refer|affiliate|open.?account|register|join|click|link",
    re.IGNORECASE,
)

# 인접 범위 (앞뒤 글자 수)
_PROXIMITY = 80


def get_broker_whitelist(lang: str) -> list[str]:
    """lang 에 따라 허용 브로커 목록 반환."""
    if lang == "ko":
        return list(KR_BROKERS)
    return list(GLOBAL_BROKERS)


def _windows(text: str, keyword: str, proximity: int) -> list[str]:
    """text 에서 keyword 주변 ±proximity 글자 슬라이스 목록 반환."""
    windows: list[str] = []
    for m in re.finditer(re.escape(keyword), text, re.IGNORECASE):
        start = max(0, m.start() - proximity)
        end = min(len(text), m.end() + proximity)
        windows.append(text[start:end])
    return windows


def is_broker_compliant(text: str, lang: str) -> tuple[bool, list[str]]:
    """
    생성된 본문 텍스트가 affiliate 컴플라이언스를 통과하는지 검사.

    Returns
    -------
    (ok: bool, violations: list[str])
        ok=True 이면 통과, False 이면 violations 에 문제 설명 포함.

    Rules
    -----
    1. 모든 lang: BLOCKED_CRYPTO_EXCHANGES + referral 인접 키워드 → 차단
       (BTC/ETH 콘텐츠 자체는 정보 형태로 허용 — 거래소 referral만 차단)
    2. lang=ko: KR_BROKERS 외 브로커 + 가입/계좌개설 인접 → 차단
    """
    violations: list[str] = []
    referral_re = _REFERRAL_KW_KO if lang == "ko" else _REFERRAL_KW_GLOBAL

    # Rule 1 — 미신고 거래소 referral (모든 lang)
    for exchange in BLOCKED_CRYPTO_EXCHANGES:
        for window in _windows(text, exchange, _PROXIMITY):
            if _REFERRAL_KW_KO.search(window) or _REFERRAL_KW_GLOBAL.search(window):
                violations.append(
                    f"차단된 거래소 referral: '{exchange}' 주변에 가입/추천 표현 감지"
                )
                break  # exchange 당 1회만 보고

    # Rule 2 — ko 전용: non-whitelist 브로커 + 가입 인접
    if lang == "ko":
        # GLOBAL_BROKERS 중 ko 에서 발견되면 차단
        for broker in GLOBAL_BROKERS:
            for window in _windows(text, broker, _PROXIMITY):
                if referral_re.search(window):
                    violations.append(
                        f"한국어 콘텐츠에 미인가 외국 브로커 가입 유도: '{broker}'"
                    )
                    break

    return (len(violations) == 0, violations)


def build_broker_prompt_block(lang: str) -> str:
    """LLM 프롬프트에 삽입할 브로커 컴플라이언스 지시 블록 반환."""
    whitelist = get_broker_whitelist(lang)
    blocked = ", ".join(BLOCKED_CRYPTO_EXCHANGES)

    if lang == "ko":
        allowed_str = ", ".join(whitelist)
        return (
            "\n[브로커/거래소 컴플라이언스 — 자본시장법 §11]\n"
            f"- 한국어 콘텐츠: 다음 FSC 인가 브로커만 언급 가능: {allowed_str}\n"
            "- 외국 브로커(eToro, Webull, Schwab, Interactive Brokers 등) 언급·추천·링크 절대 금지\n"
            f"- 모든 언어 공통: 다음 거래소 referral/추천/가입 링크 절대 금지: {blocked}\n"
            "- BTC/ETH 등 가상자산 정보/분석 자체는 허용. 특정 거래소 가입 유도만 금지.\n"
        )
    else:
        allowed_str = ", ".join(whitelist)
        return (
            "\n[Broker/Exchange Compliance]\n"
            f"- Allowed brokers for this language: {allowed_str}\n"
            f"- Never promote, link, or recommend these unregistered exchanges: {blocked}\n"
            "- BTC/ETH informational content is allowed; exchange referral/sign-up links are not.\n"
        )
