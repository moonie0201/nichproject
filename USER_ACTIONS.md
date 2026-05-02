# 사용자 직접 액션 가이드 (2026-05-02 기준)

## 🚨 긴급 (24시간 내)

### 1. OpenRouter 크레딧 충전 (자동 발행 차단 위험)
- URL: https://openrouter.ai/settings/credits
- 권장 충전: $5~10 (월 1,000회 LLM 호출 충당)
- 우회 옵션: `.env`에서 `LLM_PRIMARY_BACKEND=gemini` (Gemini CLI 무료)

### 2. Meta Developer 계정 활성화 대기 (Instagram Reels용)
- 24시간 후 자동 해제 예정
- 활성화 후: Facebook Page 생성 → Instagram Business 연결 → API key 발급

## ⚠️ 권장 (이번 주)

### 3. AdSense In-Article 슬롯 ID 발급
- AdSense → 광고 → 광고 단위 → 인아티클 광고 3개 생성
- web/layouts/_default/single.html L36, L45, L47의 placeholder (1111111111 등) 교체

### 4. n8n API Key 발급 (REST 자동화용)
- localhost:5678 → Settings → API → Create API Key
- 차후 워크플로우 일괄 관리 자동화 가능

### 5. 디스크 추가 정리 (현재 88%)
- ~/.cache/huggingface (2.3G) — AI 모델 재다운로드 가능
- ~/.cache/google-chrome (2.4G) — 브라우저 직접 정리
- money_printer_v2 (5.3G) — 사용 중이면 보존

## ✅ 자동화 완료 (모니터링만)

### 6. 다음 자동 발행 시각
- daily_publisher: 매일 06:00 KST
- us_market_wrap (en/ja/vi/id): 07:30~08:15 KST
- shorts_auto: 매일 08:30 KST
- weekly_dividend_report: 월 08:00
- (총 27개 워크플로우 활성)

### 7. TikTok token 갱신
- 24시간마다 자동 (refresh_token 보유)
- 실패 시 /health/full에서 warning 표시

## 📊 모니터링

### 시스템 상태 확인 명령
```bash
curl -s https://callback.investiqs.net/health/full
```

### 최근 발행글 확인
```bash
ls -lt /home/mh/ocstorage/workspace/nichproject/web/content/ko/daily/ | head -5
```

### 자동 발행 로그
```bash
tail -f /tmp/bridge.log
```
