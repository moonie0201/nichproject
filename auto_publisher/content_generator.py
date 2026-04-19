"""
Gemini API 기반 콘텐츠 생성기
- 블로그 포스트 (한국어, SEO 최적화, 3000자 이상)
- SNS 포스트 (Phase 2)
- 숏폼 스크립트 (Phase 3)
"""

import json
import time
import logging

from google import genai
from google.genai import types

from auto_publisher.config import GOOGLE_API_KEY, GEMINI_MODEL, CONTENT_NICHE

logger = logging.getLogger(__name__)

# Gemini 클라이언트 (지연 초기화)
_client = None


def _get_client() -> genai.Client:
    """Gemini 클라이언트 지연 초기화 — API 키가 없을 때 import 단계에서 에러 방지"""
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client


def _call_gemini(prompt: str, max_retries: int = 3) -> str:
    """Gemini API 호출 (지수 백오프 재시도)"""
    client = _get_client()
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=8192,
                ),
            )
            return response.text
        except Exception as e:
            wait = 2 ** (attempt + 1)
            logger.warning(f"Gemini API 호출 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"{wait}초 후 재시도...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"Gemini API 호출 {max_retries}회 실패: {e}")


def generate_blog_post(topic: str, keywords: list[str], niche: str = None) -> dict:
    """
    블로그 포스트 생성

    Returns:
        {title, content_html, meta_description, tags}
    """
    niche = niche or CONTENT_NICHE
    kw_str = ", ".join(keywords)

    prompt = f"""당신은 한국의 {niche} 분야 전문 블로거입니다.
아래 주제로 블로그 글을 작성해주세요.

주제: {topic}
핵심 키워드: {kw_str}

[작성 규칙]
1. 순수 JSON만 반환하세요. 마크다운 코드블록(```)이나 다른 텍스트 없이 JSON만 출력하세요.
2. 제목은 검색 유입에 최적화된 매력적인 제목 (30~50자)
3. 본문은 HTML 형식으로 3000자 이상 작성
4. H2, H3 태그로 구조화 (최소 3개 소제목)
5. 자연스러운 한국어 — 일상적이고 친근한 톤으로 작성 (AI가 쓴 느낌 배제)
6. 본문 말미에 <h2>자주 묻는 질문 (FAQ)</h2> 섹션 포함 (3개 이상 Q&A)
7. 메타 설명은 150자 이내로 핵심 키워드 포함
8. 태그는 관련 키워드 5~8개
9. 구글 애드센스 정책 준수 (금지 콘텐츠 배제)
10. 구체적인 수치, 사례, 비교를 포함하여 전문성 확보

[출력 형식 - 순수 JSON]
{{"title": "제목", "content_html": "<h2>...</h2><p>...</p>...", "meta_description": "메타 설명", "tags": ["태그1", "태그2", ...]}}
"""

    raw = _call_gemini(prompt)
    return _parse_json_response(raw, "blog_post")


def generate_sns_post(topic: str, platform: str) -> dict:
    """
    SNS 포스트 생성 (Phase 2)

    Returns:
        {text, hashtags}
    """
    char_limits = {
        "twitter": 280,
        "instagram": 2200,
    }
    limit = char_limits.get(platform, 280)

    prompt = f"""당신은 한국 {CONTENT_NICHE} 분야의 SNS 인플루언서입니다.
아래 주제로 {platform} 게시물을 작성해주세요.

주제: {topic}

[작성 규칙]
1. 순수 JSON만 반환하세요. 마크다운 코드블록(```)이나 다른 텍스트 없이 JSON만 출력하세요.
2. 본문은 {limit}자 이내
3. 한국어로 작성, 자연스러운 구어체
4. 이모지 적절히 활용
5. CTA(행동 유도) 포함
6. 관련 해시태그 5~10개

[출력 형식 - 순수 JSON]
{{"text": "게시물 본문", "hashtags": ["#해시태그1", "#해시태그2", ...]}}
"""

    raw = _call_gemini(prompt)
    return _parse_json_response(raw, "sns_post")


def generate_short_script(topic: str) -> dict:
    """
    숏폼 영상 스크립트 생성 (Phase 3)

    Returns:
        {script, title, description}
    """
    prompt = f"""당신은 한국 {CONTENT_NICHE} 분야의 유튜브 크리에이터입니다.
아래 주제로 60초 숏폼 영상 스크립트를 작성해주세요.

주제: {topic}

[작성 규칙]
1. 순수 JSON만 반환하세요. 마크다운 코드블록(```)이나 다른 텍스트 없이 JSON만 출력하세요.
2. 스크립트는 60초 분량 (약 300자)
3. 후킹 → 핵심 정보 → CTA 구조
4. 자연스러운 구어체 한국어
5. 영상 제목은 호기심 유발형
6. 설명문은 200자 이내, 키워드 포함

[출력 형식 - 순수 JSON]
{{"script": "스크립트 전문", "title": "영상 제목", "description": "영상 설명"}}
"""

    raw = _call_gemini(prompt)
    return _parse_json_response(raw, "short_script")


def _parse_json_response(raw: str, context: str) -> dict:
    """Gemini 응답에서 JSON 파싱 (코드블록 제거 포함)"""
    text = raw.strip()

    # 마크다운 코드블록 제거
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패 ({context}): {e}\n원본 응답:\n{raw[:500]}")
        # 중괄호 범위 추출 시도
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Gemini 응답을 JSON으로 파싱할 수 없습니다 ({context})")
