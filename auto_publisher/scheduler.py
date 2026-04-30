"""
스케줄러 — APScheduler 기반 정기 발행
"""

import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from auto_publisher.config import PUBLISH_SCHEDULE_HOUR, PUBLISH_SCHEDULE_MINUTE

logger = logging.getLogger(__name__)


def run_scheduled_publish():
    """스케줄된 발행 작업 실행"""
    from auto_publisher.main import do_publish
    try:
        do_publish()
    except Exception as e:
        logger.error(f"스케줄 발행 실패: {e}", exc_info=True)


def run_intraday_publish():
    """장중 시황 발행 (22:30 KST, 평일만)"""
    try:
        from auto_publisher.market_intraday import publish_intraday
        result = publish_intraday()
        if result.get("skipped"):
            logger.info(f"[intraday] 스킵: {result.get('reason')}")
        else:
            logger.info(f"[intraday] 발행 완료: {list(result.get('results', {}).keys())}")
    except Exception as e:
        logger.error(f"[intraday] 발행 실패: {e}", exc_info=True)


def run_daily_prediction_verify():
    """매일 06:00 KST: 60일 경과 예측 검증 + JSON 내보내기"""
    try:
        from auto_publisher.prediction_tracker import PredictionTracker
        tracker = PredictionTracker()
        pending = tracker.pending_verification()
        if not pending:
            logger.info("[prediction] 검증 대기 레코드 없음")
            return
        # pending ticker의 현재가 yfinance로 조회
        tickers = list({r["ticker"] for r in pending})
        import yfinance as yf
        current_prices = {}
        for t in tickers:
            try:
                hist = yf.Ticker(t).history(period="1d")
                if not hist.empty:
                    current_prices[t] = float(hist["Close"].iloc[-1])
            except Exception as e:
                logger.warning(f"[prediction] {t} 가격 조회 실패: {e}")
        results = tracker.run_verification(current_prices)
        tracker.export_json()
        logger.info(f"[prediction] 검증 완료: {len(results)}건")
    except Exception as e:
        logger.error(f"[prediction] 검증 실패: {e}", exc_info=True)


def start_scheduler():
    """스케줄러 데몬 시작 (KST 기준)"""
    scheduler = BlockingScheduler(timezone="Asia/Seoul")

    # 일반 콘텐츠 발행 (매일 09:00 KST)
    trigger = CronTrigger(
        hour=PUBLISH_SCHEDULE_HOUR,
        minute=PUBLISH_SCHEDULE_MINUTE,
        timezone="Asia/Seoul",
    )
    scheduler.add_job(
        run_scheduled_publish,
        trigger=trigger,
        id="auto_publish",
        name="자동 콘텐츠 발행",
        replace_existing=True,
    )

    # 장중 시황 발행 (평일 22:30 KST — 미국 개장 30분 후)
    intraday_trigger = CronTrigger(
        hour=22,
        minute=30,
        day_of_week="mon-fri",
        timezone="Asia/Seoul",
    )
    scheduler.add_job(
        run_intraday_publish,
        trigger=intraday_trigger,
        id="intraday_publish",
        name="장중 시황 발행",
        replace_existing=True,
    )

    # 예측 트랙레코드 자동 검증 (매일 06:00 KST)
    scheduler.add_job(
        run_daily_prediction_verify,
        CronTrigger(hour=6, minute=0, timezone="Asia/Seoul"),
        id="prediction_verify",
        name="예측 트랙레코드 검증",
        replace_existing=True,
    )

    # 종료 시그널 처리
    def shutdown(signum, frame):
        logger.info("스케줄러 종료 중...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info(
        f"스케줄러 시작 — 매일 {PUBLISH_SCHEDULE_HOUR:02d}:{PUBLISH_SCHEDULE_MINUTE:02d} KST 발행"
        " | 평일 22:30 KST 장중 시황 발행"
    )
    print(f"스케줄러 시작 — 매일 {PUBLISH_SCHEDULE_HOUR:02d}:{PUBLISH_SCHEDULE_MINUTE:02d} KST 발행")
    print("장중 시황: 평일 22:30 KST")
    print("종료: Ctrl+C")

    scheduler.start()
