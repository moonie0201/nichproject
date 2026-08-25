"""numeric_fact_checker 테스트."""
import pytest

from auto_publisher.numeric_fact_checker import check_numeric_claims, ClaimMismatch


def _source(ticker="VOO", **fields):
    return {ticker: fields}


def test_no_source_returns_empty():
    assert check_numeric_claims("VOO 87% 수익", {}) == []


def test_passing_claim_within_tolerance():
    """본문 87.0%, 실제 87.5% → 0.6% delta → 통과."""
    html = "<p>VOO 5년 수익률 87.0% 입니다.</p>"
    src = _source("VOO", **{"5y_return_pct": 87.5})
    result = check_numeric_claims(html, src)
    assert result == []


def test_failing_claim_outside_tolerance():
    """본문 90%, 실제 87% → 약 3.4% delta. default tol 10% 내라 통과."""
    html = "<p>VOO 5년 수익률 90% 였습니다.</p>"
    src = _source("VOO", **{"5y_return_pct": 60.0})
    result = check_numeric_claims(html, src)
    assert len(result) == 1
    assert result[0].field == "5y_return_pct"
    assert result[0].claimed == 90.0
    assert result[0].expected == 60.0


def test_field_specific_tolerance():
    """배당수익률은 tol 15% — 본문 1.2% vs 실제 1.05% → 14% delta, 통과."""
    html = "<p>VOO 배당수익률은 1.2%입니다.</p>"
    src = _source("VOO", **{"dividend_yield_pct": 1.05})
    result = check_numeric_claims(html, src)
    # 1.2 vs 1.05 = 14.3% delta < 15% tol → 통과
    assert result == []


def test_dividend_outside_tolerance():
    """본문 2.0% vs 실제 1.0% → 100% delta, fail."""
    html = "<p>VOO 배당률 2.0% 수준이며 매력적입니다.</p>"
    src = _source("VOO", **{"dividend_yield_pct": 1.0})
    result = check_numeric_claims(html, src)
    assert any(m.field == "dividend_yield_pct" for m in result)


def test_ticker_not_in_body_skipped():
    """본문에 ticker 등장 안 함 → 검사 안 함."""
    html = "<p>5년 수익률 90% 였습니다.</p>"  # VOO 없음
    src = _source("VOO", **{"5y_return_pct": 60.0})
    result = check_numeric_claims(html, src)
    # ticker 등장 없음 → 클레임 추출 안됨
    assert result == []


def test_multiple_tickers():
    html = "<p>VOO 1년 수익률 20%. SCHD 1년 수익률 15%.</p>"
    src = {
        "VOO": {"1y_return_pct": 28.0},  # 본문 20 vs 실제 28 → 28% delta > 10% → fail
        "SCHD": {"1y_return_pct": 14.5},  # 본문 15 vs 실제 14.5 → 3.4% delta < 10% → pass
    }
    result = check_numeric_claims(html, src)
    tickers_failed = {m.ticker for m in result}
    assert "VOO" in tickers_failed
    assert "SCHD" not in tickers_failed


def test_current_price_dollar_sign():
    html = "<p>VOO 현재가: $700 수준입니다.</p>"
    src = _source("VOO", current_price=680.0)
    # 700 vs 680 = 2.9% delta < 5% tol → pass
    result = check_numeric_claims(html, src)
    assert result == []

    src2 = _source("VOO", current_price=500.0)
    # 700 vs 500 = 40% delta > 5% tol → fail
    result2 = check_numeric_claims(html, src2)
    assert any(m.field == "current_price" for m in result2)


def test_html_tags_stripped():
    """HTML 태그 무시하고 텍스트만 검사."""
    html = '<div><p><strong>VOO</strong> 5년 누적 <em>30%</em></p></div>'
    src = _source("VOO", **{"5y_return_pct": 80.0})
    result = check_numeric_claims(html, src)
    assert any(m.field == "5y_return_pct" for m in result)


def test_mismatch_repr():
    m = ClaimMismatch(ticker="VOO", field="5y_return_pct", claimed=90.0, expected=60.0, delta_pct=50.0)
    s = str(m)
    assert "VOO" in s and "5y_return_pct" in s and "90" in s and "60" in s
