# 09. n8n 워크플로우 운영 가이드

> **작성일**: 2026-04-23
> **대상 독자**: 1인 운영자 (프로젝트 소유자)
> **범위**: `/home/mh/ocstorage/workspace/nichproject/n8n/workflows/` 10개 워크플로우
> **기반 인프라**: n8n latest (docker), bridge_api `http://host.docker.internal:8765/`, Asia/Seoul
> **연계 문서**: `record/00_executive_summary.md`, `record/02_korean_investment_youtube.md`, `record/05_shortform_viral_trends.md`, `record/06_newsletter_monetization.md`

---

## 0. 한눈에 보기 (Overview)

본 가이드는 투자/재테크 자동 퍼블리싱 파이프라인을 n8n으로 오케스트레이션하는 10개 워크플로우의 import·설정·운영·트러블슈팅을 다룬다. 기존 `daily_publisher.json`이 "콘텐츠 생성·발행"을 담당한다면, 아래 10개는 **리포트 자동화·숏폼·벤치마킹·비교 콘텐츠·뉴스레터·교차배포·SEO 모니터링·컴플라이언스·댓글 자동화·KPI 대시보드**의 운영 계층을 담당한다.

### 10개 워크플로우 요약

| # | 파일 | 트리거 | 빈도 | 핵심 출력 | 연계 KPI |
|---|---|---|---|---|---|
| 1 | `weekly_dividend_report.json` | cron | 월 08:00 | 월배당 ETF 주간 리포트 → Hugo + Tistory | Blog PV, AdSense |
| 2 | `news_react_shorts.json` | cron 30분 | 30min | Shorts 스크립트 (뉴스 리액트) | Shorts 완시청률 |
| 3 | `benchmark_youtube_tracker.json` | cron | 일 21:00 | 5대 채널 주간 영상 DB + 주간 리포트 | 콘텐츠 아이디어 |
| 4 | `comparison_content.json` | cron | 수 09:00 | "A vs B" 비교 콘텐츠 + EN 번역 | 롱테일 CTR |
| 5 | `newsletter_weekly.json` | cron | 금 07:00 | Stibee 주간 뉴스레터 발송 | 오픈율·CTR |
| 6 | `cross_platform_post.json` | webhook | 블로그 발행시 | X 스레드 + IG Reels | 크로스 도달 |
| 7 | `keyword_rank_monitor.json` | cron | 일 23:00 | GSC 상위 키워드 변동 → Discord | SEO 순위 |
| 8 | `compliance_gate.json` | webhook | 발행 직전 | 금칙어·면책 검증 → 발행/차단 | 법적 리스크 |
| 9 | `comment_auto_reply.json` | webhook | 댓글 도착시 | GPT 답변 자동 게시 | 유튜브 참여도 |
| 10 | `kpi_weekly_dashboard.json` | cron | 월 09:00 | Blog+YT+Newsletter 3채널 KPI → Discord | Health Score |

---

## 1. Import 가이드 (공통)

### 1.1 사전 준비
1. n8n 컨테이너가 `host.docker.internal:8765`로 bridge_api에 접근 가능해야 함
   - docker-compose 예: `extra_hosts: ["host.docker.internal:host-gateway"]` (Linux)
2. n8n 관리자 계정(Owner) 로그인
3. 타임존 확인: Settings → Personal → Timezone = `Asia/Seoul` (워크플로우 JSON에도 명시됨)

### 1.2 Import 절차 (각 파일 공통)
1. n8n UI 좌상단 **Workflows** → **Add workflow** → **Import from File**
2. `/home/mh/ocstorage/workspace/nichproject/n8n/workflows/<파일명>.json` 선택
3. Import 후 **필요 크리덴셜 연결**(섹션 2 참조)
4. **Save** → 검증 완료 후 **Active** 스위치 ON

### 1.3 환경변수(Variables) 주입
n8n Settings → **Variables**에 아래 5개 등록 (Community Edition이면 Credentials로 대체):

| 변수명 | 용도 | 샘플 |
|---|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API v3 | `AIzaSyXXXXXXXX...` |
| `STIBEE_API_KEY` | Stibee REST API AccessToken | `stibee_xxx...` |
| `STIBEE_LIST_ID` | Stibee 리스트 식별자 | `12345` |
| `DISCORD_WEBHOOK_KEYWORD` | 키워드 순위 알림 채널 | `https://discord.com/api/webhooks/...` |
| `DISCORD_WEBHOOK_COMPLIANCE` | 컴플라이언스 차단 알림 | `https://discord.com/api/webhooks/...` |
| `DISCORD_WEBHOOK_KPI` | 주간 KPI 리포트 | `https://discord.com/api/webhooks/...` |

> Variables가 비활성 버전(Self-host Community Edition은 라이선스별 차이)이라면 각 HTTP Request 노드에서 직접 `{{ $env.YOUTUBE_API_KEY }}`로 치환.

---

## 2. 필요 크리덴셜 리스트

| # | 크리덴셜 | 형식 | 획득 경로 | 사용 워크플로우 |
|---|---|---|---|---|
| C1 | **YouTube Data API v3 Key** | API Key | Google Cloud Console → APIs → YouTube Data v3 enable → Credentials | #3 benchmark, #9 comment |
| C2 | **YouTube OAuth2 (영상/댓글 쓰기)** | OAuth2 | Cloud Console → OAuth consent + Credentials (scope: `youtube.force-ssl`) | #9 comment_auto_reply |
| C3 | **Google Search Console API** | OAuth2 / Service Account | Cloud Console → Search Console API → 사이트 소유자 권한 | #7 keyword_rank_monitor |
| C4 | **GA4 Data API** | Service Account | Cloud Console → GA4 Reporting API → property에 service account 추가 | #10 kpi_weekly_dashboard |
| C5 | **Stibee API Token** | Bearer | stibee.com → 설정 → API 키 발급 | #5 newsletter_weekly |
| C6 | **Discord Webhook (3개)** | URL | 서버 → 채널 → 통합 → 웹후크 새로 만들기 (키워드/컴플라이언스/KPI 각 1개) | #7, #8, #10 |
| C7 | **Twitter (X) OAuth2 API** | OAuth2 | developer.x.com → App → Read+Write 권한, OAuth2 User Context | #6 cross_platform_post |
| C8 | **Instagram Graph API (Business)** | OAuth2 Long-lived | Facebook Developers → Instagram Graph API → Business/Creator 계정 연동 | #6 cross_platform_post |
| C9 | **Tistory OAuth** | OAuth | bridge_api가 대행 (`/publish-tistory`) → Tistory Open API 앱 등록 필요 | #1 weekly_dividend_report |
| C10 | **OpenAI API Key** | Bearer | platform.openai.com (bridge_api가 `/comments/gpt-reply` 내부에서 사용) | #9 comment_auto_reply |

### 2.1 크리덴셜 연결 체크리스트
- [ ] YouTube Data API 일일 쿼터 **10,000 units** 초과 주의 (Search.list = 100 units/call → #3 워크플로우 5채널 × 1회/주 = 500 units, 안전)
- [ ] Stibee API는 발송 한도가 **플랜별 다름** (Free=월 500건, Light=1만건). 테스트 시 Draft 모드 활용
- [ ] Discord Webhook은 **Rate limit 30req/60s** — 대량 알림 시 배치 필요
- [ ] X API Free tier = 월 1,500 post. 유료 Basic($100/월) 권장
- [ ] Instagram Graph API는 **Business Account + Facebook Page 연결** 필수 (개인 계정 불가)

---

## 3. 각 워크플로우 상세 설명

### 3.1 `weekly_dividend_report.json` — 주간 월배당 ETF 리포트
- **트리거**: 매주 월 08:00 KST (`0 8 * * 1`)
- **체인**: Market Cache Refresh → 리포트 생성 → Success IF → Hugo 발행 → Tistory 교차발행 → 성공 로그
- **대상 티커**: SCHD, JEPI, JEPQ, O, QYLD, DIVO, SPYD, HDV, VYM, TLTW (10종 고정, 필요시 JS 노드에서 수정)
- **bridge_api 의존**: `/refresh-market-cache`, `/dividend-report`, `/publish-hugo`, `/publish-tistory`
- **예상 실행시간**: 15~25분 (차트 렌더링 포함)
- **KPI 기여**: Pillar "월배당 ETF" 에버그린 트래픽 주간 갱신 [record 01]

### 3.2 `news_react_shorts.json` — 뉴스 리액트 Shorts 30분 폴링
- **트리거**: `*/30 * * * *` (24시간 동작, 총 48회/일)
- **체인**: RSS 폴링 → 신규 필터 (score≥7, top 3) → 존재 IF → 컴플라이언스 → Shorts 스크립트 생성
- **RSS 소스**: 한경/매경/연합/이데일리/뉴스핌/서울경제 6개
- **훅 스타일**: `curiosity_gap` (record 05 기준 상위 패턴)
- **예상 트래픽**: 일 신규 스크립트 5~15편 (중복 제거 후)
- **주의**: 실제 업로드는 하지 않음 (스크립트 생성까지). 업로드는 `cross_platform_post.json` 또는 수동 검수 후 실행

### 3.3 `benchmark_youtube_tracker.json` — 5대 벤치마크 채널 주간 수집
- **트리거**: 매주 일 21:00 KST (`0 21 * * 0`)
- **대상 채널**: 슈카월드, 삼프로TV, 김작가TV, 월급쟁이부자들TV, 부읽남TV (record 02 Top 6 중 5개)
- **API 사용**: YouTube Data v3 `search.list` (채널당 100 units, 5채널 = 500 units/주)
- **저장 경로**: `record/benchmark_weekly_YYYYMMDD.md` (bridge_api 내부)
- **활용**: Monday 09:00 KPI 대시보드와 별개로 제목 A/B 시드 확보용

### 3.4 `comparison_content.json` — "A vs B" 비교 콘텐츠
- **트리거**: 매주 수 09:00 KST
- **페어 풀**: SCHD:JEPI, JEPQ:JEPI, QQQ:VOO, VOO:SPY, SCHD:VOO, VYM:HDV, DIVO:JEPQ, TLT:TLTW, GLD:KRXGOLD, ISA:연금저축, ISA:IRP, 연금저축:IRP (12개)
- **로테이션**: `rotation_key=weekly_wed` + 60일 exclude → 자동 순환
- **체인**: 페어 선택 → 5년 백테스트 → 콘텐츠 생성 → IF → Hugo 발행 → 영문 번역(Tier-1) → 로그
- **기대 ROI**: 롱테일 전환률 36% (record 04)

### 3.5 `newsletter_weekly.json` — Stibee 주간 뉴스레터
- **트리거**: 매주 금 07:00 KST
- **섹션**: market_summary, top_posts, dividend_spotlight, tax_tip, portfolio_action (5 블록)
- **A/B 제목**: 자동 2안 생성 후 `subject_a` 사용 (B안은 차주 순환)
- **최대 분량**: 2,800자 (record 06 표준 2,000~3,000자 준수)
- **게이트**: 금칙어·면책 컴플라이언스 통과 필수
- **Stibee 엔드포인트**: `POST /v1/lists/{LIST_ID}/campaigns` (AccessToken 헤더)

### 3.6 `cross_platform_post.json` — X 스레드 + IG Reels 교차 발행
- **트리거**: Webhook (`POST /webhook/blog-published`)
- **페이로드 예**:
  ```json
  { "post_url": "https://...", "post_id": "abc", "title": "...", "summary": "..." }
  ```
- **병렬 체인**: X 스레드 발행(첫 트윗 → 나머지) ∥ Reels 렌더링 → IG 업로드 → 병합 로그
- **bridge_api 의존**: `/cross-post/generate`, `/x/post-thread`, `/reels/build`, `/instagram/upload-reel`
- **호출 예시 (curl)**:
  ```bash
  curl -X POST http://n8n:5678/webhook/blog-published \
    -H "Content-Type: application/json" \
    -d '{"post_url":"https://...","post_id":"123","title":"SCHD vs JEPI","summary":"..."}'
  ```

### 3.7 `keyword_rank_monitor.json` — GSC 순위 변동 Discord 알림
- **트리거**: 매일 23:00 KST
- **기준**: 28일 rolling, rank_delta≥3 또는 impression 25% 이상 변화
- **포맷**: 상승 Top 10 + 하락 Top 10 (임계 미달 시 스킵)
- **알림 채널**: `DISCORD_WEBHOOK_KEYWORD` 환경변수

### 3.8 `compliance_gate.json` — 발행 직전 컴플라이언스 게이트
- **트리거**: Webhook (`POST /webhook/compliance-gate`)
- **페이로드**: `{ body: { content_id, title, content } }`
- **검증 2단계**:
  1. 금칙어 (추천/따라사세요/100% 수익/보장/리딩/무조건/절대/반드시 오른다/수익률 확정)
  2. 면책 + 출처 3개 이상
- **분기**: 통과 → `/publish`, 실패 → Discord 차단 알림 (`DISCORD_WEBHOOK_COMPLIANCE`)
- **법적 근거**: record 00 R2 리스크 (자본시장법·유사투자자문업)

### 3.9 `comment_auto_reply.json` — 유튜브 댓글 GPT 자동 답글
- **트리거**: Webhook (`POST /webhook/youtube-comment`)
- **페이로드**: `{ body: { comment_id, video_id, author, text } }`
- **체인**: 페이로드 검증 → 필터(금칙어/광고/외부링크/리딩초대/전화번호/크립토스캠) → 의도 분류 → GPT 답변(max 280자) → 답글 게시
- **톤**: `friendly_expert` + 자동 disclaimer 삽입
- **스팸 처리**: 필터 탈락 시 `heldForReview` 상태로 모더레이션 큐 이동

### 3.10 `kpi_weekly_dashboard.json` — 주간 KPI 대시보드
- **트리거**: 매주 월 09:00 KST (daily 6~8시 콘텐츠 자동발행 완료 후)
- **병렬 수집**: 블로그 PV(GA4+GSC), 유튜브(조회수·완시청률·구독 순증), 뉴스레터(오픈율·CTR·해지율·순증)
- **Health Score**: PV≥3,500/week, open_rate≥0.40, completion_rate≥0.60 기준 100점 만점
- **출력**: Discord 리치 메시지 + `/kpi/save-snapshot`에 주간 히스토리 저장

---

## 4. 활성화 순서 (권장)

블로그 단일 채널 → 3채널 멀티플랫폼으로 점진적 확장. 한 번에 모두 켜지 말고 **안정 확인 후 다음 단계**로 이동.

### Phase 1 (Week 1~2) — 핵심 운영 & 안전망
1. **#8 compliance_gate** — 모든 발행 경로의 앞단 게이트. 가장 먼저 켜서 법적 리스크 차단
2. **#1 weekly_dividend_report** — 기존 daily_publisher 보완하는 에버그린 리포트
3. **#7 keyword_rank_monitor** — SEO 피드백 루프 확보
4. **#10 kpi_weekly_dashboard** — 주간 Health Score 가시성

### Phase 2 (Week 3~4) — 콘텐츠 확장
5. **#4 comparison_content** — 비교 콘텐츠 주 1건으로 롱테일 커버
6. **#3 benchmark_youtube_tracker** — 경쟁 채널 트렌드 주간 수집

### Phase 3 (Week 5~6) — 채널 확장
7. **#5 newsletter_weekly** — Stibee 구독자 0부터 시작, 첫 4주는 테스트 발송 (내부 이메일만)
8. **#6 cross_platform_post** — daily_publisher 발행 webhook과 연동, X/IG 교차 배포

### Phase 4 (Week 7~8) — 고빈도 자동화
9. **#2 news_react_shorts** — 30분 폴링, API 쿼터와 컴플라이언스 안정화 후
10. **#9 comment_auto_reply** — 댓글량 증가 시점에 활성화 (구독자 500 이후 권장)

### 활성화 체크리스트 (각 워크플로우 공통)
- [ ] 크리덴셜 연결 확인
- [ ] Manual Execute로 dry-run 1회 성공
- [ ] 로그 노드 출력에서 실패 지점 없음
- [ ] Active ON → 최소 24시간 Executions 탭 모니터링
- [ ] 의도치 않은 비용 지출 없음 (API quota, Stibee 발송 한도)

---

## 5. 트러블슈팅 FAQ

### Q1. `ECONNREFUSED host.docker.internal:8765` 오류
**원인**: n8n docker 컨테이너가 호스트 네트워크에 접근 불가
**해결**:
- Linux: `docker run --add-host=host.docker.internal:host-gateway ...`
- docker-compose.yml:
  ```yaml
  services:
    n8n:
      extra_hosts:
        - "host.docker.internal:host-gateway"
  ```
- 또는 bridge_api를 `0.0.0.0:8765`로 바인딩하고 n8n에서 호스트 IP 직접 사용

### Q2. `YouTube API 403 quotaExceeded`
**원인**: 일일 10,000 units 초과
**해결**:
- Cloud Console → Quotas → YouTube Data API v3 → 쿼터 증설 요청
- 또는 `#3 benchmark_tracker`의 `maxResults`를 10 → 5로 축소
- `#9 comment_auto_reply`는 webhook-driven이므로 영향 미미

### Q3. Stibee 발송 후 오픈율이 0%
**원인**: 개인정보 보호/Apple Mail Privacy Protection의 prefetch
**해결**:
- Stibee 대시보드에서 **Unique open vs Total open** 확인
- 최소 24시간 후 측정
- Subject line A/B 테스트로 상대 비교

### Q4. Discord 알림이 오지 않음
**원인**: Webhook URL 오타 또는 채널 권한
**체크리스트**:
1. Variables의 `DISCORD_WEBHOOK_*` 값이 실제 URL과 일치?
2. 서버 설정 → 통합 → 웹후크에서 404 아닌지 확인
3. n8n Executions 탭에서 `Discord 알림 발송` 노드 Response Code 200인지

### Q5. Webhook 엔드포인트가 404
**원인**: 워크플로우가 **Inactive** 상태 또는 `Production URL`이 아닌 `Test URL` 사용
**해결**:
- n8n Webhook 노드 → `Production URL` 복사 (Active 후에만 동작)
- Test URL은 워크플로우 `Execute Workflow` 클릭 시에만 listen

### Q6. `n8n-nodes-base.httpRequest` typeVersion 불일치 경고
**원인**: n8n 버전 업그레이드 후 typeVersion 차이
**해결**:
- 본 JSON은 `typeVersion: 4` 기준. n8n 1.x latest에서 호환
- 경고만 뜨고 실행은 정상이면 무시 가능
- 노드 재저장 시 자동으로 최신 버전으로 업데이트됨

### Q7. `JSON 파싱 오류 on jsonBody`
**원인**: `jsonBody` 필드 내 `{{ }}` 표현식이 따옴표 누락
**체크**: `"content": {{ JSON.stringify($json.content) }}` — `JSON.stringify`로 감싼 경우 바깥 따옴표 없음이 맞음

### Q8. 컴플라이언스 게이트가 정상 콘텐츠도 차단
**원인**: 금칙어 리스트가 너무 광범위하거나 오탐
**해결**:
- bridge_api `/compliance/keywords`에서 `banned_list` 파라미터 조정
- `compliance_gate.json`의 HTTP 노드 `banned_list` 기본값 수정
- 차단 Discord 알림에 사유가 기록되므로 주간 오탐 로그 리뷰 권장

### Q9. YouTube 댓글 답변이 중복 게시됨
**원인**: YouTube → n8n webhook 재전송 (YouTube PubSub/Polling 구조상 발생 가능)
**해결**:
- `#9` 워크플로우 시작부에 `Deduplicate` 노드 추가 (comment_id 기준)
- 또는 bridge_api `/comments/gpt-reply`에서 idempotency key 적용

### Q10. 시간대(타임존) 어긋남
**원인**: n8n 인스턴스 타임존 vs 워크플로우 settings.timezone 불일치
**확인**:
- `docker exec -it n8n env | grep TZ` → `TZ=Asia/Seoul`인지
- 워크플로우 settings.timezone = "Asia/Seoul" (JSON에 명시됨)
- 두 값이 일치해야 cron이 정확히 KST 기준

---

## 6. 운영 모니터링 체크리스트

### 일일 (매일 10분)
- [ ] n8n Executions 탭 → 실패 건 있는가? 있다면 로그 확인
- [ ] Discord KPI 채널에서 전일 발행 결과 요약 확인
- [ ] 컴플라이언스 차단 알림 0~2건이 정상 (5건 이상이면 리스트 점검)

### 주간 (매주 월 10:00, KPI 리포트 수신 직후)
- [ ] Health Score 70점 이상 유지
- [ ] 오픈율 40%, 완시청률 60% 근접
- [ ] Stibee 해지율 <1.5%
- [ ] GSC 순위 하락 Top 10 중 YMYL 핵심 키워드 있는지 확인

### 월간 (매월 1일)
- [ ] YouTube API 쿼터 사용량 점검
- [ ] Stibee 플랜 업그레이드 필요성 (구독자 1만 → Light, 3만 → Pro)
- [ ] Discord webhook Rate limit 충돌 로그
- [ ] 백테스트 `record/benchmark_weekly_*.md` 누적본에서 콘텐츠 아이디어 추출

---

## 7. 확장 로드맵 (이 가이드 이후)

본 10개 워크플로우로 M1(Week 1~4) 기반과 M2(Week 5~8) 초기 확장을 커버. M3(Week 9~13) 수익화 단계에서 아래 워크플로우 추가 권장:

| # | 추가 예정 | 목적 |
|---|---|---|
| 11 | `affiliate_rotator.json` | 증권사 CPA 링크 A/B 로테이션, 클릭률 기록 |
| 12 | `season_calendar.json` | 연말정산 1월·종소세 5월·FOMC·배당락 D-3 집중 발행 트리거 |
| 13 | `premium_tier_mvp.json` | 네이버 프리미엄콘텐츠 발행 + 결제 웹훅 |
| 14 | `multi_lang_sync.json` | ko→en/ja 정기 재번역 (lastmod 갱신) |
| 15 | `podcast_repurpose.json` | Hugo 블로그 → 팟캐스트 TTS 자동 생성 |

---

## 8. 참고 자료

- `record/00_executive_summary.md` — 상위 전략, 90일 로드맵, KPI 프레임워크
- `record/02_korean_investment_youtube.md` — Top 30 벤치마크 채널 선정 근거 (#3 워크플로우)
- `record/05_shortform_viral_trends.md` — Shorts 훅·포맷·길이 최적값 (#2, #6)
- `record/06_newsletter_monetization.md` — Stibee·발송 주기·섹션 템플릿 (#5)
- `auto_publisher/content_generator.py` — bridge_api 뒤의 실제 콘텐츠 생성 로직 (본 워크플로우들이 호출)
- `n8n/workflows/daily_publisher.json` — 기존 일일 발행 파이프라인 (본 10개의 상위 게이트와 연동)

---

**문서 버전**: v1.0 (2026-04-23)
**다음 리뷰 권장**: 10개 전부 Active 후 2주차
**JSON 검증 상태**: 10/10 PASS (파이썬 `json.load` 기준)
