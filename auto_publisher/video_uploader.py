"""
YouTube Data API v3 업로더 (OAuth 2.0)
- 일 100건 무료 한도 (롱폼 + 쇼츠 합산)
- 사전 준비:
  1) Google Cloud Console → YouTube Data API v3 활성화
  2) OAuth 2.0 클라이언트 ID (Desktop) 생성
  3) client_secrets.json → /home/mh/ocstorage/workspace/nichproject/.youtube_secrets/client_secrets.json 저장
  4) 첫 실행 시 브라우저 인증 → token.json 저장

TikTok Content Posting API v2 업로더
- 사전 준비:
  1) TikTok Developer Portal → app 생성, video.publish + user.info.basic scope 활성화
  2) tiktok_auth_setup() 실행하여 .tiktok_secrets/token.json 생성
  3) .env에 TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_ENABLED=true 설정
"""

import json
import logging
import math
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── TikTok ───────────────────────────────────────────────────────────────────
TIKTOK_SECRETS_DIR = Path(os.getenv("TIKTOK_SECRETS_DIR", str(Path(__file__).parent.parent / ".tiktok_secrets")))
TIKTOK_TOKEN_FILE = TIKTOK_SECRETS_DIR / "token.json"

SECRETS_DIR = Path(os.getenv("YOUTUBE_SECRETS_DIR", str(Path(__file__).parent.parent / ".youtube_secrets")))
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

    media = MediaFileUpload(str(video_path), chunksize=5 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    max_retries = 10
    for _attempt in range(max_retries):
        status, response = request.next_chunk()
        if status:
            logger.info(f"업로드 진행: {int(status.progress() * 100)}%")
        if response is not None:
            break
    else:
        raise RuntimeError("YouTube 업로드 실패: 청크 전송 최대 재시도 초과")

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


def _load_tiktok_credentials() -> dict:
    """token.json 읽고 필요시 갱신. {'access_token': ..., 'open_id': ...} 반환."""
    import urllib.request

    if not TIKTOK_TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"TikTok 토큰 없음: {TIKTOK_TOKEN_FILE}\n"
            "tiktok_auth_setup()을 먼저 실행하여 인증을 완료하세요."
        )

    token = json.loads(TIKTOK_TOKEN_FILE.read_text(encoding="utf-8"))

    # 만료 300초 전에 갱신
    if token.get("expires_at", 0) < time.time() + 300:
        client_key = os.getenv("TIKTOK_CLIENT_KEY", "")
        client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
        if not client_key or not client_secret:
            raise RuntimeError("TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET 환경변수가 설정되지 않았습니다.")

        payload = json.dumps({
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        }).encode()
        req = urllib.request.Request(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())

        token["access_token"] = data["access_token"]
        token["refresh_token"] = data.get("refresh_token", token["refresh_token"])
        token["expires_at"] = time.time() + data["expires_in"]
        token["open_id"] = data.get("open_id", token.get("open_id", ""))
        TIKTOK_SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        TIKTOK_TOKEN_FILE.write_text(json.dumps(token, indent=2), encoding="utf-8")
        logger.info("TikTok 토큰 갱신 완료")

    return {"access_token": token["access_token"], "open_id": token.get("open_id", "")}


def tiktok_auth_setup():
    """TikTok OAuth 인증 흐름 — 브라우저 인증 후 token.json 저장."""
    import urllib.parse
    import urllib.request
    from http.server import BaseHTTPRequestHandler, HTTPServer

    client_key = os.getenv("TIKTOK_CLIENT_KEY", "")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
    if not client_key or not client_secret:
        raise RuntimeError("TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET 환경변수를 먼저 설정하세요.")

    redirect_uri = "http://localhost:8080/callback"
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={client_key}"
        f"&scope=video.publish,user.info.basic"
        f"&response_type=code"
        f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
        f"&state=investiqs"
    )
    print(f"\n아래 URL을 브라우저에서 열어 TikTok 계정 인증을 완료하세요:\n\n{auth_url}\n")

    code_holder = {}

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # suppress access logs

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                code_holder["code"] = params["code"][0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h2>TikTok auth complete. You can close this tab.</h2>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code parameter.")

    server = HTTPServer(("", 8080), _Handler)
    server.timeout = 120
    print("localhost:8080에서 콜백 대기 중 (2분 타임아웃)...")
    server.handle_request()

    code = code_holder.get("code")
    if not code:
        raise RuntimeError("인증 코드를 받지 못했습니다. 다시 시도하세요.")

    payload = json.dumps({
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }).encode()
    req = urllib.request.Request(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    token = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": time.time() + data["expires_in"],
        "open_id": data.get("open_id", ""),
    }
    TIKTOK_SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    TIKTOK_TOKEN_FILE.write_text(json.dumps(token, indent=2), encoding="utf-8")
    print(f"TikTok 인증 성공! 토큰 저장 완료: {TIKTOK_TOKEN_FILE}")


def upload_tiktok(
    video_path: Path,
    title: str,
    tags: list = None,
    privacy: str = "PUBLIC_TO_EVERYONE",
    disable_duet: bool = False,
    disable_comment: bool = False,
    disable_stitch: bool = False,
) -> dict:
    """TikTok Content Posting API v2로 mp4 업로드. {'publish_id': ..., 'status': 'published', 'url': ...} 반환."""
    import urllib.request

    CHUNK_SIZE = 10 * 1024 * 1024  # 10MB

    creds = _load_tiktok_credentials()
    access_token = creds["access_token"]
    open_id = creds["open_id"]

    video_path = Path(video_path)
    file_size = video_path.stat().st_size
    total_chunks = math.ceil(file_size / CHUNK_SIZE)

    # 태그를 제목에 append (최대 5개, 전체 150자 제한)
    full_title = title
    if tags:
        hashtags = " ".join(f"#{t}" for t in tags[:5])
        full_title = f"{title} {hashtags}"[:150]
    else:
        full_title = title[:150]

    # ─── 1) Init ───
    init_body = json.dumps({
        "post_info": {
            "title": full_title,
            "privacy_level": privacy,
            "disable_duet": disable_duet,
            "disable_comment": disable_comment,
            "disable_stitch": disable_stitch,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": CHUNK_SIZE,
            "total_chunk_count": total_chunks,
        },
    }).encode()

    req = urllib.request.Request(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        data=init_body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        init_data = json.loads(resp.read().decode())

    upload_url = init_data["data"]["upload_url"]
    publish_id = init_data["data"]["publish_id"]
    logger.info(f"TikTok init 완료: publish_id={publish_id}")

    # ─── 2) Chunk upload ───
    with open(video_path, "rb") as f:
        for chunk_idx in range(total_chunks):
            start = chunk_idx * CHUNK_SIZE
            chunk = f.read(CHUNK_SIZE)
            end = start + len(chunk) - 1
            put_req = urllib.request.Request(
                upload_url,
                data=chunk,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Type": "video/mp4",
                },
                method="PUT",
            )
            with urllib.request.urlopen(put_req, timeout=120) as put_resp:
                _ = put_resp.read()
            logger.info(f"TikTok 청크 업로드: {chunk_idx + 1}/{total_chunks}")

    # ─── 3) Poll status ───
    status_body = json.dumps({"publish_id": publish_id}).encode()
    for poll_idx in range(60):
        time.sleep(5)
        poll_req = urllib.request.Request(
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            data=status_body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(poll_req, timeout=30) as poll_resp:
            poll_data = json.loads(poll_resp.read().decode())

        status = poll_data.get("data", {}).get("status", "")
        logger.info(f"TikTok 상태 폴링 {poll_idx + 1}/60: {status}")

        if status == "PUBLISH_COMPLETE":
            url = f"https://www.tiktok.com/@{open_id}/video/{publish_id}"
            logger.info(f"TikTok 업로드 완료: {url}")
            return {"publish_id": publish_id, "status": "published", "url": url}
        elif status == "FAILED":
            fail_reason = poll_data.get("data", {}).get("fail_reason", "unknown")
            raise RuntimeError(f"TikTok 업로드 실패: {fail_reason}")

    raise RuntimeError(f"TikTok 업로드 타임아웃: publish_id={publish_id} (300초 초과)")


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
