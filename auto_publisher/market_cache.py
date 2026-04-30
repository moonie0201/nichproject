"""
시장 데이터 캐시 — 매일 새벽 1회 fetch + 검증 후 저장
- Python (_fetch_market_data) 가 캐시 우선 사용 → yfinance 의존도 ↓
- n8n cron 06:00 → /refresh-market-cache → 이 모듈로 갱신
- 캐시 파일: .omc/state/market-cache.json
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_FILE = Path("/home/mh/ocstorage/workspace/nichproject/.omc/state/market-cache.json")

# 매일 캐시 갱신할 주요 ticker
WATCHED_TICKERS = [
    "VOO", "SPY", "VTI", "VT", "QQQ", "QQQM",
    "SCHD", "JEPI", "JEPQ", "QYLD", "VYM",
    "BND", "TLT", "GLD", "O",
    "AAPL", "MSFT", "NVDA", "GOOGL",
]

DEFAULT_MAX_AGE_HOURS = 24


def load_cache() -> dict:
    """캐시 전체 로드 (없으면 빈 dict)"""
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"캐시 로드 실패: {e}")
        return {}


def save_cache(data: dict):
    """캐시 저장 (atomic write)"""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CACHE_FILE)


def get_cached_data(ticker: str, max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> dict | None:
    """티커의 캐시된 데이터 반환 — 신선하면 dict, 오래됐으면 None"""
    cache = load_cache()
    entry = cache.get(ticker)
    if not entry:
        return None
    fetched_at = entry.get("_fetched_at")
    if not fetched_at:
        return None
    try:
        ts = datetime.fromisoformat(fetched_at)
        age = datetime.now() - ts
        if age > timedelta(hours=max_age_hours):
            logger.debug(f"[{ticker}] 캐시 오래됨 ({age.total_seconds()/3600:.1f}h)")
            return None
        return entry.get("data")
    except Exception:
        return None


def refresh_ticker(ticker: str) -> dict:
    """단일 티커 데이터 재수집 + 캐시 갱신"""
    # _fetch_market_data 내부에서 캐시 체크하지 않도록 force 모드 필요
    from auto_publisher.content_generator import _fetch_market_data_live
    data = _fetch_market_data_live(ticker)
    cache = load_cache()
    cache[ticker] = {
        "_fetched_at": datetime.now().isoformat(),
        "data": data,
    }
    save_cache(cache)
    return data


def refresh_all(tickers: list[str] = None) -> dict:
    """전체 watched 티커 재수집 — n8n 06:00 cron에서 호출"""
    tickers = tickers or WATCHED_TICKERS
    summary = {"success": 0, "failed": 0, "tickers": {}, "started_at": datetime.now().isoformat()}
    for t in tickers:
        try:
            data = refresh_ticker(t)
            if data:
                summary["success"] += 1
                summary["tickers"][t] = {
                    "price": data.get("current_price"),
                    "div_yield": data.get("dividend_yield_pct"),
                }
            else:
                summary["failed"] += 1
                summary["tickers"][t] = {"error": "no_data"}
        except Exception as e:
            summary["failed"] += 1
            summary["tickers"][t] = {"error": str(e)[:100]}
            logger.warning(f"[{t}] 캐시 갱신 실패: {e}")

    summary["finished_at"] = datetime.now().isoformat()
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = refresh_all()
    print(json.dumps(result, ensure_ascii=False, indent=2))
