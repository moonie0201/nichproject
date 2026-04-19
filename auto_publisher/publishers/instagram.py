"""
Phase 2 — Meta Graph API integration

Instagram 발행 모듈 (스텁)
실제 구현은 Phase 2에서 Meta Graph API 기반으로 진행
"""

import logging

logger = logging.getLogger(__name__)


class InstagramPublisher:
    """Instagram 발행기 (Phase 2 스텁)"""

    def __init__(self, access_token: str = "", business_id: str = ""):
        self.access_token = access_token
        self.business_id = business_id

    def publish_image_post(self, image_url: str, caption: str, hashtags: list[str] | None = None) -> dict:
        """이미지 게시물 발행 (미구현)"""
        logger.warning("Instagram 발행은 Phase 2에서 구현 예정입니다.")
        raise NotImplementedError("Instagram 발행은 Phase 2에서 구현 예정")

    def publish_carousel(self, media_urls: list[str], caption: str) -> dict:
        """캐러셀 게시물 발행 (미구현)"""
        logger.warning("Instagram 캐러셀 발행은 Phase 2에서 구현 예정입니다.")
        raise NotImplementedError("Instagram 캐러셀 발행은 Phase 2에서 구현 예정")
