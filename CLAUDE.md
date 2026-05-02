# investiqs.net Auto Publisher

## 주요 컴포넌트

### 자동 발행 파이프라인
- `auto_publisher/main.py` — 메인 진입점 (run, make-video, translate 등)
- `auto_publisher/content_generator.py` — LLM 콘텐츠 생성 (Gemini CLI 우선, Claude/Codex/Ollama 폴백)
- `auto_publisher/video_composer.py` — ffmpeg 영상 합성 (NVENC GPU)
- `auto_publisher/video_uploader.py` — YouTube + TikTok + Instagram Reels 업로드
- `auto_publisher/topic_manager.py` — 토픽 큐 (auto_refill로 큐 고갈 시 자동 생성)

### n8n + Bridge API
- `n8n/bridge_api.py` — HTTP API (port 8765)
- 27개 워크플로우 활성화 (us_market_wrap, daily_publisher, shorts_auto 등)
- `n8n/ACTIVATION_GUIDE.md` — 활성화 가이드

### Cloudflare 인프라
- Tunnel: `callback.investiqs.net` → localhost:8765 (TikTok OAuth)
- Pages: investiqs.net (Hugo 빌드)
- Functions: web/static/functions/tiktok-callback.js

## 환경변수 (`.env`)
- `OPENROUTER_API_KEY` — OpenRouter (영상 LLM 폴백 + market post)
- `GEMINI_CLI_MODEL=gemini-2.5-flash` — 콘텐츠 LLM 우선
- `LLM_PRIMARY_BACKEND=gemini`
- `TIKTOK_CLIENT_KEY/SECRET/ENABLED=true` — TikTok 자동화
- `META_ACCESS_TOKEN/IG_USER_ID` — Instagram Reels (Meta 24h 대기)
- `FFMPEG_VIDEO_CODEC=h264_nvenc` — GPU 인코딩
- `SKIP_LONG_VIDEO=true` — 쇼츠만 (시간 절반)
- 자세한 항목은 `.env.example` 참조

## 자주 쓰는 명령
```bash
# 수동 발행
venv/bin/python3 -m auto_publisher.main run --lang ko

# 영상 생성
venv/bin/python3 -m auto_publisher.main make-video --slug XXX --lang ko

# 시스템 상태
curl -s https://callback.investiqs.net/health/full

# bridge 재시작
pkill -f bridge_api.py
nohup venv/bin/python3 n8n/bridge_api.py > /tmp/bridge.log 2>&1 &
```

## 자동 트리거 시각 (KST)
- 06:00~07:50 daily_publisher
- 07:30~08:15 us_market_wrap (en/ja/vi/id)
- 08:30 shorts_auto
- 22:30~23:30 us_market_intraday
- 토 09:00~10:15 us_market_weekly
- 일 21:00 benchmark_youtube_tracker

## 🛠️ 트러블슈팅

### 자동 발행이 안 될 때
1. **bridge_api 살아있나**: `curl https://callback.investiqs.net/health`
2. **n8n 컨테이너 살아있나**: `docker ps | grep n8n`
3. **활성 워크플로우 수**: `docker exec n8n-n8n-1 sqlite3 /home/node/.n8n/database.sqlite "SELECT COUNT(*) FROM workflow_entity WHERE active=1"` (27이어야 함)
4. **OpenRouter 크레딧**: https://openrouter.ai/settings/credits — Gemini Flash로 자동 폴백되지만 확인 권장

### 영상 합성이 느릴 때
1. **GPU 사용 확인**: `nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader`
2. **Gemini CLI 모델 확인**: `grep GEMINI_CLI_MODEL .env` (gemini-2.5-flash 권장)
3. **SKIP_LONG_VIDEO 활성화**: `.env`에 `SKIP_LONG_VIDEO=true` (쇼츠만 만듦)
4. **stuck 프로세스 정리**: `pkill -f "auto_publisher.main make-video"`

### TikTok 업로드 실패 시
1. **token 갱신**: 자동 (24h refresh) — `/health/full`에서 expires_in_sec 확인
2. **403 unaudited**: SELF_ONLY로 자동 재시도 (코드에 폴백 있음)
3. **재인증 필요 시**: 브라우저에서 https://www.tiktok.com/v2/auth/authorize/?client_key=... 방문 (URL은 tiktok_auth_setup() 출력 참조)

### Cloudflare Pages 배포 실패 시
- wrangler CLI 직접 호출: `cd web && npx wrangler pages deploy public --project-name invest-korea`
- 환경변수: `CLOUDFLARE_API_TOKEN` 만료 안 됐는지 확인

## 📁 파일 위치
- 환경변수: `.env`
- 비밀: `.tiktok_secrets/token.json`, `.youtube_secrets/token.json`
- 로그: `/tmp/bridge.log`, `auto_publisher/auto_publisher.log`
- 영상 캐시: `.omc/video_cache/`
- 스크립트 캐시: `.omc/script_cache/`
- 발행 이력: `auto_publisher/data/published_history.json`
- 토픽 큐: `auto_publisher/data/topics_ko.json`
- n8n 백업: `n8n/backups/YYYYMMDD/`

## 🔐 보안 체크리스트
- [x] `.env`는 .gitignore에 등록
- [x] `.tiktok_secrets/`, `.youtube_secrets/`는 .gitignore에 등록
- [x] GitHub repo는 private
- [ ] OPENROUTER_API_KEY는 만료 시 교체
- [ ] CLOUDFLARE_API_TOKEN은 6개월마다 교체 권장
