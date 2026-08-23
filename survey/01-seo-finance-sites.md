# 금융 콘텐츠 사이트 트래픽 리서치 (2025–2026)

> 리서치 일자: 2026-08-17 | 담당: SEO 리서치 에이전트

## 0. 결론 먼저

investiqs.net의 낮은 조회수는 "SEO 최적화 부족"이 아니라 **구조적 문제 3개가 겹친 결과**일 가능성이 높다.

1. **채널 자체가 붕괴 중** — 소형 퍼블리셔의 구글 검색 유입은 2년간 60% 감소 (대형은 22%). "글 많이 써서 구글로 받는다"는 모델은 소형 사이트에서 사실상 작동을 멈췄다.
2. **900개 다국어 자동생성 포스트는 Google `scaled content abuse` 정책 정의문에 거의 그대로 대응**한다. 특히 "번역을 통한 자동 변환"이 명시적 위반 예시로 적혀 있다.
3. **금융 = YMYL** 이므로 신뢰(Trust) 임계값이 가장 높다. 무명 도메인 + 실명 저자 부재 + 원본 데이터 부재 조합은 YMYL에서 최악의 조합이다.

---

## 1. 채널 붕괴의 실제 수치 (가장 중요)

### Chartbeat 데이터 (Axios 2026-03-17 단독보도) — 퍼블리셔 규모별 2년간 검색 유입 감소
| 규모 (일간 PV) | 검색 유입 감소 |
|---|---|
| 소형 1,000–10,000 | **-60%** |
| 중형 10,000–100,000 | -47% |
| 대형 100,000+ | -22% |

- Google Search 리퍼럴: 2024/12 → 2025/12 **-34%**
- Google Discover: 같은 기간 **-15%**
- ChatGPT 리퍼럴: **+200% 이상 성장했으나 전체 퍼블리셔 PV 리퍼럴의 1% 미만**
- 소스: https://www.searchenginejournal.com/search-referral-traffic-down-60-for-small-publishers-data-shows/569959/

**소형이 대형보다 약 3배 더 맞았다.** Chartbeat의 명시적 결론은 "대체 채널을 만들 여력이 가장 적은 사이트가 가장 크게 잃었다". investiqs.net은 정확히 이 구간이다.

### Reuters Institute / Chartbeat (Press Gazette, 2026)
- 글로벌 퍼블리셔 구글 검색 유입 2025년 11월까지 전년比 **-33%**, Discover **-21%**
- 미국만: 검색 **-38%**, Discover **-29%**
- 가장 크게 맞은 유형: **"라이프스타일 및 유틸리티성 콘텐츠"** (날씨, TV 편성표, 운세) — 즉 **AI가 즉답 가능한 정보성 콘텐츠**. 마켓 랩업/시황 요약이 정확히 이 범주.
- 퍼블리셔들은 향후 3년간 평균 추가 **-43%** 예상
- 소스: https://pressgazette.co.uk/media-audience-and-business-data/google-traffic-down-2025-trends-report-2026/

### Ahrefs 원본 연구 (AI Overviews CTR)
- 표본: 키워드 30만개(AIO 노출 15만 + 미노출 정보성 15만), GSC 집계, 2024/03 vs 2025/03
- 1위 CTR: AIO 있는 키워드 0.073 → 0.026. 예측 기준선 0.040 대비 **-34.5%**
- 2025/12 기준 후속 갱신: 실제 0.016 vs 예측 0.037 → **-58%**로 악화
- **AIO를 트리거하는 키워드의 99.2%가 정보성 인텐트** ← 우리 콘텐츠 유형 전체가 사정권
- 소스: https://ahrefs.com/blog/ai-overviews-reduce-clicks/ , https://searchengineland.com/google-ai-overviews-hurt-click-through-rates-454428

### 대형 금융 사이트조차 무너지고 있다 — NerdWallet
- CEO Tim Chen: "**pretty brutal quarter for SEO**"
- 신용카드 매출 전년比 -16% ("지속된 오가닉 검색 트래픽 압박이 주원인"), MAU -7%
- 결정적 문장: **"organic search visibility challenges impacted traffic to non-monetizing learning-oriented content"** — **교육/설명형 콘텐츠가 먼저 죽었고 상거래 의도 트래픽은 상대적으로 버텼다.**
- 소스: https://searchengineland.com/nerdwallet-organic-search-visibility-challenges-447884

> **시사점**: "ETF란 무엇인가", "○○주 분석" 같은 설명형/시황형이 가장 먼저 증발한다. 도메인 파워 최상위 + 실명 에디터 + 규제 공시 완비인 NerdWallet조차 이 유형을 잃었다면, 무명 도메인이 같은 유형으로 경쟁하는 것은 승산이 없다.

---

## 2. Google이 대량 AI 콘텐츠를 실제로 어떻게 다루는가

### 공식 정책 원문 (developers.google.com/search/docs/essentials/spam-policies)
- **Scaled content abuse 정의**: "many pages are generated for the primary purpose of manipulating search rankings and not helping users."
- 명시적 위반 예시:
  - "using generative AI tools or other similar tools to generate many pages **without adding value for users**"
  - "**automated transformations like synonymizing, translating, or other obfuscation techniques**"
  - 여러 소스를 기워 붙이되 의미 있는 가치를 더하지 않는 것
- **방법론 중립적**: AI라서 벌하는 게 아니라 *가치 없는 대량 생산*이라서 벌한다.

### Google 공식 품질 가이드 (creating-helpful-content)
- **"If you use automation, including AI-generation, to produce content for the primary purpose of manipulating search rankings, that's a violation of our spam policies."**
- Who / How / Why 프레임워크:
  - **Who**: 바이라인 + 저자 소개 페이지로 저자 명확화
  - **How**: 콘텐츠 제작 과정 공개 — **AI 사용 여부 포함해 설명하라고 명시**
  - **Why**: "사람을 돕기 위해"여야 함
- E-E-A-T 중 **"trust is most important"**, YMYL(금융 포함)에서 특히.

> **실행 인사이트**: Google은 AI 사용을 *숨기라*고 하지 않는다. **공개하고 편집 프로세스를 설명하라**고 한다. "AI 초안 + 인간 검수" 방법론 페이지, 실명 에디터, 데이터 출처 정책 명시는 페널티가 아니라 Who/How 신호가 된다. (단, 실제 인간 검수가 존재해야 함)

### 케이스: SEO Heist (Causal)
- 경쟁사 사이트맵에서 키워드를 훔쳐 **AI로 약 1,800개 글 대량 생산** → 초기 급증 후 **Google에서 전면 디인덱스**
- 교훈은 개별 페이지 페널티가 아니라 **도메인 전체 품질 점수 하락**: 저품질 페이지 다수가 기존 정상 콘텐츠까지 끌어내림
- 소스: https://www.linkedin.com/pulse/seo-heist-aftermath-how-burn-your-organic-traffic-nick-malekos-yjqgf , https://springagency.co.uk/the-seo-heist-a-tale-about-ai/

> **900개 × 5개 언어 = 최대 4,500 URL**. 성과 없는 얇은 페이지가 소수의 좋은 페이지를 억누르고 있을 가능성이 크다. **대량 프루닝(noindex/삭제)이 신규 발행보다 우선순위가 높을 수 있다.**

### 기계번역 다국어 확장의 특수 위험
- Google 정책이 "translating"을 자동 변환 위반 예시로 **직접 명시**. 판정 기준은 "사용자에게 가치가 거의 없는 결과물"인지 여부.
- ko 원문 → en/ja/vi/id 자동 번역은, 각 언어권에 **현지 고유 가치(현지 세제, 현지 브로커, 현지 통화 기준)** 가 추가되지 않으면 정확히 이 패턴이다.
- 5개 언어를 얕게 유지하는 것보다 **1~2개 언어 집중**이 리스크/자원 양쪽에서 유리하다.

---

## 3. 상위 금융 퍼블리셔가 실제로 하는 것

핵심은 "글을 잘 쓴다"가 아니라 **복제 불가능한 자산**이다.

### (a) 무료 도구/계산기 — 가장 검증된 대체 채널
Ahrefs free-tools 전략 분석 (https://ahrefs.com/blog/the-free-tools-seo-strategy/) 실측치:

| 사이트 | 트래픽 |
|---|---|
| Omni Calculator | 월 US 약 230만 방문 (단일 목적 계산기 수천 개) |
| FreeConvert | 5년간 38만 → 150만+ 월 방문 |
| Coolors | 5년간 약 2배 → 월 59만 |
| Ahrefs `/writing-tools/` | 2023년 중반 0 → 피크 월 US 100만 근접 |
| Adobe PDF-to-Word | 월 402,101 |
| Gusto 급여 계산기 | 월 17,776 |
| Shopify 이익률 계산기 | 피크 월 20K+ |

**왜 지금 유효한가**: 계산기는 AI Overview가 대체하기 어렵다. 사용자가 *자기 숫자를 입력*해야 하므로 즉답 요약으로 소비될 수 없다. 정보성 글이 AIO에 먹히는 동안 도구 페이지는 방어된다.

**금융 도메인에서 특히 강한 이유**: 복리, 연금 수령액, 환헤지 손익, ETF 총보수 비교, 배당 재투자 시뮬, 양도세/금투세 — 전부 언어·국가별 규칙이 달라 **다국어 확장이 "번역"이 아니라 "현지 고유 가치 추가"가 된다.** §2의 번역 리스크를 정면으로 해결하는 유일한 콘텐츠 유형.

### (b) 원본 데이터 / 독자 데이터
- "원본 데이터 포함 콘텐츠가 5.2배 백링크" 류 수치는 SEO 벤더 블로그 출처라 **검증 불가, 참고만**. 다만 논리는 확실: 다른 데서 찾을 수 없는 숫자가 인용과 링크를 만든다.
- investiqs.net의 미개발 자산: **900개 포스트 × 5개 언어 × 시황 아카이브 = 시계열 데이터**. "우리가 매일 수집한 데이터로 만든 지수/대시보드"로 재구성하면 원본 자산이 된다. (예: 언어권별 관심 종목 변화, 테마 언급 빈도 지수)

### (c) 저자 엔티티 (금융 YMYL 필수)
- Google 공식: YMYL에서 **Trust가 E-E-A-T 중 최우선**
- 요구: 실명 저자, 검증 가능한 외부 프로필 링크가 있는 저자 페이지, 자격/경력, 회사 정보, 연락처, 규제/면책 공시
- **주의**: 검색 결과에 나온 "SearchMetrics 2025 연구: TOP-3가 E-E-A-T 신호 2.4배", "YMYL 랭킹 가중치 24%" 등은 AI 생성 SEO 블로그에서만 발견되며 원 연구 확인 불가. **인용하지 말 것.**

---

## 4. 신규 무브랜드 금융 사이트의 현실적 채널 순위

**구글 오가닉을 1번 채널로 잡는 전략은 2026년 기준 실패 확률이 매우 높다.**

| 채널 | 현실성 | 근거 |
|---|---|---|
| **Google 오가닉 (정보성 글)** | ★☆☆☆☆ | 소형 -60%, AIO 키워드의 99.2%가 정보성, NerdWallet조차 교육형 상실 |
| **Google 오가닉 (도구/계산기)** | ★★★★☆ | AIO 대체 불가, Omni/FreeConvert 실측, 다국어에 진짜 가치 추가 가능 |
| **Google Discover** | ★★★☆☆ | Chartbeat 네트워크에서 구글 유입의 68%가 Discover. 단 전년比 -15~21%, **변동성 극심**. 요건: HTTPS, 1200px+ 이미지(`max-image-preview:large`), 모바일, About/개인정보/연락처, 도메인 6개월+. 제출 불가, 알고리즘 선택. |
| **뉴스레터** | ★★★★☆ | 소유 채널, 알고리즘 리스크 0. beehiiv: 2025년 구독 매출 $8M→$19M(+138%). **핵심: 성장은 SNS/구글이 아니라 "다른 뉴스레터로부터의 추천"** — The Pour Over "최고 품질 성장 채널은 리퍼럴과 다른 뉴스레터". 금융 사례 GRIT Capital 36만 구독자. |
| **Reddit/커뮤니티** | ★★★☆☆ | 트래픽보다 **AI 인용 + 브랜드 신호** 목적. 스팸 취급 위험 크고 사람 손 필요 → 자동화 부적합 |
| **AI 검색 리퍼럴** | ★★☆☆☆ | 전환율은 좋으나 **볼륨이 구글 대비 47~190배 작음**, 퍼블리셔 PV 리퍼럴의 1% 미만. 2027년 대비 투자로만 유효 |

신규 도메인 3~9개월 "신뢰 평가" 기간 주장은 대부분 SEO 블로그 출처라 엄밀한 근거는 아니지만, Chartbeat의 "소형 -60%"와 방향은 일치한다.

---

## 5. AI 검색 시대: 인용되는 법과 실익

### 인용 원리 (검증된 부분)
- **Ahrefs (키워드 86.3만, URL 400만)**: top-10 랭킹과 AIO 인용의 상관관계가 **76% → 38%로 하락**. **"구글 상위 랭킹 = AI 인용"은 더 이상 성립하지 않는다.**
- SE Ranking: AI Mode 인용 URL 중 구글 top-10에 있는 건 **14%뿐**
- 최다 인용 도메인: **YouTube 20.9%, Reddit 18.5%**, Facebook 10.7%, Instagram 5.8%, Quora 5%
- Semrush 2026 AI Visibility Index: 1억 2,600만 AI 검색 프롬프트 분석

> **중요**: AI 인용 상위는 **콘텐츠 사이트가 아니라 플랫폼(YouTube, Reddit)**. investiqs.net이 이미 YouTube/TikTok/Reels 자동 발행 중이라면, **그 유튜브 채널이 블로그보다 AI 인용 자산으로서 가치가 클 수 있다.** 현 파이프라인에서 가장 저평가된 자산.

### 전환율 (신뢰도 주의)
- **가장 신뢰할 만한 수치**: Visibility Labs/Search Engine Land, 이커머스 94개 사이트 — ChatGPT 전환율 1.81% vs 논브랜드 오가닉 1.39% (**+31%**)
- "AI 트래픽 4.4~23배 전환" 류는 벤더 마케팅 콘텐츠, 표본/정의 불명확. **신뢰하지 말 것.**
- 어느 쪽이든 **절대 볼륨이 작다**는 건 Chartbeat 데이터로 확정 (전체 리퍼럴 1% 미만).

### 실무 조치 (저비용, 정책상 안전)
- llms.txt (근거 약하나 비용 거의 0)
- 구조화 데이터: Article, FAQPage, HowTo, BreadcrumbList — **이미 `schema-kr-finance` 스킬 보유**
- 크롤러 접근성 확보, 직답형 문단 구조(질문 → 2~3문장 직답 → 근거)
- 고유 숫자를 문장 안에 배치 — LLM은 인용 가능한 구체적 수치를 선호

---

## 6. investiqs.net 직접 판단

**효과가 없을 가능성이 높은 것**
- 다국어 시황 요약/마켓 랩업 대량 발행 — AIO 사정권(99.2% 정보성) + Reuters Institute가 지목한 "유틸리티성 콘텐츠" 정의 + Google 정책의 "translating" 위반 예시에 동시 해당
- 발행량 증가로 트래픽 늘리기 — Causal 사례처럼 도메인 품질 평균을 낮춰 역효과 가능

**즉시 가치가 있을 가능성이 높은 것 (근거 강도순)**
1. **계산기/도구 페이지** — Ahrefs 실측이 가장 강한 증거. 언어별 세제/통화 차이가 진짜 현지 가치를 만들어 번역 리스크를 동시 해결. 최근 커밋 `ef77a60f`, `c302d2c8`에 이미 `/tools` 계산기 + GA4 계측 존재 — **리서치가 지지하는 유일하게 명확한 방향.**
2. **콘텐츠 프루닝** — 성과 없는 얇은 페이지 대량 noindex/삭제. Google 정책 + SEO Heist 사례가 지지.
3. **저자 엔티티 + AI 사용 공개 방법론 페이지** — Google 공식 Who/How/Why가 직접 요구. 비용 대비 효과 최고.
4. **뉴스레터** — 성장 채널이 "다른 뉴스레터 추천"이라는 점이 핵심. 알고리즘 리스크 0인 유일한 소유 채널.
5. **YouTube 채널 강화** — AI 인용 점유율 1위 도메인(20.9%). 파이프라인 이미 존재.

---

## 소스

- [Search Engine Journal — Search Referral Traffic Down 60% For Small Publishers (Chartbeat/Axios)](https://www.searchenginejournal.com/search-referral-traffic-down-60-for-small-publishers-data-shows/569959/)
- [Press Gazette — Global publisher Google traffic dropped by a third in 2025 (Reuters Institute)](https://pressgazette.co.uk/media-audience-and-business-data/google-traffic-down-2025-trends-report-2026/)
- [Press Gazette — Google Discover now makes up two-thirds of search traffic](https://pressgazette.co.uk/comment-analysis/google-discover-traffic-news-websites-2025/)
- [Ahrefs — AI Overviews Reduce Clicks by 34.5%](https://ahrefs.com/blog/ai-overviews-reduce-clicks/)
- [Search Engine Land — New data: Google AI Overviews are hurting click-through rates](https://searchengineland.com/google-ai-overviews-hurt-click-through-rates-454428)
- [Search Engine Land — NerdWallet reveals costly Google SEO visibility challenges](https://searchengineland.com/nerdwallet-organic-search-visibility-challenges-447884)
- [Google Search Central — Spam policies](https://developers.google.com/search/docs/essentials/spam-policies)
- [Google Search Central — Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Ahrefs — The Free Tools SEO Strategy](https://ahrefs.com/blog/the-free-tools-seo-strategy/)
- [SEO Heist: The Aftermath (Causal 사례)](https://www.linkedin.com/pulse/seo-heist-aftermath-how-burn-your-organic-traffic-nick-malekos-yjqgf)
- [Spring Agency — The SEO Heist, A Cautionary Tale About AI](https://springagency.co.uk/the-seo-heist-a-tale-about-ai/)
- [Semrush — 2026 AI Visibility Index (1억 2,600만 프롬프트)](https://www.semrush.com/news/463141-semrush-releases-expanded-2026-ai-visibility-index-analyzing-126-million-ai-search-prompts/)
- [Decoding — Top cited domains in AI (1,000만+ 인용 분석)](https://trydecoding.com/blog/top-cited-domains-in-ai/)
- [beehiiv — The State of Newsletters 2026](https://www.beehiiv.com/blog/beehiiv-the-state-of-newsletters-2026)
- [beehiiv — GRIT Capital 금융 뉴스레터 36만 구독자 사례](https://www.beehiiv.com/case-studies/grit)

**신뢰도 경고**: 검색 상위에 나온 "March 2026 core update로 55% 하락", "SearchMetrics E-E-A-T 2.4배", "AI 트래픽 4.4~23배 전환" 등의 수치는 모두 AI 생성 SEO 마케팅 블로그에서만 발견되었고 원 연구를 추적할 수 없었습니다. 본문에서는 의사결정 근거로 사용하지 않았습니다.
