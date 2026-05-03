"""slug → 카테고리 자동 매핑 회귀 테스트.

매핑 정책:
- ETF / 운용보수 / 추적오차 → 'etf-analysis'
- 비트코인 / bitcoin / btc / 이더리움 / eth / 코인 / blockchain → 'crypto'
- 배당 / dividend → 'dividend'
- 시장 마감 / 종가 / market-wrap / market wrap → 'market-wrap'
- 장중 / intraday / 실시간 → 'intraday'
- 주간 / weekly → 'weekly'
- 세금 / tax / 절세 → 'tax'
- 매칭 안되면 'default'
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("slug,expected", [
    # ETF
    ("etf-운용보수-003-vs-05-30년-복리", "etf-analysis"),
    ("etf-tracking-error-comparison", "etf-analysis"),
    ("voo-vs-spy-expense-ratio", "etf-analysis"),
    ("qqq-tqqq-leverage-decay", "etf-analysis"),

    # Crypto
    ("bitcoin-halving-cycle-2024", "crypto"),
    ("비트코인-반감기-분석", "crypto"),
    ("btc-eth-correlation-30d", "crypto"),
    ("ethereum-staking-yield", "crypto"),
    ("crypto-winter-survival-guide", "crypto"),

    # Dividend
    ("dividend-aristocrats-30y-cagr", "dividend"),
    ("배당주-포트폴리오-구성법", "dividend"),
    # schd 는 ETF 티커이므로 etf-analysis 우선 (ETF B-roll이 더 적합)
    ("schd-vrgn-yield-comparison", "etf-analysis"),

    # Market wrap (종가/마감)
    ("us-market-close-march-15", "market-wrap"),
    ("market-wrap-dow-sp500", "market-wrap"),
    ("us-stock-market-close-2026", "market-wrap"),

    # Intraday (장중)
    ("intraday-volatility-spike", "intraday"),
    ("us-market-intraday-3pm", "intraday"),

    # Weekly
    ("weekly-summary-march-week3", "weekly"),
    ("us-market-weekly-recap", "weekly"),

    # Tax (세금) — dividend 키워드 없는 순수 tax 슬러그만
    ("종합소득세-절세-전략", "tax"),
    ("capital-gains-tax-strategy", "tax"),
    ("연말정산-환급-전략", "tax"),

    # Default fallback
    ("random-blog-post", "default"),
    ("anything-else", "default"),
    ("", "default"),
])
def test_slug_to_category_mapping(slug, expected):
    from auto_publisher.stock_broll import slug_to_category
    assert slug_to_category(slug) == expected, f"slug={slug!r} → expected={expected!r}"


def test_slug_to_category_priority_etf_over_dividend():
    """'etf-dividend-...' 같은 복합 키워드는 ETF 우선 (ETF가 더 specific)."""
    from auto_publisher.stock_broll import slug_to_category
    # ETF가 먼저 매칭되면 etf-analysis
    assert slug_to_category("etf-dividend-yield-comparison") == "etf-analysis"


def test_slug_to_category_case_insensitive():
    from auto_publisher.stock_broll import slug_to_category
    assert slug_to_category("ETF-Analysis-2026") == "etf-analysis"
    assert slug_to_category("BITCOIN-RALLY") == "crypto"
