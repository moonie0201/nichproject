"""
Phase 3 — YouTube Data API v3 + TTS video generation

YouTube 발행 모듈 (스텁)
실제 구현은 Phase 3에서 YouTube Data API v3 + TTS 기반으로 진행
"""

import logging

logger = logging.getLogger(__name__)


class YoutubePublisher:
    """YouTube 발행기 (Phase 3 스텁)"""

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret

    def upload_video(self, video_path: str, title: str, description: str,
                     tags: list[str] | None = None) -> dict:
        """영상 업로드 (미구현)"""
        logger.warning("YouTube 업로드는 Phase 3에서 구현 예정입니다.")
        raise NotImplementedError("YouTube 업로드는 Phase 3에서 구현 예정")

    def upload_short(self, video_path: str, title: str, description: str) -> dict:
        """숏츠 업로드 (미구현)"""
        logger.warning("YouTube Shorts 업로드는 Phase 3에서 구현 예정입니다.")
        raise NotImplementedError("YouTube Shorts 업로드는 Phase 3에서 구현 예정")
