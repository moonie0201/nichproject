"""Numeric claim fact-checker — 본문 숫자 vs source_data 대조.

문제: LLM이 yfinance 데이터를 받아도 "5년 수익률 90%"처럼 잘못된 숫자를 생성할 수 있음.
기존 verify_rule_based의 substring 검사로는 ±5% 오차 범위 매칭 + 변형 표기 처리 불가.

이 모듈:
- 본문에서 "{N}%" / "{N}원" / "${N}" 패턴 + 인접 문맥 (ticker / 키워드) 추출
- source_data와 ticker/field별 매칭 → tolerance band 벗어나면 mismatch 리포트
- 결과를 verify_rule_based가 critical issue로 통합

Env: NUMERIC_FACT_CHECK_TOLERANCE_PCT (기본 5.0)
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ClaimMismatch:
    ticker: str
    field: str
    claimed: float
    expected: float
    delta_pct: float
    snippet: str = ""

    def __str__(self) -> str:
        return (
            f"{self.ticker}.{self.field}: 본문={self.claimed} vs "
            f"실제={self.expected} (delta={self.delta_pct:+.1f}%)"
        )


# 필드 → 본문에서 찾을 수치 표기 패턴들 + 검증 단위
# (label_alternatives, unit_regex_postfix, multiplier_to_pct=False)
_FIELD_PATTERNS = {
    "current_price": {
        "labels": ["현재가", "가격", "주가"],
        "unit_pattern": r"\$?(\d{1,5}(?:\.\d{1,2})?)",
        "tolerance_pct": 5.0,
    },
    "1y_return_pct": {
        "labels": ["1년 수익률", "1년 수익", "1y", "지난 1년"],
        "unit_pattern": r"([+\-]?\d{1,3}(?:\.\d)?)\s?%",
        "tolerance_pct": 10.0,
    },
    "3y_return_pct": {
        "labels": ["3년 누적", "3년 수익률", "3년간 수익", "3년 수익"],
        "unit_pattern": r"([+\-]?\d{1,3}(?:\.\d)?)\s?%",
        "tolerance_pct": 10.0,
    },
    "5y_return_pct": {
        "labels": ["5년 누적", "5년 수익률", "5년간 수익", "5년 수익"],
        "unit_pattern": r"([+\-]?\d{1,3}(?:\.\d)?)\s?%",
        "tolerance_pct": 10.0,
    },
    "10y_return_pct": {
        "labels": ["10년 누적", "10년 수익률"],
        "unit_pattern": r"([+\-]?\d{1,3}(?:\.\d)?)\s?%",
        "tolerance_pct": 15.0,
    },
    "dividend_yield_pct": {
        "labels": ["배당수익률", "배당률", "배당 수익률"],
        "unit_pattern": r"(\d{1,2}(?:\.\d{1,2})?)\s?%",
        "tolerance_pct": 15.0,
    },
    "expense_ratio_pct": {
        "labels": ["운용보수", "운용 보수", "expense ratio"],
        "unit_pattern": r"(\d{1,2}(?:\.\d{1,3})?)\s?%",
        "tolerance_pct": 20.0,
    },
    "pe_ratio": {
        "labels": ["P/E", "PER", "주가수익비율"],
        "unit_pattern": r"(\d{1,3}(?:\.\d{1,2})?)",
        "tolerance_pct": 10.0,
    },
}


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def check_numeric_claims(
    body_html: str,
    source_data: dict,
    tolerance_pct: float | None = None,
    window_chars: int = 120,
) -> list[ClaimMismatch]:
    """본문에서 수치 클레임 추출 → 가장 가까운 ticker에 귀속 → source_data와 대조.

    매칭 알고리즘:
    1. body에서 모든 ticker 위치 인덱싱
    2. 각 (field, label, claim) 매치마다 가장 가까운 ticker 찾기 (≤ window_chars)
    3. 가까운 ticker의 해당 field expected와 비교, tolerance 초과 시 mismatch

    Args:
        body_html: 검증할 본문 HTML
        source_data: {ticker: {field: value}} (yfinance 검증된 값)
        tolerance_pct: 허용 오차 override (기본 field별 자체 tolerance)
        window_chars: 클레임 위치 기준 ticker 매칭 최대 거리 (기본 120 char)

    Returns:
        list[ClaimMismatch] — 빈 리스트면 모두 통과
    """
    if not source_data:
        return []

    default_tol = float(os.getenv("NUMERIC_FACT_CHECK_TOLERANCE_PCT", "5.0"))
    body = _strip_html(body_html)
    body_lower = body.lower()

    # ticker별 위치 인덱싱
    ticker_positions: dict[str, list[int]] = {}
    for ticker in source_data:
        if not isinstance(source_data[ticker], dict):
            continue
        positions = [
            m.start() for m in re.finditer(rf"\b{re.escape(ticker.lower())}\b", body_lower)
        ]
        if positions:
            ticker_positions[ticker] = positions
    if not ticker_positions:
        return []

    mismatches: list[ClaimMismatch] = []
    # 동일 (ticker, field) 중복 방지
    seen: set[tuple[str, str]] = set()

    for field_name, spec in _FIELD_PATTERNS.items():
        field_tol_default = tolerance_pct if tolerance_pct is not None else (
            spec.get("tolerance_pct") or default_tol
        )

        for label in spec["labels"]:
            pat = re.compile(
                rf"{re.escape(label)}\s*(?:은|는|이|가|:)?\s*{spec['unit_pattern']}",
                re.IGNORECASE,
            )
            for m in pat.finditer(body):
                label_pos = m.start()
                # 가장 가까운 ticker 찾기
                best_ticker = None
                best_dist = window_chars + 1
                for ticker, positions in ticker_positions.items():
                    dist = min(abs(label_pos - p) for p in positions)
                    if dist < best_dist:
                        best_dist = dist
                        best_ticker = ticker
                if best_ticker is None or best_dist > window_chars:
                    continue

                # 그 ticker의 field expected
                expected_raw = source_data[best_ticker].get(field_name)
                if expected_raw is None:
                    continue
                try:
                    expected = float(expected_raw)
                    claimed = float(m.group(1))
                except (TypeError, ValueError, IndexError):
                    continue

                key = (best_ticker, field_name)
                if key in seen:
                    continue

                delta_pct = (claimed - expected) / max(abs(expected), 0.001) * 100
                if abs(delta_pct) > field_tol_default:
                    snippet = body[max(0, label_pos - 30):label_pos + 80].strip()
                    mismatches.append(ClaimMismatch(
                        ticker=best_ticker,
                        field=field_name,
                        claimed=claimed,
                        expected=round(expected, 3),
                        delta_pct=round(delta_pct, 1),
                        snippet=snippet,
                    ))
                    seen.add(key)

    return mismatches
