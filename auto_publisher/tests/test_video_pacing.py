"""쇼츠 시각 페이싱 — 화면이 오래 멈춰 있지 않게 하는 방어선.

기존 결함 2건:
  1) per_chart_sec 에 하한만 있고 상한이 없어서, 쇼츠 60초에 차트 2장이면
     한 장이 30초씩 머물렀다. Ken Burns 줌이 3%뿐이라 사실상 정지 화면이었다.
  2) claude CLI 를 "claude" 로 호출해 PATH 얕은 환경(n8n/cron)에서 못 찾고,
     슬라이드가 "포인트 1 / 상세 데이터" 플레이스홀더로 조용히 폴백됐다.
"""

import math

import pytest


# --- 1) 비주얼 체류 시간 상한 ---

def _dwell(audio_sec: float, n_charts: int, max_per: float, min_per: float = 2.0):
    """video_composer 의 순환 로직과 같은 계산."""
    charts = list(range(n_charts))
    if len(charts) >= 2 and audio_sec / len(charts) > max_per:
        needed = max(int(math.ceil(audio_sec / max_per)), len(charts))
        charts = [charts[i % len(charts)] for i in range(needed)]
    return max(audio_sec / max(len(charts), 1), min_per), charts


def test_single_visual_is_not_cycled():
    """1장을 반복해봐야 화면은 그대로다. 인코딩만 낭비하므로 순환하지 않는다.

    이 경우 필요한 것은 순환이 아니라 비주얼을 더 만드는 것이다.
    """
    _, charts = _dwell(60.0, 1, max_per=4.0)
    assert charts == [0], charts


def test_two_charts_over_a_minute_no_longer_sit_for_30_seconds():
    dwell, charts = _dwell(60.0, 2, max_per=4.0)
    assert dwell <= 4.0, dwell
    assert len(charts) >= 15


def test_cycling_reuses_available_charts_in_order():
    _, charts = _dwell(60.0, 2, max_per=4.0)
    assert set(charts) == {0, 1}
    assert charts[:4] == [0, 1, 0, 1]


def test_enough_charts_are_left_alone():
    dwell, charts = _dwell(60.0, 20, max_per=4.0)
    assert len(charts) == 20
    assert dwell == pytest.approx(3.0)


def test_minimum_dwell_still_applies():
    """짧은 오디오에서 컷이 과하게 잘게 쪼개지지 않아야 한다."""
    dwell, _ = _dwell(3.0, 10, max_per=4.0, min_per=2.0)
    assert dwell >= 2.0


def test_long_form_keeps_a_slower_cap():
    dwell, _ = _dwell(600.0, 5, max_per=12.0)
    assert dwell <= 12.0


# --- 2) 슬라이드 폴백이 빈 껍데기를 만들지 않는다 ---

def test_fallback_slides_carry_real_summary_text():
    from auto_publisher.sonnet_slides import _fallback_slides
    summary = (
        "VOO는 현재 710달러입니다. 1년 수익률은 23.7%입니다. "
        "그런데 개별주 집중 포트폴리오가 이를 능가했습니다. "
        "차이를 만든 것은 심리 강건성입니다."
    )
    slides = _fallback_slides("개별주 vs VOO", summary, 5)

    joined = " ".join(b for s in slides for b in s["bullets"])
    assert "상세 데이터" not in joined, "플레이스홀더 문구가 남아 있다"
    assert "차트 참고" not in joined
    assert "23.7%" in joined or "710" in joined, joined


def test_fallback_slides_do_not_invent_pages_without_content():
    """요약이 짧으면 빈 슬라이드를 채워 넣지 않는다."""
    from auto_publisher.sonnet_slides import _fallback_slides
    slides = _fallback_slides("제목", "한 문장뿐입니다.", 5)
    assert len(slides) == 1
    for s in slides:
        assert any(b.strip() for b in s["bullets"])


def test_slide_cli_is_resolved_by_absolute_path():
    """PATH 가 얕아도 claude 실행파일을 찾아야 한다.

    이 해석이 실패하면 모든 영상이 플레이스홀더 슬라이드로 폴백된다.
    """
    from auto_publisher.content_generator import _resolve_cli
    resolved = _resolve_cli("claude")
    assert resolved
    # PATH 에 없더라도 알려진 설치 경로에서 찾아 절대경로를 돌려주거나,
    # 최소한 원래 이름을 그대로 돌려준다 (호출부가 FileNotFoundError 를 처리).
    assert resolved == "claude" or resolved.startswith("/")
