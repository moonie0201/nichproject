"""쇼츠 첫 3초 임팩트 hook 자동 생성 (Claude CLI).

목적:
- 시청자 retention 결정 = 첫 3초
- 평이한 첫 문장을 충격적 카피로 rewrite

설계:
- claude -p subprocess 호출 → JSON 응답 → hook 문자열
- 실패 시 None (호출자가 원본 유지)
- USE_SONNET_HOOK=false 면 즉시 None

비용: Claude Code 구독 포함 (별도 청구 X), 호출 ~12초.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    return os.getenv("USE_SONNET_HOOK", "true").lower() not in ("false", "0", "no")


def _strip_codefence(text: str) -> str:
    """LLM 응답에서 ```json ... ``` 코드펜스 제거."""
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*\n?(.*)\n?```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def _build_prompt(title: str, summary: str, max_chars: int) -> str:
    return (
        f"한국 투자 쇼츠 영상 첫 3초 임팩트 hook 1문장 생성.\n"
        f"제목: {title}\n요약: {summary}\n\n"
        f"규칙:\n"
        f"- 한국어, {max_chars}자 이내\n"
        f"- 충격적 숫자 또는 손실 강조\n"
        f"- 의문문 또는 단정문\n"
        f"- 시청자가 즉시 멈추게 하는 문장\n\n"
        '응답: {"hook": "..."} JSON 만, 코드펜스 금지'
    )


def generate_hook(title: str, summary: str, max_chars: int = 35,
                  timeout_sec: int = 60) -> Optional[str]:
    """쇼츠 첫 3초 임팩트 hook 1문장 생성.

    Returns:
        str: hook 문자열 (성공)
        None: USE_SONNET_HOOK=false / CLI 실패 / JSON 파싱 실패 / 빈 hook
    """
    if not _is_enabled():
        return None

    prompt = _build_prompt(title, summary, max_chars)
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=timeout_sec,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"shorts_hook CLI 호출 실패: {e}")
        return None
    if result.returncode != 0:
        logger.warning(f"shorts_hook CLI rc={result.returncode}: {result.stderr[:200]}")
        return None

    cleaned = _strip_codefence(result.stdout or "")
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(f"shorts_hook JSON 파싱 실패: {cleaned[:200]}")
        return None

    hook = parsed.get("hook") if isinstance(parsed, dict) else None
    if not isinstance(hook, str):
        return None
    hook = hook.strip()
    if not hook:
        return None
    if len(hook) > max_chars:
        hook = hook[:max_chars]
    logger.info(f"shorts_hook 생성: {hook!r}")
    return hook
