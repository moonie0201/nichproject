"""
Phase 2 — X/Twitter API Free tier integration

Twitter/X 발행 모듈 (스텁)
실제 구현은 Phase 2에서 tweepy 기반으로 진행
"""

import logging

logger = logging.getLogger(__name__)


class TwitterPublisher:
    """Twitter/X 발행기 (Phase 2 스텁)"""

    def __init__(self, api_key: str = "", api_secret: str = "",
                 access_token: str = "", access_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_secret = access_secret

    def publish_tweet(self, text: str) -> dict:
        """단일 트윗 발행 (미구현)"""
        logger.warning("Twitter 발행은 Phase 2에서 구현 예정입니다.")
        raise NotImplementedError("Twitter 발행은 Phase 2에서 구현 예정")

    def publish_thread(self, tweets: list[str]) -> list[dict]:
        """트윗 스레드 발행 (미구현)"""
        logger.warning("Twitter 스레드 발행은 Phase 2에서 구현 예정입니다.")
        raise NotImplementedError("Twitter 스레드 발행은 Phase 2에서 구현 예정")
