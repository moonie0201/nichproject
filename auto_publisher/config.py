"""
설정 관리 — .env 파일에서 모든 설정을 로드
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일 로드 (워크스페이스 → 프로젝트 로컬 순으로 로드, 로컬이 우선)
ENV_PATH = Path("/home/mh/ocstorage/workspace/.env")
LOCAL_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)
load_dotenv(LOCAL_ENV_PATH, override=True)


# --- AI API (OpenRouter 기본, GOOGLE_API_KEY 호환 유지) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# --- Tistory (Playwright 브라우저 자동화) ---
TISTORY_BLOG_NAME = os.getenv("TISTORY_BLOG_NAME", "")
TISTORY_KAKAO_ID = os.getenv("TISTORY_KAKAO_ID", "")
TISTORY_KAKAO_PW = os.getenv("TISTORY_KAKAO_PW", "")

# --- Twitter/X (Phase 2) ---
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")

# --- Instagram (Phase 2) ---
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ID = os.getenv("INSTAGRAM_BUSINESS_ID", "")

# --- YouTube (Phase 3) ---
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")

# --- 스케줄 설정 ---
PUBLISH_SCHEDULE_HOUR = int(os.getenv("PUBLISH_SCHEDULE_HOUR", "9"))
PUBLISH_SCHEDULE_MINUTE = int(os.getenv("PUBLISH_SCHEDULE_MINUTE", "0"))
CONTENT_NICHE = os.getenv("CONTENT_NICHE", "투자/재테크")

# --- 다국어 설정 ---
SUPPORTED_LANGUAGES = ["ko", "en", "ja", "vi", "id"]
LANGUAGE_NICHES = {
    "ko": "투자/재테크",
    "en": "personal finance & investing",
    "ja": "投資・資産運用",
    "vi": "đầu tư tài chính",
    "id": "investasi & keuangan pribadi",
}

FORBIDDEN_PHRASES = {
    "ko": [
        "완벽 가이드",
        "총정리",
        "살펴보겠습니다",
        "알아보겠습니다",
        "정리해 드리겠습니다",
        "도움이 되셨으면",
        "마치며",
        "이상으로",
        "해드리겠습니다",
        "결론적으로",
        "다음과 같이",
        "앞서 살펴본 바와 같이",
        "이렇게",
        "이런 식으로",
        "내가",
        "제가",
        "저는",
        "저희는",
        "이재훈",
        "34세 직장인",
    ],
    "en": [
        "In conclusion",
        "In summary",
        "It is worth noting",
        "It is important to note",
        "As mentioned above",
    ],
    "ja": ["まとめると", "以上を踏まえて", "ぜひ参考にしてください", "いかがでしたか"],
    "vi": ["Tóm lại", "Hy vọng bài viết", "Trên đây là"],
    "id": ["Kesimpulannya", "Demikianlah", "Semoga bermanfaat", "Sekian"],
}

# --- 플랫폼 활성화 토글 ---
TISTORY_ENABLED = os.getenv("TISTORY_ENABLED", "true").lower() == "true"
TWITTER_ENABLED = os.getenv("TWITTER_ENABLED", "false").lower() == "true"
INSTAGRAM_ENABLED = os.getenv("INSTAGRAM_ENABLED", "false").lower() == "true"
YOUTUBE_ENABLED = os.getenv("YOUTUBE_ENABLED", "false").lower() == "true"

# --- 경로 설정 ---
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
TOPICS_FILE = DATA_DIR / "topics.json"
HISTORY_FILE = DATA_DIR / "published_history.json"
LOG_FILE = PROJECT_DIR / "auto_publisher.log"


def validate_config():
    """필수 설정값 검증"""
    errors = []

    if not GOOGLE_API_KEY and not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY 또는 GOOGLE_API_KEY가 설정되지 않았습니다.")

    if TISTORY_ENABLED:
        if not TISTORY_KAKAO_ID or not TISTORY_KAKAO_PW:
            errors.append("TISTORY_KAKAO_ID / TISTORY_KAKAO_PW가 설정되지 않았습니다.")
        if not TISTORY_BLOG_NAME:
            errors.append("TISTORY_BLOG_NAME이 설정되지 않았습니다.")

    return errors
