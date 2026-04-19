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


def start_scheduler():
    """스케줄러 데몬 시작 (KST 기준)"""
    scheduler = BlockingScheduler(timezone="Asia/Seoul")

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

    # 종료 시그널 처리
    def shutdown(signum, frame):
        logger.info("스케줄러 종료 중...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info(
        f"스케줄러 시작 — 매일 {PUBLISH_SCHEDULE_HOUR:02d}:{PUBLISH_SCHEDULE_MINUTE:02d} KST 발행"
    )
    print(f"스케줄러 시작 — 매일 {PUBLISH_SCHEDULE_HOUR:02d}:{PUBLISH_SCHEDULE_MINUTE:02d} KST 발행")
    print("종료: Ctrl+C")

    scheduler.start()
