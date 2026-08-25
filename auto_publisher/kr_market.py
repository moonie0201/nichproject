"""KR 시장 데이터 수집 (FinanceDataReader 기반).

yfinance .KS suffix보다 더 정확한 KR 시장 데이터 (KOSPI/KOSDAQ 지수, KR ETF 거래량/수익률).
FDR 실패 시 yfinance 폴백 (auto_publisher.content_generator._fetch_korean_etf_data).

Env gate: KR_MARKET_FDR_ENABLED=1 (기본 ON)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.getenv("KR_MARKET_FDR_ENABLED", "1").strip() == "1"


def fetch_kr_etf_data(code: str, name: str = "") -> dict:
    """KR ETF 데이터 fetch via FinanceDataReader.

    Returns:
        {current_price_krw, 1y_return_pct, 3y_return_pct, ytd_return_pct,
         avg_volume, source, krx_code, krx_name}
        실패 시 {}
    """
    if not _enabled():
        return {}
    try:
        import FinanceDataReader as fdr
    except ImportError:
        logger.warning("FinanceDataReader not installed")
        return {}

    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365 * 3 + 30)).strftime("%Y-%m-%d")
        df = fdr.DataReader(code, start, end)
        if df is None or df.empty:
            return {}

        close = df["Close"].dropna().astype(float)
        if close.empty:
            return {}
        current = float(close.iloc[-1])

        def _ret(days):
            if len(close) >= days:
                old = float(close.iloc[-days])
                if old > 0:
                    return round((current / old - 1) * 100, 1)
            return None

        # YTD: 연초 첫 거래일 대비
        year_start = datetime(datetime.now().year, 1, 1).date()
        ytd_pct = None
        try:
            ytd_slice = close[close.index.date >= year_start]
            if len(ytd_slice) >= 2:
                ytd_old = float(ytd_slice.iloc[0])
                if ytd_old > 0:
                    ytd_pct = round((current / ytd_old - 1) * 100, 1)
        except Exception:
            pass

        avg_volume = None
        if "Volume" in df.columns:
            vol_slice = df["Volume"].dropna().tail(60)
            if not vol_slice.empty:
                avg_volume = int(vol_slice.mean())

        # 이상치 컷오프
        r1 = _ret(252)
        r3 = _ret(252 * 3)
        if r1 is not None and abs(r1) > 200:
            r1 = None
        if r3 is not None and abs(r3) > 400:
            r3 = None

        return {
            "current_price_krw": round(current, 2),
            "1y_return_pct": r1,
            "3y_return_pct": r3,
            "ytd_return_pct": ytd_pct,
            "avg_volume": avg_volume,
            "source": "FinanceDataReader",
            "krx_code": code,
            "krx_name": name or code,
        }
    except Exception as e:
        logger.warning(f"fetch_kr_etf_data({code}) FDR fail: {e}")
        return {}


def fetch_kr_index_snapshot() -> dict:
    """KOSPI + KOSDAQ 최근 데이터 (당일 + 1년 변동).

    Returns: {kospi: {close, change_1d_pct, ytd_pct}, kosdaq: {...}}
    """
    if not _enabled():
        return {}
    try:
        import FinanceDataReader as fdr
    except ImportError:
        return {}

    out: dict = {}
    end = datetime.now().strftime("%Y-%m-%d")
    start = datetime(datetime.now().year, 1, 1).strftime("%Y-%m-%d")
    for label, code in [("kospi", "KS11"), ("kosdaq", "KQ11")]:
        try:
            df = fdr.DataReader(code, start, end)
            if df is None or df.empty:
                continue
            close = df["Close"].astype(float)
            current = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) >= 2 else None
            ytd_old = float(close.iloc[0])
            out[label] = {
                "close": round(current, 2),
                "change_1d_pct": round((current / prev - 1) * 100, 2) if prev else None,
                "ytd_pct": round((current / ytd_old - 1) * 100, 1) if ytd_old > 0 else None,
            }
        except Exception as e:
            logger.warning(f"fetch_kr_index_snapshot({code}) fail: {e}")
    return out
