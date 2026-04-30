"""FRED API 거시경제 데이터 모듈."""
import logging
import os
from datetime import date, timedelta

logger = logging.getLogger(__name__)

FRED_SERIES = {
    "us10y": "DGS10",
    "vix": "VIXCLS",
    "dxy": "DTWEXBGS",
}

def fetch_macro_data(api_key: str | None = None) -> dict:
    """FRED API에서 거시 지표 최신값 조회.

    Returns: {"us10y": 4.32, "vix": 18.5, "dxy": 104.2} or {}
    """
    key = api_key or os.getenv("FRED_API_KEY", "")
    if not key:
        logger.debug("FRED_API_KEY 미설정 — 거시 데이터 스킵")
        return {}

    try:
        import requests
        result = {}
        for label, series_id in FRED_SERIES.items():
            end = date.today().isoformat()
            start = (date.today() - timedelta(days=7)).isoformat()
            resp = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": series_id,
                    "api_key": key,
                    "file_type": "json",
                    "observation_start": start,
                    "observation_end": end,
                    "sort_order": "desc",
                    "limit": 1,
                },
                timeout=10,
            )
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            if obs:
                v = obs[0].get("value", ".")
                if v != ".":
                    result[label] = round(float(v), 4)
        return result
    except Exception as e:
        logger.warning(f"FRED 데이터 조회 실패: {e}")
        return {}


def macro_block_text(macro: dict) -> str:
    """거시 데이터를 LLM 프롬프트용 텍스트 블록으로 변환."""
    if not macro:
        return ""
    lines = ["[거시경제 지표 (FRED)]"]
    labels = {"us10y": "미국 10년물 국채 수익률", "vix": "VIX 변동성 지수", "dxy": "달러 인덱스(DXY)"}
    for k, v in macro.items():
        lines.append(f"- {labels.get(k, k)}: {v}")
    return "\n".join(lines)
