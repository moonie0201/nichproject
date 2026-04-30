"""
Market Analyzer — ai-hedge-fund + yfinance 기반 주식 분석
선택한 투자자 에이전트들의 BUY/SELL/HOLD 시그널과 근거를 반환
"""

import logging
import os
import re as _re
import sys
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_INJECTION_PATTERN = _re.compile(
    r"\b(ignore|previous|system|tool|instruction|prompt|override)\b",
    _re.IGNORECASE,
)


def _sanitize_headlines(headlines: list[str]) -> list[str]:
    """LLM 프롬프트 인젝션 방어: 위험 패턴 필터링 + XML 태그 감싸기."""
    safe = []
    for h in headlines:
        if _INJECTION_PATTERN.search(h):
            continue
        safe.append(f"<headline>{h}</headline>")
    return safe

AI_HEDGE_FUND_DIR = Path(__file__).parent.parent / "ai_hedge_fund"

# 기본 분석 에이전트 (속도 우선 5개)
DEFAULT_ANALYSTS = [
    "warren_buffett",
    "technical_analyst",
    "fundamentals_analyst",
    "news_sentiment_analyst",
    "sentiment_analyst",
]

# 언어별 기본 티커
LANG_TICKERS: dict[str, list[str]] = {
    "ko": ["VOO", "SPY", "QQQ"],
    "en": ["VOO", "SCHD", "QQQ"],
    "ja": ["VOO", "EWJ", "QQQ"],
    "vi": ["VOO", "VWO"],
    "id": ["VOO", "EEM"],
}


def run_analysis(
    ticker: str,
    analysts: list[str] | None = None,
    lookback_days: int = 180,
) -> dict:
    """
    ai-hedge-fund로 단일 티커 분석

    Returns:
        {
            ticker, final_action, decisions,
            analyst_signals: {analyst: {signal, confidence, reasoning}},
            news_headlines: [str, ...]
        }
    """
    analysts = analysts or DEFAULT_ANALYSTS

    # ai-hedge-fund 경로를 sys.path에 추가
    src_dir = str(AI_HEDGE_FUND_DIR / "src")
    hedge_dir = str(AI_HEDGE_FUND_DIR)
    for p in [src_dir, hedge_dir]:
        if p not in sys.path:
            sys.path.insert(0, p)

    # OpenRouter API 키를 OPENAI 형식으로 설정 (ai-hedge-fund OpenRouter 지원)
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if not openrouter_key:
        raise RuntimeError("OPENROUTER_API_KEY 환경변수 없음")

    # ai-hedge-fund 임포트 (sys.path 설정 후)
    from src.main import run_hedge_fund

    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=lookback_days)).isoformat()

    portfolio = {
        "cash": 100000.0,
        "margin_requirement": 0.0,
        "margin_used": 0.0,
        "positions": {
            ticker: {
                "long": 0, "short": 0,
                "long_cost_basis": 0.0, "short_cost_basis": 0.0,
                "short_margin_used": 0.0,
            }
        },
        "realized_gains": {ticker: {"long": 0.0, "short": 0.0}},
    }

    ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "google/gemini-2.0-flash-exp:free")
    ANALYSIS_PROVIDER = os.getenv("ANALYSIS_PROVIDER", "OpenRouter")
    ANALYSIS_OLLAMA_MODEL = os.getenv("ANALYSIS_OLLAMA_MODEL", "gemma4:e4b-it-bf16")

    logger.info(f"[{ticker}] ai-hedge-fund 분석 시작 (에이전트: {analysts}, 모델: {ANALYSIS_MODEL})")

    try:
        result = run_hedge_fund(
            tickers=[ticker],
            start_date=start_date,
            end_date=end_date,
            portfolio=portfolio,
            show_reasoning=True,
            selected_analysts=analysts,
            model_name=ANALYSIS_MODEL,
            model_provider=ANALYSIS_PROVIDER,
        )
    except Exception as e:
        logger.warning(f"[{ticker}] {ANALYSIS_MODEL} 실패, ollama 폴백: {e}")
        result = run_hedge_fund(
            tickers=[ticker],
            start_date=start_date,
            end_date=end_date,
            portfolio=portfolio,
            show_reasoning=True,
            selected_analysts=analysts,
            model_name=ANALYSIS_OLLAMA_MODEL,
            model_provider="Ollama",
        )

    decisions = result.get("decisions") or {}
    analyst_signals = result.get("analyst_signals") or {}

    # 티커별 최종 결정 추출
    ticker_decision = {}
    if isinstance(decisions, dict):
        ticker_decision = decisions.get(ticker, decisions)

    final_action = "HOLD"
    if isinstance(ticker_decision, dict):
        action = ticker_decision.get("action", "").upper()
        if action in ("BUY", "SELL", "HOLD"):
            final_action = action

    # 에이전트별 시그널 정리
    signals: dict[str, dict] = {}
    for agent_key, agent_data in analyst_signals.items():
        ticker_data = agent_data.get(ticker, agent_data)
        if isinstance(ticker_data, dict):
            signals[agent_key] = {
                "signal": ticker_data.get("signal", "neutral"),
                "confidence": ticker_data.get("confidence", 0),
                "reasoning": ticker_data.get("reasoning", ""),
            }

    # 최근 뉴스 헤드라인 (yfinance) — 프롬프트 인젝션 방어 적용
    news_headlines = _sanitize_headlines(_fetch_news_headlines(ticker))

    # yfinance 실시간 지표 (차트·프롬프트 공유용)
    from auto_publisher.content_generator import _fetch_market_data
    mkt_data = _fetch_market_data(ticker)

    return {
        "ticker": ticker,
        "final_action": final_action,
        "decisions": ticker_decision,
        "analyst_signals": signals,
        "news_headlines": news_headlines,
        "analysis_date": end_date,
        "mkt_data": mkt_data,
    }


def _fetch_news_headlines(ticker: str, limit: int = 5) -> list[str]:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        raw = t.news or []
        headlines = []
        for item in raw[:limit]:
            content = item.get("content", {})
            title = content.get("title") or item.get("title", "")
            if title:
                headlines.append(title)
        return headlines
    except Exception as e:
        logger.warning(f"뉴스 헤드라인 가져오기 실패 {ticker}: {e}")
        return []
