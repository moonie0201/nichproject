# n8n 워크플로우 활성화 가이드

## 현재 상태 (2026-05-02)
27개 워크플로우 중 **25개 비활성화**. 영어/일본어/베트남어/인도네시아어 시장 wrap이 전혀 발행되지 않습니다.

## 활성 워크플로우 (2개)
- ✅ daily_publisher (06:00~07:50, 6회)
- ✅ shorts_auto_daily (08:30)

## 비활성 워크플로우 (25개) — 수동 활성화 필요

### 다국어 시장 wrap (장 마감 후)
- us_market_wrap_en (07:30 KST)
- us_market_wrap_ja (07:45 KST)
- us_market_wrap_vi (08:00 KST)
- us_market_wrap_id (08:15 KST)

### 다국어 장중 시황 (장 시작 후)
- us_market_intraday_en (22:45 KST)
- us_market_intraday_ja (23:00 KST)
- us_market_intraday_vi (23:15 KST)
- us_market_intraday_id (23:30 KST)

### 주말 종합
- us_market_weekly (토 09:00) — ko
- us_market_weekly_en (토 09:30)
- us_market_weekly_ja (토 09:45)
- us_market_weekly_vi (토 10:00)
- us_market_weekly_id (토 10:15)

### 기타
- weekly_dividend_report (월 08:00)
- comparison_content (수 09:00)
- newsletter_weekly (금 07:00)
- benchmark_youtube_tracker (일 21:00)
- kpi_weekly_dashboard (월 09:00)
- news_react_shorts (30분마다)
- keyword_rank_monitor (23:00)
- (기타 5개)

## 활성화 방법
1. 브라우저에서 [http://localhost:5678](http://localhost:5678) 접속
2. Workflows 메뉴
3. 비활성 워크플로우 클릭 → 우상단 토글 ON
4. Save

## 우선순위 권장
1. **다국어 시장 wrap 4개** (해외 트래픽 직접 영향)
2. **us_market_weekly 5개** (주간 SEO 강화)
3. **us_market_intraday 4개** (장중 트래픽)
4. **나머지** (선택적)
