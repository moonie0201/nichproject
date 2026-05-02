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
