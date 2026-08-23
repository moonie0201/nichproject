"""Claude Code CLI (`claude -p`) 로 롱폼 영상용 PPT 슬라이드 JSON 생성.

설계:
- Sonnet 호출 (subprocess) → JSON 배열 응답 → 파싱
- 파싱 실패 시 정적 fallback 슬라이드 생성 (영상 합성 절대 안 멈춤)
- USE_SONNET_SLIDES=false → 즉시 None 반환 (호출자 fallback)

Slide schema:
    {
        "title": str (15자 이내 권장),
        "bullets": list[str] (3-5개, 각 25자 이내),
        "accent_color": str (#hex, 그라디언트/강조에 사용),
    }
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


_DEFAULT_ACCENTS = ["#1E40AF", "#0EA5E9", "#DC2626", "#F59E0B", "#10B981",
                    "#7C3AED", "#EC4899", "#14B8A6"]


def _is_enabled() -> bool:
    return os.getenv("USE_SONNET_SLIDES", "true").lower() not in ("false", "0", "no")


def _build_prompt(title: str, summary: str, num_slides: int) -> str:
    return (
        f"한국 투자 블로그 '{title}' 의 롱폼 유튜브 영상용 PPT 슬라이드 "
        f"{num_slides}개를 JSON 배열로만 응답해. 각 슬라이드는 다음 형식:\n"
        '{"title": "제목 15자 이내", '
        '"bullets": ["핵심1 25자 이내", "핵심2", "핵심3"], '
        '"accent_color": "#hex"}\n\n'
        f"본문 요약: {summary}\n\n"
        "규칙:\n"
        "- 마크다운 코드펜스(```) 절대 금지, JSON 배열만 출력\n"
        "- 첫 슬라이드는 임팩트 있는 후크\n"
        "- 마지막 슬라이드는 행동 권유 (구독/알림 등)\n"
        "- 숫자는 구체적으로 (예: 920만원, 7.2%)\n"
        "- 한국어, 자연스러운 어투"
    )


def _strip_codefence(text: str) -> str:
    """LLM 응답에서 ```json ... ``` 코드펜스 제거."""
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*\n?(.*)\n?```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def _call_claude_cli(prompt: str, timeout: int = 60) -> Optional[str]:
    # "claude" 를 그대로 넘기면 n8n/cron 처럼 PATH 가 얕은 환경에서 FileNotFoundError 가 난다.
    # 그 결과 슬라이드가 조용히 플레이스홀더("포인트 1 / 상세 데이터")로 폴백돼
    # 쇼츠 러닝타임의 대부분이 빈 화면이 됐다. content_generator 의 리졸버를 재사용한다.
    from auto_publisher.content_generator import _resolve_cli

    try:
        result = subprocess.run(
            [_resolve_cli("claude"), "-p", prompt],
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"claude CLI 호출 실패: {e}")
        return None
    if result.returncode != 0:
        logger.warning(f"claude CLI 비정상 종료 (rc={result.returncode}): {result.stderr[:200]}")
        return None
    return result.stdout


def _fallback_slides(title: str, summary: str, num_slides: int) -> list[dict]:
    """정적 fallback — Sonnet 실패 시 요약문을 문장 단위로 잘라 슬라이드를 만든다.

    이전에는 "포인트 1 / 상세 데이터 / 차트 참고" 같은 빈 껍데기를 찍어서,
    폴백이 걸린 영상은 러닝타임 대부분이 정보 없는 화면이었다. 내용을 만들어낼
    수 없더라도 최소한 이미 가진 요약문은 화면에 띄운다.
    """
    logger.warning("슬라이드 정적 fallback 사용 — 화면에 요약문만 표시된다 (LLM 실패)")

    sentences = [s.strip() for s in re.split(r"(?<=[.!?。])\s+", summary or "") if s.strip()]
    slides = [{
        "title": title[:30],
        "bullets": [sentences[0][:60]] if sentences else [],
        "accent_color": _DEFAULT_ACCENTS[0],
    }]
    rest = sentences[1:]
    for i in range(1, num_slides):
        if not rest:
            break
        chunk, rest = rest[:2], rest[2:]
        slides.append({
            "title": title[:24],
            "bullets": [c[:60] for c in chunk],
            "accent_color": _DEFAULT_ACCENTS[i % len(_DEFAULT_ACCENTS)],
        })
    return slides


def generate_slides(title: str, summary: str, num_slides: int = 6) -> Optional[list[dict]]:
    """제목/요약 → PPT 슬라이드 N개 JSON 리스트.

    Returns:
        list[dict]: 슬라이드 리스트
        None: USE_SONNET_SLIDES=false 시 (호출자 fallback)
    """
    if not _is_enabled():
        return None

    prompt = _build_prompt(title, summary, num_slides)
    raw = _call_claude_cli(prompt)
    if raw is None:
        logger.warning("Sonnet CLI 호출 실패 → 정적 fallback 사용")
        return _fallback_slides(title, summary, num_slides)

    cleaned = _strip_codefence(raw)
    try:
        slides = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"Sonnet JSON 파싱 실패: {e} | raw={raw[:200]}")
        return _fallback_slides(title, summary, num_slides)

    if not isinstance(slides, list) or not slides:
        logger.warning(f"Sonnet 응답이 빈 배열 또는 비정상 타입: {type(slides)}")
        return _fallback_slides(title, summary, num_slides)

    # 각 슬라이드 schema 검증 + accent_color 보정
    valid = []
    for i, s in enumerate(slides):
        if not isinstance(s, dict) or "title" not in s:
            continue
        bullets = s.get("bullets") or []
        if not isinstance(bullets, list):
            bullets = [str(bullets)]
        accent = s.get("accent_color") or _DEFAULT_ACCENTS[i % len(_DEFAULT_ACCENTS)]
        if not (isinstance(accent, str) and accent.startswith("#")):
            accent = _DEFAULT_ACCENTS[i % len(_DEFAULT_ACCENTS)]
        valid.append({"title": str(s["title"])[:40],
                      "bullets": [str(b)[:60] for b in bullets[:5]],
                      "accent_color": accent})

    if not valid:
        return _fallback_slides(title, summary, num_slides)
    logger.info(f"Sonnet 슬라이드 {len(valid)}개 생성 완료")
    return valid
