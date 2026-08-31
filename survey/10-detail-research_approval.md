# 애드센스 "가치가 별로 없는 콘텐츠" 재승인 리서치

조사일: 2026-09-01 · 대상: investiqs.net (한국어 금융, 2차 거절 2026-08-31)

## 확실성 표기 규칙
- **[A] 구글 공식** — support.google.com / developers.google.com 원문
- **[B] 사례·정황** — 실제 후기, 벤더 케이스 (이해관계 있을 수 있음)
- **[C] 업계 통설** — SEO 블로그 주장, 검증 불가

---

## 0. 먼저: 이번 조사에서 확인된 한계

Google AdSense 커뮤니티 스레드(Product Expert 답변)는 JS 렌더링이라 본문을 가져오지 못했다.
검색 스니펫으로 인용된 부분만 확보했다. 또한 "저는 N편으로 승인됐습니다" 류의 후기는
대부분 SEO 블로그의 자기 홍보 글이고 검증 수단이 없다. 아래에서 [B]/[C]로 구분했다.

---

## 1. "Low value content" 거절의 실제 원인

### [A] 구글이 명시한 기준

AdSense 사이트 자격 요건 원문 (support.google.com/adsense/answer/9724):
> "Your content must be high-quality, original, and attract an audience."
> "unique and interesting content"

주목: **"attract an audience"** — 콘텐츠 품질뿐 아니라 *독자를 끌어오고 있는가*가 문구에 들어있다.
공식 최소 트래픽 수치는 어디에도 없지만, 이 문구는 "트래픽 0인 신규 사이트"가 불리하다는
근거로 자주 인용된다. **트래픽 요건 수치는 존재하지 않음 [A], 다만 무관하지도 않음 [B]**

AdSense 커뮤니티 가이드(241032356) 스니펫에서 확인된 구글 측 설명:
> 사이트를 E-E-A-T 기반으로 평가하며, **금융·건강 등 YMYL 주제에는 더 엄격한 기준(a more
> demanding standard)을 적용한다**

→ investiqs.net은 미국 ETF·절세 = **정통 YMYL**. 일반 블로그보다 높은 문턱을 통과해야 한다.
이게 이번 건에서 가장 중요한 구조적 사실이다.

### [A] Search Central "helpful content" 자가진단 (AdSense 심사도 같은 신호 사용)

developers.google.com/search/docs/fundamentals/creating-helpful-content 원문:
- Who: "Is it self-evident to your visitors who authored your content?"
- How: "Is the use of automation, including AI-generation, self-evident to visitors through
  disclosures or in other ways?" / "Are you providing background about how automation or
  AI-generation was used?"
- Why: 검색 트래픽이 아니라 사람을 돕기 위해 존재해야 함
- YMYL: "even more weight to content that aligns with strong E-E-A-T"
- "first-hand expertise and a depth of knowledge" 요구

**"Who"가 investiqs.net의 약점**: 필자가 누구인지 자명한가? `human-reviewed: automated-only`는
"How" 항목은 만족시키지만 "Who"와 "first-hand expertise"에는 정면으로 불리하다.

### [C] 업계에서 반복 언급되는 원인 (출처는 모두 SEO 블로그)

1. **Information Gain 부재** — 다른 10만 개 사이트와 같은 내용이면 기본값이 low value
   (adstimate.com, techmessy.com — 근거 제시 없음)
2. **사이트 평균 품질** — 얇은 글이 섞여 있으면 전체 평균이 깎임. "50편 중 35편이 fluff면 거절,
   지우면 승인 확률 상승" (adstimate.com — 수치 근거 없음, 그러나 이미 896→15 축소로 실행한 전략)
3. About/Contact/Privacy/Terms 푸터 링크 부재
4. 메뉴·카테고리·내부링크 부실 → 리뷰어가 사이트 목적을 파악 못 함
5. 검색 의도 불일치 (체크리스트를 찾는데 3000자 역사 설명)

이 다섯 개는 출처 신뢰도가 낮다. 다만 1~2번은 구글 공식 "original / unique" 문구와 방향이 같다.

### 이번 건에 대한 해석 (추론, 확실성 낮음)

896편 → 15편 축소는 위 2번 전략을 정확히 실행한 것인데도 **같은 사유로 재거절**됐다.
따라서 남은 가설은:
- (a) 분량 문제가 아니라 **저자/경험 부재(Who, first-hand expertise)** 가 원인
- (b) 축소 후 재크롤 전에 재신청했다 → 구글이 여전히 옛 상태를 보고 있음
- (c) 38 URL 중 23개(계산기 10 + 유틸 13)가 텍스트 얇은 페이지 → **사이트 구성상 도구가 61%**
  이며 "기사"보다 "도구 모음"으로 인식됐을 가능성 (아래 4장)
- (d) YMYL 금융인데 자동 생성 명시 → 신뢰성 심사에서 컷

---

## 2. 승인 시점의 글 개수 — 실제 수치

### [A] 공식: 최소 글 개수 기준 없음
구글은 어떤 문서에서도 최소 게시물 수를 명시하지 않는다. "high-quality, original"만 요구.

### [B]/[C] 후기에서 나오는 숫자
| 출처 | 주장 | 신뢰도 |
|---|---|---|
| 다수 SEO 가이드 종합 | "15~20편이면 충분" | [C] 근거 없는 반복 인용 |
| goodreads/dev.to 블로거 후기 | 7편으로 승인된 사례 있음 | [B] 단일 사례, 검증 불가 |
| adsenseaudit.net (도구 사이트) | 800~1,200자+ 글 10~20편 | [C] 저자 경험담, 출처 없음 |
| 한국 후기 (abtkorea.com) | 3회 거절 후 약 1달 만에 승인 | [B] |
| 한국 후기 (lazytrees.com 등) | 4개월 거절 지속 → 5개월차 승인 | [B] |

**결론: "15편으로 충분한가?"에 대한 답 — 개수는 병목이 아닐 가능성이 높다.**
7편 승인 사례가 존재하고 구글 공식 최소치가 없는 이상, 15편 자체가 거절 사유일 확률은 낮다.
같은 사유로 두 번 거절됐다는 사실이 오히려 "개수 축소는 효과가 없었다"는 증거다.
→ **다음 시도에서 글 개수를 20~30편으로 늘리는 것은 우선순위가 아니다.** (확실성: 중)

단, 주의: 15편 중 몇 편이 실제로 색인됐는지가 별개 변수다. 896→15 삭제 직후면 구글은
881개의 404/삭제 페이지를 보고 있을 수 있다. **Search Console 색인 상태 확인이 선행돼야 한다.**

---

## 3. AI 생성 콘텐츠 사이트의 승인 가능 여부 (2025~2026)

### [A] 공식 입장
- AdSense/게시자 정책 어디에도 "AI 생성 금지" 조항 없음
- 구글 스팸 정책의 **scaled content abuse** (2024-03 발표, 2024-05-05 시행)는
  "AI든 사람이든 스크래핑이든 방식 불문(method-agnostic)"으로 **순위 조작 목적의 대량 생성**을
  금지. 규모 자체가 아니라 *규모 + 독자적 가치 부재 + 조작 의도*의 결합이 문제
- Search Central은 자동화 사용 시 **공개(disclosure)를 권장**한다 (1장 인용 참조)

→ **AI 명시 공개는 구글 공식 문서 기준 "권장 방향"이지 감점 요소가 아니다.** [A]
  다만 공개 *문구*가 문제일 수 있다: `human-reviewed: automated-only`는
  "사람이 검토하지 않았음"을 능동적으로 선언한다. 구글이 요구하는 disclosure는
  "어떻게 만들었는지 배경 설명"이지 "사람 검토 없음 선언"이 아니다.
  YMYL 금융에서 이 문구는 E-E-A-T 자기부정으로 읽힐 수 있다. (추론, 확실성: 중)

### [B] 반대 방향 사례 — 주의해서 볼 것
originality.ai (AI 탐지기 판매사, **이해관계 있음**) 케이스:
- 2023-05, 상위 10개 글 중 7개가 자사 탐지기에서 "100% AI"
- 거절 사유는 **"automatically generated content"** — 이번 건의 "low value content"와 **다른 코드**
- AI 플래그된 글 전부 비공개/수정 → 다른 변경 없이 재신청 즉시 승인
- 한계: 2023년 건, 판매사 자체 홍보, N=1

→ **"AI 사이트는 승인 불가"의 근거로 쓸 수 없다.** 다만 거절 코드가 다르다는 점은 유용:
  investiqs.net은 "automatically generated content"가 아니라 "low value content"를 받았다.
  즉 **구글은 이 사이트를 "자동 생성물"로 낙인찍은 게 아니라 "가치 부족"으로 판정했다.**
  이건 오히려 좋은 신호다. (확실성: 중 — 거절 코드 구분이 실제로 유의미하다는 전제)

### [C] 2026년 업계 관측
- "2026-03 코어 업데이트가 인간 감독 없이 하루 50편+ AI 글을 뿌린 사이트를 타격"
  (여러 SEO 블로그 반복 — **1차 출처 확인 못 함, 신뢰하지 말 것**)
- "AI 사이트 거절의 가장 흔한 사유가 low value content이며, 리뷰어는 페이지마다 똑같이 읽히고
  검증 가능한 전문성을 가진 저자가 없는 걸 플래그한다" (adsenseaudit.net [C])

---

## 4. 계산기·도구 페이지는 콘텐츠로 인정되는가

### [A] 공식: 도구 사이트에 대한 별도 규정 없음
구글은 계산기/유틸리티 페이지를 명시적으로 언급하지 않는다. 일반 기준(original, high-quality,
attracts an audience)이 그대로 적용된다.

### [C] 업계 관측 (출처 신뢰도 낮음, 그러나 일관됨)
여러 도구 사이트 전문 가이드가 같은 얘기를 한다:
- "도구 전용 페이지는 텍스트가 거의 없어 구글이 사이트 목적을 판단하지 못한다"
- "승인된 도구 사이트는 도구를 감싸는 실제 블로그를 8~15편 갖고 있다" (webmatrices.com)
- "계산기·변환기 사이트는 매일 승인되지만, 모든 페이지가 입력창 + 짧은 SEO 문단뿐이면
  low value content의 흔한 원인이 된다" (tools-bundle.com)
- 도구 사이트 거절 6대 패턴 (adsenseaudit.net): 실질 원문 텍스트 부재 / 복제 쉬운 디자인 /
  프로그래매틱 유사중복 페이지 / **YMYL 신뢰 공백(금융·건강 도구는 면책·출처 필요)** /
  About·Contact·Privacy 부재 / 미완성 UX

**investiqs.net 적용**: 38 URL 중 23개(61%)가 도구·유틸이다. 즉 **사이트 표면상 "도구 61% +
기사 39%"로 보인다.** 위 [C] 관측이 맞다면 이 비율이 리뷰어에게 "도구 모음 사이트"로 읽히고,
기사 15편이 도구를 정당화하는 부속물로 보일 수 있다.
확실성은 낮지만(모두 [C]), **비용이 낮은 개선**이라 시도 가치는 있다:
각 계산기에 실제 계산 예시·근거 법령·FAQ를 붙여 도구 페이지 자체를 콘텐츠로 만드는 것.

또한 "유틸 13"이 무엇인지에 따라 **noindex 처리가 더 나을 수 있다** — 태그/검색/페이지네이션
같은 순수 기능 페이지라면 심사 대상 URL 집합에서 빼는 게 평균 품질에 유리하다. (확실성: 중)

---

## 5. 재요청 전략 — 횟수 제한과 대기

### [A] 공식 (support.google.com/adsense/answer/7003627 원문)
> "You can request a certain number of page-level reviews during a 30 day period.
> **This limit is refreshed daily.**"

> 리뷰 요청 버튼은 "**will be inactive if your site has been reviewed and rejected
> several times recently.**"

**확정 사실 [A]:**
1. 리뷰 요청 한도는 **30일 롤링**이며 **매일 조금씩 회복**된다 → 9/7 1회 회복은 이 메커니즘과 일치
2. **최근에 여러 번 거절당하면 요청 버튼 자체가 비활성화된다** — 즉 실패를 반복하면
   대기 기간이 실질적으로 길어진다. 이건 추측이 아니라 구글 공식 문구다.
3. 정확한 한도 숫자는 구글이 공개하지 않는다

→ **결론: 9/7에 회복되는 1회를 "일단 눌러보는 용도"로 쓰면 안 된다.**
  실패 시 다음 기회가 더 멀어질 수 있는 구조다. 준비가 끝난 시점에만 사용해야 한다.

### [C] 재신청 타이밍에 관한 상반된 조언
- 다수 영어 가이드: "**2~4주 기다려 구글이 재크롤할 시간을 준 뒤** 재신청. 변경 직후 즉시
  재신청하면 거절 위험 증가" — 근거 제시 없음, 그러나 [A]의 "버튼 비활성화" 규정과 정합적
- 한국 adsensefarm.kr: "**기다리지 말고 글 1~2개 추가 후 즉시 재신청**"
  ※ 이 글은 **"여러 계정 동시 신청", "계정 새로 파기"를 권한다 — AdSense 정책 위반(중복 계정)
  이며 영구 정지 사유다. 이 소스의 조언은 채택하지 말 것.**

두 조언이 충돌할 때는 [A]가 우선한다: 실패에 페널티가 있으므로 **재크롤 확인 후 신청**이 맞다.
구체적으로는 Search Console에서 변경된 15편이 "색인 생성됨" 상태이고, 삭제한 881개가
색인에서 빠졌는지 확인한 뒤 누르는 것.

### [B] 실제 승인까지 걸린 시간 사례
- 3회 거절 → 약 1달 (abtkorea.com)
- 4개월 거절 지속 → 5개월차 승인 (lazytrees.com)
- 심사 소요 자체는 "수 시간 ~ 4주+", 통상 10~15일 (adsensefarm.kr [C])

---

## 6. 종합 판단 (확실성 명시)

**높은 확실성 (구글 공식 근거 있음)**
1. YMYL 금융 사이트는 더 엄격한 기준을 받는다 → E-E-A-T가 핵심 병목
2. 최소 글 개수·최소 트래픽 요건은 존재하지 않는다
3. AI 생성 자체는 금지가 아니며, 자동화 공개는 구글이 *권장*하는 방향이다
4. 재신청 실패가 반복되면 요청 버튼이 비활성화된다 → 남은 1회는 신중하게

**중간 확실성 (정황·추론)**
5. 거절 코드가 "automatically generated content"가 아니라 "low value content"라는 건
   AI라서 걸린 게 아닐 가능성을 시사한다
6. `human-reviewed: automated-only` 문구는 disclosure로서는 정직하지만 YMYL E-E-A-T에서
   자기부정으로 읽힐 수 있다 — 표현 재검토 대상 (거짓 주장은 하지 말 것, 실제 사람 검토를
   도입하고 그걸 명시하는 게 정공법)
7. "Who" — 검증 가능한 저자/책임 주체 부재가 15편 축소로 해결되지 않은 진짜 원인 후보
8. 도구·유틸 61% 구성이 "도구 모음"으로 인식됐을 가능성

**낮은 확실성 (SEO 블로그 통설, 채택 시 근거 부족 인지할 것)**
9. Information Gain, 사이트 평균 품질, 도구 사이트는 8~15편 블로그 필요 등

**명시적으로 부정할 것**
- "AI 사이트는 애드센스 승인 불가" — 공식 근거 없음
- "글 20편/30편 이상 필요" — 공식 근거 없음, 7편 승인 사례 존재
- "여러 계정으로 동시 신청" — 정책 위반, 절대 금지

---

## 출처

구글 공식 [A]
- https://support.google.com/adsense/answer/9724 (사이트 자격 요건)
- https://support.google.com/adsense/answer/7003627 (리뷰 요청·30일 한도·버튼 비활성화)
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content (Who/How/Why, YMYL, 자동화 공개)
- https://support.google.com/adsense/community-guide/241032356/how-can-you-solve-the-low-value-content-adsense-disapproval-challenge (E-E-A-T·YMYL 엄격 기준 — 본문 렌더링 불가, 검색 스니펫 인용분만 확보)

사례·벤더 [B]
- https://originality.ai/blog/adsense-rejects-site-ai-content (AI 탐지기 판매사, 2023 케이스)
- https://abtkorea.com/41 (3회 거절 후 1달 승인)
- https://lazytrees.com/6423/ (장기 거절 사례)
- https://revertface.com/구글-애드센스-승인-2주-걸림-거절-가치가-별로-없는-콘/

업계 통설 [C]
- https://adsenseaudit.net/adSense-tool-websites (도구 사이트)
- https://adsenseaudit.net/guides/adsense-ai-content-policy-2026
- https://adstimate.com/blog/low-value-content-fix.html
- https://genieegroup.com/blog/adsense-low-value-content/
- https://www.techmessy.com/2026/07/fix-adsense-low-value-content-rejection.html
- https://henrypress.net/adsense-low-value-content-fix/
- https://webmatrices.com/adsense-eligibility-checker
- https://tools-bundle.com/google-adsense-eligibility-checker

정책 위반 조언 포함 — 참고만, 채택 금지
- https://adsensefarm.kr/adsense-reject-approval-how-to-deal-with-it/ (중복 계정 권장)
