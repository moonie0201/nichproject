# InvestIQs 자동화 시스템 — Phase Record

## 시스템 개요

InvestIQs.net 다국어(ko/en/ja/vi/id) 데이터 기반 투자 리서치 자동 발행 + YouTube 영상 자동 생성 파이프라인.

---

## Phase 1 — 콘텐츠 시스템 기반 (완료)

**적용 일시**: 2026-04-19 ~ 04-20

- 기존 50개 범용 토픽 폐기 → 데이터 분석 톤 토픽 큐
- 5개 언어 페르소나 (taber_*.json) 도입 — 1인칭 후기 캐릭터
- yfinance 실시간 데이터 자동 주입
- ai-hedge-fund 5에이전트 분석 통합 (워런 버핏/기술적/펀더멘털/뉴스/리스크)
- Codex (gpt-5.4-mini) 콘텐츠 생성
- Hugo 정적 사이트 + Cloudflare Pages 자동 배포
- Discord webhook 알림
- n8n 일일 cron 자동화

---

## Phase 2 — 콘텐츠 품질 강화 (완료)

**적용 일시**: 2026-04-20

- 차트 자동 생성 (matplotlib): price-history, return-bars, drawdown, etf-comparison, dividend-history
- Article JSON-LD with author E-E-A-T 신호
- OG 이미지 자동 (cover.image)
- Cross-section 내부 링크 (블로그 ↔ 분석 자동 연결)
- HTML→Markdown 컨버터 수정 (table/figure/aside/img 보존)
- Failed topics 재시도 큐
- 다국어 토픽 큐 (en/ja/vi/id 각 25개)
- Dynamic topic trigger (VIX/배당 이벤트 기반)

---

## Phase 3 — 데이터 무결성 (완료)

**적용 일시**: 2026-04-21

- 다중 소스 검증 + 필드별 sanity range
- Cross-check: yfinance.info vs Ticker.dividends 직접 계산 (30% 차이 시 보수적 채택)
- 월배당 ETF TTM 12개월 합산 (JEPI 8.25%, QYLD 11.59% 정확)
- 한국 ETF 폴백 (yfinance .KS suffix, 14개 종목코드)
- 액면병합 이상치 자동 거부
- Peer ETF 자동 추가 (단일 티커 → peer 매핑 15쌍)
- 시장 데이터 캐시 (.omc/state/market-cache.json) — 매일 08시 갱신
- 5,000배 속도 향상 (2.5초 → 0ms 캐시 히트)

---

## Phase 4 — YouTube 영상 자동화 (완료)

**적용 일시**: 2026-04-21 ~ 04-22

- 블로그 → 롱폼 (10~15분) + 쇼츠 (60초) 자동 생성
- 대사 생성 모듈 (video_script.py): generate_long_video_script, generate_short_video_script
- TTS (video_tts.py): edge-tts Neural 음성 + SSML 전처리 (rate -5%, | break 마커)
- 자막 자동 생성 (SRT, sentence boundary 기반)
- 영상 합성 (video_composer.py): ffmpeg + Ken Burns 효과 + 자막 burn-in
- YouTube Data API v3 OAuth 인증 + 자동 업로드
- 차트 추출: 블로그 .md에서 실제 존재하는 차트 우선 사용 (LLM 할루시네이션 차단)
- 브릿지 API: /make-video?slug=&lang=&privacy=
- n8n 07:50 KST cron 트리거

---

## Phase 5 — 규제 안전 + AI스러움 제거 (완료)

**적용 일시**: 2026-04-22

- 금감원 자본시장법 준수: "매수하세요" 같은 권유성 표현 전면 금지
- 상단 규제 배너 (모든 분석/시장 포스트)
- "BUY 신호" → "데이터상 강세 흐름" 등 안전 표현
- 타이틀에서 "사도 될까?" 같은 권유 단어 제거
- 페르소나 폐기 (시나리오 캐릭터 → 전문 리서치 애널리스트)
- analyst_*.json 5개 신규: InvestIQs Research (CFA-level, 3인칭, contrarian + disconfirming evidence)
- 교과서 클리셰 금지어 확장 ("결론적으로", "다음과 같이" 등)
- 문장 리듬 비대칭 강제 (짧은 + 긴 문장 혼합)
- 영상 대사 자체 검증 (_verify_video_script)

---

## Phase 6 — 2단계 콘텐츠 검증 (완료)

**적용 일시**: 2026-04-21

- 1차 규칙 검증: 글자수/표/금지어/H2/원본 데이터 반영 (무료, 즉시)
- 2차 Gemini 의미 검증: hallucination/contradiction/bad_phrasing/missing_chart_refs (~$0.02)
- 최대 2회 재시도 + 치명 미달 reject (실패 시 failed_topics 큐로)
- publish_market_post에도 동일 검증 적용
- 비용: 일 10개 포스트 × 30% Gemini 호출 ≈ $3/월

---

## Phase 7 — 토픽 큐 분석가 톤 일괄 재작성 (완료)

**적용 일시**: 2026-04-22

- KO 50개 토픽 재작성 (후기→데이터분석)
- EN/JA/VI/ID 각 25개 재작성 — 각 시장 ETF/세제 반영
- 카테고리 10개 신규 ("ETF 데이터 분석", "ETF 비용 분석", "배당 ETF 리서치" 등)
- 차트 매핑 모든 신규 카테고리 연결

---

## Phase 8 — 하이브리드 페르소나 (시나리오 케이스) (완료)

**적용 일시**: 2026-04-22

- analyst = 글의 작가 (Narrator, 3인칭, 모든 글 적용)
- case = 분석 대상 가상 주인공 (시나리오 박스 안에서만 등장)
- `data/cases/case_*.json` 5개 신규: K씨/Mike/田中さん/Anh Đức/Pak Budi
- _load_case + _case_brief 함수 추가
- 블로그 프롬프트에 선택적 시나리오 박스 옵션 (한 글당 1회만, 어색하면 생략)
- CSS: web/assets/css/extended/scenario.css (노란 callout 박스)
- 검증: _verify_scenario_box (footnote 누락/1회 초과/박스 안 1인칭 차단)
- 분석 포스트는 시나리오 박스 금지 (규제 안전)

---

## Phase 9 — AdSense 활성화 (완료)

**적용 일시**: 2026-04-22

- Publisher ID: ca-pub-3459019439429067 (mooniegilog 계정)
- hugo.toml params.googleAdSense 설정
- ads.txt 배포 (`google.com, pub-3459019439429067, DIRECT, f08c47fec0942fa0`)
- AdSense 사이트 등록 (investiqs.net) — Google 검토 대기 중

---

## n8n 자동화 스케줄 (KST)

```
06:00 → /refresh-market-cache (yfinance 19개 ticker 일괄 갱신 + sanity 검증)
       /dynamic-scan (VIX/배당 이벤트 → 우선순위 토픽 자동 추가)
06:30 → /publish-market (코인/시장분석) + KO 블로그
07:00 → EN/JA/VI/ID 블로그 (각 언어 native analyst tone)
07:30 → KO AI 분석 (VOO, ai-hedge-fund 5에이전트)
07:45 → EN/JA/VI/ID 분석 번역 (translate_post)
07:50 → /make-video (KO 최근 포스트 → 롱폼 + 쇼츠 YouTube 업로드)
```

---

## 파일/모듈 맵

| 모듈 | 역할 |
|------|------|
| `auto_publisher/content_generator.py` | 블로그/분석 생성 + 페르소나/케이스 로드 |
| `auto_publisher/content_verifier.py` | 2단계 검증 (규칙 + Gemini) |
| `auto_publisher/market_analyzer.py` | ai-hedge-fund 멀티에이전트 분석 |
| `auto_publisher/market_cache.py` | 시장 데이터 캐싱 |
| `auto_publisher/chart_generator.py` | matplotlib 차트 자동 생성 |
| `auto_publisher/video_script.py` | YouTube 대사 (롱폼/쇼츠) |
| `auto_publisher/video_tts.py` | edge-tts + SRT 자막 |
| `auto_publisher/video_composer.py` | ffmpeg 영상 합성 |
| `auto_publisher/video_uploader.py` | YouTube Data API v3 업로드 |
| `auto_publisher/dynamic_topics.py` | VIX/배당 이벤트 토픽 트리거 |
| `auto_publisher/topic_manager.py` | 토픽 큐 + failed retry |
| `auto_publisher/notifier.py` | Discord webhook 알림 |
| `auto_publisher/publishers/hugo.py` | Hugo + Cloudflare Pages 발행 |
| `n8n/bridge_api.py` | HTTP 8765 — n8n ↔ Python 브릿지 |
| `n8n/workflows/daily_publisher.json` | n8n 일일 cron 워크플로우 |

---

## 데이터 디렉토리

| 경로 | 내용 |
|------|------|
| `auto_publisher/data/personas/analyst_*.json` (5개) | 글의 작가 = InvestIQs Research |
| `auto_publisher/data/personas/taber_*.json` (5개) | 레거시 페르소나 (fallback) |
| `auto_publisher/data/cases/case_*.json` (5개) | 시나리오 박스 가상 주인공 |
| `auto_publisher/data/topics_{lang}.json` (5개) | 토픽 큐 (KO 50, 나머지 25개씩) |
| `auto_publisher/data/published_history_{lang}.json` (5개) | 발행 이력 |
| `auto_publisher/data/failed_topics_{lang}.json` (5개) | 재시도 큐 |
| `.omc/state/market-cache.json` | yfinance 캐시 (TTL 24시간) |
| `.youtube_secrets/client_secrets.json` | YouTube OAuth 클라이언트 |
| `.youtube_secrets/token.json` | YouTube refresh token (자동 갱신) |
| `.env` (workspace + nichproject) | OPENROUTER_API_KEY / DISCORD_WEBHOOK_URL / CLOUDFLARE_API_TOKEN |

---

## 진행 가능한 향후 Phase

| Phase | 우선순위 | 내용 |
|-------|:------:|------|
| 10 — GA4 + Search Console | P2 | 트래픽 데이터 수집 → 토픽 자동 보강 |
| 11 — OmniVoice voice cloning | P3 | TTS 자연도 ↑ (사용자 음성 샘플 필요) |
| 12 — 다중 보이스 영상 | P3 | 진행자 + 내레이터 대화형 |
| 13 — 토픽 자동 생성 | P3 | GA4 트래픽 패턴 → 유사 토픽 LLM 자동 생성 |
| 14 — Schema 강화 | P2 | Article + BreadcrumbList + FAQ JSON-LD 통합 |
| 15 — 댓글/구독 시스템 | P3 | Disqus / Substack newsletter |
| 16 — 다국어 분석 포스트 native 생성 | P2 | 현재는 KO 분석 → 4개 언어 번역만, native 분석 발행 추가 |
