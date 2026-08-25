import pytest
from auto_publisher.compliance import apply_compliance, count_sources


def test_forbidden_phrases_are_detected_not_deleted():
    """금칙어는 삭제하지 않는다 — 삭제하면 조사가 남아 문장이 무너진다.

    검출은 content_verifier 가 맡아 재생성을 트리거한다.
    상세: test_forbidden_phrase_policy.py
    """
    from auto_publisher.compliance import find_forbidden_phrases

    html = "이것은 완벽 가이드입니다."
    assert "이것은 완벽 가이드입니다." in apply_compliance(html, "ko"), "본문이 훼손되면 안 된다"
    assert "완벽 가이드" in find_forbidden_phrases(html, "ko")


def test_inject_disclaimer():
    # 면책 조항 주입 테스트
    html = "<p>투자 내용</p>"
    injected = apply_compliance(html, "ko")
    assert 'class="disclaimer"' in injected


def test_count_sources():
    # 출처 개수 테스트
    html = "내용 1 [1] 내용 2 [2] 내용 3 [3]"
    assert count_sources(html) == 3

    html_low = "내용 1 [1]"
    assert count_sources(html_low) == 1


# --- 국내 개별 종목 차단 범위 (2026-08-21 정책) ---
# 자본시장법이 규제하는 것은 특정 종목 매매 권유다.
# 개별 종목만 막고, 지수와 국내 상장 ETF 는 통과시킨다.

@pytest.mark.parametrize("text,expected", [
    ("삼성전자 10년 장기투자 수익률", "삼성전자"),
    ("LG이노텍 기술주 투자 비교", "LG이노텍"),
    ("SK하이닉스 실적 분석", "SK하이닉스"),
    ("POSCO holdings earnings", "POSCO"),
    ("종목코드 005930.KS 조회", "005930.KS"),
])
def test_domestic_individual_stocks_are_blocked(text, expected):
    from auto_publisher.compliance import contains_domestic_equity
    assert contains_domestic_equity(text) == expected


@pytest.mark.parametrize("text", [
    # 지수 — 특정 종목이 아니라 시장 서술이다
    "미국장 마감 후 아시아 증시(닛케이/항셍/KOSPI/상하이)가 열린다",
    "After the US close, Asian markets (Nikkei/HangSeng/KOSPI/Shanghai) open next.",
    "코스피와 코스닥은 오전 9시에 개장한다",
    "^KS11 지수 데이터",
    # 국내 상장 ETF — 분산 상품이라 개별 종목 권유가 아니다
    "KODEX 200 보수율 비교",
    "TIGER 미국S&P500 vs VOO 운용보수",
    "KBSTAR, ARIRANG, KINDEX 국내 ETF 브랜드",
    # 오탐 방지 — 데이터 출처·서비스명은 종목 언급이 아니다
    "네이버 금융에서 시세를 확인했다",
    "카카오톡 오픈채팅으로 공유",
])
def test_indexes_etfs_and_service_names_pass(text):
    from auto_publisher.compliance import contains_domestic_equity
    assert contains_domestic_equity(text) is None


def test_market_wrap_asia_note_passes_its_own_gate():
    """시황 생성기가 자기 compliance 게이트에 걸리지 않아야 한다.

    이전 정책에서는 아시아 증시 안내 문구의 KOSPI 때문에 en/ja/vi/id 시황이
    매일 compliance_violation 으로 실패했다.
    """
    from auto_publisher.compliance import contains_domestic_equity
    from auto_publisher.i18n_market import _BY_LANG
    for lang, table in _BY_LANG.items():
        note = table.get("asia_crypto_note", "")
        assert contains_domestic_equity(note) is None, f"{lang} asia_crypto_note 차단됨"


# --- 국내 개별 종목 커버리지 (Codex 리뷰 지적: 시총 상위 종목 누락) ---

import pytest
from auto_publisher.compliance import contains_domestic_equity


@pytest.mark.parametrize("text", [
    "LG전자 실적 발표", "삼성SDI 배터리 수주", "현대모비스 주가 흐름",
    "NAVER 목표주가 상향", "LG에너지솔루션 증설", "한화에어로스페이스 수주",
    "삼성바이오로직스 4공장", "SK이노베이션 분할",
])
def test_domestic_majors_are_blocked(text):
    assert contains_domestic_equity(text) is not None, f"차단됐어야 함: {text}"


@pytest.mark.parametrize("text", [
    "TIGER 미국S&P500 수수료 비교", "KODEX 200 리밸런싱",
    "코스피 지수가 상승 마감했다", "미국장 마감 후 아시아 증시가 열린다",
])
def test_index_and_etf_by_brand_pass(text):
    assert contains_domestic_equity(text) is None, f"통과했어야 함: {text}"


# --- 조사 경계 (Codex 리뷰 2차: 부분문자열 검사가 정상 한국어를 오탐) ---

from auto_publisher.compliance import find_forbidden_phrases


@pytest.mark.parametrize("text", [
    "문제가 있다", "경제가 회복 중이다", "국내가 아니라 해외다", "한국경제가 좋다",
])
def test_normal_korean_is_not_flagged(text):
    assert find_forbidden_phrases(text, "ko") == [], f"오탐: {text}"


@pytest.mark.parametrize("text,phrase", [
    ("제가 보기엔 이렇다", "제가"),
    ("저는 이 방식을 쓴다", "저는"),
    ("내가 산 종목", "내가"),
    ("연말정산 총정리했다", "총정리"),      # 어미가 붙어도 잡아야 한다
    ("완벽 가이드입니다", "완벽 가이드"),
])
def test_real_violations_are_flagged(text, phrase):
    assert phrase in find_forbidden_phrases(text, "ko")


# --- 국내 ETF 티커 허용 (Codex 리뷰 2차: 문서는 허용, 구현은 차단) ---

@pytest.mark.parametrize("text", [
    "KODEX 200 (069500.KS) 수수료 비교",
    "TIGER 미국S&P500 (360750.KS) 1년 수익률",
])
def test_kr_etf_ticker_is_allowed(text):
    """데이터 수집 경로가 .KS 티커를 실제로 만들어 본문에 넣는다."""
    assert contains_domestic_equity(text) is None


@pytest.mark.parametrize("text", ["005930.KS 분석", "삼성전자 005930.KS"])
def test_individual_stock_ticker_still_blocked(text):
    assert contains_domestic_equity(text) is not None
