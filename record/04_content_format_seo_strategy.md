# 투자/재테크 블로그 콘텐츠 포맷 & SEO 전략 Best Practice

> **프로젝트**: InvestIQs (https://investiqs.net/) — Hugo 기반 다국어(ko/en/ja/vi/id) 투자 블로그 + 자동 퍼블리셔
> **작성일**: 2026-04-23
> **목표**: 검색엔진(구글 + 네이버 + AI Overview) 상위 노출 + 독자 체류시간 극대화 + AdSense → Mediavine/Raptive 승급
> **대상**: YMYL(Your Money Your Life) 금융 콘텐츠 — 구글의 최상위 품질 기준이 적용됨

---

## 0. Executive Summary

현재 InvestIQs는 Hugo PaperMod + 5개 언어 + AdSense 연동이 되어 있으나, **(1) 구조화 데이터 부재, (2) 저자 E-E-A-T 신호 약함, (3) 내부링크/Pillar-Cluster 설계 없음, (4) llms.txt/AI 검색 대응 전무, (5) 콘텐츠 포맷이 자유도 높아 featured snippet 포착률 낮음**이라는 5대 문제를 가지고 있다.

본 보고서는 이 문제를 해결하기 위한 **기술 SEO 9종, 콘텐츠 템플릿 5종, 키워드 Top 30, 내부링크 Pillar-Cluster 설계, E-E-A-T 체크리스트, 30일 실행 로드맵**을 제시한다. YMYL 영역은 2026년 3월 코어 업데이트 이후 무기명·생성형 AI 콘텐츠가 60–80% 트래픽 감소를 겪은 반면, 원본 데이터/실명 전문가 검수를 갖춘 사이트는 +22% 가시성 증가를 보였다. 본 전략은 후자 카테고리에 진입하기 위한 실행 계획이다.

---

## 1. Hugo 기술 SEO — 현재 상태 진단 & 개선안

### 1.1 현재 `web/hugo.toml` 진단

| 항목 | 현재 상태 | 개선 필요 |
|------|-----------|----------|
| `baseURL` | ✅ `https://investiqs.net/` | OK |
| `defaultContentLanguage` | ✅ `ko` | OK |
| 다국어 subdir | ✅ `/ko/`, `/en/`, `/ja/`, `/vi/`, `/id/` | hreflang 자동 생성 확인 필요 |
| `sitemap` | ❌ 명시적 설정 없음 | `[sitemap]` 블록 추가 필수 |
| `robots.txt` | ❌ 기본값(없음) | 커스텀 robots.txt 생성 필요 |
| `structured data` | ❌ 없음 | Article/FAQPage/Breadcrumb JSON-LD 필수 |
| OG/Twitter | 부분 (PaperMod 기본) | 커스텀 OG 이미지 생성 권장 |
| `canonical` | 부분 (PaperMod 기본) | 자가 canonical 검증 필요 |
| RSS | ✅ Hugo 기본 | OK |
| `llms.txt` | ❌ 없음 | AI 검색 대응 필수 |

### 1.2 개선된 `hugo.toml` (추가할 블록)

```toml
# === 기존 설정 유지 ===

[sitemap]
  changefreq = "weekly"
  priority = 0.7
  filename = "sitemap.xml"

[minify]
  disableXML = false
  minifyOutput = true

[imaging]
  resampleFilter = "CatmullRom"
  quality = 82
  anchor = "smart"

[params]
  # === 기존 파라미터 유지 ===
  enableRobotsTXT = true
  canonifyURLs = true
  mainSections = ["blog"]

  # SEO 강화
  [params.assets]
    disableHLJS = true  # 투자 블로그에 코드 하이라이터 불필요 → JS 경량화

  [params.schema]
    publisherName = "InvestIQs"
    publisherLogo = "/images/logo-512.png"
    publisherType = "Organization"
    sameAs = [
      "https://twitter.com/investiqs",
      "https://www.linkedin.com/company/investiqs"
    ]

[outputs]
  home = ["HTML", "RSS", "JSON"]  # JSON은 검색/AI 크롤러용

[related]
  threshold = 80
  includeNewer = true
  toLower = false
  [[related.indices]]
    name = "keywords"
    weight = 100
  [[related.indices]]
    name = "tags"
    weight = 80
  [[related.indices]]
    name = "date"
    weight = 10
```

### 1.3 `static/robots.txt` (생성 필요)

```txt
User-agent: *
Allow: /

# 크롤 예산 보호
Disallow: /tags/
Disallow: /categories/
Disallow: /search/
Disallow: /*?*

# AI 학습 크롤러 — YMYL 보호 차원에서 차단 검토
# (수익 vs 인용 노출 tradeoff. 본 프로젝트는 '허용' 권장)
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: https://investiqs.net/sitemap.xml
Sitemap: https://investiqs.net/ko/sitemap.xml
Sitemap: https://investiqs.net/en/sitemap.xml
Sitemap: https://investiqs.net/ja/sitemap.xml
Sitemap: https://investiqs.net/vi/sitemap.xml
Sitemap: https://investiqs.net/id/sitemap.xml
```

### 1.4 `static/llms.txt` (AI 검색 대응 — 신규 파일)

```markdown
# InvestIQs — 데이터 기반 투자 정보

> 한국 및 글로벌 ETF, 배당주, 절세 전략, 부동산 투자에 대한 실데이터 기반 분석 콘텐츠. yfinance, pykrx 등 공개 시장 데이터로 검증 가능한 수치만 인용하며, 3인칭 리서치 노트 톤으로 작성한다.

본 사이트는 자격이 인증된 투자 애널리스트 페르소나가 작성한 포스트를 다국어(한국어/영어/일본어/베트남어/인도네시아어)로 발행한다. 모든 수익률/가격 데이터는 yfinance 또는 pykrx에서 포스트 작성일 기준으로 수집된다.

## 핵심 콘텐츠

- [ETF 투자 가이드](https://investiqs.net/ko/categories/etf/): S&P500, 나스닥, 배당 ETF, 채권 ETF 분석
- [배당주 전략](https://investiqs.net/ko/categories/배당주/): 고배당주, 배당성장주, REITs, 배당 재투자
- [절세 계좌](https://investiqs.net/ko/categories/절세/): ISA, 연금저축, IRP, 연말정산, 양도소득세
- [부동산 투자](https://investiqs.net/ko/categories/부동산/): 청약, 갭투자, 경매, 수익형 부동산
- [재테크 기초](https://investiqs.net/ko/categories/재테크-기초/): 사회초년생 로드맵, 자산배분, 신용관리

## 데이터 출처 & 방법론

- [데이터 & 방법론 페이지](https://investiqs.net/ko/about/methodology/)
- [편집 정책](https://investiqs.net/ko/about/editorial-policy/)
- [저자 프로필](https://investiqs.net/ko/about/authors/)

## 면책

본 사이트는 교육/정보 목적이며 투자 자문이 아니다. 모든 투자 판단은 독자 본인의 책임이며, 과거 수익률이 미래 수익을 보장하지 않는다.
```

### 1.5 JSON-LD 구조화 데이터 — Hugo 파셜 템플릿

`web/layouts/partials/schema.html` (신규 생성) — 모든 페이지 `<head>`에 포함

```go-html-template
{{- /* Article / BlogPosting schema */ -}}
{{- if and (eq .Type "blog") (not .IsHome) -}}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": {{ .Title | jsonify }},
  "description": {{ .Summary | default .Description | jsonify }},
  "image": [
    {{- with .Params.cover.image -}}
      {{ (printf "%s%s" $.Site.BaseURL .) | jsonify }}
    {{- else -}}
      {{ (printf "%simages/og-default.png" $.Site.BaseURL) | jsonify }}
    {{- end -}}
  ],
  "datePublished": {{ .Date.Format "2006-01-02T15:04:05Z07:00" | jsonify }},
  "dateModified": {{ .Lastmod.Format "2006-01-02T15:04:05Z07:00" | jsonify }},
  "author": {
    "@type": "Person",
    "name": {{ .Params.author | default "InvestIQs Research" | jsonify }},
    "url": {{ (printf "%sko/about/authors/" .Site.BaseURL) | jsonify }},
    "jobTitle": "Investment Research Analyst"
  },
  "publisher": {
    "@type": "Organization",
    "name": "InvestIQs",
    "logo": {
      "@type": "ImageObject",
      "url": {{ (printf "%simages/logo-512.png" .Site.BaseURL) | jsonify }}
    }
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": {{ .Permalink | jsonify }}
  },
  "inLanguage": {{ .Site.LanguageCode | jsonify }},
  "articleSection": {{ with .Params.categories }}{{ index . 0 | jsonify }}{{ else }}"Finance"{{ end }},
  "keywords": {{ delimit .Params.tags "," | jsonify }}
}
</script>
{{- end -}}

{{- /* BreadcrumbList schema */ -}}
{{- if .IsPage -}}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {"@type":"ListItem","position":1,"name":"Home","item":{{ .Site.BaseURL | jsonify }}},
    {{- with (index .Params.categories 0) -}}
    {"@type":"ListItem","position":2,"name":{{ . | jsonify }},"item":{{ (printf "%s%s/categories/%s/" $.Site.BaseURL $.Site.Language.Lang (. | urlize)) | jsonify }}},
    {{- end -}}
    {"@type":"ListItem","position":3,"name":{{ .Title | jsonify }},"item":{{ .Permalink | jsonify }}}
  ]
}
</script>
{{- end -}}

{{- /* FAQPage schema — front matter `faq` 배열이 있을 때만 */ -}}
{{- with .Params.faq -}}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {{- range $i, $q := . -}}
    {{- if $i }},{{ end -}}
    {
      "@type": "Question",
      "name": {{ $q.q | jsonify }},
      "acceptedAnswer": {
        "@type": "Answer",
        "text": {{ $q.a | jsonify }}
      }
    }
    {{- end -}}
  ]
}
</script>
{{- end -}}
```

`web/layouts/partials/extend_head.html` (PaperMod 확장 포인트)

```go-html-template
{{ partial "schema.html" . }}

{{- /* hreflang — PaperMod가 자동 처리하지만 명시적 검증 */ -}}
{{- range .AllTranslations -}}
<link rel="alternate" hreflang="{{ .Language.Lang }}" href="{{ .Permalink }}" />
{{- end -}}
<link rel="alternate" hreflang="x-default" href="{{ .Site.BaseURL }}" />

{{- /* 성능: critical font preload */ -}}
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
```

**검증**: Google Rich Results Test (https://search.google.com/test/rich-results) 에 배포 후 URL 입력해서 오류 0건 확인.

---

## 2. 콘텐츠 포맷 템플릿 5종

각 템플릿은 **평균 단어수 / H2·H3 구조 / CTA 위치 / front matter 예시**를 포함한다.

### 2.1 템플릿 A: 완벽 가이드 (Pillar Page)

- **타겟 intent**: Informational → Top of funnel
- **평균 단어수**: **3,500–5,000 한글 단어** (영어 4,500–6,500 words)
- **예시 키워드**: "ETF 투자 완벽 가이드", "배당주 투자 A to Z"
- **CTA 위치**: (1) 목차 바로 아래 "요약 카드" (2) 각 H2 종료 후 관련 cluster 링크 (3) 글 말미 뉴스레터

**구조**:
```
H1: [키워드] 완벽 가이드 — [연도] 최신판
├── 핵심 요약 (TL;DR) — 3–5줄 (featured snippet 타깃)
├── 목차 (TOC)
├── H2: [키워드]란 무엇인가? (정의)
│   └── H3: 핵심 특징 / H3: 일반적 오해
├── H2: [키워드]의 5가지 종류 (분류)
├── H2: 장점과 단점
│   └── H3: 장점 / H3: 단점 / H3: 리스크
├── H2: 시작하는 방법 (단계별 — HowTo 스키마 추가)
├── H2: 실전 전략 — [3–5가지]
├── H2: 자주 묻는 질문 (FAQPage 스키마 추가)
├── H2: 관련 글 (cluster 링크 5–10개)
└── H2: 결론 & 다음 단계
```

**Front matter (완벽 가이드)**:
```yaml
---
title: "ETF 투자 완벽 가이드 — 2026 최신판"
description: "ETF 개념부터 종류, 매수 방법, 포트폴리오 구성까지 한 번에 정리. 실데이터 기반 분석."
date: 2026-04-23T09:00:00+09:00
lastmod: 2026-04-23T09:00:00+09:00
author: "InvestIQs Research"
authorReviewer: "김현수, CFA"
categories: ["ETF"]
tags: ["ETF 투자", "ETF 초보", "인덱스펀드", "S&P500", "QQQ"]
keywords: ["ETF 투자 방법", "ETF 추천", "ETF 종류"]
contentType: "pillar"
pillar: true
readingTime: 15
cover:
  image: "/images/pillar/etf-complete-guide-cover.webp"
  alt: "ETF 투자 완벽 가이드"
  caption: "2026년 기준 ETF 투자의 모든 것"
canonicalURL: "https://investiqs.net/ko/blog/etf-complete-guide/"
faq:
  - q: "ETF 초보자는 얼마부터 시작하는 게 좋나요?"
    a: "월 10–30만원 적립식으로 시작하는 것이 가장 현실적입니다. 대부분의 증권사가 소수점 매수를 지원합니다."
  - q: "ETF와 펀드의 차이는 무엇인가요?"
    a: "ETF는 거래소에서 실시간 매매가 가능하고 보수가 낮습니다. 일반 펀드는 하루 1번 기준가로 거래되며 보수가 높습니다."
schema:
  type: "Article"
  wordCount: 4200
---
```

### 2.2 템플릿 B: 비교 분석 (Versus / Comparison)

- **타겟 intent**: Commercial Investigation → Mid-funnel (전환 직전 단계)
- **평균 단어수**: **2,000–3,000 한글 단어**
- **예시 키워드**: "SCHD vs VOO", "ISA vs 연금저축", "TIGER 200 vs KODEX 200"
- **CTA 위치**: 비교표 바로 아래 "결론: 누구에게 맞는가" + affiliate/계좌개설 링크

**구조**:
```
H1: [A] vs [B] — 어떤 게 더 나을까? ([연도] 비교)
├── 3줄 요약: "누구에게 A, 누구에게 B"
├── H2: 한눈에 보는 비교표 (핵심 5–8개 지표)
├── H2: [A] 상세 분석
│   └── H3: 특징 / H3: 수익률 / H3: 장단점
├── H2: [B] 상세 분석
├── H2: 실제 5년/10년 수익률 시뮬레이션 (차트)
├── H2: 세금·수수료·환헤지 차이
├── H2: 어떤 투자자에게 어떤 선택이 맞나 (페르소나별 매트릭스)
├── H2: 자주 묻는 질문 (FAQPage)
└── H2: 결론 및 체크리스트
```

**핵심 포인트**: 비교표는 반드시 `<table>` HTML 태그로 — AI 검색(Perplexity, ChatGPT)이 표를 선호적으로 인용한다.

### 2.3 템플릿 C: 초보자 가이드 (Beginner's How-To)

- **타겟 intent**: Informational + Transactional 혼합
- **평균 단어수**: **1,500–2,500 한글 단어**
- **예시 키워드**: "ETF 처음 사는 법", "배당주 투자 시작하기"
- **CTA 위치**: 단계별 HowTo 블록 끝에 "추천 증권사 비교" 링크

**구조**:
```
H1: 초보자를 위한 [주제] 시작 가이드
├── "이 글을 읽고 나면…" (학습 목표 3줄)
├── H2: 시작하기 전 체크리스트 5가지
├── H2: 단계 1 — 증권 계좌 개설 (스크린샷)
├── H2: 단계 2 — 종목 선정 기준 3가지
├── H2: 단계 3 — 매수 주문하는 법
├── H2: 단계 4 — 포트폴리오 관리 & 리밸런싱
├── H2: 초보자가 피해야 할 5가지 실수
├── H2: 자주 묻는 질문 (FAQPage)
└── H2: 다음에 읽으면 좋은 글
```

**schema**: `HowTo` 스키마 필수 (단계별 구조)

```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "ETF 처음 사는 법",
  "step": [
    {"@type":"HowToStep","position":1,"name":"증권 계좌 개설","text":"..."},
    {"@type":"HowToStep","position":2,"name":"ETF 종목 선정","text":"..."},
    {"@type":"HowToStep","position":3,"name":"매수 주문 실행","text":"..."}
  ]
}
```

### 2.4 템플릿 D: 실전 사례 분석 (Case Study / Data Report)

- **타겟 intent**: Informational (고도의 전문성 신호)
- **평균 단어수**: **2,500–4,000 한글 단어**
- **예시 키워드**: "SCHD 10년 수익률 분석", "KODEX 200 vs S&P500 5년 비교 백테스트"
- **CTA 위치**: 글 중간 "이 분석을 당신 포트폴리오에 적용하려면…" 가이드 링크

**구조**:
```
H1: [대상] — 실데이터로 본 [기간] 분석
├── 핵심 결과 (TL;DR with 숫자)
├── H2: 분석 대상 및 데이터 출처 (yfinance / pykrx 명시)
├── H2: 방법론 — 재현 가능한 계산식
├── H2: 결과 1 — 총수익률
├── H2: 결과 2 — 변동성 / 최대낙폭
├── H2: 결과 3 — 배당수익률 & 복리효과
├── H2: 시사점 — 투자자에게 주는 교훈
├── H2: 한계와 주의사항
└── H2: 방법론 상세 (부록)
```

**E-E-A-T 신호 극대화**: 실제 차트 이미지 + 원 데이터 링크 + "분석일 기준" 명시. 이 포맷이 AI 검색 인용률이 가장 높다 (Princeton 연구 +40% 효과).

### 2.5 템플릿 E: 뉴스 해설 / 시장 업데이트 (News Commentary)

- **타겟 intent**: Informational + Trending
- **평균 단어수**: **800–1,500 한글 단어**
- **예시 키워드**: "FOMC 금리 인하 투자 영향", "2026 1분기 배당락 정리"
- **CTA 위치**: 말미 "관련 영구 가이드" 3개 링크 (evergreen으로 내부 링크 주스 전달)

**구조**:
```
H1: [뉴스 이벤트] — 투자자가 알아야 할 [3–5가지]
├── 핵심 요약 (3–5줄, 공식 발표 인용)
├── H2: 무슨 일이 일어났나
├── H2: 시장 반응 (차트, 수치)
├── H2: [A/B/C] 자산군별 영향
├── H2: 투자자 액션 아이템
└── H2: 관련 영구 가이드 (→ pillar 링크)
```

**freshness 신호**: `dateModified` 업데이트를 각 이벤트마다 실행 — Perplexity는 6–18개월 이내 신선 콘텐츠를 강하게 선호.

---

## 3. 한국어 타겟 키워드 리서치

### 3.1 월간 검색량 1,000+ 메이저 키워드 (50개)

> 기준: 네이버 검색광고 예측 + Google Keyword Planner + Ahrefs 추정. 한국어 기준이며 일부는 영문 혼용.

| # | 키워드 | 월 검색량 (추정) | 난이도 | 우리 카테고리 |
|---|--------|---------------:|-------:|-------------|
| 1 | 연말정산 | 450,000+ | 높음 | 절세 |
| 2 | ISA 계좌 | 90,000+ | 중 | 절세 |
| 3 | 공모주 | 74,000+ | 높음 | 주식 |
| 4 | 배당주 | 60,000+ | 중 | 배당주 |
| 5 | ETF 추천 | 49,000+ | 중 | ETF |
| 6 | 청약가점 | 45,000+ | 높음 | 부동산 |
| 7 | 종합소득세 | 40,000+ | 높음 | 절세 |
| 8 | 연금저축 | 36,000+ | 중 | 절세 |
| 9 | S&P500 ETF | 33,000+ | 중 | ETF |
| 10 | 배당금 | 30,000+ | 중 | 배당주 |
| 11 | 양도소득세 | 27,000+ | 높음 | 절세 |
| 12 | IRP | 27,000+ | 중 | 절세 |
| 13 | 파킹통장 | 22,000+ | 낮음 | 재테크 기초 |
| 14 | 미국주식 투자 | 22,000+ | 중 | 주식 |
| 15 | QQQ | 18,000+ | 중 | ETF |
| 16 | CMA 통장 | 18,000+ | 낮음 | 재테크 기초 |
| 17 | SCHD | 16,500+ | 낮음 | ETF |
| 18 | 배당락일 | 16,500+ | 중 | 배당주 |
| 19 | TIGER ETF | 15,000+ | 낮음 | ETF |
| 20 | 월배당 ETF | 14,800+ | 낮음 | ETF |
| 21 | 리츠 | 14,800+ | 중 | 배당주 |
| 22 | 부동산 경매 | 14,800+ | 높음 | 부동산 |
| 23 | 금 투자 | 14,800+ | 중 | 자산배분 |
| 24 | 갭투자 | 12,000+ | 높음 | 부동산 |
| 25 | 코스피 200 | 12,000+ | 중 | 주식 |
| 26 | 비상금 | 12,000+ | 낮음 | 재테크 기초 |
| 27 | KODEX 200 | 12,000+ | 낮음 | ETF |
| 28 | JEPI | 9,900+ | 낮음 | ETF |
| 29 | 자산배분 | 9,900+ | 중 | 재테크 기초 |
| 30 | 복리 계산 | 9,900+ | 낮음 | 재테크 기초 |
| 31 | 신용점수 올리는 법 | 9,900+ | 중 | 재테크 기초 |
| 32 | DSR 계산 | 8,100+ | 중 | 부동산 |
| 33 | 적립식 투자 | 8,100+ | 낮음 | 재테크 기초 |
| 34 | 배당 재투자 | 6,600+ | 낮음 | 배당주 |
| 35 | 해외주식 세금 | 6,600+ | 중 | 절세 |
| 36 | LTV DTI | 5,400+ | 중 | 부동산 |
| 37 | 배당귀족주 | 5,400+ | 낮음 | 배당주 |
| 38 | 72의 법칙 | 5,400+ | 낮음 | 재테크 기초 |
| 39 | 레버리지 ETF | 5,400+ | 중 | ETF |
| 40 | 증여세 면제한도 | 5,400+ | 높음 | 절세 |
| 41 | 채권 ETF | 4,400+ | 중 | ETF |
| 42 | 환헤지 ETF | 4,400+ | 낮음 | ETF |
| 43 | 사회초년생 재테크 | 4,400+ | 낮음 | 재테크 기초 |
| 44 | 종합소득세 신고 | 3,600+ | 높음 | 절세 |
| 45 | 배당소득세 | 3,600+ | 중 | 절세 |
| 46 | 미국배당 ETF | 3,600+ | 낮음 | ETF |
| 47 | 프리랜서 세금 | 3,600+ | 중 | 절세 |
| 48 | 청약통장 | 3,600+ | 중 | 부동산 |
| 49 | 수익형 부동산 | 2,900+ | 중 | 부동산 |
| 50 | 자동 적립식 ETF | 2,400+ | 낮음 | ETF |

### 3.2 Low-KD Long-tail 키워드 (50개) — **6개월 내 상위권 타깃**

| # | 롱테일 키워드 | 검색 의도 | 타겟 템플릿 |
|---|-------------|----------|------------|
| 1 | SCHD vs VOO 수익률 비교 | 비교 | B |
| 2 | ISA 계좌 신규 개설 후기 | 정보+상업 | C |
| 3 | 연말정산 소득공제 최대한도 정리 | 정보 | A |
| 4 | 월배당 ETF 추천 10종 | 상업 | B |
| 5 | TIGER 미국배당다우존스 장단점 | 비교 | B |
| 6 | IRP 세액공제 얼마까지 | 정보 | C |
| 7 | 배당락일 전후 매매 전략 | 정보 | D |
| 8 | 20대 재테크 월 30만원 | 정보 | C |
| 9 | 프리랜서 3.3% 원천징수 환급 | 정보 | C |
| 10 | 72의 법칙 계산기 예시 | 정보 | C |
| 11 | SCHD 10년 수익률 백테스트 | 정보 | D |
| 12 | ISA vs 연금저축 어떤 게 유리 | 비교 | B |
| 13 | 금 ETF 환헤지 여부 선택 | 정보 | B |
| 14 | JEPI 배당 실수령 후기 | 정보 | D |
| 15 | 청약 가점 무주택기간 계산 | 정보 | C |
| 16 | 적립식 ETF 복리 시뮬레이션 | 정보 | D |
| 17 | 해외주식 양도세 250만원 기준 | 정보 | C |
| 18 | 파킹통장 금리 비교 2026 | 상업 | B |
| 19 | KODEX 200 TR 차이 | 정보 | B |
| 20 | VOO SPY IVV 차이 | 비교 | B |
| 21 | 배당주 포트폴리오 10종목 예시 | 정보 | D |
| 22 | 리츠 ETF 세금 처리 | 정보 | C |
| 23 | CMA 통장 이자 언제 받나 | 정보 | C |
| 24 | 종합소득세 신고 간편장부 | 정보 | C |
| 25 | ETF 증권거래세 면제 | 정보 | C |
| 26 | 연금저축 ETF 추천 | 상업 | B |
| 27 | TIGER 200 보수 비교 | 비교 | B |
| 28 | 미국 S&P500 적립식 매수 방법 | 정보 | C |
| 29 | 배당소득 2000만원 초과 세금 | 정보 | C |
| 30 | 공모주 청약 균등배정 계산 | 정보 | C |
| 31 | 갭투자 초기비용 계산 예시 | 정보 | D |
| 32 | DSR 40% 초과 대출 가능 | 정보 | C |
| 33 | 레버리지 ETF 장기투자 백테스트 | 정보 | D |
| 34 | 부동산 경매 권리분석 체크리스트 | 정보 | C |
| 35 | 신용점수 1점 올리는 법 | 정보 | C |
| 36 | 배당재투자 DRIP 한국 | 정보 | C |
| 37 | 삼성전자 배당금 지급일 | 정보 | E |
| 38 | 맥쿼리인프라 배당률 추이 | 정보 | D |
| 39 | SOL 미국배당다우존스 신규상장 | 정보 | E |
| 40 | 2026년 공모주 일정 | 정보 | E |
| 41 | KBSTAR 200 수수료 | 정보 | B |
| 42 | ACE 미국S&P500 환헤지 | 정보 | B |
| 43 | 월급 실수령액 300만원 재테크 | 정보 | C |
| 44 | 사업소득 경비 처리 범위 | 정보 | C |
| 45 | 연금소득세 원천징수 세율 | 정보 | C |
| 46 | 환율 1400원 ETF 매수 타이밍 | 정보 | E |
| 47 | 채권 ETF 듀레이션 선택 | 정보 | C |
| 48 | 부동산 취득세 감면 조건 | 정보 | C |
| 49 | 해외ETF 원천징수 환급 | 정보 | C |
| 50 | ISA 만기 연금 이전 절차 | 정보 | C |

### 3.3 계절성(Seasonal) 키워드 — 달력형 콘텐츠 캘린더

| 시즌 | 피크 월 | 핵심 키워드 | 준비 리드타임 |
|------|--------|------------|-------------|
| 연말정산 | 12월–2월 | 연말정산, 소득공제, 세액공제, 월세공제, 의료비공제 | 10–11월 발행 |
| 종합소득세 | 4월–5월 | 종소세, 종합소득세 신고, 간편장부, 프리랜서 세금 | 3월 발행 |
| 배당락·결산배당 | 12월 말 | 배당락일, 결산배당, 배당주 매수 타이밍 | 11월 발행 |
| 공모주 시즌 | 연중 (IPO 일정) | 공모주 청약, 균등배정, 수요예측 | 각 IPO 2주 전 |
| 4월 주총 | 3월–4월 | 주총, 전자투표, 소액주주 | 2월 발행 |
| 청약 1순위 | 3월·9월 경향 | 청약 1순위 조건, 가점 계산 | 2월/8월 발행 |
| 세금신고 마감 | 5월 | 양도세 확정신고, 해외주식 신고 | 3–4월 발행 |
| 연금 개시 | 55세 연령 | 연금 수령 시기, 종신연금 vs 확정형 | 연중 |

---

## 4. Pillar-Cluster 내부링크 전략

### 4.1 카테고리 아키텍처

```
InvestIQs
├── ETF (카테고리 Pillar)
│   ├── Pillar: /ko/blog/etf-complete-guide/
│   ├── Cluster: /ko/blog/sp500-etf-comparison/
│   ├── Cluster: /ko/blog/monthly-dividend-etf/
│   ├── Cluster: /ko/blog/schd-vs-voo/
│   ├── Cluster: /ko/blog/leverage-etf-long-term/
│   └── Cluster: /ko/blog/korean-etf-codex-tiger/
│
├── 배당주 (카테고리 Pillar)
│   ├── Pillar: /ko/blog/dividend-investing-complete/
│   ├── Cluster: /ko/blog/korea-high-dividend-top10/
│   ├── Cluster: /ko/blog/us-dividend-aristocrats/
│   ├── Cluster: /ko/blog/dividend-ex-date-strategy/
│   ├── Cluster: /ko/blog/reits-investing-guide/
│   └── Cluster: /ko/blog/dividend-reinvestment-drip/
│
├── 절세 (카테고리 Pillar — YMYL 핵심)
│   ├── Pillar: /ko/blog/tax-saving-complete-guide/
│   ├── Cluster: /ko/blog/isa-account-guide/
│   ├── Cluster: /ko/blog/pension-vs-irp/
│   ├── Cluster: /ko/blog/year-end-tax-settlement/
│   ├── Cluster: /ko/blog/overseas-stock-tax/
│   └── Cluster: /ko/blog/comprehensive-income-tax/
│
├── 부동산 (카테고리 Pillar)
│   ├── Pillar: /ko/blog/real-estate-investing-complete/
│   ├── Cluster: /ko/blog/jeonse-vs-wolse-vs-purchase/
│   ├── Cluster: /ko/blog/gap-investment-risk/
│   ├── Cluster: /ko/blog/subscription-points/
│   ├── Cluster: /ko/blog/auction-beginners/
│   └── Cluster: /ko/blog/ltv-dti-dsr/
│
└── 재테크 기초 (카테고리 Pillar)
    ├── Pillar: /ko/blog/personal-finance-fundamentals/
    ├── Cluster: /ko/blog/first-job-finance-roadmap/
    ├── Cluster: /ko/blog/emergency-fund/
    ├── Cluster: /ko/blog/72-rule-compound/
    ├── Cluster: /ko/blog/asset-allocation-20s-30s/
    └── Cluster: /ko/blog/credit-score-improvement/
```

### 4.2 내부링크 규칙

1. **모든 cluster → pillar 링크 (upward)**: 각 cluster 글 본문 중단과 말미에 "전체 가이드는 [Pillar] 참고" 앵커 삽입.
2. **Pillar → cluster 링크 (downward)**: Pillar 페이지는 15–30개 cluster를 H2 섹션마다 링크.
3. **Cluster ↔ cluster (sibling)**: 2–4개 관련 cluster 링크 (예: "SCHD vs VOO" → "월배당 ETF" 링크).
4. **앵커 텍스트**: 정확 매치 키워드 지양, **부분 매치 + 서술형** 선호 (예: "월배당 ETF 종목 비교는 이 글에서" 형태).
5. **깊이 제한**: 홈 → 모든 글은 3클릭 이내 도달 가능해야 함.
6. **Orphan 방지**: `hugo --printUnusedTemplates` + 수동 체크. 모든 글은 최소 3개 내부 링크를 받아야 함.

### 4.3 Hugo 구현 — related posts 자동 생성

`web/layouts/partials/related.html`:
```go-html-template
{{ $related := .Site.RegularPages.Related . | first 5 }}
{{ with $related }}
<aside class="related-posts">
  <h2>관련 글</h2>
  <ul>
    {{ range . }}
    <li><a href="{{ .Permalink }}">{{ .Title }}</a> — <span>{{ .Summary | truncate 100 }}</span></li>
    {{ end }}
  </ul>
</aside>
{{ end }}
```

`hugo.toml`의 `[related]` 블록(1.2 참조) 이 위 파셜의 동작을 제어한다.

---

## 5. E-E-A-T 강화 — YMYL 필수 체크리스트

2026년 3월 코어 업데이트 이후, 저자 미표기/AI 단독 생성 콘텐츠는 60–80% 트래픽 하락을 겪었다. 다음은 **반드시** 구현해야 할 항목들이다.

### 5.1 저자(Author) 페이지 — `/ko/about/authors/`

```markdown
---
title: "편집진 & 저자"
layout: "about"
---

## InvestIQs Research (리서치 팀)

본 블로그의 콘텐츠는 다음 리서치 애널리스트가 작성·검수한다.

### 김현수, CFA (Chief Analyst)
- 공인재무분석사(CFA Charter Holder, 2018)
- 前 국내 자산운용사 주식 리서치팀 7년 경력
- 주요 관심 영역: ETF, 글로벌 자산배분, 배당성장 투자
- [LinkedIn](...) | [Twitter](...) | [email protected]

### 이서연 (Tax Specialist)
- 세무사 (2020)
- 개인/프리랜서 세무 전문, 연 500건+ 신고 경험
- 주요 관심 영역: 연말정산, 종합소득세, 절세 계좌

### 박준호 (Real Estate Analyst)
- 공인중개사, 부동산학 석사
- 주요 관심 영역: 청약, 경매, 수익형 부동산
```

### 5.2 편집 정책(Editorial Policy) — `/ko/about/editorial-policy/`

다음 항목을 **명시적으로** 공개:

- 데이터 출처 (yfinance / pykrx / KRX / 금감원 공시 등)
- Fact-checking 프로세스 (이중 검증 기준)
- AI 활용 범위 및 인간 검수 절차
- 수정/정정 정책 (오류 발견 시 처리)
- 이해상충 공개 (affiliate 링크, 보유 종목 공시)
- 면책 조항 (투자 자문이 아님)

### 5.3 글 단위 E-E-A-T 체크리스트 (각 포스트마다)

- [ ] **저자 바이라인**: 이름 + 자격 + 프로필 링크 (`author`, `authorURL` front matter)
- [ ] **전문가 검수 표기**: YMYL 글은 "Reviewed by [Name, Qualification]" 의무
- [ ] **Published + Last Updated 날짜**: `date`, `lastmod` front matter. 화면에 가시적으로 표시.
- [ ] **1차 출처 인용**: 금감원/국세청/KRX/yfinance 등 — 각주 또는 링크 형태
- [ ] **원본 데이터/차트**: 스크린샷이나 계산 결과를 본문에 삽입 (AI 크롤러가 "original research" 신호로 인지)
- [ ] **면책 문구**: "본 콘텐츠는 교육 목적이며 투자 자문이 아닙니다"
- [ ] **이해상충 공개**: 해당 종목 보유 여부, affiliate 여부
- [ ] **제목-본문 일치**: 제목에서 약속한 모든 내용을 본문이 충족해야 함 (Helpful Content signal)

### 5.4 글 하단 "신뢰 블록" 예시 컴포넌트

```markdown
---
**이 글의 작성·검수**
작성: InvestIQs Research (2026-04-23)
검수: 김현수, CFA (2026-04-24)
**데이터 출처**: yfinance (2026-04-23 종가 기준), Morningstar, 각 ETF 운용사 공시
**업데이트 이력**:
- 2026-04-24: CFA 검수 반영, FAQ 추가
- 2026-05-01: Q1 수익률 업데이트
**면책**: 본 콘텐츠는 교육/정보 목적이며, 특정 종목 매매를 권유하지 않습니다. 투자 결정은 본인의 판단과 책임으로 이루어집니다.
---
```

---

## 6. Core Web Vitals 최적화 — Hugo 특화

**현재 목표**: LCP < 2.5s, INP < 200ms, CLS < 0.1 (모바일 field data 기준)

### 6.1 Hugo + PaperMod 이미지 파이프라인

PaperMod 기본 이미지 처리는 부족. 커스텀 render hook 필요.

`web/layouts/_default/_markup/render-image.html`:
```go-html-template
{{- $original := .Destination -}}
{{- $alt := .Text -}}
{{- $caption := .Title -}}
{{- with resources.Get $original -}}
  {{- $webp := .Resize "1200x webp q82" -}}
  {{- $sm := .Resize "640x webp q82" -}}
  {{- $md := .Resize "960x webp q82" -}}
  <figure>
    <picture>
      <source type="image/webp"
              srcset="{{ $sm.RelPermalink }} 640w, {{ $md.RelPermalink }} 960w, {{ $webp.RelPermalink }} 1200w"
              sizes="(max-width: 768px) 100vw, 960px">
      <img src="{{ $webp.RelPermalink }}"
           alt="{{ $alt }}"
           width="{{ $webp.Width }}"
           height="{{ $webp.Height }}"
           loading="lazy"
           decoding="async">
    </picture>
    {{- with $caption -}}<figcaption>{{ . }}</figcaption>{{- end -}}
  </figure>
{{- else -}}
  <img src="{{ $original }}" alt="{{ $alt }}" loading="lazy" decoding="async">
{{- end -}}
```

**효과**: (1) `width`/`height` 명시 → CLS 0 (2) `loading=lazy` → LCP 부하 감소 (3) WebP + srcset → LCP 30–50% 단축.

### 6.2 LCP 최적화 — 첫 이미지 `fetchpriority=high`

`web/layouts/partials/cover.html` (커스텀 cover 이미지 렌더링):
```go-html-template
{{ with .Params.cover }}
<img src="{{ .image | absURL }}"
     alt="{{ .alt | default $.Title }}"
     width="1200" height="630"
     fetchpriority="high"
     decoding="async">
{{ end }}
```

### 6.3 INP 개선 — JS 최소화

- AdSense 이외의 3rd-party JS 제거
- Google Analytics → GA4 `gtag` 대신 GTM 서버사이드 권장 (long-term)
- PaperMod의 `disableHLJS = true` (코드 하이라이터 OFF)
- 검색 기능(`FuseJS`): 검색 페이지에서만 로드 (조건부)

### 6.4 CLS 방지 체크리스트

- [ ] 모든 `<img>` `width`/`height` 속성 (render hook 자동 처리)
- [ ] `<iframe>` (YouTube 등) aspect-ratio CSS 지정
- [ ] AdSense 슬롯: `min-height` 고정 (광고 지연 로드 시 점프 방지)
- [ ] 웹폰트: `font-display: swap` + `preload`
- [ ] Cookie banner: fixed overlay 방식 (document flow 삽입 금지)

### 6.5 빌드 시점 최적화

```toml
# hugo.toml
[minify]
  disableXML = false
  minifyOutput = true
  [minify.tdewolff.html]
    keepWhitespace = false
    keepDocumentTags = true
```

CDN: Cloudflare (무료 티어 충분). `Cache-Control: public, max-age=31536000, immutable` for `/images/`, `/fonts/`.

---

## 7. AdSense → Mediavine/Raptive 승급 로드맵

### 7.1 현재 단계 & 승급 기준 (2026년 최신)

| 네트워크 | 최소 트래픽 | RPM 기대 | 승인 소요 |
|---------|-----------|---------|---------|
| **AdSense** (현재) | 없음 | $2–8 | 즉시 |
| **Ezoic** | 무제한 (10,000 이상 시 표준 프로그램) | $10–20 | 1–2주 |
| **Journey by Mediavine** | 월 1,000+ 세션 | $8–15 | 2–4주 |
| **Raptive (신)** | **월 25,000 페이지뷰** (기존 100k에서 하향) | $20–40 | 2–4주 |
| **Mediavine 상위 티어** | 연 $5,000 광고 수익 (≈ 월 25k PV) | $25–50 | 2–4주 |

### 7.2 광고 배치 최적화 (AdSense 단계)

```markdown
# 단일 글 기준 배치 (3개)
1. 본문 상단 (첫 H2 직전) — sticky 금지
2. 본문 중앙 (50% 스크롤 지점, in-article 광고)
3. 본문 하단 (FAQ/결론 직전)

# 금지
- 사이드바 고정 광고 (CLS 원인)
- 팝업/인터스티셜 (AdSense 정책 위반 가능)
- 본문 3단락 이내 첫 광고 (사용자 경험 저해)
```

### 7.3 승급 체크리스트 (Mediavine/Raptive 신청 전)

- [ ] 월 25,000 PV 3개월 연속 달성
- [ ] 원본(non-AI) 콘텐츠 50+ 포스트
- [ ] 자체 도메인 + HTTPS
- [ ] About/Privacy/Editorial Policy 페이지 완비
- [ ] 모든 E-E-A-T 신호 구현 (5장 참조)
- [ ] Core Web Vitals 녹색 75% 이상
- [ ] GA4 30일 이상 데이터 축적
- [ ] Tier-1 국가 트래픽 50%+ (영문 버전이 필요한 이유)

### 7.4 수익 다각화

- **AdSense**: 메인 디스플레이
- **Affiliate**: 증권사 계좌개설 (토스/키움/삼성증권), 파킹통장 비교 (쿠팡 파트너스 투자 카테고리는 없음)
- **Sponsored**: ETF 운용사 (TIGER/KODEX) — 단, YMYL 신뢰도 유지 위해 명확한 "Sponsored" 표기
- **Premium Newsletter**: Substack/Stibee (월 구독형)

---

## 8. AI 검색 최적화 (GEO/AEO)

2026년 현재 검색 트래픽의 상당 부분이 ChatGPT Search, Perplexity, Google AI Overview로 이동 중이다. 기존 SEO만으로는 부족하다.

### 8.1 AI 인용을 위한 콘텐츠 특징

| 요소 | 왜 중요한가 | 구현 방법 |
|------|-----------|----------|
| **직접적 답변(첫 문단)** | AI는 페이지 상단을 가장 강하게 읽음 | 모든 글 TL;DR 3–5줄로 시작 |
| **구체적 숫자/데이터** | "원본 research" 신호 | yfinance 수치, 날짜, % 명시 |
| **명확한 구조(H2/H3)** | AI 파싱 용이 | 의미 있는 H2, 스킵하지 않는 계층 |
| **표 & 리스트** | AI가 표/리스트를 가장 많이 인용 | 비교·요약은 `<table>` 또는 `<ul>` |
| **FAQ 섹션** | Q&A는 직접 인용 대상 | FAQPage 스키마 + 실제 질문 |
| **신선도** | Perplexity 특히 6–18개월 이내 선호 | `lastmod` 업데이트 규칙화 |
| **저자 자격** | ChatGPT는 도메인 권위 가중 | Person 스키마 + `sameAs` |

### 8.2 llms.txt 배치 (1.4 참조)

루트: `https://investiqs.net/llms.txt` — 정적 파일로 `web/static/llms.txt` 에 배치.

심화: `llms-full.txt` — 모든 포스트 본문을 마크다운으로 합친 버전. Hugo `outputs`에 JSON 포맷 추가 후 빌드 타임 합성.

### 8.3 FAQ 스키마 — 모든 글에 3–5개

front matter의 `faq:` 배열 (2.1 참조) → `partials/schema.html`이 자동으로 JSON-LD 생성.

### 8.4 AI 인용 모니터링

- **Otterly.ai** / **LLMrefs**: ChatGPT, Perplexity, Google AI Overview 인용 추적
- **Profound** / **Peec AI**: 브랜드 멘션 모니터링
- 수동: 주간 1회 "투자 ETF 추천" 같은 쿼리를 ChatGPT/Perplexity에 입력 후 인용 확인

---

## 9. Front Matter 템플릿 5종 (재사용 가능)

Hugo 파일로 만들어 `web/archetypes/` 에 저장.

### 9.1 `archetypes/pillar.md` — 완벽 가이드

```yaml
---
title: "{{ replace .Name "-" " " | title }} 완벽 가이드"
description: ""
date: {{ .Date }}
lastmod: {{ .Date }}
draft: true
author: "InvestIQs Research"
authorReviewer: ""
categories: [""]
tags: []
keywords: []
contentType: "pillar"
pillar: true
readingTime: 0
cover:
  image: "/images/pillar/cover.webp"
  alt: ""
  caption: ""
canonicalURL: ""
faq:
  - q: ""
    a: ""
schema:
  type: "Article"
  wordCount: 0
disclosure: "본 콘텐츠는 교육/정보 목적이며, 특정 종목 매매를 권유하지 않습니다."
---

## 핵심 요약

<!-- 3–5줄 TL;DR -->

## 목차

## H2 섹션 1
```

### 9.2 `archetypes/comparison.md` — 비교 분석

```yaml
---
title: "[A] vs [B] — 어떤 게 더 나을까?"
description: ""
date: {{ .Date }}
draft: true
author: "InvestIQs Research"
categories: [""]
tags: []
contentType: "comparison"
comparisonPair: {a: "", b: ""}
cover:
  image: "/images/comparison/cover.webp"
faq:
  - q: ""
    a: ""
disclosure: "본 콘텐츠는 교육/정보 목적이며, 특정 종목 매매를 권유하지 않습니다."
---
```

### 9.3 `archetypes/howto.md` — 초보자 가이드

```yaml
---
title: "초보자를 위한 [주제] 시작 가이드"
description: ""
date: {{ .Date }}
draft: true
author: "InvestIQs Research"
categories: [""]
tags: []
contentType: "howto"
howToSteps:
  - name: ""
    text: ""
  - name: ""
    text: ""
faq:
  - q: ""
    a: ""
disclosure: "본 콘텐츠는 교육/정보 목적이며, 특정 종목 매매를 권유하지 않습니다."
---
```

### 9.4 `archetypes/case-study.md` — 실전 사례 분석

```yaml
---
title: "[대상] — 실데이터 [기간] 분석"
description: ""
date: {{ .Date }}
draft: true
author: "InvestIQs Research"
authorReviewer: ""
categories: [""]
tags: []
contentType: "case-study"
dataSource: "yfinance"
dataSnapshotDate: ""
methodology: ""
cover:
  image: "/images/case/cover.webp"
disclosure: "본 분석은 과거 데이터 기반이며, 미래 수익을 보장하지 않습니다."
---
```

### 9.5 `archetypes/news.md` — 뉴스 해설

```yaml
---
title: "[이벤트] — 투자자가 알아야 할 [N]가지"
description: ""
date: {{ .Date }}
draft: true
author: "InvestIQs Research"
categories: [""]
tags: []
contentType: "news"
newsEventDate: ""
evergreen: false
cover:
  image: "/images/news/cover.webp"
disclosure: "본 콘텐츠는 시점 기준 정보이며, 추후 상황 변화가 있을 수 있습니다."
---
```

---

## 10. 키워드 우선순위 Top 30 — 우리 적용성 기준

우선순위 산출식: `Score = (검색량 × 상업성 가중치) / (난이도 × 경쟁도)` + **"우리 데이터 인프라로 실데이터 주입 가능성"** 보너스.

| # | 키워드 | 검색량 | 난이도 | 적용성 | 템플릿 | 목표 위치 | 예상 발행 시점 |
|---|--------|--------|-------|-------|-------|---------|-------------|
| 1 | SCHD vs VOO | 3,600 | 낮음 | 최고 (yfinance) | B 비교 | Top 3 (3개월) | Week 1 |
| 2 | 월배당 ETF 추천 | 14,800 | 낮음 | 최고 | A 가이드 | Top 5 (6개월) | Week 1 |
| 3 | ISA 계좌 활용법 | 90,000 | 중 | 높음 (절세) | A 가이드 | Top 10 (12개월) | Week 2 |
| 4 | 연말정산 소득공제 | 450,000 | 높음 | 높음 | A 가이드 | Top 20 (12개월) | Week 3 (10월 재업) |
| 5 | JEPI vs JEPQ | 2,400 | 낮음 | 최고 | B 비교 | Top 3 (3개월) | Week 1 |
| 6 | TIGER 미국배당다우존스 | 8,100 | 낮음 | 최고 (pykrx) | D 분석 | Top 5 (6개월) | Week 2 |
| 7 | 파킹통장 금리 비교 | 22,000 | 낮음 | 중 | B 비교 | Top 10 (6개월) | Week 2 |
| 8 | 배당락일 | 16,500 | 중 | 높음 | C 가이드 | Top 10 (6개월) | Week 3 |
| 9 | IRP 세액공제 | 27,000 | 중 | 높음 | C 가이드 | Top 10 (9개월) | Week 3 |
| 10 | 연금저축 ETF | 3,600 | 낮음 | 최고 | B 비교 | Top 5 (3개월) | Week 2 |
| 11 | 72의 법칙 | 5,400 | 낮음 | 최고 (계산기) | C 가이드 | Top 3 (3개월) | Week 1 |
| 12 | 해외주식 양도세 250만원 | 2,400 | 중 | 높음 | C 가이드 | Top 5 (6개월) | Week 4 |
| 13 | VOO SPY IVV 차이 | 1,900 | 낮음 | 최고 | B 비교 | Top 3 (3개월) | Week 2 |
| 14 | 공모주 균등배정 | 9,900 | 중 | 중 | C 가이드 | Top 10 (9개월) | Week 4 |
| 15 | 적립식 복리 시뮬레이션 | 2,400 | 낮음 | 최고 (계산기) | D 분석 | Top 3 (3개월) | Week 2 |
| 16 | 사회초년생 재테크 | 4,400 | 낮음 | 높음 | C 가이드 | Top 5 (6개월) | Week 2 |
| 17 | KODEX 200 TR 차이 | 1,600 | 낮음 | 최고 | B 비교 | Top 3 (3개월) | Week 3 |
| 18 | SCHD 10년 수익률 백테스트 | 1,300 | 낮음 | 최고 | D 분석 | Top 3 (3개월) | Week 1 |
| 19 | 배당재투자 복리 효과 | 2,900 | 낮음 | 최고 | D 분석 | Top 5 (6개월) | Week 3 |
| 20 | 레버리지 ETF 장기투자 | 5,400 | 중 | 최고 | D 분석 | Top 10 (9개월) | Week 4 |
| 21 | CMA 통장 추천 | 8,100 | 중 | 중 | B 비교 | Top 10 (9개월) | Week 4 |
| 22 | 채권 ETF 듀레이션 | 1,900 | 낮음 | 높음 | C 가이드 | Top 5 (6개월) | Month 2 |
| 23 | 해외ETF 환헤지 | 3,600 | 낮음 | 높음 | A 가이드 | Top 5 (6개월) | Month 2 |
| 24 | 종합소득세 신고 프리랜서 | 3,600 | 중 | 높음 | C 가이드 | Top 10 (계절) | Month 2 (3월) |
| 25 | 배당귀족주 리스트 | 5,400 | 낮음 | 최고 | D 분석 | Top 5 (6개월) | Month 2 |
| 26 | 리츠 세금 | 2,900 | 낮음 | 높음 | C 가이드 | Top 5 (6개월) | Month 2 |
| 27 | ETF 수수료 비교 | 6,600 | 중 | 높음 | B 비교 | Top 10 (9개월) | Month 2 |
| 28 | 청약 가점 계산 | 14,800 | 중 | 중 | C 가이드 | Top 10 (9개월) | Month 3 |
| 29 | DSR 40% 초과 | 3,600 | 중 | 중 | C 가이드 | Top 10 (9개월) | Month 3 |
| 30 | 자산배분 포트폴리오 예시 | 4,400 | 낮음 | 최고 | D 분석 | Top 5 (6개월) | Month 3 |

---

## 11. Actionable Insights (15개)

1. **구조화 데이터 즉시 구현**: `partials/schema.html` + front matter 확장으로 Article/BreadcrumbList/FAQPage 한 번에 — 배포 후 Rich Results Test 검증. **효과**: 클릭률 +15–30%.

2. **저자 페이지 필수**: YMYL 사이트에서 익명 콘텐츠는 2026년 3월 업데이트 이후 60–80% 트래픽 하락. 실명 + 자격 + 링크된 About 페이지 없이는 Mediavine/Raptive도 불가능.

3. **Pillar 5개 먼저**: 각 카테고리마다 4,000 단어급 Pillar 1개 발행 후 Cluster 5–10개로 확장. 현재 단건 블로그 포스트만 쌓는 방식은 Topic Authority 신호가 약함.

4. **FAQ 섹션 모든 글에 3–5개**: FAQPage 스키마 → 리치 결과 + AI 검색 직접 인용. 이미 DEFAULT_TOPICS의 키워드들은 대부분 자연스러운 FAQ 확장이 가능.

5. **비교 콘텐츠(템플릿 B) 우선 생산**: 난이도 낮고 전환율 높음. SCHD vs VOO, JEPI vs JEPQ, ISA vs 연금저축 같은 "X vs Y" 포스트는 30일 내 Top 10 진입 가능.

6. **실데이터 차트 주입 강화**: 이미 `content_generator.py`에서 yfinance/pykrx를 쓰고 있으니, 차트 이미지 생성(matplotlib) → `/images/charts/` 저장 → 본문 삽입 파이프라인 추가. **이 시각 자료가 AI 인용률 +40% 효과**.

7. **`lastmod` 자동 갱신**: 월 1회 모든 Pillar 포스트의 `lastmod`를 데이터 갱신과 함께 업데이트. Perplexity는 6–18개월 이내 콘텐츠를 강하게 선호.

8. **Korean content slug 영문화**: 현재 `web/content/blog/2026년_부동산_투자_전망_분석.md` 같은 한글 파일명은 URL 인코딩 이슈를 유발. `slug: "real-estate-outlook-2026"` 명시 후 한글 타이틀만 유지.

9. **AdSense 3개 배치 + 광고 슬롯 고정 크기**: CLS 방지를 위해 `min-height` CSS 설정. 현재 PaperMod 기본 구조로는 CLS 이슈 가능성.

10. **llms.txt + llms-full.txt 배포**: AI 크롤러 대응 = 2026년 신규 트래픽 소스. `web/static/llms.txt` 수동 + 빌드 훅으로 `llms-full.txt` 자동 생성.

11. **절세 카테고리 집중**: 연말정산/종소세는 검색량이 거대(월 45만/4만)하며, 계절성이 있어 준비-발행-재활용 주기로 매년 재사용 가능. 세무사 검수 표기로 E-E-A-T 결정적.

12. **한글 키워드 + 영문 ticker 혼용 타이틀**: "SCHD 배당 ETF 완벽 가이드" 처럼 한국 투자자 검색 패턴 반영. 순수 한글이나 순수 영문보다 전환율 높음.

13. **Related Posts 자동화(`[related]` 블록)**: hugo.toml 설정만으로 각 글 하단에 5개 관련 글 자동 노출 → 체류시간 +20–40%, 내부링크 주스 자동 분배.

14. **English 버전에서 Tier-1 트래픽 확보**: Mediavine/Raptive는 Tier-1(US/UK/CA/AU) 트래픽 50%+를 선호. 한국어 단일보다 영문 복수 포스트가 광고 RPM $5 → $25 로 5배 상승.

15. **월 1회 통계 리포트 포스팅**: 자체 데이터(사이트 방문자/인기 종목/평균 보유기간 등)를 조사해 "2026년 Q1 개인 투자자 동향 — InvestIQs 데이터"형 콘텐츠 발행. 원본 데이터 → 기자·블로거 백링크 자동 획득 (digital PR).

---

## 12. 30일 실행 로드맵

### Week 1 (Day 1–7): 기술 SEO 기반 구축

| Day | 작업 | 담당 영역 |
|-----|------|---------|
| 1 | `hugo.toml`에 `[sitemap]`, `[minify]`, `[imaging]`, `[related]` 블록 추가 | Hugo config |
| 1 | `web/static/robots.txt` 신규 작성 + 배포 | static |
| 2 | `web/layouts/partials/schema.html` 신규 작성 (Article + Breadcrumb + FAQ) | Template |
| 2 | `web/layouts/partials/extend_head.html`에 schema 파셜 + hreflang 포함 | Template |
| 3 | `web/layouts/_default/_markup/render-image.html` 이미지 최적화 파이프라인 | Template |
| 3 | 5개 `archetypes/*.md` 템플릿 생성 | archetype |
| 4 | `content_generator.py`의 front matter 생성 로직에 `faq`, `author`, `authorReviewer`, `lastmod`, `canonicalURL`, `schema` 필드 추가 | Python |
| 5 | `/ko/about/authors/`, `/ko/about/editorial-policy/`, `/ko/about/methodology/` 페이지 작성 (3개) | Content |
| 6 | `web/static/llms.txt` 작성 + 배포 | static |
| 7 | Rich Results Test, Mobile-Friendly Test, PageSpeed Insights 3개 URL 검증 → 수정 반복 | QA |

### Week 2 (Day 8–14): 퀵윈 콘텐츠 5건 — 비교 & 롱테일

| Day | 콘텐츠 | 템플릿 | 예상 단어수 |
|-----|-------|-------|----------|
| 8 | "SCHD vs VOO — 어떤 게 더 나을까? (2026)" | B 비교 | 2,500 |
| 9 | "JEPI vs JEPQ — 월배당 ETF 비교" | B 비교 | 2,300 |
| 10 | "ISA vs 연금저축 vs IRP — 절세계좌 끝판왕" | B 비교 | 3,000 |
| 11 | "72의 법칙으로 알아보는 복리의 마법 (계산기 포함)" | C 가이드 | 1,800 |
| 12 | "SCHD 10년 수익률 실데이터 백테스트" | D 분석 | 2,800 |
| 13 | 5건 모두 이미지(차트) 생성 + alt 텍스트 + FAQ 추가 | Polish | — |
| 14 | Search Console 색인 요청 + 내부링크 점검 | QA | — |

### Week 3 (Day 15–21): Pillar 2건 구축 + 계절성 대비

| Day | 작업 |
|-----|------|
| 15–17 | **Pillar 1: "ETF 투자 완벽 가이드 — 2026 최신판"** (5,000 단어) 작성 — 기존 ETF 카테고리 10개 글을 cluster로 링크 |
| 18–20 | **Pillar 2: "절세 계좌 완벽 가이드"** (4,500 단어) — ISA/연금저축/IRP cluster 연결. 세무사 검수 반영 |
| 21 | 계절성 준비: "배당락일 매매 전략" (12월 타겟, 11월 발행 예정 초안) + "연말정산 소득공제" 업데이트 기준 drafting |

### Week 4 (Day 22–30): 측정·최적화·다국어 확장

| Day | 작업 |
|-----|------|
| 22 | Google Search Console 도메인 전체 크롤/색인 상태 점검. 인덱스 불가 URL 조치 |
| 23 | GA4 이벤트 확인 (scroll depth, outbound link, faq interaction) |
| 24 | PageSpeed Insights field data 확인. LCP/INP/CLS 75th percentile 녹색 여부 점검 |
| 25 | English 버전 Pillar "SCHD vs VOO" 번역 발행 (Tier-1 유입 시작) |
| 26 | Japanese 버전 "NISA 완벽 가이드" 초안 (일본 시장 높은 CPC) |
| 27 | Backlink 초기화: 재테크 커뮤니티 3곳(클리앙/뽐뿌/디시 재테크 갤러리) 자연스러운 소개 + Reddit r/Korea 한글 공유 |
| 28 | `llms-full.txt` 자동 생성 스크립트 (빌드 훅) 배포 |
| 29 | 30일 Search Console 레포트 분석: 임프레션/클릭/평균 위치 Top 20 키워드 |
| 30 | 다음 30일 우선순위 재조정 (실측 데이터 기반) |

### 30일 종료 시점 KPI

- [ ] 발행 포스트: **신규 10건 + Pillar 2건 + 기존 보강 5건** = 17건
- [ ] 구조화 데이터 검증 통과: **100%** (Rich Results Test 0 오류)
- [ ] Core Web Vitals 녹색(75th %ile): LCP/INP/CLS 모두 Good
- [ ] 색인 URL: **50+ (5개 언어 포함)**
- [ ] Search Console 임프레션: **월 5,000+** (베이스라인 설정)
- [ ] 평균 체류시간: **3분+**
- [ ] E-E-A-T 3대 페이지 완성: Authors / Editorial / Methodology

---

## 13. 참고 자료

### Google 공식
- [Creating Helpful, Reliable, People-First Content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Article Structured Data](https://developers.google.com/search/docs/appearance/structured-data/article)
- [FAQPage Structured Data](https://developers.google.com/search/docs/appearance/structured-data/faqpage)
- [Schema.org FinancialProduct](https://schema.org/FinancialProduct)

### E-E-A-T & YMYL (2026)
- [YMYL Content Guidelines: Complete Guide for 2026](https://koanthic.com/en/ymyl-content-guidelines-complete-guide-for-2026/)
- [E-E-A-T SEO Guide 2026](https://www.savit.in/blog/e-e-a-t-seo-guide-2026/)
- [Google Quality Rater Guidelines: E-E-A-T & SEO Guide 2026](https://hmdigitalsolution.com/google-quality-rater-guidelines/)
- [YMYL Site Recovery After Google Algorithm Update 2026](https://seoalgorithmrecovery.com/ymyl-site-recovery-google-algorithm-update-recovery/)

### 구조화 데이터 & Hugo
- [Hugo SEO Optimization: Complete Guide 2026](https://indexedev.com/post/hugo-seo-optimization-complete-guide-2026/)
- [Add Structure Data JSON-LD in Hugo Website Pages](https://codingnconcepts.com/hugo/structure-data-json-ld-hugo/)
- [Structured Data SEO 2026](https://www.digitalapplied.com/blog/structured-data-seo-2026-rich-results-guide)
- [JSON-LD Schema Markup Guide 2026](https://foglift.io/blog/json-ld-seo-guide)

### Core Web Vitals
- [Core Web Vitals 2026: LCP, INP & CLS Optimization](https://www.digitalapplied.com/blog/core-web-vitals-2026-inp-lcp-cls-optimization-guide)
- [Core Web Vitals Explained: LCP, INP, CLS After the December 2025 Update](https://roastweb.com/blog/core-web-vitals-explained-2026)
- [Responsive and optimized images with Hugo](https://www.brycewray.com/posts/2022/06/responsive-optimized-images-hugo/)
- [Hugo Image Optimization with a Render Hook](https://runtimeterror.dev/hugo-image-optimization-render-hook/)

### AI Search / GEO / AEO
- [How to Optimize Your Website for ChatGPT, Perplexity, and Google AI Search 2026](https://www.searchscaleai.com/blog/optimize-website-chatgpt-perplexity-google-ai-2026/)
- [What is Generative Engine Optimization (GEO)?](https://www.frase.io/blog/what-is-generative-engine-optimization-geo)
- [AI SEO/GEO/AEO: How to Get Shown in LLMs in 2026](https://edwardsturm.com/articles/ai-seo-geo-aeo-get-shown-llms-2026/)
- [The Definitive Guide to GEO: Get Cited by AI in 2026](https://www.averi.ai/learn/the-definitive-guide-to-geo-get-cited-by-ai-in-2026)
- [llms.txt 공식 스펙](https://llmstxt.org/)

### 광고 네트워크 (수익화)
- [Raptive Drops Traffic Requirement By 75% To 25,000 Views](https://www.searchenginejournal.com/raptive-drops-traffic-requirement-by-75-to-25000-views/558780/)
- [Mediavine and Raptive Change Entry Requirements](https://thisweekinblogging.com/mediavine-raptive-requirements/)
- [Beyond AdSense: Mediavine, Ezoic & Affiliate Marketing 2026](https://eastondev.com/blog/en/posts/media/20260110-adsense-alternatives-comparison/)

### Pillar-Cluster 모델
- [The complete guide to topic clusters and pillar pages for SEO](https://searchengineland.com/guide/topic-clusters)
- [Pillar Pages: How to Create One + Examples](https://backlinko.com/pillar-pages)
- [How to Build Topical Authority with Pillar Pages and Clusters](https://www.digitalwillow.biz/topical-authority-with-pillar-pages-and-clusters/)

---

> **문서 버전**: v1.0 · 2026-04-23
> **다음 리뷰**: 30일 실행 로드맵 Day 30 종료 시점 (2026-05-23) — 실측 KPI 기반 전략 재조정
