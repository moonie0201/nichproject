---
version: alpha
name: InvestIQs
description: 데이터 기반 투자 분석 채널 — 신뢰·정확·간결을 시각 언어로 표현

colors:
  # Base
  bg:          "#0f172a"   # 영상 기본 배경 (slate-900)
  bg-shorts:   "#1e293b"   # 쇼츠 배경 (slate-800)
  bg-panel:    "#020617"   # 패널/오버레이 (slate-950)
  bg-risk:     "#7f1d1d"   # 리스크 패널 (red-900)

  # Brand
  primary:     "#38BDF8"   # InvestIQs 블루 (sky-400)
  accent:      "#FACC15"   # 핵심 수치 강조 (yellow-400)
  success:     "#22C55E"   # 긍정 지표 (green-500)
  warning:     "#FFD54F"   # 리스크 경고 (amber-300)

  # Text
  text:        "#FFFFFF"   # 본문 흰색
  text-sub:    "#CBD5E1"   # 보조 텍스트 (slate-300)
  text-muted:  "#D7E3F4"   # 흐린 텍스트
  text-risk:   "#FDE68A"   # 리스크 섹션 텍스트 (amber-200)

  # Hugo (웹)
  web-bg:      "#FFFFFF"
  web-primary: "#0369A1"   # sky-700 (웹 링크/CTA)
  web-border:  "#E2E8F0"   # slate-200

typography:
  # 영상 카드
  card-brand:
    fontFamily: Noto Sans CJK KR
    fontSize: 28px
    fontWeight: "700"
  card-headline:
    fontFamily: Noto Sans CJK KR
    fontSize: 52px
    fontWeight: "700"
    lineHeight: "1.2"
  card-headline-short:
    fontFamily: Noto Sans CJK KR
    fontSize: 46px
    fontWeight: "700"
    lineHeight: "1.2"
  card-subhead:
    fontFamily: Noto Sans CJK KR
    fontSize: 30px
    fontWeight: "400"
    lineHeight: "1.4"
  card-accent:
    fontFamily: Noto Sans CJK KR
    fontSize: 72px
    fontWeight: "800"
  card-label:
    fontFamily: Noto Sans CJK KR
    fontSize: 34px
    fontWeight: "600"

  # 자막 (SRT)
  subtitle-longform:
    fontFamily: Noto Sans CJK KR
    fontSize: 18px
    fontWeight: "700"
  subtitle-shorts:
    fontFamily: Noto Sans CJK KR
    fontSize: 32px
    fontWeight: "700"

spacing:
  card-margin:  64px
  card-padding: 96px

components:
  thesis-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.primary}"
    highlightColor: "{colors.accent}"
    typography: "{typography.card-headline}"

  number-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.accent}"
    typography: "{typography.card-accent}"

  risk-card:
    backgroundColor: "{colors.bg-risk}"
    textColor: "{colors.text}"
    accentColor: "{colors.warning}"
    typography: "{typography.card-headline}"

  cta-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.accent}"
    typography: "{typography.card-headline}"

  comparison-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.accent}"
    typography: "{typography.card-headline}"

  market-dashboard-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.accent}"
    primaryPanel: "{colors.primary}"
    secondaryPanel: "#1D4ED8"
    typography: "{typography.card-label}"

  intro-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.primary}"
    height: "2.5s"            # 롱폼 인트로 길이 (쇼츠: 1.0s)
    # 레이아웃: InvestIQs(primary, brand) → 수평바 8px(primary, y=height×0.46) → 제목(text) → 날짜(accent)
    # alpha: fade-in 0.4s / fade-out 0.3s

  transition-card:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text}"
    height: "0.6s"
    # 전체 primary 배경 + 챕터 제목 중앙
    # alpha: fade-in 0.15s / fade-out 0.15s

  outro-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.accent}"
    height: "3.0s"            # 쇼츠: 1.5s (60s 예산)
    # 상단 10px 가로바(accent) + "구독 + 알림 설정"(text) + 블로그 URL(accent)

  lower-third:
    backgroundColor: "{colors.bg-panel}"   # opacity 0.6
    textColor: "{colors.text}"
    accentColor: "{colors.primary}"
    width: "iw - 128px"
    height: "110px"
    padding: "x=64, y=ih-180"
    # 좌측 8px 수직 액센트바(primary) + 챕터 제목
    # ffmpeg enable='between(t,{show_from},{show_until})'
---

## Overview

InvestIQs는 AI 멀티에이전트 분석 결과를 한국어 투자 콘텐츠로 자동 발행하는 채널입니다.
**신뢰, 정확, 간결**이 핵심 가치입니다.

- 감정보다 데이터를 우선합니다.
- 불확실성을 항상 명시합니다.
- 디자인은 정보를 방해하지 않습니다.

## Colors

배경은 어두운 Navy(#0f172a)로 차트·수치의 대비를 극대화합니다.
브랜드 블루(#38BDF8)는 헤더·레이블 등 정보 계층을 표시하고,
노란 강조(#FACC15)는 핵심 수치 한 가지에만 사용합니다.
리스크 섹션은 독립적인 붉은 패널(#7f1d1d)로 즉각 식별 가능하게 합니다.

## Typography

한국어 콘텐츠이므로 Noto Sans CJK KR을 기본 서체로 사용합니다.
시스템에서 찾지 못할 경우 DejaVu Sans로 폴백합니다.
영상 카드는 큰 서체(52–72px)로 모바일 가독성을 보장합니다.

## Layout

- 영상 카드 여백: 64px (margin), 96px (padding)
- 롱폼: 1920×1080 (16:9)
- 쇼츠: 1080×1920 (9:16), 상단 960px 차트 / 하단 960px 자막

## Components

### thesis-card
분석 핵심 주장 카드. 좌상단 InvestIQs Research 레이블 + 대형 헤드라인 + 노란 accent 수치.

### number-card
단일 핵심 수치를 72px accent로 중앙 표시. 쇼츠 첫 카드에 사용.

### risk-card
붉은 배경 + 노란 좌측 세로줄로 리스크 섹션 즉각 식별.

### market-dashboard-card
복수 시장 지표를 두 개의 패널에 나열. 스캔바 3개로 시각적 분리.

### cta-card
채널명과 블로그 링크 유도. 중앙 정렬, accent 색상으로 강조.

### intro-card (`branding.make_intro_clip`)
영상 맨 앞 브랜딩 카드. 다크 배경 위 InvestIQs(primary) + 수평 구분선(8px, primary) + 제목(white) + 날짜(accent).
롱폼 2.5s / 쇼츠 1.0s. alpha fade-in 0.4s / fade-out 0.3s.

### transition-card (`branding.make_transition_clip`)
챕터 간 0.6s 전환 카드. 전체 primary 배경 + 챕터 제목 중앙. fade-in/out 각 0.15s.

### outro-card (`branding.make_outro_clip`)
영상 마지막 CTA 카드. 상단 10px 가로바(accent) + 구독 문구(white) + 블로그 URL(accent).
롱폼 3.0s / 쇼츠 1.5s.

### lower-third (`branding.make_lower_third_overlay`)
기존 클립 위 반투명 하단 자막바. bg-panel @ 0.6 + 좌측 8px 수직 액센트(primary) + 챕터 제목.
`VIDEO_LOWER_THIRD=1` 환경변수로 제어.

## Do's and Don'ts

- ✅ 핵심 수치는 노란색(#FACC15) 하나에만 적용
- ✅ 리스크 정보는 반드시 별도 카드로 분리
- ✅ 모든 수치는 소수점 1자리 이하로 반올림
- ❌ 브랜드 블루와 노란 강조를 같은 요소에 동시 사용하지 않음
- ❌ 흰 배경 카드 사용 금지 (차트 가독성 저하)
- ❌ 1인칭 표현, 투자 권유 문구 화면 표시 금지

---

# 시스템 아키텍처 (Phase 2/3)

## 개요

InvestIQs는 **다중 채널 입력 → 콘텐츠 생성 → 다중 채널 발행**의 통합 파이프라인입니다.
Paperclip API를 통한 감사 추적(audit trail), 비용 추적, 작업 생명주기 관리를 지원합니다.

**핵심 원칙:**
- **비동기 첫 설계**: 모든 장시간 작업(콘텐츠 생성, 영상 합성, 배포)은 job 큐 기반
- **폴백 LLM**: Gemini CLI → Claude Haiku → Ollama (가용성 우선)
- **감사 투명성**: Paperclip issue ↔ work_product ↔ cost_events 삼각 추적
- **환경 게이트**: 각 채널·기능은 env var로 opt-in (마스터 스위치 우선)

---

## 1. 입력 채널 (Input Channels)

### 1.1 Discord (Hermes Bot)
```
Discord 서버 → :8900 (FastAPI + interactions.py) → /url-to-content 트리거
```
- 용도: URL 공유 → 자동 분석 + 블로그 발행 + 쇼츠 생성
- 메시지 포맷: `!analyze https://www.youtube.com/...` 또는 message reaction
- 응답: job_id 반환 → DM으로 진행 상황 알림

### 1.2 Telegram Bot
```
Telegram 채팅 → :8901 (pyTelegramBotAPI) → /url-to-content 트리거
```
- 환경 게이트: `TELEGRAM_ENABLED=1`, `TELEGRAM_BOT_TOKEN`
- 용도: Discord와 동일 (다중 언어 지원: ko/en/ja/vi/id)
- 비활성 시 self-managed pool에서 대기만 수행

### 1.3 Slack Integration
```
Slack 워크스페이스 → :8902 (slack-bolt) → /url-to-content 또는 /publish 트리거
```
- 환경 게이트: `SLACK_ENABLED=1`, `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`
- 용도: 팀 내부 콘텐츠 리뷰 + 1-클릭 발행

### 1.4 n8n Cron (27 활성 워크플로우)
```
n8n 컨테이너 (docker-compose) → bridge_api :8765
```
- **daily_publisher** (06:00~07:50 KST): 일일 토픽 자동 콘텐츠 생성
- **us_market_wrap** (07:30~08:15): 미국 증시 마감 분석 (en/ja/vi/id)
- **us_market_intraday** (22:30~23:30): 미국 증시 장중 분석
- **us_market_weekly** (토 09:00~10:15): 주간 시장 분석
- **shorts_auto** (08:30): 최신 발행 콘텐츠 → YouTube Shorts 자동 생성
- **benchmark_youtube_tracker** (일 21:00): 경쟁사 채널 모니터링
- 기타: cost-alert-check, health-monitor, topic-refill 등

---

## 2. Bridge API (중앙 라우터) :8765

`n8n/bridge_api.py` — ThreadingHTTPServer (포트 8765)

### 2.1 GET 엔드포인트

| 경로 | 파라미터 | 설명 |
|------|---------|------|
| `/health` | - | 기본 상태 체크 (TikTok token 유효 여부) |
| `/health/full` | - | 상세 상태 (bot, cost, n8n, bridge 전체) |
| `/publish` | `lang` | 즉시 블로그 콘텐츠 생성 + 발행 |
| `/analyze` | `ticker`, `lang` | 종목 분석 리포트 생성 |
| `/translate` | `from`, `to` | 언어 변환 (ko↔en/ja/vi/id) |
| `/publish-us-market-wrap` | `lang`, `force`, `dry_run` | 미국 증시 마감 분석 |
| `/publish-us-market-intraday` | `lang`, `force`, `dry_run` | 미국 증시 장중 분석 |
| `/publish-us-market-weekly` | `lang`, `force`, `dry_run` | 주간 시장 분석 |
| `/shorts/auto-latest` | `lang`, `privacy`, `dry_run` | 최신 블로그 → Shorts 영상화 |
| `/make-video` | `slug`, `lang`, `privacy` | 마크다운 → YouTube 영상 합성 (비동기 job) |

### 2.2 POST 엔드포인트

| 경로 | 요청 본문 | 설명 |
|------|---------|------|
| `/url-to-content` | `{url, lang, publish_blog, publish_shorts, callback_url, job_id}` | URL 수집 → 콘텐츠 생성 (비동기) |
| `/url-to-content-status` | Query: `job_id=X` | 비동기 작업 상태 조회 |
| `/compliance/check` | `{content, lang, channel}` | 규제 준수 검증 |
| `/publish-us-market-wrap` | `{lang, force, dry_run}` | 미국 증시 마감 (JSON 바디) |
| `/publish-us-market-intraday` | `{lang, force, dry_run}` | 미국 증시 장중 (JSON 바디) |
| `/publish-us-market-weekly` | `{lang, force, dry_run}` | 주간 시장 분석 (JSON 바디) |
| `/generate/monthly-dividend` | `{symbols, lang, force_timeout}` | 월간 배당 리포트 생성 |
| `/make-video` | `{slug, lang, privacy}` | 영상 생성 (비동기 job 등록) |
| `/make-video-status` | Query: `job_id=X` | 영상 생성 작업 상태 조회 |
| `/paperclip/poll-and-publish` | `{max_items}` | Paperclip work_product 폴링 + 발행 |
| `/paperclip/cost-alert-check` | - | 일일 비용 임계값 체크 (23:00 KST) |

### 2.3 인증
```python
# Bridge API 인증: Authorization 헤더
headers = {"Authorization": f"Bearer {BRIDGE_API_KEY}"}

# 환경 변수
BRIDGE_API_KEY          # 기본값: "investiqs-dev"
BRIDGE_ALLOWED_ORIGINS  # CORS whitelist (n8n 도메인)
```

---

## 3. 콘텐츠 생성 파이프라인

### 3.1 URL → 콘텐츠 (async `/url-to-content`)

```
입력: URL (YouTube/Instagram/TikTok/뉴스 기사)
↓
[url_fetcher.py] 콘텐츠 추출
├─ YouTube: youtube-transcript-api (자막) + yt-dlp (메타)
├─ Instagram/TikTok: yt-dlp
└─ 뉴스 기사: trafilatura
↓
표준 출력: {title, text, platform, thumbnail_url, source_url, fetched_at}
↓
[content_generator.py] LLM 콘텐츠 생성
├─ 1차 시도: Gemini CLI (GEMINI_CLI_MODEL=gemini-2.5-flash)
├─ 2차 폴백: Claude Haiku (ANTHROPIC_API_KEY)
├─ 3차 폴백: Ollama (OLLAMA_BASE_URL)
└─ 결과: {title, slug, content_html, tags, meta_description}
↓
[content_verifier.py] 2단계 검증
├─ 1단계: SEO + 규정 준수 + 길이 체크
└─ 2단계: 페르소나 일관성 + 사실 확인 (토픽 피드백)
↓
[publishers/hugo.py] Hugo 마크다운 → Cloudflare Pages 배포
├─ 파일 저장: web/content/{lang}/{section}/{slug}.md
├─ Hugo 빌드: `hugo --cleanDestinationDir --minify`
└─ CF 배포: `wrangler pages deploy public --project-name invest-korea`
↓
[paperclip_audit.py] 감사 로깅
├─ issue 생성 (job_type=url-to-content)
├─ work_product 추가 (type=blog_post, url=...)
└─ cost_events 기록 (tokens + USD 비용)
↓
출력: {success, url, slug, title, duration_sec}
```

**LLM 선택 로직:**
```python
if GEMINI_CLI_MODEL and gemini_available():
    use_gemini_cli()      # 1차 (빠름, 무료)
elif ANTHROPIC_API_KEY:
    use_claude_haiku()    # 2차 (신뢰성)
elif OLLAMA_BASE_URL:
    use_ollama()          # 3차 (로컬)
else:
    raise RuntimeError("no LLM available")
```

### 3.2 시장 분석 → 콘텐츠 (`publish_market_post`)

```
[market_wrap.py] 미국 증시 스냅샷 수집
├─ yfinance: SPY, QQQ, VTI 등 지수
├─ alpha_vantage: 시장 심리 지표
└─ 출력: {indices, narrative_hint, date_kst}
↓
[content_generator.py] LLM으로 리서치 노트 작성
├─ 페르소나: InvestIQs Research Analyst
├─ 톤: 3인칭 데이터 분석 (1인칭 금지)
├─ 구조: H2/H3 태그 + 구체적 수치 + FAQ 섹션
└─ 결과: JSON {title, content_html, meta_description, tags}
↓
[compliance.py] 규제 배너 + 면책 조항 삽입
├─ 상단: "⚠️ 정보 제공용 데이터 분석" 배너
└─ 하단: 투자 권유 금지 명시 텍스트
↓
[publishers/hugo.py] Hugo 발행
↓
[paperclip_audit.py] 감사 로깅
```

---

## 4. 영상 생성 파이프라인 (비동기)

### 4.1 블로그 마크다운 → YouTube Shorts (async `/make-video`)

```
입력: slug (web/content/{lang}/blog/{slug}.md)
↓
[video_script.py] 마크다운 → 스크립트 변환
├─ LLM으로 자막 생성 (한국어: kinetic 서브타이틀)
├─ 섹션별 시간 분배 (쇼츠: 60초 예산)
└─ B-roll 큐 표시 (5개 17초씩 전환)
↓
[chart_generator.py] 동적 차트 생성 (ffmpeg + PIL)
├─ SVG → PNG 렌더링
├─ 범례 + 주석 오버레이
└─ 배경색: DESIGN.md 기준 (dark navy #0f172a)
↓
[video_composer.py] ffmpeg NVENC 인코딩
├─ codec: h264_nvenc (GPU 가속)
├─ 해상도: 1080x1920 (쇼츠 9:16)
├─ 프레임: concat 필터로 B-roll 합성
└─ 출력: MP4 (최대 60MB)
↓
[bgm_manager.py] 배경음악 오버레이 (선택사항)
├─ 환경: BGM_ENABLED, BGM_CACHE_DIR
└─ 음향: -30dB (말 명료성 우선)
↓
[video_uploader.py] 다중 채널 배포
├─ YouTube: youtube-dl (oauth2)
├─ TikTok: tiktok-api (2FA + refresh token)
└─ Instagram Reels: meta-graph-api (24h 대기)
↓
[paperclip_audit.py] 감사 로깅
├─ work_product: type=youtube_short, url=...
└─ cost_events: video_processing 비용
↓
출력: {success, video_id, url, duration_sec, file_size}
```

**환경 게이트:**
- `FFMPEG_VIDEO_CODEC=h264_nvenc` — GPU 인코딩 (기본, 빠름)
- `SKIP_LONG_VIDEO=true` — 쇼츠만 생성 (시간 절반)
- `VIDEO_LOWER_THIRD=1` — 하단 자막바 오버레이
- `NVENC_PRESET=fast` — `fast|default|slow` (품질 vs 속도)

---

## 5. Paperclip 통합 (감사 + 비용 추적)

### 5.1 Issue Lifecycle

```
┌─────────────────────────────────────┐
│ n8n → bridge_api /url-to-content    │
└────────────┬────────────────────────┘
             ↓
      [create_audit_issue]
      ├─ title: "[url-to-content] youtube.com/..."
      ├─ status: "todo"
      └─ issue_id: UUID
             ↓
┌─────────────────────────────────────┐
│ URL fetch → Content Gen → Publish   │ (병렬 처리)
└────────────┬────────────────────────┘
             ↓
      [complete_audit_issue]
      ├─ status: success/failure
      ├─ work_product: {type, url, title}
      ├─ cost_events: {provider, model, tokens, costCents}
      └─ comment: 에러 메시지 (실패 시)
```

### 5.2 Cost Events 기록

```python
{
  "agentId": "auto-publisher",
  "issueId": UUID,
  "provider": "anthropic|openai|google",
  "model": "claude-haiku-4-5|gpt-4|gemini-2.5-flash",
  "inputTokens": 1200,
  "outputTokens": 450,
  "costCents": 12,           # USD 센트 (정수)
  "occurredAt": "2026-05-22T15:40:05.878Z"  # ISO 8601
}
```

**비용 계산:**
```
Anthropic Claude Haiku: $0.80/M input, $4.00/M output
Google Gemini Flash:    $0.075/M input, $0.30/M output
OpenAI GPT-4:          $30/M input, $60/M output

costCents = int((inputTokens/1e6 * input_rate + outputTokens/1e6 * output_rate) * 100)
```

### 5.3 Daily Cost Alert (23:00 KST)

```
POST /paperclip/cost-alert-check
↓
[paperclip_audit.check_cost_threshold]
├─ 금일 누적 비용 조회 (cost-events API)
├─ 임계값 비교 (env: PAPERCLIP_COST_DAILY_LIMIT_USD)
└─ 초과 시 Slack 알림 + issue 생성
```

---

## 6. 환경 변수 (마스터 게이트)

### 6.1 입력 채널

```bash
# Discord Hermes
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
DISCORD_CALLBACK_PORT=8900

# Telegram Bot
TELEGRAM_ENABLED=1                    # 기본: 0 (opt-in)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CALLBACK_PORT=8901

# Slack
SLACK_ENABLED=1                       # 기본: 0
SLACK_BOT_TOKEN=...
SLACK_SIGNING_SECRET=...
SLACK_CALLBACK_PORT=8902
```

### 6.2 Bridge API

```bash
BRIDGE_API_KEY=investiqs-dev          # 기본값
BRIDGE_ALLOWED_ORIGINS=https://n8n.investiqs.net,http://localhost:5678
BRIDGE_MAX_WORKERS=8                  # ThreadingHTTPServer 스레드 풀
RUN_PUBLISH_TIMEOUT_SEC=600           # 최대 실행 시간
```

### 6.3 LLM 백엔드

```bash
# Gemini CLI (1차)
GEMINI_CLI_MODEL=gemini-2.5-flash
LLM_PRIMARY_BACKEND=gemini

# Claude (2차)
ANTHROPIC_API_KEY=...

# Ollama (3차)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b

# OpenRouter (시장 분석 LLM)
OPENROUTER_API_KEY=...
OPENROUTER_MAX_TOKENS=2000
```

### 6.4 영상 생성

```bash
FFMPEG_VIDEO_CODEC=h264_nvenc         # GPU 코덱
NVENC_PRESET=fast                     # fast|default|slow
SKIP_LONG_VIDEO=true                  # 쇼츠만 (시간 절반)
VIDEO_LOWER_THIRD=1                   # 하단 자막바

# 배경음악
BGM_ENABLED=0                         # opt-in
BGM_CACHE_DIR=.omc/bgm_cache/
```

### 6.5 Paperclip 감사

```bash
PAPERCLIP_API_BASE=http://127.0.0.1:3100
PAPERCLIP_COMPANY_ID=ccd0c00a-d565-4fc4-910f-9d823665313b
PAPERCLIP_AUDIT_ENABLED=1             # 기본: 활성
PAPERCLIP_PUBLISH_ENABLED=0            # opt-in
PAPERCLIP_PUBLISH_DRY_RUN=0
PAPERCLIP_PUBLISH_DAILY_LIMIT=3
PAPERCLIP_COST_DAILY_LIMIT_USD=10.0   # 일일 비용 임계값
```

### 6.6 발행 채널

```bash
# YouTube
YOUTUBE_CHANNEL_ID=...
YOUTUBE_ENABLED=1

# TikTok
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...
TIKTOK_ENABLED=true

# Instagram Reels
META_ACCESS_TOKEN=...
IG_USER_ID=...

# Hugo + Cloudflare Pages
CLOUDFLARE_API_TOKEN=...
CLOUDFLARE_PAGES_PROJECT=invest-korea
```

---

## 7. 데이터 흐름 예시: URL → 블로그 + Shorts

### 시나리오: 사용자가 Discord에서 YouTube 링크 공유

```
1. 사용자 메시지 (Discord)
   > "분석해주세요: https://www.youtube.com/watch?v=dQw4w9WgXcQ"

2. Hermes Bot (:8900) 수신
   → /url-to-content POST 트리거
   → job_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
   → "작업 중입니다... 진행 상황은 DM으로 알려드릴게요"

3. _run_url_to_content_job() 비동기 실행
   a) [url_fetcher.py] YouTube 자막 추출
      - youtube-transcript-api: "오늘 시장은 S&P 500이 3% 상승..."
      - yt-dlp 메타: title, 채널명, 썸네일
   
   b) [content_generator.py] LLM 콘텐츠 생성
      - Prompt: 자막 + 페르소나 (InvestIQs Analyst)
      - Gemini 응답: HTML 블로그 본문 생성
   
   c) [content_verifier.py] 2단계 검증
      - SEO 점수, 단어 길이 (>1500), 규제 배너
      - 페르소나 일관성 (1인칭 금지)
   
   d) [publishers/hugo.py] Hugo 발행
      - 파일: web/content/ko/blog/sp500-march-surge.md
      - Hugo 빌드 + Cloudflare 배포
      - URL: https://investiqs.net/ko/blog/sp500-march-surge/
   
   e) [paperclip_audit.py] 감사 로깅
      - Issue: "[url-to-content] youtube.com/watch?v=dQw4w9WgXcQ"
      - Work_product: blog_post, https://investiqs.net/ko/blog/sp500-march-surge/
      - Cost_event: gemini-flash, 2500 tokens → 0.1¢

4. 블로그 발행 완료
   → Hermes DM: "✅ 블로그 발행됨: https://investiqs.net/ko/blog/sp500-march-surge/"

5. n8n (08:30 shorts_auto) 트리거
   a) [video_script.py] 마크다운 → 쇼츠 스크립트
      - 60초 분할: 도입(10초) + 차트(30초) + 핵심 수치(15초) + CTA(5초)
   
   b) [chart_generator.py] 차트 생성
      - S&P 500 일봉 차트 (최근 1개월)
      - 텍스트: "3% 상승 (DESIGN.md 강조색)"
   
   c) [video_composer.py] ffmpeg 합성
      - 입력: 차트 PNG, 자막 SRT, 배경음악 MP3
      - 코덱: h264_nvenc (GPU)
      - 출력: shorts_sp500_march_surge.mp4 (1080x1920, 60초)
   
   d) [video_uploader.py] YouTube Shorts 업로드
      - Privacy: public
      - 설명: "InvestIQs Research | S&P 500 3% 상승"
      - 썸네일: 블로그 이미지 자동 추출
   
   e) [paperclip_audit.py] 감사
      - Work_product: youtube_short, https://www.youtube.com/shorts/xyzABC...
      - Cost_event: video_generation, ffmpeg (compute), 3¢

6. TikTok / Instagram Reels 업로드 (비동기)
   - TikTok: 즉시 업로드 (token 유효 시)
   - Instagram: 24시간 대기 (Meta 정책) + callback 완료

7. 최종 Discord DM
   > "✅ 완료!\n블로그: https://investiqs.net/ko/blog/sp500-march-surge/\nYouTube: https://www.youtube.com/shorts/xyzABC...\nTikTok: https://vm.tiktok.com/..."
```

---

## 8. 모듈 책임 매트릭스

| 파일 경로 | 책임 | 의존성 |
|----------|------|--------|
| **n8n/bridge_api.py** | HTTP 라우터, job 큐 관리 | auto_publisher.* |
| **auto_publisher/url_fetcher.py** | URL → 콘텐츠 추출 (YT/IG/TikTok/기사) | youtube-transcript-api, yt-dlp, trafilatura |
| **auto_publisher/content_generator.py** | LLM 콘텐츠 생성, 페르소나 일관성 | gemini CLI, anthropic SDK |
| **auto_publisher/content_verifier.py** | 2단계 검증 (SEO, 규제, 페르소나) | auto_publisher.compliance |
| **auto_publisher/publishers/hugo.py** | 마크다운 파일 저장, Hugo 빌드, CF 배포 | hugo binary, wrangler CLI |
| **auto_publisher/paperclip_publish.py** | Paperclip work_product 폴링 + 발행 | paperclip API |
| **auto_publisher/paperclip_audit.py** | Paperclip issue/cost_events 로깅 | paperclip API |
| **auto_publisher/video_script.py** | 마크다운 → 영상 스크립트 + SRT 자막 | LLM (Gemini/Claude) |
| **auto_publisher/chart_generator.py** | 데이터 시각화 (PIL, matplotlib) | yfinance, pillow |
| **auto_publisher/video_composer.py** | ffmpeg 영상 합성 (NVENC) | ffmpeg binary |
| **auto_publisher/bgm_manager.py** | 배경음악 오버레이 | pydub, ffmpeg |
| **auto_publisher/video_uploader.py** | YouTube/TikTok/Instagram 업로드 | google-api-client, TikTok API, meta-graph-api |
| **auto_publisher/topic_manager.py** | 토픽 큐 관리 (JSON 기반) | file I/O |
| **auto_publisher/market_wrap.py** | 미국 증시 스냅샷 수집 + 분석 | yfinance, alpha_vantage |
| **auto_publisher/market_intraday.py** | 미국 증시 장중 분석 | yfinance, 실시간 데이터 |
| **auto_publisher/market_weekly.py** | 주간 시장 분석 리포트 | yfinance, 과거 데이터 |
| **auto_publisher/health_alerter.py** | 백그라운드 헬스 체크 (30분 간격) | bridge_api /health/full |
| **auto_publisher/compliance.py** | 규제 배너 + 면책 조항 삽입 | 설정 JSON |
| **auto_publisher/token_estimator.py** | 토큰 → USD 비용 추정 | LLM 가격 테이블 |

---

## 9. 트러블슈팅 (Phase 2/3)

### 9.1 자동 발행이 안 될 때

1. **Bridge API 살아있나?**
   ```bash
   curl -s https://callback.investiqs.net/health/full
   # 응답: {status: ok, n8n: ok, bot: ok, cost_events: []}
   ```

2. **n8n 컨테이너 상태**
   ```bash
   docker ps | grep n8n
   docker exec n8n-n8n-1 sqlite3 /home/node/.n8n/database.sqlite \
     "SELECT COUNT(*) FROM workflow_entity WHERE active=1"
   # 27이 나와야 함
   ```

3. **LLM 가용성**
   ```bash
   which gemini                    # Gemini CLI 설치 확인
   curl http://localhost:11434     # Ollama 실행 확인
   ```

4. **Paperclip 연결**
   ```bash
   curl -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
     http://127.0.0.1:3100/api/health
   ```

### 9.2 영상 합성이 느릴 때

1. **GPU 사용 확인**
   ```bash
   nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader
   # 80% 이상이면 정상
   ```

2. **NVENC 하드웨어 가용성**
   ```bash
   ffmpeg -encoders | grep nvenc
   # h264_nvenc 또는 hevc_nvenc 보이면 OK
   ```

3. **쇼츠 전용 모드 활성화**
   ```bash
   export SKIP_LONG_VIDEO=true    # 시간 절반으로 단축
   ```

### 9.3 TikTok 업로드 실패

1. **Token 갱신 상태**
   ```bash
   curl https://callback.investiqs.net/health/full | jq .tiktok_token_expires_in_sec
   # 86400초(24h) 이상이면 안전
   ```

2. **재인증 필요 시 (403 unaudited)**
   ```bash
   # 브라우저: https://www.tiktok.com/v2/auth/authorize/?client_key=...
   # URL은 auto_publisher/video_uploader.py의 tiktok_auth_setup() 출력 참조
   ```

---

## 10. 향후 계획 (Phase 3)

### 10.1 Event-Driven Paperclip (polling → webhook)

현재: n8n cron이 bridge_api를 주기적으로 폴링  
계획: Paperclip이 issue 상태 변경 시 webhook 발행 → bridge_api 자동 트리거

```
Paperclip issue status: todo → ready
↓
webhook POST https://callback.investiqs.net/paperclip/event
├─ event_type: work_product_ready
├─ work_product_id: UUID
└─ metadata: {type: blog_post, ...}
↓
bridge_api [on_work_product_ready]
└─ /url-to-content 또는 /publish 즉시 실행
```

### 10.2 비용 최적화

- **LLM 모델 자동 선택**: 작업 복잡도별 Haiku ↔ Sonnet 동적 라우팅
- **배치 처리**: 여러 job을 벡터화해 한 번의 LLM 호출로 처리
- **캐싱 계층**: 반복 질의 결과 Redis 캐시

### 10.3 다중 언어 최적화

- 언어별 LLM 선택 (한국어: Gemini, 영어: Claude, 일본어: Claude)
- 지역별 시장 데이터 피더 (미국, 한국, 일본, 동남아)

---

## 11. 배포 체크리스트

### 사전 조건
- [ ] Docker + docker-compose (n8n 컨테이너)
- [ ] Python 3.10+ + venv
- [ ] NVIDIA GPU + CUDA 12.1 (ffmpeg NVENC)
- [ ] Hugo 0.125+ 설치
- [ ] Cloudflare Pages 설정
- [ ] n8n 27개 워크플로우 활성화 (`n8n/ACTIVATION_GUIDE.md`)

### 환경 설정
- [ ] `.env` 파일 생성 (`.env.example` 참조)
- [ ] 모든 API 키 설정 (Gemini, Claude, OpenRouter, Paperclip, TikTok, YouTube)
- [ ] Discord/Telegram/Slack bot 토큰 설정
- [ ] Cloudflare 토큰 설정

### 테스트
- [ ] `/health/full` 응답 확인 (모든 서브 시스템)
- [ ] `/publish?lang=ko` 수동 테스트
- [ ] `/url-to-content` POST 테스트 (Discord)
- [ ] `/make-video` 영상 생성 테스트 (GPU 확인)

### 모니터링
- [ ] Bridge API 로그 (`/tmp/bridge.log`)
- [ ] Auto publisher 로그 (`auto_publisher/auto_publisher.log`)
- [ ] Paperclip issue 대시보드 (cost_events 확인)
- [ ] n8n 워크플로우 실행 로그 (docker logs)
