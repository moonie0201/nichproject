"""
다이나믹 토픽 트리거 — 매일 시장 이벤트 스캔하여 시의성 있는 토픽 자동 생성
"""
import json
import logging
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

# 모니터링할 종목 (한국 투자자 관심)
WATCHED_TICKERS = {
    "blog": ["VOO", "QQQ", "SCHD", "JEPI", "TQQQ"],
    "analysis": ["VOO", "SPY", "QQQ", "SCHD", "JEPI", "VT", "BND"],
}

def scan_market_events() -> list[dict]:
    """yfinance로 시장 이벤트 스캔, 토픽 후보 반환"""
    import yfinance as yf
    events = []
    today = date.today().isoformat()

    # 1) VIX 공포지수 체크
    try:
        vix = yf.Ticker("^VIX")
        hist = yf.download("^VIX", period="5d", progress=False, auto_adjust=True)
        if not hist.empty:
            close = hist["Close"]
            if hasattr(close, "squeeze"):
                close = close.squeeze()
            current = float(close.iloc[-1])
            week_ago = float(close.iloc[0]) if len(close) >= 5 else current
            change_pct = (current / week_ago - 1) * 100 if week_ago else 0

            if current > 28:
                events.append({
                    "id": f"dyn-vix-spike-{today}",
                    "topic": f"공포지수 VIX {current:.1f} 돌파 — 이럴 때 ETF 매수해도 될까?",
                    "keywords": ["VIX", "공포지수", "변동성", "ETF 매수 타이밍"],
                    "category": "시장 이벤트",
                    "type": "blog",
                    "priority": "urgent",
                    "trigger": f"VIX={current:.1f}",
                })
            elif change_pct > 30:
                events.append({
                    "id": f"dyn-vix-surge-{today}",
                    "topic": f"VIX 1주만에 +{change_pct:.0f}% 급등 — 시장은 무엇을 두려워하나",
                    "keywords": ["VIX", "변동성 급등", "시장 분석"],
                    "category": "시장 이벤트",
                    "type": "analysis_topic",
                    "priority": "urgent",
                    "trigger": f"VIX +{change_pct:.0f}% in 5d",
                })
    except Exception as e:
        logger.warning(f"VIX scan 실패: {e}")

    # 2) 주요 ETF 큰 가격 변동 (1일 ±3% 이상)
    for ticker in ["VOO", "QQQ", "SCHD"]:
        try:
            hist = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
            if hist.empty or len(hist) < 2:
                continue
            close = hist["Close"]
            if hasattr(close, "squeeze"):
                close = close.squeeze()
            today_close = float(close.iloc[-1])
            yesterday_close = float(close.iloc[-2])
            change = (today_close / yesterday_close - 1) * 100

            if change <= -3:
                events.append({
                    "id": f"dyn-{ticker.lower()}-drop-{today}",
                    "topic": f"{ticker} 하루만에 {change:.1f}% 급락 — 줍줍 기회인가 추가 하락 신호인가",
                    "keywords": [ticker, f"{ticker} 급락", "ETF 하락", "매수 타이밍"],
                    "category": "시장 이벤트",
                    "type": "analysis_topic",
                    "priority": "urgent",
                    "trigger": f"{ticker} {change:.1f}% 1d",
                })
            elif change >= 3:
                events.append({
                    "id": f"dyn-{ticker.lower()}-surge-{today}",
                    "topic": f"{ticker} 하루만에 +{change:.1f}% 급등 — 추격매수 타이밍 분석",
                    "keywords": [ticker, f"{ticker} 급등", "ETF 상승", "추격매수"],
                    "category": "시장 이벤트",
                    "type": "analysis_topic",
                    "priority": "urgent",
                    "trigger": f"{ticker} +{change:.1f}% 1d",
                })
        except Exception as e:
            logger.warning(f"{ticker} scan 실패: {e}")

    # 3) 배당 ETF 새 배당 발표 (당일 ex-div date)
    for ticker in ["SCHD", "JEPI", "VYM", "JEPQ"]:
        try:
            t = yf.Ticker(ticker)
            divs = t.dividends
            if divs is None or len(divs) == 0:
                continue
            last_div_date = divs.index[-1].date()
            last_div_amount = float(divs.iloc[-1])
            days_ago = (date.today() - last_div_date).days

            # 최근 7일 이내 배당 발표
            if 0 <= days_ago <= 7:
                # 이전 동기간 배당과 비교
                if len(divs) >= 5:
                    prev_div = float(divs.iloc[-5])  # 1년 전 같은 분기
                    growth_pct = (last_div_amount / prev_div - 1) * 100 if prev_div else 0
                    direction = "인상" if growth_pct > 0 else "삭감"
                    events.append({
                        "id": f"dyn-{ticker.lower()}-div-{last_div_date.isoformat()}",
                        "topic": f"{ticker} 분기 배당 ${last_div_amount:.4f} 발표 — 작년 대비 {growth_pct:+.1f}% {direction}",
                        "keywords": [ticker, f"{ticker} 배당", "배당 발표", "배당 성장률"],
                        "category": "배당 이벤트",
                        "type": "blog",
                        "priority": "urgent",
                        "trigger": f"{ticker} ex-div {last_div_date}",
                    })
        except Exception as e:
            logger.warning(f"{ticker} dividend scan 실패: {e}")

    return events


def inject_dynamic_topics(lang: str = "ko") -> int:
    """오늘 스캔된 이벤트들을 토픽 큐 앞쪽에 우선순위 삽입. 중복 방지. 추가된 개수 반환."""
    topics_file = DATA_DIR / f"topics_{lang}.json"
    if not topics_file.exists():
        return 0

    topics = json.loads(topics_file.read_text(encoding="utf-8"))
    existing_ids = {t["id"] for t in topics}

    # ko 언어만 일단 지원 (다른 언어는 추후 확장)
    if lang != "ko":
        logger.info(f"[{lang}] 다이나믹 토픽은 ko만 지원합니다.")
        return 0

    events = scan_market_events()
    added = 0
    for ev in events:
        if ev["id"] in existing_ids:
            continue
        # urgent 토픽은 큐 맨 앞에 삽입
        topics.insert(0, ev)
        added += 1
        logger.info(f"다이나믹 토픽 추가: [{ev['trigger']}] {ev['topic']}")

    if added > 0:
        topics_file.write_text(
            json.dumps(topics, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    return added


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    n = inject_dynamic_topics("ko")
    print(f"추가된 다이나믹 토픽: {n}개")
