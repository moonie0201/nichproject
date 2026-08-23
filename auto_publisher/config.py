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
# 신규 발행 대상. ja/vi/id 는 기존 URL 유지를 위해 아래 사전에는 남기되 발행에서 제외한다.
SUPPORTED_LANGUAGES = ["ko", "en"]
RETIRED_LANGUAGES = ["ja", "vi", "id"]
LANGUAGE_NICHES = {
    "ko": "투자/재테크",
    "en": "personal finance & investing",
    "ja": "投資・資産運用",
    "vi": "đầu tư tài chính",
    "id": "investasi & keuangan pribadi",
}

# 자본시장법 §445 / 금융소비자보호법 §46 / 유사수신법 §2 위반 표현
BANNED_KO_FINANCIAL = [
    # 자본시장법 §445 — 특정 종목 매수/매도 추천
    "매수 추천", "매도 추천", "매수 타이밍", "매도 타이밍",
    "지금 사야", "지금 팔아야", "지금 매수", "지금 매도",
    "강력 매수", "강력 매도", "매수 시그널", "매도 시그널",
    "필승 종목", "추천 종목", "확정 매수",
    # 금융소비자보호법 §46 + 유사수신법 §2 — 수익/원금 보장
    "원금 보장", "수익 보장", "손실 보장", "확정 수익",
    "보장된 수익", "안전한 투자", "100% 안전",
    # 과장/선동 표현
    "필승", "대박", "폭락 임박", "폭등 임박",
    "지금이 마지막 기회", "놓치면 후회",
]

BANNED_EN_FINANCIAL = [
    "buy now", "sell now", "must buy", "must sell",
    "guaranteed return", "guaranteed profit", "risk-free",
    "100% safe", "can't lose", "sure thing",
]

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
        # 1인칭 정책 (2026-08-21 조정)
        # 이 사이트는 AI 생성임을 about/authors 에서 공개하고 human_reviewed=false 다.
        # 따라서 "제가 직접 개설해보니" 류의 개인 경험 서술은 사실이 아니므로 계속 막는다.
        # 반면 발행 주체로서의 1인칭 복수("저희는", "저희 계산기로 보면")는 참이고
        # E-E-A-T 의 Who 신호에 기여하므로 허용한다. 실제 경험 서술은 사람이 직접
        # 글을 손볼 때만 들어가야 한다.
        "내가",
        "제가",
        "저는",
        # 가상 페르소나 — 지어낸 인물은 어떤 경우에도 금지
        "이재훈",
        "34세 직장인",
        # 클리셰 (이렇게/이런 식으로는 일반 한국어라 제외했다)
        "살펴보기",
        "일반적으로 알려진",
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

    primary_backend = os.getenv("LLM_PRIMARY_BACKEND", "").lower()
    cli_backend = primary_backend in ("gemini", "ollama", "claude", "codex")
    ollama_enabled = primary_backend == "ollama" or bool(os.getenv("OLLAMA_HOST", ""))
    if not GOOGLE_API_KEY and not OPENROUTER_API_KEY and not cli_backend and not ollama_enabled:
        errors.append("OPENROUTER_API_KEY, GOOGLE_API_KEY, 또는 LLM_PRIMARY_BACKEND가 설정되지 않았습니다.")

    # TISTORY: 자동으로 비활성화 (자격증명 누락 시) — 오류 로그 안 함
    if TISTORY_ENABLED:
        has_creds = TISTORY_KAKAO_ID and TISTORY_KAKAO_PW and TISTORY_BLOG_NAME
        if not has_creds:
            import logging
            logging.getLogger(__name__).info("Tistory disabled (credentials not configured)")

    return errors
