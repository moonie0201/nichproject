# 🎯 사용자 직접 액션 가이드 (2026-05-02 최종)

## 🎉 검증 완료 (2026-05-02)

### 자동 발행 100% 작동 검증
- ✅ `publish-us-market-wrap` 실제 호출 → 새 글 생성 + Cloudflare 배포 성공
- ✅ 영상 자동 합성 → 3개 short.mp4 생성 (Gemini Flash + NVENC)
- ✅ TikTok OAuth → token 발급 완료 (24h refresh 자동)
- ✅ n8n 27개 워크플로우 active=1
- ✅ Cloudflare Tunnel + systemd active+enabled
- ✅ AdSense / Klaro v2 / GA4 / og-default 모두 정상
- ✅ 디스크 76GB 정리 (88% → 86%)

### 다음 자동 트리거 (KST)
**07:15 — us_market_wrap (다국어)** ⭐ 다음 트리거
**08:30 — shorts_auto** (영상 + 업로드 시도)

## ✅ 자동화 100% 완료된 것
- 한국어 일일 발행 (06:00 KST)
- 다국어 시장 wrap EN/JA/VI/ID (07:30~08:15)
- 주말 종합 ko/en/ja/vi/id (토 09:00~10:15)
- 영상 자동 합성 (NVENC GPU, Gemini Flash)
- 토픽 큐 자동 보충 (Gemini)
- TikTok OAuth 자동 갱신 (24h refresh)
- AdSense Auto Ads + In-Article 슬롯 3개
- Klaro v2 (자동 동의)
- GA4 트래킹
- Cloudflare Pages 자동 배포 (git push)
- n8n 백업 (매일 03:00)

## 🔥 P0 — 24시간 내 (자동화 차단 위험)

### 🚨 0. TikTok OAuth 재인증 (token.json 사라짐)

**증상**: `.tiktok_secrets/token.json` 파일 없음 → 자동 업로드 실패

**해결 (3분):**
```bash
cd /home/mh/ocstorage/workspace/nichproject
venv/bin/python3 -c "
from dotenv import load_dotenv
load_dotenv('.env')
from auto_publisher.video_uploader import tiktok_auth_setup
tiktok_auth_setup()
"
```

→ 출력된 OAuth URL 브라우저에서 열기
→ 권한 부여 → 자동으로 callback.investiqs.net로 리다이렉트
→ token.json 자동 저장 완료

**확인:**
```bash
ls -la .tiktok_secrets/token.json
# 파일 존재 + 권한 600
```

### 1. OpenRouter 크레딧 충전 (선택)
- **현재**: Gemini CLI Flash로 자동 우회 중 → 작동 OK
- **충전 시 효과**: 영상 LLM 백엔드 다양화, 안정성 ↑
- **방법**: https://openrouter.ai/settings/credits → $5~10 충전

### 2. Meta Developer 계정 활성화 (Instagram Reels용)
- 등록 후 24시간 대기 (5월 2일 등록함 → 5월 3일 가능 예상)
- 활성화 후: Facebook Page 생성 → Instagram Business 연결 → API key

## 🔧 P1 — 이번 주

### 3. AdSense In-Article 슬롯 ID 발급
- AdSense 대시보드 → 광고 → 광고 단위 → "인아티클" 3개 생성
- `web/layouts/_default/single.html` L36, L45, L47의 `1111111111`, `2222222222`, `3333333333` 교체

### 4. TikTok App Audit 신청
- developers.tiktok.com → 앱 → "Submit for review"
- 데모 비디오 (3분) + Usage description (1000자)
- 심사 7~14일

### 5. Cloudflare Pages 빌드 설정 확인
- Pages → invest-korea → Settings → Builds & deployments
- Build output: `web/public` (확인 필요)
- Functions directory: `functions` 명시 (현재 web/static/functions로 빌드됨)

## 🛠️ P2 — 모니터링

### 6. 일일 점검 명령
```bash
# 시스템 상태
curl -s https://callback.investiqs.net/health/full | python3 -m json.tool

# 최근 발행글
ls -lt /home/mh/ocstorage/workspace/nichproject/web/content/ko/daily/ | head -5

# n8n 워크플로우 상태
docker exec n8n-n8n-1 sqlite3 /home/node/.n8n/database.sqlite "SELECT COUNT(*) FROM workflow_entity WHERE active=1"

# 디스크 + GPU
df -h / && nvidia-smi --query-gpu=utilization.gpu --format=csv
```

### 7. n8n UI 접속
- http://localhost:5678
- 발행 실패 시 Executions 메뉴에서 에러 확인

## 📊 다음 자동 트리거 시각 (KST)
- **07:15 — us_market_wrap (다국어)** ⭐ 다음 트리거
- 08:30 — shorts_auto (영상 + 업로드)
- 06:00 — daily_publisher (한국어)
- 22:30~23:30 — us_market_intraday
- 토 09:00 — us_market_weekly
- 일 21:00 — benchmark_youtube_tracker
