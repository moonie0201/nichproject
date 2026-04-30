from auto_publisher.content_generator import _ensure_primary_keyword_in_title
import auto_publisher.content_generator as content_generator
from auto_publisher.video_script import (
    _postprocess_long_script,
    _postprocess_short_script,
    _score_rules,
    build_video_data_pack,
    generate_long_video_script,
)
from auto_publisher.video_composer import _build_fallback_cards


def test_postprocess_long_script_removes_first_person_and_adds_visual_plan():
    raw = {
        "chapters": [
            {"start_sec": 0, "title": "Hook", "text": "제가 본 숫자는 12%입니다.", "chart": None},
            {"start_sec": 90, "title": "근거", "text": "결론적으로 이 데이터가 중요합니다.", "chart": None},
            {"start_sec": 600, "title": "마무리", "text": "여기서 끝냅니다.", "chart": None},
        ]
    }
    result = _postprocess_long_script(raw, title="S&P500 데이터 해설", blog_url="https://investiqs.net/ko/daily/x/", lang="ko")

    combined = " ".join(ch["text"] for ch in result["chapters"])
    assert "제가" not in combined
    assert "결론적으로" not in combined
    assert result["format"] == "longform_broadcast"
    assert result["fallback_visual_plan"]
    assert result["visual_beats"]
    assert "끝까지 보면" in result["chapters"][0]["text"]


def test_postprocess_short_script_expands_short_cta_and_tags():
    raw = {
        "title": "짧은 쇼츠",
        "chapters": [
            {"start_sec": 0, "title": "Hook", "text": "내가 본 건 이겁니다.", "chart": None},
            {"start_sec": 3, "title": "핵심", "text": "핵심 수치만 짚습니다.", "chart": None},
            {"start_sec": 50, "title": "CTA", "text": "끝.", "chart": None},
        ],
    }
    result = _postprocess_short_script(raw, long_title="VOO 5년 데이터", blog_url="https://investiqs.net/ko/blog/voo/", lang="ko")

    combined = " ".join(ch["text"] for ch in result["chapters"])
    assert "내가" not in combined
    assert len(combined) >= 200
    assert "#shorts" in result["title"].lower()
    assert "전체 분석" in result["chapters"][-1]["text"]
    assert result["fallback_visual_plan"]


def test_postprocess_short_script_prefers_source_points():
    raw = {
        "title": "짧은 쇼츠",
        "chapters": [
            {"start_sec": 0, "title": "Hook", "text": "지수는 멈췄습니다.", "chart": None},
            {"start_sec": 3, "title": "핵심", "text": "본문 초안", "chart": None},
            {"start_sec": 50, "title": "CTA", "text": "마무리 초안", "chart": None},
        ],
    }
    points = [
        {"label": "S&P500", "value": "0.00%", "display_value": "0.00%", "spoken_value": "0.00퍼센트", "context": "S&P500은 0.00%로 멈췄습니다.", "confidence": "exact"},
        {"label": "VIX", "value": "18.02", "display_value": "18.02", "spoken_value": "18.02", "context": "VIX 18.02는 변동성 완화 신호였습니다.", "confidence": "exact"},
        {"label": "리스크", "value": "금리 4.5%", "display_value": "4.5%", "spoken_value": "4.5퍼센트", "context": "다만 금리 4.5% 구간은 여전히 부담입니다.", "confidence": "exact"},
    ]
    result = _postprocess_short_script(
        raw,
        long_title="시장 마감",
        blog_url="https://investiqs.net/ko/blog/voo/",
        lang="ko",
        source_data_points=points,
    )

    body = result["chapters"][1]["text"]
    cta = result["chapters"][2]["text"]
    assert "0.00퍼센트" in body
    assert "18.02" in body
    assert "4.5퍼센트" in cta


def test_ensure_primary_keyword_in_title_appends_when_missing():
    title = "Dividend strategy for retirement"
    keyword = "SPT Tahunan dividen"
    fixed = _ensure_primary_keyword_in_title(title, keyword)
    assert keyword in fixed


def test_ensure_primary_keyword_in_title_keeps_existing_keyword():
    title = "SPT Tahunan dividen guide for retirement"
    keyword = "SPT Tahunan dividen"
    fixed = _ensure_primary_keyword_in_title(title, keyword)
    assert fixed == title


def test_build_video_data_pack_extracts_points_and_numbers(tmp_path):
    blog = tmp_path / "sample.md"
    blog.write_text(
        """---
title: "미국 증시 마감 정리"
---
## 핵심 요약
S&P500은 1.2% 올랐지만 나스닥은 0.4%에 그쳤습니다.

## 리스크
다만 금리 4.5% 구간이 유지되면 변동성이 다시 커질 수 있습니다.
""",
        encoding="utf-8",
    )

    data_pack = build_video_data_pack(blog, blog_url="https://investiqs.net/ko/daily/sample/")
    assert data_pack["title"] == "미국 증시 마감 정리"
    assert data_pack["source_data_points"]
    assert any("1.2%" in point["value"] or "4.5%" in point["value"] for point in data_pack["source_data_points"])
    assert all("display_value" in point for point in data_pack["source_data_points"])
    assert all("spoken_value" in point for point in data_pack["source_data_points"])
    assert all(point["confidence"] in {"exact", "inferred"} for point in data_pack["source_data_points"])
    assert data_pack["risk_points"]
    assert data_pack["research_pack"]["research_style"] == "source_grounded_notebook"
    assert data_pack["research_pack"]["claims"]
    assert data_pack["research_pack"]["visual_scenes"]


def test_research_pack_drives_professional_fallback_cards(tmp_path):
    blog = tmp_path / "sample.md"
    blog.write_text(
        """---
title: "미국 증시 마감 정리"
---
## 핵심 요약
S&P500은 1.2% 올랐지만 나스닥은 0.4%에 그쳤습니다.

## 리스크
다만 금리 4.5% 구간이 유지되면 변동성이 다시 커질 수 있습니다.
""",
        encoding="utf-8",
    )

    data_pack = build_video_data_pack(blog, blog_url="https://investiqs.net/ko/daily/sample/")
    raw = {
        "chapters": [
            {"start_sec": 0, "title": "Hook", "text": "S&P500 1.2%와 나스닥 0.4%를 봅니다.", "chart": None},
            {"start_sec": 90, "title": "리스크", "text": "금리 4.5% 구간은 변수입니다.", "chart": None},
        ],
        "research_pack": data_pack["research_pack"],
    }
    result = _postprocess_long_script(
        raw,
        title=data_pack["title"],
        blog_url="https://investiqs.net/ko/daily/sample/",
        lang="ko",
        source_data_points=data_pack["source_data_points"],
    )

    card_types = {card["card_type"] for card in result["fallback_visual_plan"]}
    assert "thesis" in card_types
    assert {"market_dashboard", "risk_matrix", "timeline"} & card_types


def test_generate_long_video_script_adds_quality_report_and_source_points(tmp_path, monkeypatch):
    blog = tmp_path / "sample.md"
    blog.write_text(
        """---
title: "미국 증시 마감 정리"
---
## 핵심 요약
S&P500은 1.2% 올랐지만 나스닥은 0.4%에 그쳤습니다.

## 리스크
다만 금리 4.5% 구간이 유지되면 변동성이 다시 커질 수 있습니다.
""",
        encoding="utf-8",
    )

    responses = iter([
        """{
          "title": "초안 제목",
          "description": "설명",
          "tags": ["시장"],
          "chapters": [
            {"start_sec": 0, "title": "Hook", "text": "시장은 올랐습니다.", "chart": null},
            {"start_sec": 90, "title": "근거", "text": "숫자는 애매합니다.", "chart": null},
            {"start_sec": 540, "title": "마무리", "text": "여기서 끝냅니다.", "chart": null}
          ],
          "mid_roll_marks_sec": [240, 480],
          "total_duration_sec": 720,
          "hashtags": ["#시장"]
        }""",
        """{
          "score": 62,
          "strengths": ["숫자 언급 의도는 있음"],
          "issues": ["리스크 파트 부족", "마지막 CTA 약함"],
          "must_fix": ["리스크 챕터 추가", "CTA 강화"],
          "regenerate": true,
          "summary": "핵심은 있으나 구조가 약함"
        }""",
        """{
          "title": "미국 증시 마감, 숫자보다 중요한 리스크",
          "description": "설명",
          "tags": ["시장"],
          "chapters": [
            {"start_sec": 0, "title": "Hook", "text": "S&P500 1.2퍼센트 반등, 그런데 끝까지 보면 시선이 달라집니다.", "chart": null},
            {"start_sec": 45, "title": "핵심 프레임", "text": "시장은 반등했지만 나스닥 0.4퍼센트는 탄력이 약했습니다.", "chart": null},
            {"start_sec": 150, "title": "데이터 근거", "text": "핵심 숫자는 1.2퍼센트와 0.4퍼센트, 그리고 금리 4.5퍼센트입니다.", "chart": null},
            {"start_sec": 300, "title": "반론과 리스크", "text": "다만 금리 4.5퍼센트가 유지되면 변동성이 다시 커질 수 있습니다.", "chart": null},
            {"start_sec": 540, "title": "정리와 CTA", "text": "전체 분석은 블로그와 본 영상에서 이어집니다.", "chart": null}
          ],
          "mid_roll_marks_sec": [240, 480],
          "total_duration_sec": 720,
          "hashtags": ["#시장"]
        }""",
        """{
          "score": 88,
          "strengths": ["리스크 챕터는 생김"],
          "issues": ["스크립트 밀도가 더 필요함"],
          "must_fix": ["숫자와 실행 포인트를 더 선명하게 확장"],
          "regenerate": true,
          "summary": "구조는 좋아졌지만 밀도를 더 높여야 함"
        }""",
        """{
          "title": "미국 증시 마감, 숫자보다 중요한 리스크",
          "description": "설명",
          "tags": ["시장"],
          "chapters": [
            {"start_sec": 0, "title": "Hook", "text": "S&P500 1.2퍼센트 반등, 그런데 끝까지 보면 시선이 달라집니다. 숫자 하나만 보면 강세 같지만, 내부 동력은 그렇게 단순하지 않습니다.", "chart": null},
            {"start_sec": 45, "title": "핵심 프레임", "text": "시장은 반등했지만 나스닥 0.4퍼센트는 탄력이 약했습니다. 시장에서는 안도 랠리라고 부르지만, 데이터는 섹터별 체력이 갈리고 있다는 쪽에 가깝습니다.", "chart": null},
            {"start_sec": 150, "title": "데이터 근거", "text": "핵심 숫자는 1.2퍼센트와 0.4퍼센트, 그리고 금리 4.5퍼센트입니다. 이 세 숫자를 함께 보면 지수 자체보다 할인율과 성장주 민감도가 훨씬 중요해집니다.", "chart": null},
            {"start_sec": 300, "title": "반론과 리스크", "text": "다만 금리 4.5퍼센트가 유지되면 변동성이 다시 커질 수 있습니다. 실적 가이던스가 꺾이거나 장기금리가 다시 뛰면 지금의 반등 해석은 빠르게 흔들릴 수 있습니다.", "chart": null},
            {"start_sec": 540, "title": "정리와 CTA", "text": "핵심은 반등 숫자만 볼 게 아니라 금리와 섹터 회전을 같이 보는 것입니다. 전체 분석은 블로그와 본 영상에서 이어집니다.", "chart": null}
          ],
          "mid_roll_marks_sec": [240, 480],
          "total_duration_sec": 720,
          "hashtags": ["#시장"]
        }""",
        """{
          "score": 92,
          "strengths": ["숫자, 리스크, CTA가 모두 들어감"],
          "issues": [],
          "must_fix": [],
          "regenerate": false,
          "summary": "방송형 구조가 충분히 살아남"
        }""",
    ])

    monkeypatch.setattr("auto_publisher.video_script._call_llm", lambda *args, **kwargs: next(responses))

    result = generate_long_video_script(blog, blog_url="https://investiqs.net/ko/daily/sample/")
    assert result["quality_report"]["regenerated"] is True
    assert result["quality_report"]["score"] >= 90
    assert result["quality_report"]["rule_score"] >= 95
    assert result["quality_report"]["editorial_score"] >= 90
    assert result["quality_report"]["quality_failed"] is False
    assert result["source_data_points"]
    assert any("리스크" in chapter["title"] for chapter in result["chapters"])


def test_rule_score_flags_missing_exact_data():
    script = {
        "format": "shorts_reveal",
        "hook_text": "끝까지 보면 알 수 있습니다.",
        "cta_text": "전체 분석은 블로그에서 이어집니다.",
        "source_data_points": [
            {"display_value": "1.2%", "spoken_value": "1.2퍼센트", "confidence": "exact"},
            {"display_value": "4.5%", "spoken_value": "4.5퍼센트", "confidence": "exact"},
        ],
        "chapters": [
            {"text": "끝까지 보면 알 수 있습니다."},
            {"text": "데이터를 해석합니다."},
            {"text": "전체 분석은 블로그에서 이어집니다."},
        ],
    }
    score, issues = _score_rules(script, [])
    assert score < 95
    assert any("exact 데이터 직접 인용 부족" in issue for issue in issues)


def test_build_fallback_cards_assigns_card_types():
    points = [
        {"label": "핵심 수치", "value": "1.2%", "context": "지수 반등 폭입니다."},
        {"label": "리스크", "value": "금리 4.5%", "context": "금리 부담이 남아 있습니다."},
        {"label": "다음 액션", "value": "블로그 확인", "context": "전체 분석은 블로그로 이어집니다."},
    ]
    cards = _build_fallback_cards(None, None, points)
    assert cards[0]["card_type"] in {"number", "comparison"}
    assert any(card["card_type"] == "risk" for card in cards)
    assert any(card["card_type"] == "cta" for card in cards)


def test_call_llm_prefers_gemini_then_ollama_then_codex(monkeypatch):
    calls = []

    def fail_gemini(prompt):
        calls.append("gemini")
        raise RuntimeError("gemini failed")

    def ok_ollama(prompt, **kwargs):
        calls.append("ollama")
        return '{"ok": true}'

    def fail_codex(prompt, max_retries=3):
        calls.append("codex")
        raise RuntimeError("codex should not be called")

    monkeypatch.setattr(content_generator, "LLM_PRIMARY_BACKEND", "gemini")
    monkeypatch.setattr(content_generator, "_call_gemini_cli", fail_gemini)
    monkeypatch.setattr(content_generator, "_call_ollama", ok_ollama)
    monkeypatch.setattr(content_generator, "_call_codex", fail_codex)

    assert content_generator._call_llm("prompt") == '{"ok": true}'
    assert calls == ["gemini", "ollama"]


def test_prepare_ollama_prompt_disables_qwen_thinking(monkeypatch):
    monkeypatch.setattr(content_generator, "OLLAMA_MODEL", "qwen3.6:35b-a3b")
    prepared = content_generator._prepare_ollama_prompt("Return JSON only")
    assert prepared.startswith("/no_think\n")


def test_prepare_ollama_prompt_enables_qwen_thinking(monkeypatch):
    monkeypatch.setattr(content_generator, "OLLAMA_MODEL", "qwen3.6:35b-a3b")
    prepared = content_generator._prepare_ollama_prompt("Return JSON only", think=True)
    assert prepared.startswith("/think\n")


def test_prepare_ollama_prompt_keeps_gemma_plain(monkeypatch):
    monkeypatch.setattr(content_generator, "OLLAMA_MODEL", "gemma4:26b-a4b-it-q8_0")
    prepared = content_generator._prepare_ollama_prompt("Return JSON only")
    assert prepared == "Return JSON only"


def test_parse_json_response_strips_thinking_output():
    raw = '<think>reasoning details</think>\nFinal Answer:\n{"ok": true}'
    assert content_generator._parse_json_response(raw, "thinking_json") == {"ok": True}
