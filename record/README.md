# 투자/재테크 자동 퍼블리싱 — 리서치 & 전략 레포트

> 생성일: 2026-04-23 | 프로젝트: nichproject (Hugo 블로그 + auto_publisher + n8n)
> 총 11개 문서, 6,000+ 줄, 300KB+

## 읽는 순서

### 🎯 5분 안에 핵심만 — 의사결정자용
1. **[00_executive_summary.md](00_executive_summary.md)** — BLUF + Top 3 전략 + 90일 로드맵 + Top 10 액션

### 📊 시장 리서치 (6개)
| # | 파일 | 분량 | 핵심 |
|---|------|-----:|------|
| 01 | [한국 투자 블로그](01_korean_investment_blogs.md) | 390줄 | Top 20 블로그, SEO 키워드 35개, 수익화 10종 |
| 02 | [한국 투자 유튜브](02_korean_investment_youtube.md) | 549줄 | Top 30 채널, Shorts 템플릿 5종, 8-Act 롱폼 구조 |
| 03 | [글로벌 크리에이터](03_global_investment_creators.md) | 486줄 | Top 20 블로그/유튜브/뉴스레터, 영어 템플릿 3종 |
| 04 | [SEO/콘텐츠 전략](04_content_format_seo_strategy.md) | 1,179줄 | Hugo 설정, E-E-A-T, GEO/AEO, 키워드 Top 30, 30일 로드맵 |
| 05 | [숏폼 바이럴 트렌드](05_shortform_viral_trends.md) | 885줄 | 훅 40종, 스크립트 10개 (KR 5+EN 5), 플랫폼 비교 |
| 06 | [뉴스레터 수익모델](06_newsletter_monetization.md) | 472줄 | 한국/글로벌 Top 15+15, 시나리오 3종, 90일 로드맵 |

### 🔧 실행 전략 (n8n 기반)
| # | 파일 | 핵심 |
|---|------|------|
| 07 | [n8n 통합 마스터플랜](07_n8n_integration_masterplan.md) | 12개 워크플로우 카탈로그, 10개 API 엔드포인트, 8주 로드맵 |
| 08 | [bridge_api 확장 설계](08_bridge_api_expansion.md) | 12개 신규 엔드포인트, FastAPI + HMAC + Redis 큐 전환안 |
| 09 | [n8n 워크플로우 가이드](09_n8n_workflows_guide.md) | 10개 JSON import 가이드 + 크리덴셜 10종 + FAQ 10 |
| 10 | [KPI 모니터링 대시보드](10_kpi_monitoring_dashboard.md) | NSM + L1×3 + L2×9, SQL 스키마 5개, 경고 10종 |

### 🛠️ 실제 구현 산출물
- `n8n/workflows/*.json` — 10개 import 가능한 워크플로우 (weekly_dividend_report, news_react_shorts, benchmark_youtube_tracker, comparison_content, newsletter_weekly, cross_platform_post, keyword_rank_monitor, compliance_gate, comment_auto_reply, kpi_weekly_dashboard)
- `web/static/llms.txt` — AI 크롤러 가이드라인 (신규)
- `web/static/robots.txt` — AI 봇 9종 명시 허용 (업데이트)

## 핵심 결론 (00 요약)

### Bottom Line
"한국 월배당/커버드콜 + 절세계좌 에버그린" × "실데이터 E-E-A-T" × "1원본 → 5플랫폼 자동화" 3중 축.

### Top 3 전략
- **S1**: Evidence-Based Korean Tax & Dividend Hub (월배당 ETF 58.9조원 시장 [01])
- **S2**: 1 Canonical → 5 Platforms 자동 배포 (Hugo → 티스토리/네이버/X/유튜브/뉴스레터)
- **S3**: 다국어 블루오션 (ja/vi/id — 경쟁 낮고 검색 수요 있음)

### Top 3 즉시 액션
1. JSON-LD Article + FAQPage + BreadcrumbList 스키마 (Hugo partials/schema.html)
2. 저자 E-E-A-T 페이지 (/ko/about/authors/) + lastmod + canonicalURL 자동 주입
3. 5대 Pillar-Cluster 구조 (배당ETF / ISA·연금 / 미국주식 / 부동산 / 암호화폐·기타)

### 핵심 리스크
- YMYL 분야 Google 2026.03 코어 업데이트 영향 (-60~80% AI 콘텐츠) [04]
- 금감원 2026.04 5개 채널 적발 (리딩방/매매 프로그램) [02][05]
- 한글 파일명 URL 인코딩 이슈 (slug 영문화 필요)

## 프로젝트 연동 포인트

### auto_publisher/ (Python)
- `content_generator.py` — Front matter 확장 (faq, author, lastmod)
- `topic_manager.py` — 35개 키워드 시드 [01] + 계절성 캘린더 [04]
- `publishers/hugo.py` — 쿠팡/CPA 링크 + 면책 자동 주입

### web/ (Hugo)
- `hugo.toml` — sitemap/minify/imaging 블록 추가 [04]
- `layouts/partials/schema.html` — JSON-LD
- `static/llms.txt` + `static/robots.txt` — AI 크롤러 대응

### n8n/
- `workflows/` — 신규 10개 + 기존 daily_publisher.json 리팩토
- `bridge_api.py` — 12개 엔드포인트 추가 + FastAPI 전환 고려

## 구현 로드맵 (8주 요약)

| Week | 핵심 작업 |
|------|----------|
| W1 | Bridge API 안정화 + compliance gate 가동 |
| W2 | 월배당 ETF 주간 리포트 + Pillar 5종 런칭 |
| W3 | KPI 수집 pipeline + Discord 알림 |
| W4 | Shorts 파이프라인 (AI 스크립트 → ElevenLabs → 자동 업로드) |
| W5 | 뉴스레터 Stibee 연동 + 주간 발송 |
| W6 | 다중 플랫폼 cross-post (X + IG) |
| W7 | YouTube 댓글 자동 응답 + KPI 대시보드 v1.0 |
| W8 | 런칭 리허설 + 실운영 전환 |

## 인용 레이블
각 주장은 `[00]~[10]` 형식으로 원본 리포트 인용됨. 허구 통계 없음.
