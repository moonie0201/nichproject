"""쇼츠 나레이션 길이 예산 — 영상이 문장 중간에서 잘리지 않게 하는 방어선.

기존 결함: total_duration_sec 메타데이터만 60으로 고쳐 쓰고 대사는 그대로 둬서,
한국어 대본이 60초 상한의 2배(약 112초)로 생성됐고 TTS 오디오가 60초에서 통째로
잘렸다. 문장 중간이 끊기고 CTA 가 재생되지 않았다 (최근 10편 중 8편).
"""

import pytest

from auto_publisher.video_script import (
    _TTS_CHARS_PER_SEC,
    estimate_narration_sec,
    narration_char_budget,
    trim_narration_text,
)


def test_korean_budget_is_well_under_latin():
    """한국어는 음절 밀도가 높아 같은 시간에 들어가는 글자 수가 절반 수준이다.

    이 차이를 무시한 것이 최초 결함의 원인이었다.
    """
    ko = narration_char_budget(60, "ko")
    en = narration_char_budget(60, "en")
    assert ko < en * 0.65, (ko, en)


def test_budget_uses_slow_end_not_average():
    """예산은 평균이 아니라 느린 쪽 발화 속도로 잡아야 상한이 보장된다.

    평균(ko 5.30자/초)으로 잡았을 때 317자 예산이 최저 4.65자/초 케이스에서
    68초가 되어 8초가 잘렸다. 실측 표본 100편 전부가 60초 안에 들어오려면
    10퍼센타일(4.80) 이하를 써야 한다.
    """
    assert _TTS_CHARS_PER_SEC["ko"] <= 4.8, "ko 발화속도 추정이 평균 쪽으로 올라가면 상한이 깨진다"
    assert narration_char_budget(60, "ko") <= 290

    # 실측 최저 속도로 읽어도 상한 안에 들어와야 한다.
    slowest_ko = 4.65
    assert narration_char_budget(60, "ko") / slowest_ko <= 62.0


def test_unknown_language_falls_back():
    assert narration_char_budget(60, "xx") == narration_char_budget(60, "en")


def test_estimate_matches_measured_rate():
    """실측 기준: 한국어 580자 ≈ 110초."""
    assert 115 <= estimate_narration_sec("가" * 580, "ko") <= 125


# --- (A) 검증 단계: 과길이를 issue 로 잡아 rewrite 루프에 넘긴다 ---

def _script(*texts):
    return {"chapters": [{"start_sec": 0, "title": "t", "text": t} for t in texts]}


def test_verify_flags_overlong_script():
    from auto_publisher.video_script import _verify_video_script
    long_ko = "이 숫자는 중요합니다. " * 60          # 약 720자 ≈ 136초
    ok, issues = _verify_video_script(_script(long_ko), "ko")
    assert not ok
    assert any("너무 김" in i for i in issues), issues


def test_verify_accepts_within_budget():
    from auto_publisher.video_script import _verify_video_script
    body = "이 숫자는 중요합니다. " * 20             # 약 240자 ≈ 45초
    _, issues = _verify_video_script(_script(body), "ko")
    assert not any("너무 김" in i for i in issues), issues


# --- (B) 안전망: 축약은 훅까지 붙은 뒤 TTS 직전 한 곳에서만 일어난다 ---
#
# 예전에는 대본 단계(챕터 기준)와 TTS 직전(평문 기준) 두 곳에서 잘랐다.
# 앞단이 훅 자리를 남기지 않아 뒷단이 다시 자르는 구조였고, 실측 10편 중
# 9편이 두 방식의 결과가 글자 단위까지 같았다. 한 곳으로 합쳤다.

def test_trim_cuts_on_sentence_boundary():
    """중간에서 끊긴 문장이 남으면 안 된다."""
    text = "훅입니다. " + "첫 문장입니다. 두 번째 문장입니다. " * 30 + "CTA 입니다."
    out = trim_narration_text(text, 60, "ko")
    assert out.rstrip().endswith("."), out[-40:]


def test_trim_narration_text_keeps_hook_and_cta():
    """훅(앞)과 CTA(뒤)를 남기고 가운데를 덜어낸다."""
    hook = "이 수치가 뒤집힙니다."
    middle = " ".join(f"중간 문장 {i} 입니다." for i in range(60))
    cta = "전체 분석은 블로그에서 확인하세요."
    out = trim_narration_text(f"{hook} {middle} {cta}", 60, "ko")

    assert out.startswith(hook)
    assert out.endswith(cta), out[-40:]
    assert len(out) <= narration_char_budget(60, "ko")


def test_trim_narration_text_is_noop_within_budget():
    text = "짧습니다. 전체 분석은 블로그에서."
    assert trim_narration_text(text, 60, "ko") == text


@pytest.mark.parametrize("lang", ["ko", "en", "ja", "vi", "id"])
def test_trimmed_output_fits_the_cap_in_every_language(lang):
    """모든 언어에서 축약 결과가 상한 안에 들어와야 한다.

    이 성질이 깨지면 ffmpeg 강제 절단으로 넘어가고 CTA 가 유실된다.
    """
    text = " ".join(f"Sentence number {i} here." for i in range(200))
    out = trim_narration_text(text, 60, lang)
    assert estimate_narration_sec(out, lang) <= 60.5, len(out)
