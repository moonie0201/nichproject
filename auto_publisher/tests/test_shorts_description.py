"""쇼츠 설명문 — 구독 전환과 사이트 유입을 막던 구조 수정.

실측 근거 (2026-08, 채널 263편):
  - 쇼츠 143편 8.3만 조회 vs 롱폼 120편 약 300회 → 롱폼은 죽은 목적지
  - 구독 전환 0.011% (8.4만 조회 / 9명). 정상 쇼츠 채널은 0.3~2%
  - 설명문 블로그 링크 7개 중 5개가 404 (심사용 축소로 /ko/daily/, /en/ 내려감)

수정 방향: 구독을 맨 위로, 계산기(항상 살아 있음)를 목적지로, 죽은 링크 차단.
"""

import pytest

from auto_publisher.shorts_description import enrich_shorts_description


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """링크 생존 확인은 별도 테스트에서 다룬다. 기본은 통과로 둔다."""
    monkeypatch.setattr("auto_publisher.shorts_description._url_alive", lambda *a, **k: True)


@pytest.fixture
def real_url_alive(monkeypatch):
    """_url_alive 자체를 검증하는 테스트용. 위 autouse 패치를 되돌린다."""
    import importlib
    from auto_publisher import shorts_description as sd
    monkeypatch.setattr(sd, "_url_alive", importlib.reload(sd)._url_alive)
    return sd


def test_subscribe_cta_comes_before_links():
    """쇼츠 설명문은 접혀 있어 앞 몇 줄만 보인다. 구독이 링크보다 위여야 한다."""
    out = enrich_shorts_description("본문", "https://investiqs.net/ko/study/x/", "tax")
    assert "🔔" in out
    assert out.index("🔔") < out.index("🧮"), "구독이 계산기 링크보다 위"
    assert out.index("🔔") < out.index("자세한 분석"), "구독이 블로그 링크보다 위"


def test_calculator_link_always_present():
    """개별 글은 내려갈 수 있지만 계산기는 항상 살아 있다."""
    out = enrich_shorts_description("본문", "", "tax")
    assert "/ko/tools/pension-tax-credit/" in out


@pytest.mark.parametrize("category,slug", [
    ("tax", "pension-tax-credit"),
    ("dividend", "portfolio-income"),
    ("etf-analysis", "etf-fee-calculator"),
    ("market-wrap", "portfolio-rebalance"),
    ("crypto", "dca-calculator"),
    ("알수없는카테고리", "dca-calculator"),
])
def test_calculator_matches_topic(category, slug):
    out = enrich_shorts_description("본문", "", category)
    assert f"/ko/tools/{slug}/" in out


def test_longform_youtube_link_is_not_added():
    """롱폼은 실측 조회수 0~2회. 보내면 이탈만 만든다."""
    out = enrich_shorts_description("본문", "https://youtube.com/watch?v=abc", "tax")
    assert "youtube.com/watch" not in out


def test_dead_blog_link_is_dropped(monkeypatch):
    monkeypatch.setattr("auto_publisher.shorts_description._url_alive", lambda *a, **k: False)
    out = enrich_shorts_description("본문", "https://investiqs.net/ko/daily/gone/", "market-wrap")
    assert "/ko/daily/gone/" not in out
    assert "/ko/tools/portfolio-rebalance/" in out, "죽은 링크를 빼도 계산기는 남아야 한다"


def test_live_blog_link_is_kept():
    out = enrich_shorts_description("본문", "https://investiqs.net/ko/study/alive/", "tax")
    assert "/ko/study/alive/" in out


def test_idempotent():
    """두 번 호출해도 중복이 붙지 않아야 한다."""
    once = enrich_shorts_description("본문", "https://investiqs.net/ko/study/x/", "tax")
    twice = enrich_shorts_description(once, "https://investiqs.net/ko/study/x/", "tax")
    assert twice.count("🔔") == 1
    assert twice.count("🧮") == 1


def test_disabled_returns_base(monkeypatch):
    monkeypatch.setenv("SHORTS_CTA_ENABLED", "false")
    assert enrich_shorts_description("본문", "u", "tax") == "본문"


def test_hashtags_present():
    out = enrich_shorts_description("본문", "", "tax")
    assert "#shorts" in out


# --- 링크 생존 확인 자체의 동작 ---

def test_url_alive_treats_network_error_as_alive(monkeypatch):
    """검증 실패로 링크를 빠뜨리는 쪽이 더 손해다."""
    from auto_publisher import shorts_description as sd
    monkeypatch.setattr(sd.urllib if hasattr(sd, "urllib") else sd, "__name__", sd.__name__)

    def boom(*a, **k):
        raise OSError("network down")

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert sd._url_alive("https://example.com/x") is True


def test_url_alive_can_be_disabled(monkeypatch):
    from auto_publisher import shorts_description as sd
    monkeypatch.setenv("SHORTS_VERIFY_LINKS", "0")
    assert sd._url_alive("https://never-resolved.invalid/") is True


# --- 본문에 섞여 들어온 롱폼 링크 (Codex 리뷰 지적) ---

def test_longform_link_inside_base_is_stripped():
    """blog_url 뿐 아니라 LLM 본문 안의 롱폼 링크도 걷어내야 한다."""
    base = "SCHD 배당 함정 분석\n전체 영상: https://youtube.com/watch?v=abc123"
    out = enrich_shorts_description(base, "", "dividend")
    assert "youtube.com" not in out
    assert "youtu.be" not in out
    assert "SCHD 배당 함정 분석" in out, "본문은 살아 있어야 한다"
    assert "전체 영상" not in out, "목적어 잃은 유도 문구도 정리"


def test_stripping_link_does_not_eat_body_text():
    """링크가 문장 끝에 붙어 있어도 문장 자체는 남아야 한다."""
    base = "연금저축 세액공제 한도가 바뀐다. 무료 확인 👉 https://youtu.be/xyz"
    out = enrich_shorts_description(base, "", "tax")
    assert "연금저축 세액공제 한도가 바뀐다." in out
    assert "👉" not in out.split("🔔")[0]


def test_url_alive_405_is_not_treated_as_dead(monkeypatch, real_url_alive):
    """HEAD 를 막는 서버(403/405)를 죽은 링크로 오판하면 안 된다."""
    import urllib.error, urllib.request
    sd = real_url_alive

    def raise_405(*a, **k):
        raise urllib.error.HTTPError("u", 405, "Not Allowed", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", raise_405)
    assert sd._url_alive("https://investiqs.net/ko/study/x/") is True


def test_url_alive_404_is_dead(monkeypatch, real_url_alive):
    import urllib.error, urllib.request
    sd = real_url_alive

    def raise_404(*a, **k):
        raise urllib.error.HTTPError("u", 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", raise_404)
    assert sd._url_alive("https://investiqs.net/ko/daily/gone/") is False
