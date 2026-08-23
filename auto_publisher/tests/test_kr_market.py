"""kr_market 테스트 — FDR 데이터 fetch 모킹 + env gate."""
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from auto_publisher import kr_market


@pytest.fixture(autouse=True)
def enable_fdr(monkeypatch):
    monkeypatch.setenv("KR_MARKET_FDR_ENABLED", "1")


def _fake_df(rows: int = 800, start_price: float = 10000.0):
    """가짜 OHLCV DataFrame."""
    dates = pd.date_range(end=datetime.now(), periods=rows, freq="B")
    prices = [start_price + i * 5 for i in range(rows)]
    return pd.DataFrame({
        "Open": prices, "High": [p + 100 for p in prices],
        "Low": [p - 100 for p in prices], "Close": prices,
        "Volume": [1000000 + i * 100 for i in range(rows)],
        "Change": [0.001] * rows,
    }, index=dates)


def test_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("KR_MARKET_FDR_ENABLED", "0")
    assert kr_market.fetch_kr_etf_data("069500") == {}
    assert kr_market.fetch_kr_index_snapshot() == {}


def test_fetch_kr_etf_data_basic():
    fake = _fake_df(rows=800)
    with patch("FinanceDataReader.DataReader", return_value=fake):
        d = kr_market.fetch_kr_etf_data("069500", "KODEX 200")
    assert d["source"] == "FinanceDataReader"
    assert d["krx_code"] == "069500"
    assert d["krx_name"] == "KODEX 200"
    assert d["current_price_krw"] is not None
    assert d["1y_return_pct"] is not None
    assert d["avg_volume"] is not None


def test_fetch_kr_etf_data_empty_df():
    with patch("FinanceDataReader.DataReader", return_value=pd.DataFrame()):
        d = kr_market.fetch_kr_etf_data("999999")
    assert d == {}


def test_fetch_kr_etf_data_exception_returns_empty():
    with patch("FinanceDataReader.DataReader", side_effect=Exception("network")):
        d = kr_market.fetch_kr_etf_data("069500")
    assert d == {}


def test_fetch_kr_etf_outlier_returns_filtered():
    """200% 넘는 비현실적 1년 수익은 None으로."""
    # 거대한 가격 점프
    df = _fake_df(rows=300)
    df.iloc[0, df.columns.get_loc("Close")] = 100  # 1년 전 100원
    df.iloc[-1, df.columns.get_loc("Close")] = 100000  # 현재 100,000원 → 1000% 상승
    with patch("FinanceDataReader.DataReader", return_value=df):
        d = kr_market.fetch_kr_etf_data("069500")
    # 1y_return_pct 가 outlier 컷오프 (200% 초과)로 None
    assert d.get("1y_return_pct") is None


def test_fetch_kr_index_snapshot():
    fake = _fake_df(rows=120, start_price=7000)
    with patch("FinanceDataReader.DataReader", return_value=fake):
        snap = kr_market.fetch_kr_index_snapshot()
    assert "kospi" in snap
    assert "kosdaq" in snap
    assert snap["kospi"]["close"] > 0
    assert snap["kospi"]["change_1d_pct"] is not None


def test_fetch_kr_index_snapshot_fdr_fail():
    """FDR 실패 시 빈 dict."""
    with patch("FinanceDataReader.DataReader", side_effect=Exception("fail")):
        snap = kr_market.fetch_kr_index_snapshot()
    assert snap == {}
