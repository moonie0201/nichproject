"""
콘텐츠 2단계 검증기
- 1차: 규칙 기반 (무료, 즉시) — 글자수/표/금지어/숫자 주입 검증
- 2차: Gemini CLI 의미 검증 — 할루시네이션/모순/문맥 규제 (OpenRouter 제거)
"""

import json
import logging
import os
import re
import subprocess
from typing import Any

import requests

# dotenv 로드 (config.py가 workspace/.env + nichproject/.env 둘 다 로드)
from auto_publisher import config  # noqa: F401

logger = logging.getLogger(__name__)


def _get_key():
    return os.getenv("OPENROUTER_API_KEY", "")


VERIFIER_MODEL = os.getenv("VERIFIER_MODEL", "google/gemini-2.0-flash-exp:free")

from auto_publisher.config import BANNED_KO_FINANCIAL, BANNED_EN_FINANCIAL

FORBIDDEN_IN_BODY = {
    "ko": ["매수하세요", "사야 한다", "팔아야 한다", "추천합니다", "투자 권유",
           "BUY 신호", "SELL 신호", "완벽 가이드", "총정리",
           "결론적으로", "앞서 살펴본 바와 같이",
           "이재훈", "34세 직장인", "나는 ", "제가 ", "내가 ", "저는 ",
           # 예전에는 compliance 가 이 표현들을 본문에서 통째로 삭제했다. 조사가
           # 남아 문장이 무너졌고(“연말정산 를  정리했습니다”), 그 자체가 AI 티로
           # 읽혔다. 삭제 대신 여기서 잡아 재생성시킨다.
           "살펴보겠습니다", "알아보겠습니다", "정리해 드리겠습니다",
           "해드리겠습니다", "도움이 되셨으면", "마치며", "이상으로",
           "다음과 같이"],
    "en": [
        "Buy now", "Sell now", "You should buy", "Recommended to buy",
        "I recommend", "Strong buy", "must buy", "don't miss",
        "guaranteed returns", "risk-free", "100% safe",
        "financial advice", "investment advice", "consult me",
        "I personally own", "my portfolio", "trust me",
        "you will profit", "certain gains", "act now",
        "limited time offer", "exclusive tip",
    ],
    "ja": [
        "買ってください", "売ってください", "買うべき",
        "絶対に買い", "強くお勧め", "今すぐ購入",
        "損しない", "必ず上がる", "保証された利益",
        "リスクなし", "私のポートフォリオ", "私が持っている",
        "投資アドバイス", "金融アドバイス",
        "今がチャンス",
    ],
    "vi": [
        "Nên mua", "Nên bán", "Hãy mua ngay", "Tôi khuyên",
        "Chắc chắn có lời", "Không có rủi ro", "Đảm bảo sinh lời",
        "Đầu tư ngay", "Cơ hội vàng", "Tôi đang nắm giữ",
    ],
    "id": [
        "Beli sekarang", "Jual sekarang", "Saya rekomendasikan",
        "Pasti untung", "Tanpa risiko", "Dijamin untung",
        "Investasi sekarang", "Saya pegang saham ini",
        "Kesempatan emas", "Jangan lewatkan",
    ],
}


def check_financial_compliance(text: str, lang: str = "ko") -> list[str]:
    """자본시장법 §445 / 금융소비자보호법 §46 / 유사수신법 §2 위반 표현 검출.

    Returns list of violation strings found (empty = clean).
    """
    violations: list[str] = []
    text_lower = text.lower()

    # 한국어 금지어 — 모든 언어 공통 적용 (한국어 콘텐츠 포함 가능성)
    for phrase in BANNED_KO_FINANCIAL:
        if phrase in text:
            violations.append(f"[KO-금융법] '{phrase}'")

    # 영문 금지어 — 대소문자 무시
    for phrase in BANNED_EN_FINANCIAL:
        if phrase in text_lower:
            violations.append(f"[EN-금융법] '{phrase}'")

    return violations


def _verify_scenario_box(html: str) -> list[str]:
    """시나리오 박스 사용 시 형식 검증 (footnote 누락 / 1회 초과 / 1인칭)."""
    issues = []
    box_count = html.count('class="scenario-box"')
    if box_count == 0:
        return issues
    if box_count > 1:
        issues.append(f"scenario-box 1회 초과 ({box_count}개) — 한 글당 1개 제한")
    if 'class="scenario-footnote"' not in html:
        issues.append("scenario-box 사용했으나 scenario-footnote(가상 인물 안내) 누락")
    # 박스 내부 1인칭 단어 검사
    import re as _re
    for m in _re.finditer(r'<aside class="scenario-box".*?</aside>', html, _re.DOTALL):
        block = m.group(0)
        for w in ("내가 ", "제가 ", "저는 "):
            if w in block:
                issues.append(f"scenario-box 안에 1인칭 표현: '{w.strip()}'")
                break
    return issues


_SOFT_DIRECTIONAL_PATTERNS = [
    re.compile(r"선택 기준은.{0,10}쪽"),
    re.compile(r"더 나은 선택은"),
    re.compile(r"이 구간에서는.{0,20}효율적"),
    re.compile(r"(대부분|일반적으로).{0,20}(추천|선택)"),
]
_PERSONAL_CONTEXT_RE = re.compile(r"개인.{0,20}(목표|상황|구조|세금|책임)")
_DOWNSIDE_KEYWORDS = ["하락", "손실", "약세", "위험", "리스크", "낮아", "줄어", "감소", "bear"]


def verify_rule_based(
    post: dict, source_data: dict | None = None, lang: str = "ko",
    min_len: int = 4000,
) -> tuple[bool, list[str], list[str]]:
    """1차: 규칙 기반 검증. 반환: (ok, critical_issues, warnings)"""
    issues: list[str] = []
    warnings: list[str] = []
    html = post.get("content_html", "")
    title = post.get("title", "")
    pkw = post.get("primary_keyword", "")

    # 필수 요소
    if len(html) < min_len:
        issues.append(f"글자수 {len(html)} < {min_len}")
    if "<table" not in html:
        issues.append("비교표(<table>) 누락")
    if html.count("<h2") < 3:
        issues.append(f"H2 개수 부족 ({html.count('<h2')})")
    if pkw and pkw.lower() not in title.lower() and pkw not in title:
        issues.append(f"제목에 primary_keyword '{pkw}' 누락")

    # 금지어 (본문 + 제목)
    # 목록이 두 벌이다: 여기 FORBIDDEN_IN_BODY 와 config.FORBIDDEN_PHRASES.
    # 후자는 검증 경로에 연결돼 있지 않아 죽은 규칙이었다(Codex 리뷰 지적) —
    # 1인칭 금지가 후자에만 있다. 둘을 합치되 중복은 한 번만 보고한다.
    from auto_publisher.compliance import find_forbidden_phrases
    hits = dict.fromkeys(
        [f for f in FORBIDDEN_IN_BODY.get(lang, []) if f in html or f in title]
        + find_forbidden_phrases(html + " " + title, lang)
    )
    issues.extend(f"금지어: '{f}'" for f in hits)

    # 자본시장법/금융소비자보호법/유사수신법 위반 표현
    fin_violations = check_financial_compliance(html + " " + title, lang)
    issues.extend(fin_violations)

    # 주입된 실데이터 숫자 반영 검증 (할루시네이션 1차 방어)
    if source_data:
        missing = []
        for ticker, data in source_data.items():
            if not isinstance(data, dict):
                continue
            critical_keys = [
                ("current_price", f"${data.get('current_price')}"),
                ("dividend_yield_pct", f"{data.get('dividend_yield_pct')}%"),
                ("1y_return_pct", f"{data.get('1y_return_pct')}"),
            ]
            for key, expected_repr in critical_keys:
                v = data.get(key)
                if v is None:
                    continue
                if str(v) not in html:
                    missing.append(f"{ticker}.{key}={v}")
        if missing:
            issues.append(f"원본 데이터 미반영: {', '.join(missing[:5])}")

        # Tier 3 #9 — 프로그램적 numeric fact-check (할루시네이션 2차 방어)
        # 본문 숫자 클레임 vs source_data tolerance band 검증
        try:
            from auto_publisher.numeric_fact_checker import check_numeric_claims
            mismatches = check_numeric_claims(html, source_data)
            if mismatches:
                # 처음 3건만 issue로 (critical), 나머지는 warning
                for m in mismatches[:3]:
                    issues.append(f"숫자 불일치: {m}")
                for m in mismatches[3:5]:
                    warnings.append(f"숫자 불일치(warning): {m}")
        except Exception as e:
            logger.warning(f"numeric_fact_check 실행 실패: {e}")

    # 시나리오 박스 형식 검증
    issues.extend(_verify_scenario_box(html))

    # ⑤ 시나리오 박스 하락 시나리오 필수
    if html.count('class="scenario-box"') > 0:
        if not any(kw in html for kw in _DOWNSIDE_KEYWORDS):
            issues.append("scenario_missing_downside")

    # ⑥ 결론부 소프트 방향성 언어 감지 (경고 — ok에 영향 없음)
    has_soft = any(p.search(html) for p in _SOFT_DIRECTIONAL_PATTERNS)
    has_personal = bool(_PERSONAL_CONTEXT_RE.search(html))
    if has_soft and not has_personal:
        warnings.append("soft_directional: 방향성 결론 발견, '개인 목표·상황' 문구 추가 권장")

    return len(issues) == 0, issues, warnings


def verify_semantic_gemini(
    post: dict, source_data: dict | None = None, lang: str = "ko",
) -> tuple[bool, dict]:
    """2차: Gemini CLI로 의미 검증. 반환: (ok, report)
    report = {"hallucination": [...], "contradiction": [...], "bad_phrasing": [...]}
    """
    gemini_model = os.getenv("GEMINI_CLI_MODEL", "gemini-2.5-flash")

    source_block = json.dumps(source_data, ensure_ascii=False, indent=2) if source_data else "(없음)"
    # 본문 텍스트만 (HTML 태그 제거)
    body_text = re.sub(r"<[^>]+>", " ", post.get("content_html", ""))
    body_text = re.sub(r"\s+", " ", body_text)[:4000]

    prompt = f"""당신은 금융 블로그 팩트체커입니다. 아래 [원본 실데이터]와 [블로그 본문]을 대조해 검증하세요.

[원본 실데이터 — yfinance 검증된 숫자]
{source_block}

[블로그 본문 (HTML 태그 제거됨)]
{body_text}

[검증 항목]
1. hallucination: 원본에 없는 숫자/사실을 본문이 만들어낸 곳 (예: "배당률 5%"인데 원본은 3.4%)
2. contradiction: 본문 내 내부 모순 (도입부 vs FAQ 등 수치 불일치)
3. bad_phrasing: 금융 자문/권유로 해석될 수 있는 표현 ("지금 사세요", "강력 추천", "반드시 매수")
4. missing_chart_refs: "아래 차트" "위 그래프" 참조인데 실제 차트 삽입이 없는 경우

[출력: 순수 JSON만]
{{
  "hallucination": ["구체적 문구 1", ...],
  "contradiction": ["..."],
  "bad_phrasing": ["..."],
  "missing_chart_refs": ["..."]
}}
각 배열이 비어있으면 [] 반환. 문제 없으면 모든 배열 []."""

    import time
    last_err = None
    raw = None
    # 검증은 정확도 중요 — Gemini 3.1 Pro Preview primary (할루시네이션 catch 우수).
    # 실패 시 Claude haiku → Ollama 폴백.
    from auto_publisher.content_generator import _call_gemini_cli, _call_claude_cli, _call_ollama
    verify_model = os.getenv("GEMINI_VERIFY_MODEL", "gemini-3.1-pro-preview")
    for attempt in range(3):
        try:
            raw = (_call_gemini_cli(prompt, model=verify_model) or "").strip()
            if raw:
                break
            raise RuntimeError("Gemini Pro Preview 빈 응답")
        except Exception as e:
            last_err = e
            logger.warning(f"Gemini 검증 시도 {attempt+1}/3 실패: {e}")
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
    if not raw:
        # Gemini 실패 시 Claude haiku → Ollama 순 폴백
        try:
            raw = (_call_claude_cli(prompt) or "").strip()
            logger.info("Gemini 실패, Claude 검증 폴백 성공")
        except Exception:
            try:
                raw = (_call_ollama(prompt) or "").strip()
                logger.info("Claude 실패, Ollama 검증 폴백 성공")
            except Exception as e:
                logger.warning(f"모든 폴백 실패: {e}")

    if raw is None or not raw:
        logger.warning("모든 검증 백엔드 (ollama + claude/gemini) 실패")
        return False, {"error": "모든 검증 백엔드 실패", "critical_count": 99}

    try:
        # ``` 코드블록 제거
        if raw.startswith("```"):
            raw = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("```"))
        start = raw.find("{")
        end = raw.rfind("}") + 1
        report = json.loads(raw[start:end]) if start >= 0 and end > start else {}
    except Exception as e:
        logger.warning(f"Gemini 검증 실패: {e}")
        return False, {"error": str(e)[:200], "critical_count": 99}

    # critical 판정: hallucination 완전 차단, bad_phrasing/contradiction 1건까지 허용
    critical = (
        len(report.get("hallucination", [])) +
        max(0, len(report.get("bad_phrasing", [])) - 1) +
        max(0, len(report.get("contradiction", [])) - 1)
    )
    ok = critical == 0
    report["critical_count"] = critical
    return ok, report


def verify_two_stage(
    post: dict, source_data: dict | None = None, lang: str = "ko",
    min_len: int = 4000, run_semantic: bool = True,
) -> dict:
    """2단계 검증: 1차(규칙) → 통과 시에만 2차(Gemini).
    Returns: {
      "ok": bool,              # 최종 통과 여부
      "stage1_ok": bool, "stage1_issues": [...],
      "stage2_ok": bool, "stage2_report": {...},
      "retry_prompt": str,     # 재시도 프롬프트에 주입할 이슈 요약
    }
    """
    s1_ok, s1_issues, _s1_warns = verify_rule_based(post, source_data, lang, min_len)
    result = {"ok": False, "stage1_ok": s1_ok, "stage1_issues": s1_issues}

    if not s1_ok:
        result["retry_prompt"] = "규칙 위반: " + "; ".join(s1_issues[:5])
        return result

    if not run_semantic:
        result["ok"] = True
        return result

    s2_ok, s2_report = verify_semantic_gemini(post, source_data, lang)
    result["stage2_ok"] = s2_ok
    result["stage2_report"] = s2_report
    result["ok"] = s2_ok

    if not s2_ok:
        lines = []
        for k in ["hallucination", "bad_phrasing", "contradiction"]:
            items = s2_report.get(k, [])[:3]
            if items:
                lines.append(f"{k}: {', '.join(items)}")
        result["retry_prompt"] = "의미 검증 실패: " + " | ".join(lines)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_post = {
        "title": "VOO 5년 수익률 분석",
        "content_html": "<h2>개요</h2><p>VOO 현재가 $650.44, 1년 수익률 36.7%입니다. <table><tr><td>1</td></tr></table></p><h2>상세</h2><p>배당률 1.19%.</p>" * 20,
        "primary_keyword": "VOO",
    }
    test_source = {"VOO": {"current_price": 650.44, "dividend_yield_pct": 1.19, "1y_return_pct": 36.7}}
    r = verify_two_stage(test_post, test_source, "ko", min_len=500)
    print(json.dumps(r, ensure_ascii=False, indent=2))
