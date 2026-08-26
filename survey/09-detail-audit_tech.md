# investiqs.net 기술 SEO 감사 (2026-08-27)

대상: https://investiqs.net (ko 전용, en/ja/vi/id 비활성)
소스: 라이브 사이트 HTTP 응답 실측 (`curl`, 헤더, HTML 파싱). 추정 없음 — 확인된 것만 기재.

## 요약 (Pass/Fail)

| 카테고리 | 상태 |
|---|---|
| 크롤러빌리티 (robots/sitemap) | PASS (경미한 개선 여지) |
| 색인성 (canonical/noindex) | FAIL — 루트 URL 노출 문제 1건 |
| 보안 헤더/HTTPS | PASS |
| URL 구조/리다이렉트 | PASS (경미한 개선 여지) |
| 모바일 | PASS |
| 구조화 데이터 | PASS |
| JS 렌더링 | PASS (완전 SSR/정적) |

**기술 점수: 82/100** — 치명 이슈 1건(루트 도메인 noindex+meta-refresh)이 재심사 맥락에서 감점 요인.

---

## 1. 크롤러빌리티

- `robots.txt` (https://investiqs.net/robots.txt): `Allow: /` + `/tags/`, `/categories/`, `/search/`, `?*` 쿼리 차단. 언어 서브패스 규칙(`/*/tags/` 등)도 정상 반영됨. AI 크롤러(GPTBot, ClaudeBot, PerplexityBot, Google-Extended) 명시적 허용 — **문제 없음**.
- `Sitemap:` 선언 2개 모두 200 응답, 유효한 XML (`sitemap_discovery.py` 검증 통과):
  - `https://investiqs.net/sitemap.xml` → sitemapindex, `ko/sitemap.xml` 1개만 포함 (은퇴한 en/ja/vi/id 사이트맵 참조 없음 — **정합성 정상**)
  - `https://investiqs.net/ko/sitemap.xml` → urlset, 정확히 38개 URL
- 은퇴 언어 확인: `/en/`, `/ja/`, `/vi/`, `/id/`, 각 언어 `sitemap.xml` 모두 실제 HTTP **404** (소프트 404 아님, 정상 404 헤더) — 요청하신 언어 은퇴→404 전환이 실제로 적용되어 있음을 확인.
- `_redirects` 파일: 79개 규칙, 최근 국내 종목/템플릿 통합 301이 반영됨. 루프나 체인 없음 (확인함).
- **[낮음] `/en/study/...` 구 URL → `/en/study/` (301) → 그 페이지 자체가 404.** 301이 최종적으로 404로 끝나는 체인. Google 입장에선 404와 동일하게 처리되어 실질적 피해는 없으나, 굳이 301을 거칠 이유가 없음 — ja/vi/id처럼 바로 404 처리가 일관적.
  - 위치: `web/static/_redirects` (en 관련 규칙들)
  - 수정: en 은퇴 규칙을 ja/vi/id와 동일하게 제거하거나 direct 404로 정리 (en은 "심사 후 복구 예정"이므로 유지 여부는 판단 필요 — 복구 계획이 있다면 현행 유지 가능, 아니면 정리 권장)

## 2. 색인성 (canonical / noindex)

- **[치명] 루트 도메인 `https://investiqs.net/` 이 진짜 301이 아니라 HTTP 200 + `<meta name="robots" content="noindex">` + `<meta http-equiv="refresh">` 메타 리프레시 페이지를 반환.**
  - 실측 응답 본문: `<link rel=canonical href=https://investiqs.net/ko/><meta name=robots content="noindex"><meta http-equiv="refresh" content="0; url=https://investiqs.net/ko/">`
  - 이는 Hugo의 `defaultContentLanguageInSubdir = true` 표준 동작(서버 리다이렉트 대신 정적 HTML placeholder 생성)이며 커스텀 버그는 아님. 그러나 사이트가 GSC 재심사 대기 중이고 과거 저품질 색인거부 이력이 있는 도메인이라, "가장 많이 공유/링크되는 형태인 apex URL"이 noindex + JS 기반 리다이렉트로 남는 것은 링크 신호(백링크 equity)가 `/ko/`로 정상 이관되지 않는 구조적 결함.
  - 위치: Cloudflare Pages 빌드 결과물, 원인은 `web/hugo.toml:2-3` (`defaultContentLanguage`, `defaultContentLanguageInSubdir`)
  - 수정: `web/static/_redirects`에 `/ /ko/ 301` 규칙 1줄 추가 (Cloudflare Pages `_redirects`는 정적 파일보다 우선 처리되므로 Hugo의 meta-refresh 페이지를 가리기만 하면 됨). 가장 저비용·고효과 수정.
- 개별 페이지 canonical: 확인한 study/tools/blog 페이지 모두 self-referencing canonical 정상 (`https://investiqs.net/ko/study/foreign-tax-credit-overseas-etf-2026/` 등).
- `noindex` 잔재: 표본 페이지(`/ko/tools/pension-tax-credit/`, `/ko/blog/`, `/ko/study/`, study 상세 1건) 모두 `meta robots` 태그 없음 (= 인덱스 허용) — 언어 축소 과정에서 남은 noindex 함정 **없음**.
- `hreflang`: 표본 페이지 모두 `hreflang` 속성 없음 — en/ja/vi/id 은퇴 후 죽은 hreflang 링크가 남아있는 문제 **없음** (정상 제거됨).
- `X-Robots-Tag` HTTP 헤더: 응답에 없음 (문제 없음, meta robots만 사용).
- 구조화 데이터: study 페이지에 `Article` JSON-LD 3개 스크립트 확인, headline/description/datePublished/dateModified/author/publisher/mainEntityOfPage 필드 모두 존재. **정상.**

## 3. 보안 헤더 / HTTPS

- HTTPS 강제: `http://investiqs.net/` → 301 → `https://investiqs.net/` (정상)
- 응답 헤더 확인 (Cloudflare Pages `_headers` 적용됨):
  - `Content-Security-Policy` — Google AdSense/Analytics 도메인 화이트리스트 구성됨
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: SAMEORIGIN`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- **[낮음] `Strict-Transport-Security` (HSTS) 헤더 없음.** Cloudflare 프록시 레벨에서 HTTPS 강제는 되지만 HSTS 미선언 시 다운그레이드 공격 여지 및 일부 보안 스캐너 감점 요인.
  - 위치: `web/static/_headers`
  - 수정: `Strict-Transport-Security: max-age=31536000; includeSubDomains` 추가
- **[낮음] `www.investiqs.net` DNS 레코드 자체가 없음 (`Could not resolve host`).** apex만 서비스 중. 의도된 구성이면 문제 없으나, 외부에서 www 형태로 링크/공유될 경우 완전히 연결 실패(404가 아니라 DNS 실패)로 이어짐.
  - 수정: Cloudflare에 www CNAME 추가 + apex로 301 리다이렉트 (선택 사항, 낮은 우선순위)

## 4. URL 구조 / 리다이렉트

- 트레일링 슬래시 정규화: `/ko/study/foreign-tax-credit-overseas-etf-2026` (슬래시 없음) → 308 → 슬래시 버전. 일관성 있음.
- URL 패턴: 소문자, 하이픈 구분, 의미 있는 slug. 한국어 슬러그(퍼센트 인코딩)가 일부 study URL에 남아있음 (`%EA%B0%9C%EB%B3%84%EC%A3%BC-10%EA%B0%9C...`) — 기능상 문제는 없으나 영문 슬러그 대비 URL 가독성/공유성이 떨어짐. 신규 콘텐츠부터 로마자 slug 정책 검토 여지 (우선순위 낮음, 기존 URL 변경은 비권장 — 재차 301 유발).
- 최근 55개 301 및 계산기/비교 페이지 통합(2026-08-23, 쿠키커터 대응)이 `_redirects`에 정확히 반영됨 — 확인 완료.
- 404 처리: 존재하지 않는 경로(`/ko/nonexistent-xyz-page/`) → 실제 HTTP 404. 소프트 404 없음.

## 5. 모바일 (쇼츠 유입 100% 모바일 감안)

- `<meta name="viewport" content="width=device-width,initial-scale=1,shrink-to-fit=no">` 정상 선언.
- 반응형 프레임워크(PaperMod) 기반 — 로컬 소스 확인상 별도 모바일 차단 요소(플래시, 고정폭 레이아웃) 없음.
- 터치 타겟/폰트 크기는 HTML 소스만으로 완전 검증 불가 — 실기기 Lighthouse 모바일 감사 권장 (범위 외, 별도 실행 필요).

## 6. JS 렌더링

- Hugo 정적 빌드 — 콘텐츠 전체가 초기 HTML에 포함된 순수 SSR/정적 페이지. `--mode auto` 렌더 판별상 SPA 쉘 아님. 크롤러가 JS 실행 없이 전체 콘텐츠 파싱 가능 — **문제 없음.**
- 유일한 클라이언트 사이드 JS 의존 요소는 루트(`/`) 자체의 meta-refresh 리다이렉트뿐 (위 2번 항목).

## 7. 과거 색인거부 이력 사이트의 재색인 시 걸림돌 (종합 판단)

실측 기준으로 이번 감사에서 발견된, 재심사에 실질적 영향을 줄 수 있는 항목은 **루트 URL의 noindex+meta-refresh (2번 항목)** 하나뿐. 나머지 축소/은퇴 처리(301, 404, sitemap 정합성, hreflang 제거)는 모두 정상적으로 완료되어 있어 "저품질 콘텐츠 흔적"이나 "크롤 함정"은 확인되지 않았다. 38개 URL 규모의 sitemap과 실제 라이브 URL 수가 일치하며, GSC가 크롤할 새로운 이슈 소스는 확인되지 않음.

---

## 우선순위별 정리

| 우선순위 | 이슈 | 위치 | 수정 |
|---|---|---|---|
| 치명 | 루트 `/`가 200+noindex+meta-refresh (진짜 301 아님) | `web/static/_redirects` (Hugo `hugo.toml:2-3` 기본 동작) | `_redirects`에 `/ /ko/ 301` 추가 |
| 낮음 | HSTS 헤더 없음 | `web/static/_headers` | `Strict-Transport-Security: max-age=31536000; includeSubDomains` 추가 |
| 낮음 | 은퇴 en URL이 301→404 체인 | `web/static/_redirects` | ja/vi/id처럼 직접 404 처리로 정리 (en 복구 계획 있으면 유지 검토) |
| 낮음 | `www.investiqs.net` DNS 레코드 없음 | Cloudflare DNS 설정 | www CNAME + apex 301 추가 (선택) |
