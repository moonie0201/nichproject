"""
YouTube Data API v3 업로더 (OAuth 2.0)
- 일 100건 무료 한도 (롱폼 + 쇼츠 합산)
- 사전 준비:
  1) Google Cloud Console → YouTube Data API v3 활성화
  2) OAuth 2.0 클라이언트 ID (Desktop) 생성
  3) client_secrets.json → /home/mh/ocstorage/workspace/nichproject/.youtube_secrets/client_secrets.json 저장
  4) 첫 실행 시 브라우저 인증 → token.json 저장
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SECRETS_DIR = Path("/home/mh/ocstorage/workspace/nichproject/.youtube_secrets")
CLIENT_SECRETS = SECRETS_DIR / "client_secrets.json"
TOKEN_FILE = SECRETS_DIR / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",  # 채널 조회 + 영상 삭제용
]


def _load_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                raise FileNotFoundError(
                    f"client_secrets.json 없음. {CLIENT_SECRETS} 위치에 OAuth 2.0 Desktop 클라이언트 JSON 저장 필요.\n"
                    "Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Desktop Client → JSON 다운로드"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())
    return creds


def upload_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str] = None,
    is_short: bool = False,
    privacy: str = "public",
    category_id: str = "25",
    thumbnail_path: Path | None = None,
    md_path: Path | None = None,  # 썸네일 자동 생성용 .md 경로
) -> dict:
    """mp4 업로드 → {video_id, url, status} 반환. 실패 시 RuntimeError"""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = _load_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    if is_short and "#shorts" not in title.lower():
        title = f"{title} #shorts"
    if is_short and "#shorts" not in description.lower():
        description = f"{description}\n\n#shorts"

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:30],
            "categoryId": category_id,
            "defaultLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"업로드 진행: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    url = f"https://youtube.com/{'shorts/' if is_short else 'watch?v='}{video_id}"
    logger.info(f"YouTube 업로드 완료: {url}")

    # 썸네일 설정
    thumb = _resolve_thumbnail(thumbnail_path, md_path)
    if thumb and thumb.exists():
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb), mimetype="image/png"),
            ).execute()
            logger.info(f"썸네일 설정 완료: {thumb}")
        except Exception as e:
            logger.warning(f"썸네일 설정 실패 (영상 업로드는 성공): {e}")

    return {"video_id": video_id, "url": url, "status": "uploaded", "privacy": privacy}


def _resolve_thumbnail(thumbnail_path: Path | None, md_path: Path | None) -> Path | None:
    """썸네일 경로 확정 — 직접 지정 > md 파일 자동 생성 순"""
    if thumbnail_path and Path(thumbnail_path).exists():
        return Path(thumbnail_path)
    if md_path:
        try:
            from auto_publisher.thumbnail_generator import generate_thumbnail_from_md
            return generate_thumbnail_from_md(Path(md_path))
        except Exception as e:
            logger.warning(f"썸네일 자동 생성 실패: {e}")
    return None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 3:
        print("usage: python -m auto_publisher.video_uploader <mp4> <title>")
        sys.exit(1)
    r = upload_youtube(
        video_path=Path(sys.argv[1]),
        title=sys.argv[2],
        description="InvestIQs 데이터 분석 영상\n\n블로그: https://investiqs.net",
        tags=["ETF", "투자분석"],
        is_short=True,
        privacy="unlisted",  # 테스트는 unlisted
    )
    print(r)
