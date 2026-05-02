"""
YouTube 영상 대사 생성 — 블로그 → 롱폼 + 쇼츠 대사 변환
- 롱폼: 10~15분 (~3000자, 7~10 챕터, mid-roll 광고 슬롯 포함)
- 쇼츠: 60초 (~300자, hook 1포인트, 롱폼 링크 CTA)
"""

import hashlib
import json
import logging
import os
import re
import urllib.request
from pathlib import Path

from auto_publisher.content_generator import _call_llm, _parse_json_response
from auto_publisher.research_pack import build_research_pack

logger = logging.getLogger(__name__)
_NUMBER_PATTERN = re.compile(r"(?:\$?\d[\d,]*\.?\d*%?|[0-9]+년|[0-9]+개월|[0-9]+배)")
_QUALITY_TARGET_SCORE = 90
_RULE_TARGET_SCORE = 95
_VIDEO_THINK_MODE = os.getenv("OLLAMA_THINK_MODE", "script").strip().lower()
_VIDEO_SCRIPT_MAX_ITER = int(os.getenv("VIDEO_SCRIPT_MAX_ITER", "1"))

# --- 스크립트 캐시 설정 ---
CACHE_DIR = Path(os.getenv("WORKSPACE", "/home/mh/ocstorage/workspace/nichproject")) / ".omc" / "script_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(slug: str, lang: str, kind: str) -> Path:
    return CACHE_DIR / f"{slug}_{lang}_{kind}.json"


# --- Video LLM 백엔드 설정 ---
LLM_VIDEO_BACKEND = os.getenv("LLM_VIDEO_BACKEND", "openrouter").strip().lower()
VIDEO_LLM_MODEL = os.getenv("VIDEO_LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
VIDEO_LLM_TIMEOUT_SEC = int(os.getenv("VIDEO_LLM_TIMEOUT_SEC", "60"))
_OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# 환경변수 VIDEO_LLM_MODELS_FALLBACK (콤마 구분) 또는 하드코딩 기본 리스트
def _build_fallback_models() -> list[str]:
    env_fallback = os.getenv("VIDEO_LLM_MODELS_FALLBACK", "").strip()
    if env_fallback:
        return [m.strip() for m in env_fallback.split(",") if m.strip()]
    return [
        os.getenv("VIDEO_LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "meta-llama/llama-3.2-3b-instruct:free",
    ]

FALLBACK_MODELS = _build_fallback_models()


def _call_openrouter(prompt: str) -> str:
    """OpenRouter HTTP API 직접 호출 — 429/5xx 시 다음 무료 모델로 순차 폴백."""
    if not _OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY 미설정")
    last_exc: Exception | None = None
    for model in FALLBACK_MODELS:
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_OPENROUTER_API_KEY}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=VIDEO_LLM_TIMEOUT_SEC) as resp:
                data = json.loads(resp.read())
            if "choices" not in data:
                _err = data.get("error", {})
                raise RuntimeError(f"OpenRouter error: {_err.get('message', str(data))[:200]}")
            logger.info("[openrouter] 모델 성공: %s", model)
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504):
                logger.warning("[openrouter] 모델 %s HTTP %d, 다음 모델 시도", model, exc.code)
                last_exc = exc
                continue
            raise
        except Exception as exc:
            logger.warning("[openrouter] 모델 %s 오류: %s, 다음 모델 시도", model, exc)
            last_exc = exc
            continue
    raise RuntimeError(f"OpenRouter 모든 모델 실패: {last_exc}") from last_exc


def _strip_html(html: str) -> str:
    """HTML 태그 제거 — 본문 텍스트만 추출"""
    text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_blog_text(blog_md_path: Path) -> tuple[str, str, list[str]]:
    """블로그 .md 파일에서 (title, body_text, chart_paths) 추출"""
    raw = blog_md_path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return "", raw, []
    front, body = parts[1], parts[2]

    title_match = re.search(r'^title:\s*"(.+)"', front, re.MULTILINE)
    title = title_match.group(1) if title_match else blog_md_path.stem

    chart_paths = re.findall(r'(/images/[^\s")]+\.png)', body)
    body_text = _strip_html(body)

    return title, body_text, chart_paths


def _read_blog_sections(blog_md_path: Path) -> tuple[str, str]:
    raw = blog_md_path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return "", raw
    return parts[1], parts[2]


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    chunks = re.split(r"(?<=[.!?。다요\.])\s+|(?<=\))\s+", normalized)
    return [chunk.strip(" -") for chunk in chunks if chunk.strip()]


def _pick_sentences(sentences: list[str], limit: int, *, risk: bool = False) -> list[str]:
    keywords = ("리스크", "위험", "반면", "하지만", "다만", "낙폭", "변동성", "금리", "실적", "경고")

    def score(sentence: str) -> tuple[int, int, int]:
        has_number = len(_pick_key_numbers(sentence, limit=3))
        risk_score = sum(1 for kw in keywords if kw in sentence)
        length_score = min(len(sentence), 120)
        if risk:
            return (risk_score * 4 + has_number, has_number, length_score)
        return (has_number * 4 + risk_score, risk_score, length_score)

    ranked = sorted(sentences, key=score, reverse=True)
    picked: list[str] = []
    for sentence in ranked:
        if sentence in picked:
            continue
        picked.append(sentence)
        if len(picked) >= limit:
            break
    return picked


def _point_priority(sentence: str, idx: int) -> str:
    if any(token in sentence for token in ("리스크", "위험", "다만", "변동성", "금리", "틀릴 수")):
        return "risk"
    if idx == 0:
        return "hook"
    if idx >= 4:
        return "cta"
    return "body"


def _clean_display_value(value: str) -> str:
    tokens = _pick_key_numbers(value, limit=2)
    if tokens:
        cleaned = []
        for token in tokens:
            token = token.rstrip(",")
            if token and token not in cleaned:
                cleaned.append(token)
        return ", ".join(cleaned)
    return _pick_focus_line(value, limit=18)


def _spoken_value(value: str) -> str:
    text = value.replace("$", "")
    text = text.replace("%", "퍼센트")
    # 소수점 3자리 이상 숫자 → 반올림 (TTS 긴 숫자 방지)
    def _round_decimal(m: re.Match) -> str:
        try:
            return str(round(float(m.group()), 1))
        except ValueError:
            return m.group()
    text = re.sub(r"\d+\.\d{3,}", _round_decimal, text)
    return re.sub(r"\s+", " ", text).strip()


def build_video_data_pack(blog_md_path: Path, blog_url: str = "") -> dict:
    title, body_text, chart_paths = _extract_blog_text(blog_md_path)
    front, body_md = _read_blog_sections(blog_md_path)
    headings = re.findall(r"^#{2,3}\s+(.+)$", body_md, flags=re.MULTILINE)
    sentences = _split_sentences(body_text)
    key_points = _pick_sentences(sentences, limit=4)
    risk_points = _pick_sentences(sentences, limit=2, risk=True)

    key_numbers: list[str] = []
    for sentence in key_points + risk_points:
        for token in _pick_key_numbers(sentence, limit=3):
            if token not in key_numbers:
                key_numbers.append(token)
            if len(key_numbers) >= 6:
                break
        if len(key_numbers) >= 6:
            break

    source_data_points = []
    seen_points: set[tuple[str, str]] = set()
    for idx, sentence in enumerate(key_points + risk_points):
        numbers = _pick_key_numbers(sentence, limit=2)
        label = headings[min(idx, len(headings) - 1)] if headings else f"핵심 포인트 {idx + 1}"
        value = ", ".join(numbers) if numbers else _pick_focus_line(sentence, limit=24)
        display_value = _clean_display_value(value)
        point_key = (display_value, _pick_focus_line(sentence, limit=60))
        if point_key in seen_points:
            continue
        seen_points.add(point_key)
        source_data_points.append(
            {
                "label": _pick_focus_line(label, limit=28),
                "value": value,
                "display_value": display_value,
                "spoken_value": _spoken_value(display_value),
                "anchor_sentence": _pick_focus_line(sentence, limit=88),
                "priority": _point_priority(sentence, idx),
                "confidence": "exact" if numbers else "inferred",
                "context": _pick_focus_line(sentence, limit=88),
            }
        )
    if not source_data_points:
        source_data_points.append(
            {
                "label": "핵심 요약",
                "value": title,
                "display_value": _pick_focus_line(title, limit=18),
                "spoken_value": _pick_focus_line(title, limit=18),
                "anchor_sentence": _pick_focus_line(body_text, limit=88),
                "priority": "hook",
                "confidence": "inferred",
                "context": _pick_focus_line(body_text, limit=88),
            }
        )

    research_pack = build_research_pack(
        title=title or blog_md_path.stem,
        headings=headings[:6],
        key_points=key_points,
        risk_points=risk_points,
        source_data_points=source_data_points[:6],
        chart_paths=chart_paths,
        blog_url=blog_url,
    )

    return {
        "title": title or blog_md_path.stem,
        "body_text": body_text,
        "frontmatter": front,
        "headings": headings[:6],
        "chart_paths": chart_paths,
        "key_numbers": key_numbers,
        "key_points": key_points,
        "risk_points": risk_points,
        "source_data_points": source_data_points[:6],
        "research_pack": research_pack,
        "blog_url": blog_url,
        "body_excerpt": body_text[:6000],
    }


def _replace_for_tts(text: str, replacements: dict[str, str]) -> str:
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def _pick_key_numbers(text: str, limit: int = 4) -> list[str]:
    seen: list[str] = []
    for match in _NUMBER_PATTERN.findall(text):
        token = match.strip()
        if token and token not in seen:
            seen.append(token)
        if len(seen) >= limit:
            break
    return seen


def _pick_focus_line(text: str, limit: int = 68) -> str:
    cleaned = re.sub(r"\[[^\]]+\]", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _build_visual_beats(script: dict, source_data_points: list[dict] | None = None) -> list[dict]:
    beats: list[dict] = []
    for chapter in script.get("chapters", []):
        text = chapter.get("text", "")
        numbers = _pick_key_numbers(text, limit=2)
        if not numbers and source_data_points:
            point = source_data_points[min(len(beats), len(source_data_points) - 1)]
            numbers = _pick_key_numbers(point.get("value", ""), limit=2)
        beats.append(
            {
                "title": chapter.get("title", ""),
                "focus": _pick_focus_line(text, limit=72),
                "numbers": numbers,
            }
        )
    return beats


def _build_fallback_visual_plan(
    script: dict,
    title: str,
    blog_url: str,
    is_short: bool,
    source_data_points: list[dict] | None = None,
) -> list[dict]:
    beats = _build_visual_beats(script, source_data_points=source_data_points)
    research_scenes = script.get("research_pack", {}).get("visual_scenes", []) if isinstance(script.get("research_pack"), dict) else []
    cards: list[dict] = []
    if is_short:
        short_point = source_data_points[0] if source_data_points else {}
        cards.append(
            {
                "headline": _pick_focus_line(title, limit=38),
                "subhead": "3초 안에 핵심부터 짚습니다",
                "accent": (
                    short_point.get("value")
                    or (beats[0]["numbers"][0] if beats and beats[0]["numbers"] else "핵심 데이터")
                ),
                "card_type": "number",
            }
        )
        if beats:
            point = source_data_points[min(1, len(source_data_points) - 1)] if source_data_points else {}
            cards.append(
                {
                    "headline": _pick_focus_line(point.get("context") or beats[min(1, len(beats) - 1)]["focus"], limit=34),
                    "subhead": "데이터가 말하는 한 가지 포인트",
                    "accent": (
                        point.get("value")
                        or (beats[min(1, len(beats) - 1)]["numbers"][0] if beats[min(1, len(beats) - 1)]["numbers"] else "숫자로 확인")
                    ),
                    "card_type": "comparison",
                }
            )
        cards.append(
            {
                "headline": "전체 분석은 본 영상으로",
                "subhead": _pick_focus_line(blog_url.replace("https://", ""), limit=38),
                "accent": "InvestIQs",
                "card_type": "cta",
            }
        )
        return cards

    cards.append(
        {
            "headline": _pick_focus_line(title, limit=52),
            "subhead": _pick_focus_line(
                script.get("research_pack", {}).get("core_thesis", "")
                if isinstance(script.get("research_pack"), dict)
                else "핵심 숫자와 리스크를 순서대로 정리합니다",
                limit=70,
            ),
            "accent": (
                source_data_points[0].get("display_value") or source_data_points[0].get("value")
                if source_data_points
                else (beats[0]["numbers"][0] if beats and beats[0]["numbers"] else "Long-form")
            ),
            "card_type": "thesis",
        }
    )
    for scene in research_scenes[:3]:
        cards.append(
            {
                "headline": scene.get("headline") or "리서치 포인트",
                "subhead": scene.get("supporting_text") or "소스 기반 근거를 확인합니다",
                "accent": ", ".join(scene.get("numbers", [])[:2]) or "Source-grounded",
                "card_type": scene.get("scene_type", "market_dashboard"),
            }
        )
    if beats:
        lead = beats[min(1, len(beats) - 1)]
        point = source_data_points[min(1, len(source_data_points) - 1)] if source_data_points else {}
        cards.append(
            {
                "headline": _pick_focus_line(point.get("context") or lead["focus"], limit=58),
                "subhead": "시장 통념보다 데이터 흐름을 우선합니다",
                "accent": (point.get("display_value") or point.get("value") or (lead["numbers"][0] if lead["numbers"] else "데이터 포인트")),
                "card_type": "comparison",
            }
        )
    if len(beats) > 2:
        risk = beats[-2]
        risk_point = source_data_points[-1] if source_data_points else {}
        cards.append(
            {
                "headline": _pick_focus_line(risk_point.get("context") or risk["focus"], limit=58),
                "subhead": "틀릴 수 있는 구간과 변수도 함께 확인합니다",
                "accent": (risk_point.get("display_value") or risk_point.get("value") or (risk["numbers"][0] if risk["numbers"] else "리스크 체크")),
                "card_type": "risk",
            }
        )
    cards.append(
        {
            "headline": "핵심 요약과 다음 액션",
            "subhead": "전체 데이터 해석은 블로그와 롱폼에서 이어집니다",
            "accent": "InvestIQs Research",
            "card_type": "cta",
        }
    )
    return cards


def _normalize_chapters(chapters: list[dict], defaults: list[tuple[int, str]]) -> list[dict]:
    normalized = []
    for idx, chapter in enumerate(chapters):
        start_sec = chapter.get("start_sec")
        if start_sec is None:
            start_sec = defaults[min(idx, len(defaults) - 1)][0]
        title = chapter.get("title") or defaults[min(idx, len(defaults) - 1)][1]
        normalized.append(
            {
                "start_sec": start_sec,
                "title": title,
                "text": chapter.get("text", "").strip(),
                "chart": chapter.get("chart"),
            }
        )
    return normalized


def _postprocess_long_script(
    result: dict,
    title: str,
    blog_url: str,
    lang: str,
    source_data_points: list[dict] | None = None,
    quality_report: dict | None = None,
) -> dict:
    replacements = {
        "제가": "이 분석에서는",
        "저는": "이 분석은",
        "나는": "이 관점은",
        "내가": "이 분석이",
        "결론적으로": "핵심은",
        "다음과 같이": "이 흐름을 보면",
        "앞서 살펴본 바와 같이": "이미 확인한 흐름처럼",
    }

    defaults = [
        (0, "Hook"),
        (45, "핵심 프레임"),
        (150, "데이터 근거"),
        (300, "반론과 리스크"),
        (540, "정리와 CTA"),
    ]
    result["chapters"] = _normalize_chapters(result.get("chapters", []), defaults)
    for chapter in result["chapters"]:
        chapter["text"] = _replace_for_tts(chapter.get("text", ""), replacements)

    if result["chapters"]:
        first = result["chapters"][0]
        if "끝까지 보면" not in first["text"]:
            first["text"] = f"{first['text']} 끝까지 보면, 데이터가 어디서 갈리는지 알게 됩니다.".strip()

        last = result["chapters"][-1]
        if "전체 데이터" not in last["text"] and "블로그" not in last["text"]:
            last["text"] = f"{last['text']} 전체 데이터 해석은 블로그와 본문 링크에서 이어서 확인할 수 있습니다.".strip()

    combined = " ".join(ch["text"] for ch in result["chapters"])
    if "틀릴 수 있는 경우" not in combined and len(result["chapters"]) >= 2:
        result["chapters"][-2]["text"] = (
            f"{result['chapters'][-2]['text']} 다만 이 관점이 틀릴 수 있는 경우는, "
            "실적과 금리 변수가 동시에 뒤집히는 구간입니다."
        ).strip()

    result["format"] = "longform_broadcast"
    result["hook_text"] = result["chapters"][0]["text"] if result["chapters"] else title
    result["cta_text"] = result["chapters"][-1]["text"] if result["chapters"] else title
    result["visual_beats"] = _build_visual_beats(result, source_data_points=source_data_points)
    result["fallback_visual_plan"] = _build_fallback_visual_plan(
        result, title, blog_url, is_short=False, source_data_points=source_data_points
    )
    result["quality_report"] = quality_report or {"score": 0, "issues": [], "regenerated": False}
    result["source_data_points"] = source_data_points or []
    return result


def _postprocess_short_script(
    result: dict,
    long_title: str,
    blog_url: str,
    lang: str,
    source_data_points: list[dict] | None = None,
    quality_report: dict | None = None,
) -> dict:
    replacements = {
        "제가": "이 포인트는",
        "저는": "핵심은",
        "나는": "이 관점은",
        "내가": "이 분석이",
        "결론적으로": "핵심은",
    }
    defaults = [
        (0, "Hook"),
        (3, "핵심"),
        (50, "CTA"),
    ]
    result["chapters"] = _normalize_chapters(result.get("chapters", []), defaults)
    for chapter in result["chapters"]:
        chapter["text"] = _replace_for_tts(chapter.get("text", ""), replacements)

    if len(result["chapters"]) < 3:
        while len(result["chapters"]) < 3:
            idx = len(result["chapters"])
            start_sec, title = defaults[idx]
            result["chapters"].append({"start_sec": start_sec, "title": title, "text": "", "chart": None})

    hook, body, cta = result["chapters"][0], result["chapters"][1], result["chapters"][2]
    primary_point = source_data_points[0] if source_data_points else {}
    secondary_point = source_data_points[min(1, len(source_data_points) - 1)] if source_data_points else {}
    risk_point = source_data_points[-1] if source_data_points else {}
    if "숫자" not in hook["text"] and not _pick_key_numbers(hook["text"], limit=1):
        hook_seed = primary_point.get("value") or "핵심 숫자 하나"
        hook["text"] = f"{hook_seed}. {hook['text']} 핵심 숫자 하나만 먼저 보면, 판단 기준이 확 달라집니다.".strip()
    if "끝까지 보면" not in hook["text"]:
        hook["text"] = f"{hook['text']} 끝까지 보면, 이 숫자의 함정까지 한 번에 정리됩니다.".strip()
    source_body = []
    if primary_point:
        source_body.append(
            f"{primary_point.get('label', '핵심 데이터')}는 {primary_point.get('spoken_value') or primary_point.get('display_value') or primary_point.get('value', '')}입니다. "
            f"{primary_point.get('anchor_sentence') or primary_point.get('context', '')}"
        )
    if secondary_point and secondary_point != primary_point:
        source_body.append(
            f"여기에 {secondary_point.get('label', '두 번째 포인트')} {secondary_point.get('spoken_value') or secondary_point.get('display_value') or secondary_point.get('value', '')}를 같이 보면, "
            f"{secondary_point.get('anchor_sentence') or secondary_point.get('context', '')}"
        )
    if risk_point and risk_point not in (primary_point, secondary_point):
        source_body.append(
            f"다만 리스크는 {risk_point.get('spoken_value') or risk_point.get('display_value') or risk_point.get('value', '')} 쪽입니다. "
            f"{risk_point.get('anchor_sentence') or risk_point.get('context', '')}"
        )
    source_body_text = " ".join(_pick_focus_line(line, limit=110) for line in source_body if line.strip())
    if source_body_text:
        body["text"] = source_body_text.strip()
    elif len(" ".join(ch["text"] for ch in result["chapters"])) < 220:
        body["text"] = (
            f"{body['text']} 시장에서는 단순한 방향성만 보지만, 실제로는 수익률과 변동성, "
            "그리고 리스크 구간을 같이 봐야 이 숫자의 의미가 선명해집니다. "
            "특히 최근 1년 수익률 하나만 볼 게 아니라, 낙폭이 얼마나 깊었는지도 함께 봐야 "
            "숫자가 과장인지 아닌지 구분할 수 있습니다."
        ).strip()
    if "전체 분석" not in cta["text"]:
        cta_seed = risk_point.get("spoken_value") or risk_point.get("display_value") or risk_point.get("value") or risk_point.get("label") or "변동성 구간"
        cta["text"] = f"{cta_seed}까지 포함한 전체 분석은 본 영상과 블로그 링크에서 바로 이어집니다.".strip()

    title = result.get("title", long_title[:50]).strip()
    if "#shorts" not in title.lower():
        title = f"{title} #shorts"
    result["title"] = title
    result["format"] = "shorts_reveal"
    result["hook_text"] = hook["text"]
    result["cta_text"] = cta["text"]
    result["visual_beats"] = _build_visual_beats(result, source_data_points=source_data_points)
    result["fallback_visual_plan"] = _build_fallback_visual_plan(
        result, long_title, blog_url, is_short=True, source_data_points=source_data_points
    )
    result["quality_report"] = quality_report or {"score": 0, "issues": [], "regenerated": False}
    result["source_data_points"] = source_data_points or []
    return result


def _format_source_points(source_data_points: list[dict]) -> str:
    if not source_data_points:
        return "  - (핵심 데이터 포인트 없음)"
    return "\n".join(
        f"  - {point.get('label', '포인트')}: {point.get('display_value') or point.get('value', '')}"
        f" / priority={point.get('priority', 'body')}"
        f" / confidence={point.get('confidence', 'inferred')}"
        f" / {point.get('anchor_sentence') or point.get('context', '')}"
        for point in source_data_points[:6]
    )


def _build_long_script_prompt(data_pack: dict, lang: str) -> str:
    title = data_pack["title"]
    body_excerpt = data_pack["body_excerpt"]
    chart_list = "\n".join(f"  · {c}" for c in data_pack["chart_paths"][:7]) or "  · (차트 없음)"
    source_points = _format_source_points(data_pack.get("source_data_points", []))
    headings = "\n".join(f"  - {h}" for h in data_pack.get("headings", [])[:6]) or "  - (소제목 없음)"
    risk_points = "\n".join(f"  - {line}" for line in data_pack.get("risk_points", [])[:3]) or "  - (리스크 포인트 없음)"
    research_pack = json.dumps(data_pack.get("research_pack", {}), ensure_ascii=False, indent=2)
    forbidden = '"매수하세요", "사야 한다", "추천", "투자 권유", "Buy", "Sell", "지금 사도 될까"'
    if lang != "ko":
        forbidden = '"Buy now", "Should you buy", "Recommend", "Invest now"'

    return f"""You are a Korean financial YouTube creator producing a premium 10~15 min analysis video.
Convert the blog post below into a long-form video narration script.

[Blog Title]
{title}

[Blog Body Excerpt]
{body_excerpt}

[Video Data Pack]
{source_points}

[Headings]
{headings}

[Risk / Counterpoints]
{risk_points}

[Research Pack]
{research_pack}

[Available Charts]
{chart_list}

[CRITICAL RULES]
- Output language: {"한국어" if lang == "ko" else "English"}
- Hook → 핵심 주장 → 데이터 근거 → 반론/리스크 → 실행 포인트 → CTA 구조
- 3인칭 전문 애널리스트 톤 (InvestIQs Research). 1인칭 금지.
- Hook 첫 30초에는 "끝까지 보면" 류의 시청 유인 문구 포함
- 시장 통념과 다른 contrarian angle 1개 필수
- 이 관점이 틀릴 수 있는 경우 1개 필수
- 숫자 근거는 위 Video Data Pack을 우선 활용
- Research Pack의 claims/counterpoints/visual_scenes를 각 챕터에 반영
- 각 챕터는 말뿐인 설명이 아니라 화면에 표시할 데이터/리스크/타임라인 단서를 포함
- 절대 금지 표현: {forbidden}
- 교과서 문체 금지: "다음과 같이", "결론적으로", "앞서 살펴본 바와 같이"
- 마지막 1분: 핵심 요약 + 실행 포인트 + 블로그 링크 CTA

[Output: pure JSON only, no markdown]
{{
  "title": "60자 이내 SEO 제목",
  "description": "1500자 이내 설명란",
  "tags": ["태그1", "태그2"],
  "chapters": [
    {{"start_sec": 0, "title": "Hook", "text": "30초 분량 대사", "chart": null}},
    {{"start_sec": 45, "title": "핵심 프레임", "text": "...", "chart": null}},
    {{"start_sec": 150, "title": "데이터 근거", "text": "...", "chart": "/images/.../chart.png"}},
    {{"start_sec": 300, "title": "반론과 리스크", "text": "...", "chart": null}},
    {{"start_sec": 420, "title": "실행 포인트", "text": "...", "chart": null}},
    {{"start_sec": 540, "title": "정리와 CTA", "text": "...", "chart": null}}
  ],
  "mid_roll_marks_sec": [240, 480, 720],
  "total_duration_sec": 720,
  "hashtags": ["#ETF", "#투자분석"]
}}"""


def _build_short_script_prompt(long_script: dict, blog_url: str, lang: str = "ko") -> str:
    long_title = long_script.get("title", "")
    source_points = _format_source_points(long_script.get("source_data_points", []))
    forbidden = '"매수하세요", "사야 한다", "추천", "투자 권유", "Buy", "Sell"'
    if lang != "ko":
        forbidden = '"Buy now", "Recommend"'

    return f"""You are creating a 60-second Korean YouTube SHORTS script from exact data points.

[Long-form Title]
{long_title}

[Source Data Points]
{source_points}

[Long-form URL]
{blog_url}

[CRITICAL RULES]
- Output language: {"한국어" if lang == "ko" else "English"}
- Use at least two confidence=exact data points verbatim via display_value or spoken_value.
- Sentence 1: one exact number.
- Sentence 2: one interpretation of that number.
- Sentence 3: one risk or reversal.
- Final sentence: information CTA with "전체 분석".
- Do not add facts that are absent from Source Data Points.
- 절대 금지: {forbidden}

[Output: pure JSON only]
{{
  "title": "쇼츠 제목 (60자, #shorts 포함)",
  "description": "쇼츠 설명 (롱폼 링크 포함)",
  "tags": ["태그"],
  "chapters": [
    {{"start_sec": 0, "title": "Hook", "text": "0-3초 hook", "chart": null}},
    {{"start_sec": 3, "title": "핵심", "text": "3-50초 본문", "chart": "/images/.../chart.png"}},
    {{"start_sec": 50, "title": "CTA", "text": "50-60초 안내", "chart": null}}
  ],
  "mid_roll_marks_sec": [],
  "total_duration_sec": 60,
  "hashtags": ["#shorts", "#ETF분석"]
}}"""


def _video_llm_json(prompt: str, context: str) -> dict:
    """Call LLM for video JSON — OpenRouter HTTP API 우선, 실패 시 CLI 폴백."""
    if LLM_VIDEO_BACKEND == "openrouter":
        try:
            logger.info("[%s] LLM_START backend=openrouter model=%s", context, VIDEO_LLM_MODEL)
            raw = _call_openrouter(prompt)
            logger.info("[%s] LLM_END backend=openrouter response_len=%d", context, len(raw))
            return _parse_json_response(raw, context)
        except Exception as exc:
            logger.warning("[%s] OpenRouter 실패, CLI 폴백: %s", context, exc)

    # CLI 폴백 (기존 _call_llm 경로)
    use_think = _VIDEO_THINK_MODE in {"script", "video", "all", "true", "1", "yes"}
    if use_think:
        try:
            logger.info("[%s] LLM_START backend=cli think=True", context)
            raw = _call_llm(prompt, think=True)
            logger.info("[%s] LLM_END backend=cli response_len=%d", context, len(raw))
            return _parse_json_response(raw, context)
        except Exception as exc:
            logger.warning("[%s] think mode JSON 실패, no-think 재시도: %s", context, exc)
    logger.info("[%s] LLM_START backend=cli think=False", context)
    raw = _call_llm(prompt, think=False)
    logger.info("[%s] LLM_END backend=cli response_len=%d", context, len(raw))
    return _parse_json_response(raw, context)


def _rewrite_short_part(script: dict, data_pack: dict, blog_url: str, part: str, critique: dict) -> dict:
    prompt = f"""Rewrite only the {part} part of this Korean shorts script.
Return the full JSON script with all other parts preserved.

[Source Data Points]
{_format_source_points(data_pack.get("source_data_points", []))}

[Current Script JSON]
{json.dumps(script, ensure_ascii=False)}

[Critique]
{json.dumps(critique, ensure_ascii=False)}

[Rules]
- Use exact display_value or spoken_value from Source Data Points.
- Hook must contain one exact number and "끝까지 보면".
- Body must contain two exact data points and one interpretation.
- CTA must contain "전체 분석" and one risk or action data point.

[Output JSON]
{json.dumps(script, ensure_ascii=False)}"""
    return _video_llm_json(prompt, "short_video_part_rewrite")


def _rewrite_weak_parts(script: dict, critique: dict, data_pack: dict, blog_url: str, script_kind: str) -> dict:
    if script_kind != "short":
        return script
    issues_text = " ".join(critique.get("issues", []) + critique.get("must_fix", []))
    parts = []
    if any(token in issues_text for token in ("훅", "hook", "Hook")):
        parts.append("hook")
    if any(token in issues_text for token in ("숫자", "근거", "body", "본문", "데이터")):
        parts.append("body")
    if any(token in issues_text for token in ("CTA", "cta", "클릭", "마지막")):
        parts.append("cta")
    for part in parts[:2]:
        script = _rewrite_short_part(script, data_pack, blog_url, part, critique)
    return script


def _critique_script(script: dict, data_pack: dict, lang: str, script_kind: str, verify_issues: list[str] | None = None) -> dict:
    verify_block = "\n".join(f"- {issue}" for issue in (verify_issues or [])) or "- (없음)"
    prompt = f"""You are reviewing a {"long-form" if script_kind == "long" else "short-form"} Korean finance video script.
Score it strictly and return JSON only.

[Reference Title]
{data_pack.get("title", "")}

[Source Data Points]
{_format_source_points(data_pack.get("source_data_points", []))}

[Current Script JSON]
{json.dumps(script, ensure_ascii=False)}

[Automatic Verification Issues]
{verify_block}

[Review Criteria]
- hook 흡입력
- 숫자 근거의 선명함
- 반론/리스크 존재
- 1인칭/교과서 문체 제거
- CTA 강도
- 한국어 방송형 리듬감
- source data point 직접 활용 비율

[Output JSON]
{{
  "score": 0,
  "strengths": ["..."],
  "issues": ["..."],
  "must_fix": ["..."],
  "regenerate": true,
  "summary": "한 줄 총평"
}}"""
    try:
        critique = _video_llm_json(prompt, f"{script_kind}_video_critique")
    except Exception:
        critique = {}
    critique.setdefault("score", 0 if verify_issues else 70)
    critique.setdefault("strengths", [])
    critique.setdefault("issues", verify_issues or [])
    critique.setdefault("must_fix", verify_issues or critique.get("issues", []))
    critique.setdefault("regenerate", bool(critique.get("must_fix")))
    critique.setdefault("summary", "자동 비평 결과")
    return critique


def _rewrite_script(
    script: dict,
    critique: dict,
    data_pack: dict,
    blog_url: str,
    lang: str,
    script_kind: str,
) -> dict:
    prompt = f"""Rewrite the {"long-form" if script_kind == "long" else "short-form"} script below.
Return JSON only and preserve the same schema.

[Reference Title]
{data_pack.get("title", "")}

[Source Data Points]
{_format_source_points(data_pack.get("source_data_points", []))}

[Current Script JSON]
{json.dumps(script, ensure_ascii=False)}

[Critique]
{json.dumps(critique, ensure_ascii=False)}

[Required Fixes]
- Apply every must_fix item
- Keep Korean broadcast tone
- Keep 3rd-person analyst voice
- Keep CTA linked to: {blog_url}
- For long-form, ensure a distinct risk/counterpoint section
- For shorts, use at least two exact source data points and do not invent absent facts

[Output JSON]
{{
  "title": "...",
  "description": "...",
  "tags": ["..."],
  "chapters": [{{"start_sec": 0, "title": "Hook", "text": "...", "chart": null}}],
  "mid_roll_marks_sec": [],
  "total_duration_sec": 60,
  "hashtags": ["#shorts"]
}}"""
    return _video_llm_json(prompt, f"{script_kind}_video_rewrite")


def _count_exact_points_used(script: dict) -> int:
    combined = " ".join(ch.get("text", "") for ch in script.get("chapters", []))
    used = 0
    for point in script.get("source_data_points", []):
        if point.get("confidence") != "exact":
            continue
        candidates = [
            point.get("display_value", ""),
            point.get("spoken_value", ""),
            point.get("value", ""),
        ]
        for token in _pick_key_numbers(point.get("display_value", "") + " " + point.get("value", ""), limit=4):
            candidates.append(token)
            candidates.append(_spoken_value(token))
        if any(candidate and candidate in combined for candidate in candidates):
            used += 1
    return used


def _score_rules(script: dict, verify_issues: list[str]) -> tuple[int, list[str]]:
    issues = list(verify_issues)
    chapters = script.get("chapters", [])
    combined = " ".join(ch.get("text", "") for ch in chapters)
    is_short = script.get("format") == "shorts_reveal"
    available_exact = sum(1 for point in script.get("source_data_points", []) if point.get("confidence") == "exact")
    required_exact = 2 if is_short else 4
    required_exact = min(required_exact, available_exact) if available_exact else 0
    used_exact = _count_exact_points_used(script)

    if required_exact and used_exact < required_exact:
        issues.append(f"exact 데이터 직접 인용 부족: {used_exact}/{required_exact}")
    if is_short and len(chapters) >= 3:
        if len(_split_sentences(chapters[1].get("text", ""))) > 4:
            issues.append("쇼츠 본문 문장 수 과다")
    if len(chapters) >= 1 and not script.get("hook_text"):
        issues.append("hook_text 누락")
    if len(chapters) >= 1 and not script.get("cta_text"):
        issues.append("cta_text 누락")
    if not _pick_key_numbers(combined, limit=2):
        issues.append("직접 숫자 언급 부족")

    score = 100
    score -= min(len(verify_issues) * 10, 40)
    score -= max(required_exact - used_exact, 0) * 8
    if any("문장 수" in issue for issue in issues):
        score -= 5
    return max(score, 0), issues


def _editorial_score(critique: dict) -> int:
    return int(critique.get("score", 0) or 0)


def _finalize_quality_report(script: dict, critique: dict, verify_issues: list[str], regenerated: bool) -> dict:
    rule_score, rule_issues = _score_rules(script, verify_issues)
    editorial_score = _editorial_score(critique)
    merged_issues: list[str] = []
    for issue in (critique.get("issues", []) + rule_issues):
        if issue and issue not in merged_issues:
            merged_issues.append(issue)
    score = min(rule_score, editorial_score)
    quality_failed = rule_score < _RULE_TARGET_SCORE or editorial_score < _QUALITY_TARGET_SCORE
    return {
        "score": score,
        "rule_score": rule_score,
        "editorial_score": editorial_score,
        "quality_failed": quality_failed,
        "issues": merged_issues,
        "strengths": critique.get("strengths", []),
        "summary": critique.get("summary", ""),
        "regenerated": regenerated,
    }


def _needs_more_revision(script: dict, critique: dict, issues: list[str]) -> bool:
    rule_score, _ = _score_rules(script, issues)
    editorial_score = _editorial_score(critique)
    if rule_score < _RULE_TARGET_SCORE:
        return True
    if editorial_score < _QUALITY_TARGET_SCORE:
        return True
    return False


def generate_long_video_script(
    blog_md_path: Path,
    lang: str = "ko",
    blog_url: str = "",
    data_pack: dict | None = None,
) -> dict:
    """블로그 .md 파일 → 10~15분 롱폼 대사.

    Returns:
        {
          'title': str,           # SEO 영상 제목
          'description': str,     # 설명란 + 챕터 타임스탬프 + 블로그 링크
          'tags': list[str],
          'chapters': [
            {'start_sec': 0, 'title': 'Hook', 'text': '...', 'chart': None}
          ],
          'mid_roll_marks_sec': [240, 480, 720],
          'total_duration_sec': int,
          'hashtags': list[str],
        }
    """
    slug = blog_md_path.stem
    cache_path = _cache_key(slug, lang, "long")
    if cache_path.exists() and not os.getenv("FORCE_REGEN_SCRIPT"):
        logger.info("[long_video_script] 캐시 적중: %s", cache_path)
        return json.loads(cache_path.read_text(encoding="utf-8"))

    data_pack = data_pack or build_video_data_pack(blog_md_path, blog_url=blog_url)
    title = data_pack["title"]
    body_text = data_pack["body_text"]
    if not body_text:
        raise ValueError(f"블로그 본문 추출 실패: {blog_md_path}")
    result = _video_llm_json(_build_long_script_prompt(data_pack, lang), "long_video_script")

    # 기본값
    result.setdefault("title", title)
    result.setdefault("tags", [])
    result.setdefault("chapters", [])
    result.setdefault("mid_roll_marks_sec", [240, 480, 720])
    result.setdefault("hashtags", [])
    result["research_pack"] = data_pack.get("research_pack", {})

    # 총 길이 검증/계산
    if not result.get("total_duration_sec"):
        if result["chapters"]:
            last = result["chapters"][-1]
            result["total_duration_sec"] = last.get("start_sec", 0) + 90
        else:
            result["total_duration_sec"] = 720

    critique = _critique_script(result, data_pack, lang, "long")
    regenerated = False
    ok, issues = True, []
    for _ in range(_VIDEO_SCRIPT_MAX_ITER):
        if critique.get("regenerate", True) or int(critique.get("score", 0) or 0) < _QUALITY_TARGET_SCORE:
            result = _rewrite_script(result, critique, data_pack, blog_url, lang, "long")
            regenerated = True
        result = _postprocess_long_script(
            result,
            title=title,
            blog_url=blog_url,
            lang=lang,
            source_data_points=data_pack.get("source_data_points", []),
            quality_report={"score": critique.get("score", 0), "issues": [], "regenerated": regenerated},
        )
        result["research_pack"] = data_pack.get("research_pack", {})
        ok, issues = _verify_video_script(result, lang)
        if not _needs_more_revision(result, critique, issues):
            break
        critique = _critique_script(result, data_pack, lang, "long", verify_issues=issues)

    quality_report = _finalize_quality_report(result, critique, issues, regenerated)
    result["quality_report"] = quality_report

    if not ok:
        for issue in issues:
            logger.warning("[long_video_script] 스크립트 검증 경고: %s", issue)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    logger.info("[long_video_script] 캐시 저장: %s", cache_path)

    return result


def generate_short_video_script(
    long_script: dict,
    blog_url: str,
    lang: str = "ko",
    data_pack: dict | None = None,
) -> dict:
    """롱폼 대사 → 60초 쇼츠 hook 압축.

    Returns: long_script와 동일 구조, 60초 짧은 버전 + 롱폼 링크 CTA
    """
    long_title = long_script.get("title", "")
    slug = hashlib.md5(long_title.encode()).hexdigest()[:16]
    cache_path = _cache_key(slug, lang, "short")
    if cache_path.exists() and not os.getenv("FORCE_REGEN_SCRIPT"):
        logger.info("[short_video_script] 캐시 적중: %s", cache_path)
        return json.loads(cache_path.read_text(encoding="utf-8"))

    data_pack = data_pack or {
        "title": long_title,
        "source_data_points": long_script.get("source_data_points", []),
    }

    _short_max_sec = int(os.getenv("SHORT_DURATION_SEC", "60"))

    result = _video_llm_json(_build_short_script_prompt(long_script, blog_url, lang), "short_video_script")
    result.setdefault("title", f"{data_pack.get('title', '')[:50]} #shorts")
    result.setdefault("tags", [])
    result.setdefault("chapters", [])
    result.setdefault("mid_roll_marks_sec", [])
    result.setdefault("total_duration_sec", _short_max_sec)
    result.setdefault("hashtags", ["#shorts"])

    critique = _critique_script(result, data_pack, lang, "short")
    regenerated = False
    ok, issues = True, []
    for _ in range(_VIDEO_SCRIPT_MAX_ITER):
        if critique.get("regenerate", True) or int(critique.get("score", 0) or 0) < _QUALITY_TARGET_SCORE:
            result = _rewrite_script(result, critique, data_pack, blog_url, lang, "short")
            regenerated = True
        result = _postprocess_short_script(
            result,
            long_title=data_pack.get("title", ""),
            blog_url=blog_url,
            lang=lang,
            source_data_points=data_pack.get("source_data_points", []),
            quality_report={"score": critique.get("score", 0), "issues": [], "regenerated": regenerated},
        )
        ok, issues = _verify_video_script(result, lang)
        if not _needs_more_revision(result, critique, issues):
            break
        critique = _critique_script(result, data_pack, lang, "short", verify_issues=issues)
        result = _rewrite_weak_parts(result, critique, data_pack, blog_url, "short")

    quality_report = _finalize_quality_report(result, critique, issues, regenerated)
    result["quality_report"] = quality_report

    if not ok:
        for issue in issues:
            logger.warning("[short_video_script] 스크립트 검증 경고: %s", issue)

    # SHORT_DURATION_SEC 환경변수 캡 적용
    if result.get("total_duration_sec", 0) > _short_max_sec:
        result["total_duration_sec"] = _short_max_sec
        logger.info(f"[short_video_script] total_duration_sec 캡 적용: {_short_max_sec}s")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    logger.info("[short_video_script] 캐시 저장: %s", cache_path)

    return result


def _verify_video_script(script: dict, lang: str = "ko") -> tuple[bool, list[str]]:
    """스크립트 품질 검증 — 금지 표현, 레거시 페르소나, 최소 길이 확인.

    Returns:
        (ok, issues)  — ok=True면 문제 없음, issues는 발견된 문제 목록
    """
    chapters = script.get("chapters", [])
    combined = " ".join(ch.get("text", "") for ch in chapters)

    issues: list[str] = []

    # 1인칭 표현
    first_person = ["내가", "제가", "저는", "나는"]
    for w in first_person:
        if w in combined:
            issues.append(f"1인칭 표현 발견: '{w}'")

    # 금융 권유 표현
    fin_phrases = ["매수하세요", "사야 한다", "추천합니다", "BUY 신호", "SELL 신호"]
    for w in fin_phrases:
        if w in combined:
            issues.append(f"금융 권유 표현 발견: '{w}'")

    # 교과서 문체 클리셰
    cliches = ["결론적으로", "다음과 같이", "앞서 살펴본 바와 같이"]
    for w in cliches:
        if w in combined:
            issues.append(f"교과서 문체 발견: '{w}'")

    # 레거시 페르소나 참조
    legacy = ["이재훈", "34세 직장인", "월 70만원 시뮬레이션"]
    for w in legacy:
        if w in combined:
            issues.append(f"레거시 페르소나 발견: '{w}'")

    # 최소 길이 (200자)
    if len(combined) < 200:
        issues.append(f"스크립트 너무 짧음: 합산 {len(combined)}자 (최소 200자)")

    hook_text = script.get("hook_text") or (chapters[0].get("text", "") if chapters else "")
    cta_text = script.get("cta_text") or (chapters[-1].get("text", "") if chapters else "")

    if hook_text and "끝까지 보면" not in hook_text:
        issues.append("훅에 시청 유인 문구 부족")
    if cta_text and "전체 분석" not in cta_text and "블로그" not in cta_text:
        issues.append("마지막 CTA 약함")
    if len(chapters) >= 4:
        risk_text = " ".join(ch.get("title", "") + " " + ch.get("text", "") for ch in chapters)
        if not any(token in risk_text for token in ("리스크", "반론", "틀릴 수", "변수", "위험")):
            issues.append("리스크 파트 부족")
    if len(_pick_key_numbers(combined, limit=3)) < 1:
        issues.append("핵심 숫자 부족")

    ok = len(issues) == 0
    return ok, issues


def script_to_plain_text(script: dict) -> str:
    """대사를 TTS 입력용 단일 문자열로 변환 (챕터 사이 자연스러운 일시 정지)"""
    parts = []
    for ch in script.get("chapters", []):
        text = ch.get("text", "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("usage: python -m auto_publisher.video_script <blog_md_path>")
        sys.exit(1)
    p = Path(sys.argv[1])
    long_script = generate_long_video_script(p)
    print(json.dumps(long_script, ensure_ascii=False, indent=2)[:1500])
    print("---")
    short_script = generate_short_video_script(long_script, "https://investiqs.net/blog")
    print(json.dumps(short_script, ensure_ascii=False, indent=2)[:1000])
