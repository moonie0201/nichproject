# investiqs.net GEO(AI 검색 인용) 감사 — 2026-08-27

## 조사 방법
- `render_page.py --mode auto`로 4개 URL 실제 fetch (모두 `is_spa: false` — 순수 서버 렌더링, JS 실행 없이도 전체 콘텐츠 확보됨. AI 크롤러 대부분이 JS를 실행하지 않으므로 이 자체가 강점).
- `curl`로 robots.txt, llms.txt 실물 확인.
- HTML 내 JSON-LD 구조화 데이터 직접 파싱.

---

## 1. AI 크롤러 접근성 (실측)

robots.txt (`https://investiqs.net/robots.txt`) 실제 내용:
```
User-agent: *
Allow: /
Disallow: /tags/ /categories/ /search/ /*/tags/ /*/categories/ /*/search/ /*?*

User-agent: GPTBot        → Allow: /
User-agent: ClaudeBot     → Allow: /
User-agent: PerplexityBot → Allow: /
User-agent: Google-Extended → Allow: /
```

| 크롤러 | 상태 | 비고 |
|---|---|---|
| GPTBot | 허용 | 명시적 규칙 |
| ClaudeBot | 허용 | 명시적 규칙 |
| PerplexityBot | 허용 | 명시적 규칙 |
| OAI-SearchBot | 허용 (암묵) | 전용 규칙 없음, `User-agent: *`의 `Allow: /`에 포함됨 |
| Google-Extended | 허용 | 명시적 규칙 |
| CCBot / anthropic-ai / cohere-ai | 허용 (암묵) | 전용 차단 규칙 없음 → 학습용 크롤러도 전부 수집 가능. 브리프에 있던 "학습만 차단" 옵션은 현재 미적용 상태 (의도적 정책 결정 사항이라면 그대로 둬도 무방, 학습 데이터 노출을 줄이고 싶다면 `CCBot: Disallow: /` 추가 검토) |

**문제 발견 — llms.txt와 robots.txt의 모순:**
`llms.txt`(200 OK, 정상 응답)의 "핵심 콘텐츠" 섹션이 카테고리 허브 링크로 구성돼 있음:
```
- [ETF 투자 가이드](https://investiqs.net/ko/categories/etf/)
- [배당주 전략](https://investiqs.net/ko/categories/배당주/)
- [절세 계좌](https://investiqs.net/ko/categories/절세/)
- [부동산 투자](https://investiqs.net/ko/categories/부동산/)
- [재테크 기초](https://investiqs.net/ko/categories/재테크-기초/)
```
그런데 robots.txt는 `/categories/`와 `/*/categories/`를 전면 차단한다. GPTBot/ClaudeBot/PerplexityBot 모두 robots.txt를 준수하는 크롤러이므로, llms.txt가 안내하는 5개 핵심 진입 링크 전부가 실제로는 접근 불가 — llms.txt의 실효성을 스스로 깎아먹는 구조.
**수정안:** llms.txt의 카테고리 링크를 개별 아티클 목록(사이트맵 기반 상위 글 URL)이나 태그가 아닌 정적 허브 페이지로 교체. 또는 카테고리 페이지에 한해 AI 봇 예외 규칙 추가 (`User-agent: GPTBot \n Allow: /*/categories/`).

---

## 2. llms.txt 평가

- `/llms.txt` 200 OK, 형식은 llms.txt 표준(H1 + `>` 요약 + H2 섹션 + 링크 목록)을 정확히 준수. 사이트 정체성, 콘텐츠 방법론(yfinance/pykrx 실데이터), 다국어 발행 사실, 면책 조항까지 간결하게 요약돼 있어 구조 자체는 우수.
- 구글은 llms.txt를 인덱싱/랭킹에 사용하지 않는다고 공식적으로 밝힌 바 있음(AI Overviews에는 영향 없음) — 따라서 이 파일의 가치는 **ChatGPT(OAI-SearchBot 학습/조회), Perplexity, 기타 LLM 기반 에이전트가 사이트 개요를 빠르게 파악하는 용도**로 한정해서 봐야 함. 유지할 가치는 있으나 순위 신호로 기대하면 안 됨.
- 위 1번 카테고리 링크 문제만 고치면 이 파일은 그대로 둬도 됨. 대표 아티클(예: `foreign-tax-credit-overseas-etf-2026`) 직접 링크를 1~2개 추가하는 것도 저비용 개선.

---

## 3. Passage 단위 인용 가능성 (기사 2건)

### `foreign-tax-credit-overseas-etf-2026` (해외 ETF 외국납부세액공제)
- 리드 문단: 120 단어, 결론 우선 구조("결론부터 말하면...") + 4개 요약 불릿. AI 요약 추출에 이상적인 형태.
- H2 12개 중 다수가 질문형/판별형 헤딩("먼저 판별: 누가...", "왜 구분해야 하나", 오해 1~4 등) — 구조적 추출성 좋음.
- `FAQPage` JSON-LD 5문항 실재 확인. 각 답변이 2문장(약 35~50단어)으로 자기완결적이며 조건부 표현("~일 수 있습니다", "확인이 필요합니다")으로 오인용 리스크를 낮춤. **FAQ 답변이 AI가 그대로 인용하기 가장 좋은 블록.**
- 1차 출처 명시 우수: "출처와 확인일" 섹션에 국세청 보도자료(날짜 명시), 국가법령정보센터 조항 2건을 직접 인용. 인용 가능성에 크게 기여.
- **결함:** `datePublished`와 `dateModified`가 동일(2026-07-30T00:00:00Z) — 실제 갱신 이력이 없어 "최신성" 신호가 약함. 법령/세율처럼 자주 바뀌는 주제일수록 재검증 후 `dateModified`를 갱신하는 루틴이 인용 신뢰도에 유리.
- **결함:** Article의 `author`가 `Organization`(InvestIQs Research)뿐, `Person` 타입 저자 없음 → 아래 4번 참조.

**인용 준비도 점수: 82/100** (구조·출처는 최상급, 저자·최신성만 보완하면 90+)

### `etf-distribution-health-insurance-dependent-2026` (ETF 분배금 건강보험료)
- 동일 템플릿(리드 120단어대, 요약 불릿, FAQ 5문항, 출처 인용) — 구조 일관성 좋음.
- 표(table) 2개로 "가입자 유형별" 비교 정리 — 이런 표는 AI가 그대로 답변에 옮기기 좋은 형태(투자자 유형 → 확인 기준 매핑).
- 동일한 datePublished=dateModified 문제, 동일한 Organization-only author 문제.

**인용 준비도 점수: 80/100**

### 공통 개선안 (두 기사 동일 적용)
1. FAQ 질문을 실제 검색창에 입력할 법한 완전한 문장(예: "ETF 분배금 받으면 건강보험료 오르나요?")으로 1개씩 더 추가 — 현재도 좋지만 롱테일 질의 커버리지를 넓히면 인용 기회 증가.
2. `dateModified`를 실제 재검토 시점에 갱신 — 코드 변경 없이 프론트매터에 갱신일만 넣으면 됨 (`auto_publisher/publishers/hugo.py` 프론트매터 로직에 `dateModified` 필드가 `datePublished`를 그대로 복사하는지 확인 필요).

---

## 4. 저자/권위 신호 (Authority)

- `about/authors/` 페이지가 놀랍도록 투명함: "사람 애널리스트가 한 줄 한 줄 작성한 것이 아닙니다"라고 명시하고, 사용 모델(Claude Haiku 4.5/Sonnet 4.6, Gemini)까지 공개. 각 기사 `<head>`에도 `<meta name="ai-generated" content="true">`, `<meta name="human-reviewed" content="automated-only">` 태그 존재.
- **이 투명성은 양날의 검이다.** 정직성 자체는 신뢰 신호가 될 수 있지만, YMYL(금융) 카테고리에서 "사람 검수 없음"을 명시적으로 선언하는 것은 구글 AI Overviews의 E-E-A-T 평가나 향후 LLM 검색엔진의 콘텐츠 신뢰도 필터에서 감점 요인이 될 가능성이 실제로 있음. 반대로 ChatGPT/Perplexity처럼 출처 URL 자체보다 "인용문이 검증 가능한 1차 자료를 얼마나 명확히 달고 있는가"를 우선하는 시스템에서는 이 페이지의 영향이 상대적으로 작다.
- Article schema의 `author`가 `Organization`(InvestIQs Research)으로만 돼 있고 `Person`(자격, `sameAs` 링크 포함)이 없음. 반면 홈페이지 Organization schema에는 `sameAs`(Twitter, LinkedIn)가 있는데 기사 author 객체에는 이 링크가 상속되지 않음.
- **수정안 (선택):** ①"InvestIQs Research"를 `Person`이 아닌 `Organization` 저자로 유지하는 대신, 최소한 Article schema의 author 객체에도 `sameAs`(위 두 링크 + about/authors 페이지 URL)를 추가해 엔티티 연결을 강화. ②`about/authors/` 페이지의 검증 절차 설명(yfinance/공시 인용, 룰 기반 검증, 시나리오 균형 검사)을 Article 하단에 요약 링크로 노출하면 "방법론이 검증 가능함"이라는 신호가 각 기사 단위로도 전달됨 — 지금은 사이트 전체에 한 번만 존재.

---

## 5. 계산기 페이지 (`/ko/tools/dividend-calculator/`)

- SPA 아님, 서버에서 514단어 텍스트 렌더링 확인 — JS 미실행 크롤러도 전체 콘텐츠 수집 가능(강점).
- SCHD/VYM/JEPI/JEPQ/QYLD 5종 배당 ETF의 구조적 차이를 표 + 종목별 문단으로 설명 — "이 계산기가 하지 않는 것"(세금 미반영, 환율 고정, 배당 성장률 가정 등 5개 한계) 섹션은 그 자체로 자기완결적 인용 블록이며 오인용 방지 문구도 포함돼 있어 우수함.
- `WebApplication` + `BreadcrumbList` JSON-LD만 존재, **`FAQPage` 없음.** 반면 실제 본문 구조("계산 방법과 한계", "데이터 출처", "반영하지 않는 것", "직접 검증하는 방법" 등 H2)는 FAQ로 변환하기 매우 쉬운 Q&A 형태.
- `WebApplication` schema에는 `datePublished`/`dateModified` 필드 자체가 없음 — 최신성 신호 부재.

**인용 준비도 점수: 68/100**

**수정안 (구체적):**
1. 기존 "이 계산기가 하지 않는 것" 5개 항목을 FAQPage JSON-LD로 변환. 질문 예시:
   - "배당 ETF 계산기 결과에 세금이 반영되나요?"
   - "SCHD와 JEPI 중 어떤 게 배당 성장률을 높게 잡아야 하나요?"
   - 답변 텍스트는 이미 본문에 있는 문장을 그대로 재사용 가능 (신규 작성 불필요, JSON-LD 블록 추가만).
2. `WebApplication` schema에 `dateModified` 필드 추가 (계산기 로직/ETF 데이터 갱신 시점 기준).

---

## 6. 홈페이지 (`/ko/`)

- 본문 텍스트 125단어로 매우 얇음(단순 링크 허브 구조) — AI가 사이트 정체성을 판단할 근거가 부족.
- `Organization` JSON-LD에 `sameAs`(Twitter, LinkedIn) 존재 — 브랜드 엔티티 신호로는 최소한의 기반은 갖춤.
- **브랜드 엔티티 신호(YouTube/Reddit/Wikipedia) 부재**: 페이지 내 어디에도 YouTube 채널이나 Reddit 언급이 없음(auto_publisher가 YouTube에 영상을 업로드하는 파이프라인이 있음에도 홈페이지에 채널 링크가 없는 것으로 확인됨). 브랜드 언급-인용 상관관계가 가장 높은 신호(YouTube ~0.737)를 활용하지 못하고 있음.
- `WebSite` 타입 schema(사이트 전체를 대표하는) 자체가 없고 `Organization`만 있음.

**수정안:**
1. 홈페이지 헤더/푸터에 YouTube 채널 링크 추가 (이미 `video_uploader.py`로 업로드 중이므로 콘텐츠는 존재, 링크만 노출하면 됨) + Organization schema `sameAs`에도 추가.
2. 홈페이지 상단에 사이트가 무엇을 하는 곳인지 2~3문장 설명 텍스트 추가(현재 태그라인 한 줄뿐) — AI가 "이 사이트는 무엇에 대한 권위가 있는가"를 판단할 최소 컨텍스트 확보.

---

## 7. 한국어 질의에 대한 실제 인용 가능성 평가

- 콘텐츠 구조(리드 요약 → 판별 기준 → FAQ → 1차 출처)는 한국어/영어 구분 없이 AI 인용 친화적 포맷을 정확히 따르고 있음 — 이 부분은 언어와 무관하게 통할 구조.
- 국세청·법령 1차 출처 인용 + 확인일 명시는 한국어 금융 질의에서 특히 중요한 신호(국내 세법은 자주 바뀌므로 AI가 "최신인지" 신뢰도를 소스 자체보다 출처·날짜로 판단하는 경향). 이 부분은 이미 강점.
- 다만 검색 순위 26위권이라는 현재 위치는 AI 인용에도 직접 영향: Perplexity·ChatGPT의 웹 검색 기반 답변 상당수가 여전히 Google/Bing 색인 순위와 상관관계가 있음(완전 독립적이지 않음). 따라서 GEO 구조 개선은 "전통 SERP 순위와 무관하게 인용을 만드는 지름길"이 아니라 **SERP 개선과 병행할 때 상승효과가 나는 보완 채널**로 보는 것이 현실적. 콘텐츠 구조만으로 순위와 무관하게 인용되는 경우는 (a) 매우 좁고 구체적인 롱테일 질의, (b) FAQ 형태로 정확히 매칭되는 질문일 때로 한정됨.
- 즉 이 사이트 상황(순위 26위, 신규 도메인 추정)에서 GEO는 "대안 진입로"라기보다 **SERP 상승과 함께 인용 빈도가 같이 오르는 보조 채널**로 기대하는 것이 정확한 평가.

---

## 8. 종합 점수 (페이지별 GEO Readiness, 0-100)

| 페이지 | 점수 | 핵심 병목 |
|---|---|---|
| foreign-tax-credit-overseas-etf-2026 | 82 | dateModified 미갱신, Person author 부재 |
| etf-distribution-health-insurance-dependent-2026 | 80 | 동일 |
| dividend-calculator (계산기) | 68 | FAQPage schema 부재, dateModified 부재 |
| 홈 (/ko/) | 55 | 본문 텍스트 부족, YouTube/브랜드 신호 부재, WebSite schema 부재 |

## 9. 우선순위 Top 5 수정안 (효과/공수)

1. **llms.txt ↔ robots.txt 모순 해결** (공수: 낮음, 효과: 높음) — llms.txt 카테고리 링크를 robots.txt가 차단하지 않는 경로로 교체.
2. **계산기 페이지에 FAQPage JSON-LD 추가** (공수: 낮음, 효과: 중간) — 기존 "이 계산기가 하지 않는 것" 텍스트 재활용, 신규 작성 불필요.
3. **dateModified 실제 갱신 파이프라인화** (공수: 중간, 효과: 중간) — `auto_publisher/publishers/hugo.py` 프론트매터에서 재검토 시 `dateModified`를 별도 갱신하도록 처리 (현재 datePublished와 항상 동일).
4. **홈페이지에 YouTube 채널 링크 + 소개 문단 추가** (공수: 낮음, 효과: 중간) — 이미 존재하는 영상 자산을 홈페이지에서 노출만 하면 되는 저비용 개선.
5. **Article author 객체에 sameAs 링크 추가** (공수: 낮음, 효과: 낮음~중간) — 홈페이지 Organization schema의 sameAs를 기사 author 객체에도 복제.

## 10. 플랫폼별 예상 스코어 (참고용, 실측 아님 — 구조적 추정)
- **Google AI Overviews**: 낮음~중간. SERP 26위권 자체가 AIO 노출의 선결 조건에 못 미칠 가능성 높음. llms.txt는 무관.
- **ChatGPT(웹 검색 포함)**: 중간. FAQ/1차 출처 구조는 유리하나 신규 도메인 권위 신호 약함.
- **Perplexity**: 중간~높음. PerplexityBot 명시적 허용 + 출처 인용 스타일이 Perplexity의 인용 선호 패턴(날짜·1차 출처 명시)과 잘 맞음.
- **Bing Copilot**: 미확인 (Bing 크롤러 규칙 미검토, robots.txt에 Bingbot 전용 규칙 없음 → wildcard로 허용됨).
