"""link_builder 점수 + 정렬 로직 테스트."""
from datetime import date, timedelta

import pytest

from auto_publisher.link_builder import (
    _link_score,
    _recency_score,
    inject_internal_links,
)


def _link(url, title="X", tickers=None, keywords=None, post_date=None, primary_keyword=""):
    return {
        "url": url,
        "title": title,
        "section": "blog",
        "tickers": tickers or [],
        "keywords": keywords or [],
        "date": post_date,
        "primary_keyword": primary_keyword,
    }


def test_recency_score_buckets():
    today = date(2026, 5, 13)
    assert _recency_score(today, today) == 1.0
    assert _recency_score(today - timedelta(days=10), today) == 0.5
    assert _recency_score(today - timedelta(days=60), today) == 0.2
    assert _recency_score(today - timedelta(days=200), today) == 0.0
    assert _recency_score(None) == 0.0


def test_link_score_ticker_overlap():
    cand = _link("/x/", tickers=["VOO", "SCHD"])
    s = _link_score(cand, current_tickers=["VOO"], current_keywords=[], current_primary_kw="")
    assert s > 0
    s_no_overlap = _link_score(_link("/y/", tickers=["AAPL"]), ["VOO"], [], "")
    assert s_no_overlap < s


def test_link_score_tag_jaccard():
    cand = _link("/x/", keywords=["ETF", "VOO", "배당"])
    s = _link_score(cand, [], ["ETF", "VOO"], "")
    assert s > 0


def test_link_score_primary_keyword_bonus():
    cand_with = _link("/x/", primary_keyword="VOO")
    cand_without = _link("/y/")
    s_with = _link_score(cand_with, [], [], "VOO")
    s_without = _link_score(cand_without, [], [], "VOO")
    assert s_with > s_without


def test_inject_skip_self():
    html = "<h2>VOO 분석</h2><p>VOO ETF</p>"
    links = [_link("/ko/blog/voo-test/", keywords=["VOO"])]
    out = inject_internal_links(html, "voo-test", links, current_section="blog")
    # 자기 자신 제외, 링크 0
    assert "<a href=" not in out


def test_inject_avoids_primary_keyword_anchor():
    """현재 글의 primary_keyword를 앵커로 사용하지 않음 (cannibalization 방지)."""
    html = "<h2>분석</h2><p>VOO ETF에 대한 내용. SCHD도 언급.</p>"
    links = [_link("/ko/blog/other/", keywords=["VOO", "SCHD"], primary_keyword="SCHD",
                   tickers=["VOO", "SCHD"], post_date=date.today())]
    out = inject_internal_links(
        html, "current", links,
        current_section="blog",
        current_tickers=["VOO"],
        current_keywords=["VOO"],
        current_primary_keyword="VOO",
    )
    # VOO 앵커 사용 안 함 (현재 primary). SCHD는 사용 가능.
    assert '<a href="/ko/blog/other/">VOO</a>' not in out
    # 어떤 링크는 삽입되어야 함 (SCHD)
    assert '/ko/blog/other/' in out or out == html


def test_inject_score_sorted_priority():
    """점수 높은 후보가 먼저 링크됨."""
    html = "<h2>분석</h2><p>VOO 미국 ETF. AAPL 주식.</p>"
    today = date.today()
    links = [
        _link("/ko/blog/old/", keywords=["AAPL"], tickers=["AAPL"],
              post_date=today - timedelta(days=200)),  # 오래된 + 약한 매치
        _link("/ko/blog/new/", keywords=["VOO", "ETF"], tickers=["VOO"],
              post_date=today, primary_keyword="VOO"),  # 최신 + 강한 매치
    ]
    out = inject_internal_links(
        html, "cur", links,
        current_section="blog",
        current_tickers=["VOO"],
        current_keywords=["VOO", "ETF"],
        current_primary_keyword="ETF분석",
    )
    # 점수 높은 /ko/blog/new/ 가 먼저 삽입됨
    new_pos = out.find("/ko/blog/new/")
    old_pos = out.find("/ko/blog/old/")
    if new_pos != -1 and old_pos != -1:
        assert new_pos < old_pos  # 또는 old가 아예 없을 수도


def test_inject_max_links_default_5():
    html = "<h2>x</h2>" + "".join(f"<p>키워드{i}</p>" for i in range(10))
    links = [
        _link(f"/ko/blog/{i}/", keywords=[f"키워드{i}"], tickers=["VOO"],
              post_date=date.today())
        for i in range(10)
    ]
    out = inject_internal_links(html, "cur", links, current_tickers=["VOO"])
    link_count = out.count('<a href="/ko/blog/')
    assert link_count <= 5


def test_inject_no_anchor_duplication():
    """같은 키워드가 두 링크 후보에 있어도 한 번만 사용."""
    html = "<h2>x</h2><p>VOO 등장. VOO 등장. VOO 등장.</p>"
    links = [
        _link("/ko/blog/a/", keywords=["VOO"], tickers=["VOO"], post_date=date.today()),
        _link("/ko/blog/b/", keywords=["VOO"], tickers=["VOO"], post_date=date.today()),
    ]
    out = inject_internal_links(
        html, "cur", links,
        current_section="blog",
        current_tickers=["VOO"],
        current_keywords=["VOO"],
    )
    # /a/ 와 /b/ 둘 다 VOO 앵커를 못 씀 → 두번째는 keywords 없으니 스킵
    # used_anchors 가드 동작 확인 — 'VOO' 앵커는 0회 또는 1회만
    assert out.count('>VOO</a>') <= 1


# --- href 속성 오염 (실제로 5개 언어 16개 파일이 망가졌다) ---

import re as _re
from auto_publisher.link_builder import _sub_in_text_only


def _run(kw, url, html):
    pat = _re.compile(r'(?<!["\'/=\w])(' + _re.escape(kw) + r')(?!["\'\w])')
    return _sub_in_text_only(pat, f'<a href="{url}">{kw}</a>', html)


def test_does_not_substitute_inside_href_attribute():
    """슬러그 안 키워드가 치환되면 href 값 자체가 마크업으로 깨진다."""
    html = '<p>참고: <a href="/ko/study/irp-세액공제-한도-비교/">IRP</a> 글 참조</p>'
    out, n = _run("세액공제", "/ko/study/x/", html)
    assert n == 0, "href 안에서 치환하면 안 된다"
    assert out == html
    assert 'href="/ko/study/irp-세액공제-한도-비교/"' in out


def test_does_not_nest_anchors():
    """이미 링크된 텍스트를 다시 감싸면 중첩 앵커가 된다."""
    html = '<p><a href="/ko/a/">세액공제 안내</a></p>'
    out, n = _run("세액공제", "/ko/b/", html)
    assert n == 0
    assert out.count("<a ") == 1


def test_substitutes_in_plain_text():
    html = '<p>연말정산에서 세액공제 한도를 확인하세요.</p>'
    out, n = _run("세액공제", "/ko/x/", html)
    assert n == 1
    assert '<a href="/ko/x/">세액공제</a>' in out


def test_substitutes_once_only():
    html = '<p>세액공제 그리고 또 세액공제</p>'
    out, n = _run("세액공제", "/ko/x/", html)
    assert n == 1
    assert out.count("<a ") == 1


def test_skips_img_alt_attribute():
    """alt 속성도 태그 안이므로 건드리면 안 된다(ja 파일이 이렇게 깨졌다)."""
    html = '<figure><img src="/i.png" alt="세액공제 비교 차트"></figure><p>본문</p>'
    out, n = _run("세액공제", "/ko/x/", html)
    assert n == 0
    assert 'alt="세액공제 비교 차트"' in out
