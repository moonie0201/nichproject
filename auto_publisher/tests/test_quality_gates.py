"""TDD: 투자 콘텐츠 품질 10/10 — 11개 갭 순차 검증"""
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from auto_publisher.content_generator import (
    _inject_disclaimer,
    build_eeat_frontmatter,
)
from auto_publisher.content_verifier import verify_rule_based


# ─────────────────────────────────────────────
# ① data_fetched_at 타임스탬프
# ─────────────────────────────────────────────

def test_frontmatter_includes_data_fetched_at():
    fm = build_eeat_frontmatter(
        title="VOO 분석", slug="voo", lang="ko",
        data_fetched_at="2026-04-30T22:47:00+09:00",
        data_source="yfinance",
    )
    assert "data_fetched_at" in fm
    assert "data_source" in fm
    assert "yfinance" in fm


def test_frontmatter_data_source_default_exists():
    fm = build_eeat_frontmatter(title="X", slug="x")
    assert "data_source" in fm


def test_disclaimer_includes_data_delay_notice():
    html = _inject_disclaimer(
        "<p>본문</p>", "ko",
        data_fetched_at="2026-04-30T22:47:00+09:00",
    )
    assert "15분" in html or "지연" in html


# ─────────────────────────────────────────────
# ② AI 생성 콘텐츠 레이블
# ─────────────────────────────────────────────

def test_frontmatter_has_ai_generated_flag():
    fm = build_eeat_frontmatter(title="X", slug="x")
    assert "ai_generated" in fm
    assert "true" in fm.lower()


def test_disclaimer_has_ai_disclosure_ko():
    html = _inject_disclaimer("<p>본문</p>", "ko")
    assert "AI" in html
    assert "Claude" in html or "Gemini" in html or "자동" in html


def test_disclaimer_has_ai_disclosure_en():
    html = _inject_disclaimer("<p>body</p>", "en")
    assert "AI" in html
    assert "automated" in html.lower() or "generated" in html.lower()


# ─────────────────────────────────────────────
# ③ 이해충돌 고지
# ─────────────────────────────────────────────

def test_disclaimer_has_conflict_of_interest_ko():
    html = _inject_disclaimer("<p>본문</p>", "ko")
    assert "광고" in html or "AdSense" in html
    assert "협찬" in html or "보상" in html


def test_disclaimer_has_conflict_of_interest_en():
    html = _inject_disclaimer("<p>body</p>", "en")
    assert "advertising" in html.lower() or "adsense" in html.lower()
    assert "compensation" in html.lower() or "sponsored" in html.lower()


# ─────────────────────────────────────────────
# ④ 불확실성 등급 (Morningstar 모델)
# ─────────────────────────────────────────────

def test_frontmatter_accepts_analysis_confidence():
    fm = build_eeat_frontmatter(
        title="X", slug="x",
        analysis_confidence="medium",
        confidence_note="단기 기술지표 기반",
    )
    assert "analysis_confidence" in fm
    assert "confidence_note" in fm


def test_frontmatter_confidence_default_is_medium():
    fm = build_eeat_frontmatter(title="X", slug="x")
    assert "medium" in fm


def test_frontmatter_confidence_invalid_raises():
    with pytest.raises(ValueError):
        build_eeat_frontmatter(title="X", slug="x", analysis_confidence="excellent")


# ─────────────────────────────────────────────
# ⑤ 시나리오 박스 대칭 강제
# ─────────────────────────────────────────────

def _make_post(body: str) -> dict:
    """테스트용 post dict 헬퍼."""
    base = "<h2>A</h2><h2>B</h2><h2>C</h2><table></table>" + "x" * 4000
    return {"content_html": body + base, "title": "테스트 x", "primary_keyword": "x"}


def test_verifier_rejects_scenario_box_without_downside():
    post = _make_post(
        '<div class="scenario-box">원금이 두 배가 됩니다</div>'
        '<div class="scenario-footnote">가상 인물입니다</div>'
    )
    ok, issues, _warns = verify_rule_based(post, source_data={})
    assert not ok
    assert "scenario_missing_downside" in issues


def test_verifier_passes_scenario_box_with_both_sides():
    post = _make_post(
        '<div class="scenario-box">상승 시 두 배. 하락 시 원금 손실 가능</div>'
        '<div class="scenario-footnote">가상 인물입니다</div>'
    )
    ok, issues, _warns = verify_rule_based(post, source_data={})
    assert "scenario_missing_downside" not in issues


# ─────────────────────────────────────────────
# ⑥ 결론부 방향성 언어 소프트콜
# ─────────────────────────────────────────────

def test_verifier_detects_soft_directional_language():
    post = _make_post("## 결론\n선택 기준은 VOO 쪽이다. ")
    _ok, _issues, warns = verify_rule_based(post, source_data={})
    assert any("soft_directional" in w for w in warns)


def test_verifier_passes_conclusion_with_personal_context():
    post = _make_post(
        "## 결론\n선택 기준은 VOO 쪽이다. "
        "단, 개인의 투자 목표와 계좌 구조에 따라 다릅니다. "
    )
    _ok, _issues, warns = verify_rule_based(post, source_data={})
    assert not any("soft_directional" in w for w in warns)


# ─────────────────────────────────────────────
# ⑦ 낮은 신뢰도 뱃지
# ─────────────────────────────────────────────

def test_low_confidence_signal_gets_badge():
    from auto_publisher.content_generator import _format_signal_with_badge
    result = _format_signal_with_badge(
        "news_sentiment", "bullish", confidence=0.30, sample_size=5
    )
    assert "⚠️" in result or "낮은 신뢰도" in result
    assert "5" in result


def test_high_confidence_signal_no_badge():
    from auto_publisher.content_generator import _format_signal_with_badge
    result = _format_signal_with_badge(
        "technical", "bullish", confidence=0.85, sample_size=None
    )
    assert "⚠️" not in result


# ─────────────────────────────────────────────
# ⑨ 재현 가능 코드 스니펫
# ─────────────────────────────────────────────

def test_verification_snippet_us_etf():
    from auto_publisher.content_generator import _build_verification_snippet
    snippet = _build_verification_snippet(ticker="VOO", lang="ko")
    assert "yfinance" in snippet
    assert "VOO" in snippet
    assert "```python" in snippet


def test_verification_snippet_skipped_for_korean_stock():
    from auto_publisher.content_generator import _build_verification_snippet
    assert _build_verification_snippet(ticker="005930.KS", lang="ko") == ""
    assert _build_verification_snippet(ticker="035720.KQ", lang="ko") == ""


# ─────────────────────────────────────────────
# ⑪ EU AI Act 메타 태그
# ─────────────────────────────────────────────

def test_hugo_head_partial_has_ai_meta_tags():
    partial = Path("web/layouts/partials/extend_head.html").read_text()
    assert 'name="ai-generated"' in partial
    assert 'name="ai-model"' in partial


# ─────────────────────────────────────────────
# ⑫ 예측 추적 시스템
# ─────────────────────────────────────────────

def test_prediction_tracker_records_signal():
    from auto_publisher.prediction_tracker import PredictionTracker
    tracker = PredictionTracker(db_path=":memory:")
    tracker.record(
        slug="voo-2026-04", ticker="VOO",
        signal="hold", price_at_publish=653.14,
        published_at="2026-04-23",
    )
    rows = tracker.pending_verification()
    assert len(rows) == 1
    assert rows[0]["ticker"] == "VOO"


def test_prediction_tracker_verifies_after_60_days():
    from auto_publisher.prediction_tracker import PredictionTracker
    tracker = PredictionTracker(db_path=":memory:")
    past = (date.today() - timedelta(days=61)).isoformat()
    tracker.record(
        slug="voo-old", ticker="VOO",
        signal="hold", price_at_publish=600.0,
        published_at=past,
    )
    results = tracker.run_verification(current_prices={"VOO": 653.14})
    assert len(results) == 1
    assert results[0]["return_pct"] == pytest.approx(8.857, rel=0.01)
    assert results[0]["direction_correct"] is True


def test_prediction_tracker_accuracy_summary():
    from auto_publisher.prediction_tracker import PredictionTracker
    tracker = PredictionTracker(db_path=":memory:")
    past = (date.today() - timedelta(days=61)).isoformat()
    tracker.record(
        slug="voo-old", ticker="VOO",
        signal="bullish", price_at_publish=600.0,
        published_at=past,
    )
    tracker.run_verification(current_prices={"VOO": 650.0})
    summary = tracker.accuracy_summary()
    assert "direction_accuracy" in summary
    assert "total_verified" in summary
    assert summary["total_verified"] == 1


# ─────────────────────────────────────────────
# ⑬ 3단 표기 (작성/검증/감수)
# ─────────────────────────────────────────────

def test_frontmatter_has_three_tier_attribution():
    fm = build_eeat_frontmatter(title="X", slug="x")
    assert "ai_generated" in fm
    assert "verifiedBy" in fm
    assert "reviewedBy" in fm


def test_frontmatter_reviewed_by_default_is_honest():
    fm = build_eeat_frontmatter(title="X", slug="x", reviewed_by=None)
    assert "편집자 미검토" in fm or "unreviewed" in fm.lower()
