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

### URL Hook Bots
- `NICHPROJECT_BRIDGE_URL=http://172.17.0.1:8765` — bridge API 주소
- `NICHPROJECT_CALLBACK_PORT=8900` — Discord hermes 콜백
- `TELEGRAM_BOT_TOKEN` — Telegram 봇 토큰 (선택)
- `TELEGRAM_CALLBACK_PORT=8901` — Telegram webhook 포트
- `TELEGRAM_URL_HOOK_ENABLED=0` — Telegram 활성화 (0=비활성, 1=활성)
- `SLACK_BOT_TOKEN=xoxb-...` — Slack 봇 토큰 (선택)
- `SLACK_APP_TOKEN=xapp-...` — Slack 앱 토큰 (선택)
- `SLACK_CALLBACK_PORT=8902` — Slack webhook 포트
- `SLACK_URL_HOOK_ENABLED=0` — Slack 활성화 (0=비활성, 1=활성)

### Paperclip Audit
- `PAPERCLIP_AUDIT_ENABLED=1` — Paperclip 감시 활성화
- `PAPERCLIP_COMPANY_ID=ccd0c00a-d565-4fc4-910f-9d823665313b` — 회사 ID
- `PAPERCLIP_DAILY_COST_LIMIT_USD=5.0` — 일일 비용 한도 (초과 시 alert)
- `DISCORD_WEBHOOK_URL=<webhook>` — 비용 alert 수신 Discord webhook
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

# 다중 봇 상태 확인
scripts/start_bots.sh status

# Paperclip 월간 비용 요약
venv/bin/python3 -m auto_publisher.paperclip_audit summary

# Paperclip 일일 비용 alert 확인
venv/bin/python3 -m auto_publisher.paperclip_audit alert
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

## URL → 콘텐츠 자동화

### 동작 흐름
Discord (Hermes), Telegram, Slack URL hook이 YouTube/Instagram/TikTok/뉴스 기사 링크를 감지하면:
1. 사용자가 봇에 URL 전송 (Discord, Telegram, Slack)
2. 봇이 bridge `/url-to-content` API 호출
3. `url_fetcher.py`가 메타데이터 추출 (제목, 설명, 이미지 등)
4. 콘텐츠 생성기가 자동 마켓 포스트/분석글 생성
5. Paperclip issue 자동 생성 + token/cost 기록

### 지원 도메인
- YouTube: `youtube.com`, `youtu.be`
- Instagram: `instagram.com`, `instagr.am`
- TikTok: `tiktok.com`, `vm.tiktok.com`
- 뉴스: CNBC, Reuters, Yahoo Finance, 기타 금융 매체

### Bridge API 사용
```bash
# URL → 콘텐츠 변환
curl -X POST http://localhost:8765/url-to-content \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=...",
    "lang": "ko",
    "source": "discord"
  }'

# 상태 확인 (비동기 작업용)
curl http://localhost:8765/url-to-content-status?job_id=<job_id>
```

### 봇 활성화 절차
1. `.env`에서 원하는 봇 토큰 설정:
   - Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_URL_HOOK_ENABLED=1`
   - Slack: `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_URL_HOOK_ENABLED=1`
   - Discord: 이미 Hermes로 실행 중
2. `scripts/start_bots.sh start` 실행 (tmux 세션 자동 시작)
3. 각 플랫폼에서 봇에 URL 전송

## Paperclip Audit + 비용 추적

### 개요
모든 `url-to-content`, `market-wrap`, `weekly`, `intraday` 작업이 Paperclip에 자동 이슈 생성하고:
- token 수, 비용 (USD) 기록
- 모델별 cost_events 누적
- 일일/월간 집계 및 alert 발송

### 일일 비용 alert
```bash
# 현재 일일 비용 확인 + 한도 초과 시 Discord alert
venv/bin/python3 -m auto_publisher.paperclip_audit alert
```
- 임계값: `PAPERCLIP_DAILY_COST_LIMIT_USD` (기본 5.0 USD)
- 초과 시: Discord webhook으로 alert 발송

### 월간 요약
```bash
# 전월 비용, 모델별 분포, 이슈 건수
venv/bin/python3 -m auto_publisher.paperclip_audit summary
```
- 출력: 모델별 token 수, 총 비용, top 5 고비용 이슈

### Paperclip 이슈 구조
```
Title: [url-to-content] YouTube: "제목" (KO, Gemini Flash, 0.005 USD)
Tags: url-to-content, source:discord, model:gemini-2.5-flash
Custom Fields:
  - tokens_used: 1234
  - cost_usd: 0.005
  - model: gemini-2.5-flash
  - content_type: youtube
  - source_platform: discord
```

## 봇 Launcher

### 다중 봇 시작/중지
```bash
# 모든 봇 시작 (tmux 세션)
scripts/start_bots.sh start

# 상태 확인
scripts/start_bots.sh status

# 모든 봇 중지
scripts/start_bots.sh stop

# 재시작
scripts/start_bots.sh restart
```

### tmux 세션
- `nich-tg`: Telegram 봇 (포트 8901)
- `nich-slack`: Slack 봇 (포트 8902)
- Discord Hermes: 별도 프로세스 (포트 8900, 이미 실행 중)

### 로그 확인
```bash
# Telegram 봇 로그
tmux capture-pane -t nich-tg -p

# Slack 봇 로그
tmux capture-pane -t nich-slack -p
```

## 파일 위치 (추가)
- URL fetcher: `auto_publisher/url_fetcher.py`
- Telegram hook: `auto_publisher/telegram_url_hook.py`
- Slack hook: `auto_publisher/slack_url_hook.py`
- Paperclip audit: `auto_publisher/paperclip_audit.py`
- Token estimator: `auto_publisher/token_estimator.py`
- Bot launcher: `scripts/start_bots.sh`
- Bridge API routes: `n8n/bridge_api.py` (`/url-to-content`, `/paperclip/poll-and-publish` 등)
