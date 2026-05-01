# 08. bridge_api.py 확장 설계서 — n8n 투자/재테크 자동화 워크플로우 Bridge v2

> **작성일**: 2026-04-23
> **작성자**: Backend Architect Agent (oh-my-claudecode)
> **대상 파일**: `/home/mh/ocstorage/workspace/nichproject/n8n/bridge_api.py`
> **현 버전**: v1 (HTTPServer 기반, 6개 엔드포인트)
> **목표 버전**: v2 (FastAPI 기반, 18개 엔드포인트, HMAC 인증, BackgroundTasks 비동기)
> **전략 근거**: `record/00_executive_summary.md` S1·S2·S3, `record/02`, `record/05`, `record/06`

---

## 0. Executive Summary (3분 요약)

현 `bridge_api.py`는 파이썬 표준 라이브러리 `HTTPServer` + 동기 `subprocess.run()` 기반으로 구현되어 있어, (1) 한 요청이 최대 15분(`make-video` 900초) 블로킹하는 **단일 스레드 직렬화 문제**, (2) 인증 부재로 `host.docker.internal:8765` 노출 시 **RCE 리스크**, (3) POST/GET이 구분되지 않는 **스키마 비정합성**, (4) 서브프로세스 호출 오버헤드(평균 +1.2초)로 인한 **비효율**이 있다. 본 설계서는 **FastAPI + Pydantic + BackgroundTasks + HMAC 인증**으로의 마이그레이션을 전제로 12개 신규 엔드포인트를 명세하며, `record/00 S1~S3` (Pillar·Comparison·Shorts·Newsletter·GSC·YouTube Analytics·Benchmark·Compliance·KPI·Social) 전략과 1:1 매핑한다. 전환 비용은 약 3~4일, 이후 워크플로우 확장 속도는 2~3배 개선된다.

---

## 1. 현재 bridge_api.py 리뷰

### 1.1 파일 구조 요약

| 항목 | 값 |
|------|---|
| 라인 수 | 398 |
| 엔드포인트 | 6 GET + 6 ROUTES (lambda) |
| 서버 | `http.server.HTTPServer` (stdlib, 단일 스레드) |
| 인증 | **없음** |
| 타임아웃 | 최대 900초 (make-video) |
| 로깅 | `log_message`를 `pass`로 override (출력 억제) |
| 외부 의존 | `subprocess.run` × 6 (모두 `VENV_PYTHON -m auto_publisher.main ...`) |

### 1.2 식별된 설계 결함 (심각도 순)

| # | 영역 | 결함 | 심각도 | 영향 |
|---|------|------|:------:|------|
| D1 | **인증** | 토큰/서명 검증 없음. `host.docker.internal` 바인딩(`0.0.0.0`)으로 호스트 네트워크 노출 | 🔴 High | 원격 공격자가 `curl http://HOST:8765/publish`로 AdSense/YouTube 계정에 임의 발행 가능 |
| D2 | **동시성** | `HTTPServer`는 단일 스레드. `make-video` 실행 중이면 `/health`도 블로킹 | 🔴 High | n8n 재시도/모니터링 워크플로우가 한 포스트 생성으로 15분 마비 |
| D3 | **GET/POST 미분리** | `do_POST`가 `do_GET`을 그대로 호출 → 바디 파싱 로직 없음 | 🟠 Mid | POST로 JSON payload 전달 불가. 모든 파라미터가 query string으로 제한 |
| D4 | **타임아웃 하드코딩** | subprocess 타임아웃이 함수별 상수(30/120/180/300/600/900) → 재시도 시 누적 타임아웃 계산 불가 | 🟠 Mid | n8n Wait 노드와 어긋나 false-negative 빈번 |
| D5 | **에러 레벨링** | `stderr[-500:]`로 자르면 multi-line traceback 원인 구간 손실 | 🟡 Low | 디버깅 시 원인 추적 실패 |
| D6 | **로그 억제** | `log_message`가 `pass`여서 접근 로그 없음 | 🟡 Low | 누가 언제 호출했는지 감사(audit) 불가 |
| D7 | **serialization** | `default=str`로 모든 타입 fallback → 날짜/Decimal이 문자열화되어 n8n JSON 노드 파싱 이상 | 🟡 Low | `publish_market_post` 결과에서 timestamp 타입 혼선 |
| D8 | **서브프로세스 오버헤드** | 매 호출마다 Python 인터프리터 부팅(평균 +1.2초) + `auto_publisher.main` import chain 재실행 | 🟠 Mid | 고빈도 엔드포인트(`/analytics/*`, `/kpi/*`)에 치명적 |
| D9 | **의존성 순환 리스크** | `bridge_api.py`가 `auto_publisher.dynamic_topics`를 직접 import → 모듈 로딩 실패 시 서버 기동 불가 | 🟠 Mid | 단일 토픽 모듈 버그로 전체 API 다운 |
| D10 | **상태 저장소 부재** | 비동기 작업(`make-video`)의 진행 상태를 조회할 수 없음 | 🟠 Mid | n8n이 "끝났는지" 폴링할 방법이 없음 → 반드시 HTTP 응답 끝까지 대기 |

### 1.3 개선 원칙 (본 설계서 전반에 적용)

1. **Security-first**: 모든 변경 엔드포인트(`POST /publish/*`, `POST /newsletter/send`, `POST /social/cross-post`)는 HMAC-SHA256 서명 필수.
2. **Async-by-default**: `>5초` 소요 예상 작업은 `202 Accepted + job_id` 패턴으로 분리.
3. **Schema-first**: Pydantic 모델로 Request/Response 계약을 코드와 OpenAPI 모두에 단일 소스.
4. **Observability**: 모든 엔드포인트에 `X-Request-ID` 주입, JSON 구조화 로그, `/metrics` (Prometheus) 노출.
5. **Graceful degradation**: 외부 API(GSC·YouTube·Stibee·Beehiiv) 실패 시 circuit breaker로 60초 차단.

---

## 2. 확장 엔드포인트 명세 (12개)

### 공통 규칙

- **Base URL**: `http://host.docker.internal:8765`
- **인증**: `X-Bridge-Signature: sha256=<hmac(body, BRIDGE_SECRET)>` (변경 API는 필수, GET은 선택적 rate-limit 토큰)
- **Content-Type**: `application/json; charset=utf-8`
- **Request-ID**: 요청 시 `X-Request-ID` 없으면 서버가 UUIDv4 주입 → 응답에 동일 헤더 반환
- **에러 포맷**: `{"success": false, "error": {"code": "E_XXX", "message": "...", "details": {...}}}`
- **성공 포맷**: `{"success": true, "data": {...}, "meta": {"request_id": "...", "elapsed_ms": 123, "ts": "2026-04-23T12:34:56Z"}}`
- **비동기 작업**: 응답 `202` + `{"job_id": "jbx_...", "status_url": "/jobs/jbx_..."}` 패턴

---

### 2.1 `POST /generate/pillar` — Pillar 콘텐츠 생성

**전략 매핑**: `record/00` Action #3 (5대 Pillar Page), `record/02` Insight #4, `record/06` 시나리오 C.

| 항목 | 값 |
|------|---|
| Method | POST |
| Path | `/generate/pillar` |
| Query | (없음) |
| 인증 | HMAC 필수 |
| 실행 시간 | 40~90초 (동기) 또는 비동기(`async=true`) |

#### Request Body

```json
{
  "category": "etf",
  "primary_keyword": "SCHD ETF 배당 완벽 가이드",
  "long_tail_keywords": [
    "SCHD 배당성장률 10년",
    "SCHD 월배당 아님",
    "SCHD vs VOO 수익률"
  ],
  "target_length_chars": 8000,
  "lang": "ko",
  "include_charts": true,
  "include_faq": true,
  "cluster_links": [
    "/ko/blog/isa-schd-tax-guide/",
    "/ko/blog/jepi-vs-schd/"
  ],
  "publish_immediately": false,
  "async": false
}
```

#### Response Body (200)

```json
{
  "success": true,
  "data": {
    "title": "SCHD ETF 배당 완벽 가이드 2026 — 10년 배당성장률 11.8%의 비밀",
    "slug": "schd-etf-dividend-complete-guide-2026",
    "content_html": "<h2>...</h2>...",
    "meta_description": "...",
    "tags": ["SCHD", "배당성장", "ETF"],
    "word_count": 8214,
    "schema_faq": [{"q": "...", "a": "..."}],
    "charts": ["/charts/schd_dividend_growth_10y.png"],
    "published": false,
    "hugo_filepath": null,
    "compliance": {"pass": true, "warnings": []}
  },
  "meta": {"request_id": "req_01HWX...", "elapsed_ms": 48210, "ts": "..."}
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_INVALID_CATEGORY` | 422 | `category`가 `{etf, dividend, tax, realestate, basics}` 외 |
| `E_LLM_TIMEOUT` | 504 | OpenRouter 120초 초과 |
| `E_COMPLIANCE_FAIL` | 409 | 금칙어 필터 검출 → `details.violations` 포함 |
| `E_LENGTH_BELOW_MIN` | 422 | `word_count < target_length_chars * 0.8` |
| `E_HMAC_INVALID` | 401 | 서명 불일치 |

#### Python 구현 skeleton

```python
# n8n/routes/generate.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, constr
from typing import Literal
from n8n.deps import require_hmac, get_job_store
from auto_publisher.content_generator import generate_blog_post
from auto_publisher.compliance import check_content
from auto_publisher.publishers.hugo import HugoPublisher

router = APIRouter(prefix="/generate", tags=["generate"])

class PillarRequest(BaseModel):
    category: Literal["etf", "dividend", "tax", "realestate", "basics"]
    primary_keyword: constr(min_length=3, max_length=80)
    long_tail_keywords: list[str] = Field(default_factory=list, max_items=20)
    target_length_chars: int = Field(default=8000, ge=3000, le=15000)
    lang: Literal["ko", "en", "ja", "vi", "id"] = "ko"
    include_charts: bool = True
    include_faq: bool = True
    cluster_links: list[str] = []
    publish_immediately: bool = False
    async_: bool = Field(default=False, alias="async")

@router.post("/pillar", dependencies=[Depends(require_hmac)])
async def generate_pillar(
    req: PillarRequest,
    bg: BackgroundTasks,
    jobs=Depends(get_job_store),
):
    if req.async_:
        job = jobs.create(kind="pillar", payload=req.model_dump())
        bg.add_task(_run_pillar_job, job.id, req)
        return {"success": True, "data": {"job_id": job.id,
                                          "status_url": f"/jobs/{job.id}"}}
    post = generate_blog_post(
        topic=req.primary_keyword,
        keywords=req.long_tail_keywords,
        lang=req.lang,
        category=req.category,
        content_type="pillar",
        target_length=req.target_length_chars,
    )
    comp = check_content(post["content_html"], lang=req.lang)
    if not comp["pass"]:
        raise HTTPException(409, {"code": "E_COMPLIANCE_FAIL",
                                   "violations": comp["violations"]})
    hugo_path = None
    if req.publish_immediately:
        pub = HugoPublisher(lang=req.lang)
        hugo_path = pub.publish(**post, categories=[req.category, "pillar"])["filepath"]
    return {"success": True, "data": {**post, "published": req.publish_immediately,
                                       "hugo_filepath": hugo_path, "compliance": comp}}
```

---

### 2.2 `POST /generate/comparison` — 비교 분석 글 생성 (A vs B)

**전략 매핑**: `record/00` Action #4 (비교 5건 퀵윈), `record/02` Insight #4.

| 항목 | 값 |
|------|---|
| Method | POST |
| Path | `/generate/comparison` |
| 인증 | HMAC 필수 |
| 실행 시간 | 30~60초 |

#### Request Body

```json
{
  "item_a": {"ticker": "SCHD", "label": "SCHD"},
  "item_b": {"ticker": "VOO", "label": "VOO"},
  "comparison_dimensions": [
    "dividend_yield", "total_return_10y",
    "expense_ratio", "tax_efficiency_kr", "volatility"
  ],
  "lang": "ko",
  "include_live_data": true,
  "tone": "analytical",
  "publish_immediately": false
}
```

#### Response Body (200)

```json
{
  "success": true,
  "data": {
    "title": "SCHD vs VOO 완벽 비교 2026 — 배당 성장형 vs 시장 추종, 당신에겐 어느 쪽?",
    "slug": "schd-vs-voo-2026-comparison",
    "content_html": "...",
    "comparison_table": {
      "dividend_yield": {"SCHD": 3.52, "VOO": 1.28, "winner": "SCHD"},
      "total_return_10y_pct": {"SCHD": 201.4, "VOO": 232.1, "winner": "VOO"}
    },
    "verdict_ko": "장기 Total Return은 VOO 우위, 현금흐름은 SCHD 우위",
    "charts": ["/charts/schd_vs_voo_return.png"],
    "word_count": 4120
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_TICKER_NOT_FOUND` | 422 | yfinance/KRX에 존재하지 않는 티커 |
| `E_DATA_STALE` | 503 | `market-cache.json`의 `item_a/b` 데이터가 72h 경과 |
| `E_LLM_JSON_PARSE` | 502 | Gemini가 `comparison_table` JSON 파싱 실패 |

#### Python 구현 skeleton

```python
class ComparisonItem(BaseModel):
    ticker: str
    label: str | None = None

class ComparisonRequest(BaseModel):
    item_a: ComparisonItem
    item_b: ComparisonItem
    comparison_dimensions: list[str] = Field(..., min_items=2, max_items=8)
    lang: Literal["ko", "en"] = "ko"
    include_live_data: bool = True
    tone: Literal["analytical", "conversational"] = "analytical"
    publish_immediately: bool = False

@router.post("/comparison", dependencies=[Depends(require_hmac)])
def generate_comparison(req: ComparisonRequest):
    from auto_publisher.market_cache import load_ticker
    from auto_publisher.content_generator import generate_comparison_post  # 신규

    a_data = load_ticker(req.item_a.ticker, max_age_hours=72)
    b_data = load_ticker(req.item_b.ticker, max_age_hours=72)
    if not a_data or not b_data:
        raise HTTPException(503, {"code": "E_DATA_STALE"})

    post = generate_comparison_post(
        a=req.item_a.model_dump() | {"data": a_data},
        b=req.item_b.model_dump() | {"data": b_data},
        dimensions=req.comparison_dimensions,
        lang=req.lang, tone=req.tone,
    )
    hugo_path = None
    if req.publish_immediately:
        pub = HugoPublisher(lang=req.lang)
        hugo_path = pub.publish(
            title=post["title"], content_html=post["content_html"],
            tags=post.get("tags", []), categories=["비교분석", "ETF"],
            meta_description=post.get("meta_description", ""),
            content_type="comparison",
        )["filepath"]
    return {"success": True, "data": {**post, "hugo_filepath": hugo_path}}
```

---

### 2.3 `POST /generate/news-react` — 뉴스 리액트 Shorts 스크립트

**전략 매핑**: `record/05` §6 템플릿 #2, `record/02` Insight #1.

| 항목 | 값 |
|------|---|
| Method | POST |
| Path | `/generate/news-react` |
| 인증 | HMAC 필수 |
| 실행 시간 | 8~20초 |

#### Request Body

```json
{
  "news": {
    "headline": "연준 3회 연속 금리 동결, 파월 '데이터 우선'",
    "source_url": "https://www.reuters.com/...",
    "published_at": "2026-04-22T18:30:00Z",
    "summary": "FOMC가 기준금리를 3.5~3.75%로 동결..."
  },
  "target_platform": "youtube_shorts",
  "target_duration_sec": 45,
  "angle": "portfolio_impact",
  "lang": "ko",
  "voice_profile": "analyst_calm"
}
```

#### Response Body

```json
{
  "success": true,
  "data": {
    "script": {
      "hook_sec": [0, 3],
      "hook_text": "연준이 또 동결했습니다. 포트폴리오에서 당장 바꿔야 할 3가지.",
      "beats": [
        {"range": [3, 18], "text": "...", "overlay": "3.5~3.75% 동결"},
        {"range": [18, 35], "text": "...", "b_roll": "chart:tlt_ytd"},
        {"range": [35, 45], "text": "...", "cta": "팔로우 + 풀영상 링크"}
      ],
      "captions_srt": "WEBVTT\n...",
      "hashtags": ["#FOMC", "#금리동결", "#포트폴리오"]
    },
    "compliance": {"pass": true, "disclaimers_auto_injected": true},
    "estimated_tts_sec": 43.2
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_STALE_NEWS` | 422 | `published_at`이 24h 경과 (리액트 시효 초과) |
| `E_DURATION_OUT_OF_RANGE` | 422 | `target_duration_sec`이 `[15, 60]` 범위 밖 |
| `E_ANGLE_UNSUPPORTED` | 422 | `angle` 값이 허용 목록 밖 |

#### Python 구현 skeleton

```python
class NewsPayload(BaseModel):
    headline: constr(min_length=10, max_length=200)
    source_url: str
    published_at: str  # ISO8601
    summary: constr(min_length=50, max_length=2000)

class NewsReactRequest(BaseModel):
    news: NewsPayload
    target_platform: Literal["youtube_shorts", "tiktok", "reels"] = "youtube_shorts"
    target_duration_sec: int = Field(default=45, ge=15, le=60)
    angle: Literal["portfolio_impact", "contrarian", "beginner_explainer",
                   "historical_parallel"] = "portfolio_impact"
    lang: Literal["ko", "en"] = "ko"
    voice_profile: str = "analyst_calm"

@router.post("/news-react", dependencies=[Depends(require_hmac)])
def generate_news_react(req: NewsReactRequest):
    from datetime import datetime, timezone, timedelta
    pub_at = datetime.fromisoformat(req.news.published_at.replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - pub_at > timedelta(hours=24):
        raise HTTPException(422, {"code": "E_STALE_NEWS"})

    from auto_publisher.video_script import generate_news_react_script  # 신규
    script = generate_news_react_script(
        headline=req.news.headline, summary=req.news.summary,
        source_url=req.news.source_url, angle=req.angle,
        duration_sec=req.target_duration_sec, lang=req.lang,
        platform=req.target_platform,
    )
    from auto_publisher.compliance import check_content, inject_disclaimer
    comp = check_content(script["full_text"], lang=req.lang)
    if not comp["pass"]:
        script = inject_disclaimer(script, comp["violations"], lang=req.lang)
    return {"success": True,
            "data": {"script": script, "compliance": comp,
                     "estimated_tts_sec": script.get("estimated_tts_sec", 0)}}
```

---

### 2.4 `POST /generate/monthly-dividend` — 월배당 ETF 리포트

**전략 매핑**: `record/00` S1·Action #3 (월배당·커버드콜 Pillar), `record/02` #9.

| 항목 | 값 |
|------|---|
| Method | POST |
| Path | `/generate/monthly-dividend` |
| 인증 | HMAC 필수 |
| 실행 시간 | 60~120초 |

#### Request Body

```json
{
  "universe": ["JEPI", "JEPQ", "SCHD", "SCHY", "DIVO", "QYLD"],
  "target_month": "2026-05",
  "ranking_criteria": {
    "dividend_yield_weight": 0.4,
    "stability_weight": 0.3,
    "tax_efficiency_kr_weight": 0.3
  },
  "include_krx_alternatives": true,
  "lang": "ko",
  "publish_immediately": false,
  "include_tax_scenario": {
    "isa_balance_krw": 20000000,
    "regular_account_balance_krw": 30000000
  }
}
```

#### Response Body

```json
{
  "success": true,
  "data": {
    "title": "2026년 5월 월배당 ETF 추천 TOP 6 — ISA/일반계좌별 세후수익 비교",
    "ranking": [
      {"rank": 1, "ticker": "JEPI", "score": 0.84, "fwd_yield": 7.2,
       "payout_schedule": "monthly", "commentary": "..."},
      {"rank": 2, "ticker": "SCHD", "score": 0.81, "fwd_yield": 3.6, ...}
    ],
    "krx_alternatives": ["TIGER 미국배당다우존스", "KODEX 미국S&P500TR(H)"],
    "tax_scenario_result": {
      "isa_after_tax_krw": 1345000,
      "regular_after_tax_krw": 1897000,
      "delta_krw": 552000
    },
    "content_html": "...",
    "hugo_filepath": null
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_UNIVERSE_TOO_SMALL` | 422 | `universe.length < 3` |
| `E_WEIGHT_SUM_INVALID` | 422 | `ranking_criteria` 가중치 합 ≠ 1.0 ± 0.01 |
| `E_TICKER_DATA_MISSING` | 503 | universe 중 50% 이상 데이터 결손 |

#### Python 구현 skeleton

```python
class RankingCriteria(BaseModel):
    dividend_yield_weight: float = Field(ge=0, le=1)
    stability_weight: float = Field(ge=0, le=1)
    tax_efficiency_kr_weight: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _check_sum(self):
        s = (self.dividend_yield_weight + self.stability_weight
             + self.tax_efficiency_kr_weight)
        if abs(s - 1.0) > 0.01:
            raise ValueError("weights must sum to 1.0")
        return self

class MonthlyDividendRequest(BaseModel):
    universe: list[str] = Field(..., min_items=3, max_items=30)
    target_month: constr(regex=r"^\d{4}-\d{2}$")
    ranking_criteria: RankingCriteria
    include_krx_alternatives: bool = True
    lang: Literal["ko", "en"] = "ko"
    publish_immediately: bool = False
    include_tax_scenario: dict | None = None

@router.post("/monthly-dividend", dependencies=[Depends(require_hmac)])
def generate_monthly_dividend(req: MonthlyDividendRequest):
    from auto_publisher.market_cache import load_ticker_batch
    from auto_publisher.ranking import rank_monthly_dividend  # 신규
    from auto_publisher.tax_kr import simulate_isa_vs_regular  # 신규

    data = load_ticker_batch(req.universe, max_age_hours=168)
    if len([d for d in data.values() if d]) < len(req.universe) * 0.5:
        raise HTTPException(503, {"code": "E_TICKER_DATA_MISSING"})

    ranking = rank_monthly_dividend(data, req.ranking_criteria.model_dump())
    tax_result = None
    if req.include_tax_scenario:
        tax_result = simulate_isa_vs_regular(
            ranking=ranking, lang=req.lang, **req.include_tax_scenario)
    from auto_publisher.content_generator import generate_monthly_dividend_post
    post = generate_monthly_dividend_post(
        ranking=ranking, target_month=req.target_month,
        tax_result=tax_result, lang=req.lang,
        include_krx=req.include_krx_alternatives)
    return {"success": True, "data": {**post, "ranking": ranking,
                                       "tax_scenario_result": tax_result}}
```

---

### 2.5 `GET /analytics/gsc?days=7` — Google Search Console 요약

**전략 매핑**: `record/00` KPI 프레임워크 (임프레션·평균 순위).

| 항목 | 값 |
|------|---|
| Method | GET |
| Path | `/analytics/gsc` |
| Query | `days` (1~90, 기본 7), `site` (기본 `sc-domain:investiqs.net`), `lang` (필터) |
| 인증 | GET 토큰(`X-Bridge-Token`) 권장 |
| 실행 시간 | 1~3초 (캐시 히트 시 ~50ms) |

#### Response Body

```json
{
  "success": true,
  "data": {
    "range": {"from": "2026-04-16", "to": "2026-04-23"},
    "totals": {"clicks": 241, "impressions": 12480, "ctr": 0.0193, "avg_position": 11.4},
    "top_queries": [
      {"query": "SCHD 배당금", "clicks": 48, "impressions": 2100, "position": 3.2},
      {"query": "ISA 연금저축 비교", "clicks": 31, "impressions": 1840, "position": 6.8}
    ],
    "top_pages": [
      {"url": "/ko/blog/schd-dividend-guide/", "clicks": 82, "impressions": 3400}
    ],
    "deltas_vs_prev_period": {"clicks_pct": 22.4, "impressions_pct": 15.1},
    "alerts": [
      {"type": "rank_drop", "query": "covered call ETF",
       "from_pos": 6.2, "to_pos": 14.8, "severity": "high"}
    ]
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_GSC_AUTH_EXPIRED` | 401 | GSC OAuth 토큰 만료 |
| `E_DAYS_OUT_OF_RANGE` | 422 | days < 1 or > 90 |
| `E_QUOTA_EXCEEDED` | 429 | GSC API 일일 쿼터 소진 |

#### Python 구현 skeleton

```python
from fastapi import Query
from n8n.cache import ttl_cache

@router.get("/analytics/gsc")
@ttl_cache(ttl_sec=600, key_fn=lambda **kw: f"gsc:{kw}")
def analytics_gsc(
    days: int = Query(7, ge=1, le=90),
    site: str = Query("sc-domain:investiqs.net"),
    lang: str | None = Query(None),
):
    from auto_publisher.integrations.gsc import query_search_analytics
    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=days)
    try:
        totals, queries, pages = query_search_analytics(
            site=site, start=start, end=end, lang_filter=lang)
    except Exception as e:
        if "401" in str(e):
            raise HTTPException(401, {"code": "E_GSC_AUTH_EXPIRED"})
        if "429" in str(e):
            raise HTTPException(429, {"code": "E_QUOTA_EXCEEDED"})
        raise
    prev_totals, _, _ = query_search_analytics(
        site=site, start=start - timedelta(days=days),
        end=start - timedelta(days=1), lang_filter=lang)
    deltas = {
        "clicks_pct": _pct_delta(totals["clicks"], prev_totals["clicks"]),
        "impressions_pct": _pct_delta(totals["impressions"], prev_totals["impressions"]),
    }
    from auto_publisher.integrations.gsc_alerts import detect_rank_drops
    alerts = detect_rank_drops(current=queries, prev_days=days)
    return {"success": True, "data": {
        "range": {"from": str(start), "to": str(end)},
        "totals": totals, "top_queries": queries[:20],
        "top_pages": pages[:20], "deltas_vs_prev_period": deltas,
        "alerts": alerts,
    }}
```

---

### 2.6 `GET /analytics/youtube?channel=...` — YouTube Analytics 요약

**전략 매핑**: `record/00` KPI (완시청률·팔로우 전환), `record/02` #10, `record/05` §11 INSIGHT #1.

| 항목 | 값 |
|------|---|
| Method | GET |
| Path | `/analytics/youtube` |
| Query | `channel` (UC... 또는 handle), `days` (1~90), `kind` (`shorts`/`long`/`all`) |
| 인증 | 토큰 |
| 실행 시간 | 2~5초 |

#### Response Body

```json
{
  "success": true,
  "data": {
    "channel": "UCxxxxxxxxxxxx",
    "range": {"from": "2026-04-16", "to": "2026-04-23"},
    "summary": {
      "views": 14230, "watch_time_min": 2480,
      "subs_gained": 58, "subs_lost": 9, "rpm_usd": 1.82
    },
    "by_kind": {
      "shorts": {"views": 11520, "avg_view_pct": 62.4, "follow_conversion_rate": 0.0042},
      "long": {"views": 2710, "avg_view_duration_sec": 412, "ctr": 0.064}
    },
    "top_videos": [
      {"video_id": "abc123", "title": "...",
       "views": 1240, "avg_view_pct": 71.0, "kind": "shorts"}
    ],
    "alerts": [
      {"type": "retention_drop", "video_id": "xyz", "from": 0.68, "to": 0.41}
    ]
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_YT_AUTH_EXPIRED` | 401 | YouTube OAuth refresh 실패 |
| `E_CHANNEL_NOT_FOUND` | 404 | channel ID/handle 해석 실패 |
| `E_QUOTA_EXCEEDED` | 429 | YouTube Data API v3 쿼터 소진 |

#### Python 구현 skeleton

```python
@router.get("/analytics/youtube")
@ttl_cache(ttl_sec=300)
def analytics_youtube(
    channel: str = Query(..., min_length=3),
    days: int = Query(7, ge=1, le=90),
    kind: Literal["shorts", "long", "all"] = "all",
):
    from auto_publisher.integrations.youtube_analytics import (
        resolve_channel_id, fetch_summary, fetch_by_kind, fetch_top_videos,
        detect_retention_drops,
    )
    channel_id = resolve_channel_id(channel)
    if not channel_id:
        raise HTTPException(404, {"code": "E_CHANNEL_NOT_FOUND"})
    from datetime import date, timedelta
    end, start = date.today(), date.today() - timedelta(days=days)
    summary = fetch_summary(channel_id, start, end)
    by_kind = fetch_by_kind(channel_id, start, end) if kind == "all" \
        else {kind: fetch_by_kind(channel_id, start, end, only=kind)}
    top = fetch_top_videos(channel_id, start, end, kind=kind, limit=10)
    alerts = detect_retention_drops(channel_id, days=days)
    return {"success": True, "data": {
        "channel": channel_id,
        "range": {"from": str(start), "to": str(end)},
        "summary": summary, "by_kind": by_kind,
        "top_videos": top, "alerts": alerts,
    }}
```

---

### 2.7 `GET /benchmark/channels` — 벤치마크 채널 신규 영상 리스트

**전략 매핑**: `record/00` Action #10, `record/02` Insight #10.

| 항목 | 값 |
|------|---|
| Method | GET |
| Path | `/benchmark/channels` |
| Query | `since_hours` (기본 24, 1~168), `group` (`korean_youtube`/`korean_newsletter`/`global`) |
| 인증 | 토큰 |
| 실행 시간 | 3~10초 |

#### Response Body

```json
{
  "success": true,
  "data": {
    "fetched_at": "2026-04-23T09:00:00+09:00",
    "group": "korean_youtube",
    "channels": [
      {
        "handle": "@shukaworld", "name": "슈카월드", "subscribers": 3620000,
        "new_videos": [
          {"video_id": "abc", "title": "엔비디아 다음 분기 실적 미리보기",
           "published_at": "2026-04-23T06:12:00Z",
           "duration_sec": 1320, "views_24h": 82000,
           "thumbnail_url": "...", "is_shorts": false,
           "title_pattern": "B.숫자 전망형"}
        ]
      }
    ],
    "trending_topics": [
      {"topic": "엔비디아 HBM4", "mentions": 7, "sentiment": "positive"},
      {"topic": "파월 FOMC", "mentions": 5, "sentiment": "neutral"}
    ]
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_GROUP_UNKNOWN` | 422 | group 허용 목록 외 |
| `E_SOURCE_UNAVAILABLE` | 503 | 일부 채널 RSS 실패 → `details.partial_failure` |

#### Python 구현 skeleton

```python
@router.get("/benchmark/channels")
@ttl_cache(ttl_sec=900)
def benchmark_channels(
    since_hours: int = Query(24, ge=1, le=168),
    group: Literal["korean_youtube", "korean_newsletter",
                    "global", "all"] = "korean_youtube",
):
    from auto_publisher.benchmark import (
        load_channel_config, fetch_new_videos, extract_title_pattern,
        aggregate_trending,
    )
    configs = load_channel_config(group)  # JSON: 슈카/삼프로/월부/부읽남/김작가...
    from datetime import datetime, timezone, timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    channels_out, failures = [], []
    for cfg in configs:
        try:
            vids = fetch_new_videos(cfg["handle"], since=since)
            for v in vids:
                v["title_pattern"] = extract_title_pattern(v["title"])
            channels_out.append({**cfg, "new_videos": vids})
        except Exception as e:
            failures.append({"channel": cfg["handle"], "error": str(e)[:120]})
    trending = aggregate_trending([v for ch in channels_out
                                    for v in ch["new_videos"]])
    resp = {"success": True, "data": {
        "fetched_at": datetime.now().isoformat(),
        "group": group, "channels": channels_out,
        "trending_topics": trending,
    }}
    if failures:
        resp["data"]["partial_failure"] = failures
    return resp
```

---

### 2.8 `POST /compliance/check` — 콘텐츠 금칙어/면책 검증

**전략 매핑**: `record/00` Action #9·Risk R2, `record/05` §13, `record/02` §8 법적 리스크.

| 항목 | 값 |
|------|---|
| Method | POST |
| Path | `/compliance/check` |
| 인증 | HMAC |
| 실행 시간 | 50~300ms |

#### Request Body

```json
{
  "content": {"title": "...", "html": "<h2>...</h2>..."},
  "lang": "ko",
  "channel": "blog",
  "strictness": "strict",
  "auto_fix": true
}
```

#### Response Body

```json
{
  "success": true,
  "data": {
    "pass": false,
    "violations": [
      {"rule": "FORBIDDEN_GUARANTEE", "span": [120, 135],
       "matched": "100% 수익 보장", "severity": "critical",
       "fix_suggestion": "안정적인 배당 실적"},
      {"rule": "MISSING_DISCLAIMER", "severity": "high",
       "fix_suggestion": "하단 면책 문구 자동 삽입 가능"}
    ],
    "auto_fixed_content": {"title": "...", "html": "..."},
    "disclaimer_injected": true,
    "risk_score": 0.78
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_CONTENT_TOO_LARGE` | 413 | `content.html > 200KB` |
| `E_RULESET_NOT_FOUND` | 422 | lang × channel 조합의 ruleset 부재 |

#### Python 구현 skeleton

```python
class ComplianceCheckRequest(BaseModel):
    content: dict
    lang: Literal["ko", "en", "ja", "vi", "id"] = "ko"
    channel: Literal["blog", "shorts", "newsletter", "social"] = "blog"
    strictness: Literal["lenient", "standard", "strict"] = "strict"
    auto_fix: bool = True

@router.post("/compliance/check", dependencies=[Depends(require_hmac)])
def compliance_check(req: ComplianceCheckRequest):
    html = req.content.get("html", "")
    if len(html) > 200_000:
        raise HTTPException(413, {"code": "E_CONTENT_TOO_LARGE"})
    from auto_publisher.compliance import (
        load_ruleset, scan_violations, apply_fixes, inject_disclaimer,
    )
    rules = load_ruleset(lang=req.lang, channel=req.channel,
                          strictness=req.strictness)
    violations = scan_violations(html, rules=rules,
                                  title=req.content.get("title", ""))
    fixed_content = None
    disclaimer_injected = False
    if req.auto_fix and violations:
        fixed_html = apply_fixes(html, violations, rules)
        fixed_html = inject_disclaimer(fixed_html, lang=req.lang,
                                        channel=req.channel)
        fixed_content = {"title": req.content.get("title", ""),
                         "html": fixed_html}
        disclaimer_injected = True
    risk = sum(v.severity_weight for v in violations) / max(len(rules), 1)
    return {"success": True, "data": {
        "pass": len([v for v in violations if v.severity in ("critical", "high")]) == 0,
        "violations": [v.to_dict() for v in violations],
        "auto_fixed_content": fixed_content,
        "disclaimer_injected": disclaimer_injected,
        "risk_score": round(risk, 3),
    }}
```

---

### 2.9 `POST /newsletter/send` — Stibee/Beehiiv API 발송

**전략 매핑**: `record/00` Action #6·S2, `record/06` §4·§6.

| 항목 | 값 |
|------|---|
| Method | POST |
| Path | `/newsletter/send` |
| 인증 | HMAC 필수 (변경 작업) |
| 실행 시간 | 1~10초 (발송 enqueue), 실제 발송은 Stibee 큐 |

#### Request Body

```json
{
  "provider": "stibee",
  "list_id": "L_6f9b...",
  "subject": {"a": "3%만 알고 있는 월배당 ETF 5선",
              "b": "이번 달, 월세 만드는 ETF 5개 공개"},
  "preheader": "JEPI/SCHD/DIVO 세후수익 비교",
  "content_html": "<html>...</html>",
  "segment": {"tags": ["active_30d"], "exclude_tags": ["unsubscribed"]},
  "ab_test": {"sample_pct": 10, "winner_metric": "open_rate", "wait_min": 120},
  "schedule_at": "2026-04-25T07:00:00+09:00",
  "test_email_list": ["ops@investiqs.net"],
  "dry_run": false
}
```

#### Response Body

```json
{
  "success": true,
  "data": {
    "campaign_id": "C_1a2b3c",
    "status": "scheduled",
    "scheduled_at": "2026-04-25T07:00:00+09:00",
    "audience_size": 8240,
    "ab_test": {"variant_a_size": 412, "variant_b_size": 412,
                 "winner_send_size": 7416},
    "preview_urls": [
      {"variant": "a", "url": "https://stibee.com/preview/..."}
    ]
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_PROVIDER_UNSUPPORTED` | 422 | `provider`가 `{stibee, beehiiv}` 외 |
| `E_LIST_NOT_FOUND` | 404 | list_id 해석 실패 |
| `E_SUBJECT_TOO_LONG` | 422 | subject가 80자 초과 |
| `E_SCHEDULE_IN_PAST` | 422 | `schedule_at < now + 5min` |
| `E_PROVIDER_5XX` | 502 | Stibee/Beehiiv 5xx → 지수 backoff 후 재시도 |

#### Python 구현 skeleton

```python
class NewsletterSendRequest(BaseModel):
    provider: Literal["stibee", "beehiiv"]
    list_id: str
    subject: dict
    preheader: constr(max_length=110) = ""
    content_html: str
    segment: dict = Field(default_factory=dict)
    ab_test: dict | None = None
    schedule_at: str | None = None
    test_email_list: list[str] = []
    dry_run: bool = False

@router.post("/newsletter/send", dependencies=[Depends(require_hmac)])
def newsletter_send(req: NewsletterSendRequest):
    from auto_publisher.integrations.newsletter import get_provider
    for v in ("a", "b"):
        if v in req.subject and len(req.subject[v]) > 80:
            raise HTTPException(422, {"code": "E_SUBJECT_TOO_LONG",
                                       "variant": v})
    provider = get_provider(req.provider)
    audience_size = provider.estimate_audience(req.list_id, req.segment)
    if audience_size == 0 and not req.dry_run:
        raise HTTPException(404, {"code": "E_LIST_NOT_FOUND"})
    if req.dry_run:
        for addr in req.test_email_list:
            provider.send_test(subject=req.subject.get("a") or req.subject.get("b"),
                                html=req.content_html, to=addr)
        return {"success": True, "data": {"status": "test_sent",
                                            "recipients": req.test_email_list}}
    campaign = provider.schedule_campaign(
        list_id=req.list_id, subject=req.subject, preheader=req.preheader,
        html=req.content_html, segment=req.segment,
        ab_test=req.ab_test, schedule_at=req.schedule_at,
    )
    return {"success": True, "data": {
        "campaign_id": campaign.id, "status": campaign.status,
        "scheduled_at": campaign.scheduled_at,
        "audience_size": audience_size,
        "ab_test": campaign.ab_metadata,
        "preview_urls": campaign.preview_urls,
    }}
```

---

### 2.10 `GET /kpi/dashboard` — 주간 KPI 집계

**전략 매핑**: `record/00` §7 KPI 프레임워크, `record/06` §9 90일 KPI.

| 항목 | 값 |
|------|---|
| Method | GET |
| Path | `/kpi/dashboard` |
| Query | `period` (`7d`, `30d`, `90d`), `channels` (`blog,youtube,newsletter`) |
| 인증 | 토큰 |
| 실행 시간 | 1~4초 (캐시 히트 시 <100ms) |

#### Response Body

```json
{
  "success": true,
  "data": {
    "period": "7d",
    "as_of": "2026-04-23T00:00:00+09:00",
    "single_decision_kpi": {
      "newsletter_open_rate": 0.42, "newsletter_subs_growth_pct_30d": 18.4,
      "verdict": "GREEN"
    },
    "channels": {
      "blog": {"impressions": 12480, "clicks": 241, "ctr": 0.019,
                "avg_position": 11.4, "rpm_usd": 3.8},
      "youtube": {"views": 14230, "watch_time_min": 2480,
                   "subs_gained_net": 49, "shorts_follow_conv": 0.0042},
      "newsletter": {"subscribers": 2142, "open_rate": 0.42,
                      "ctr": 0.058, "unsubs_rate": 0.011}
    },
    "alerts": [
      {"severity": "warn", "source": "youtube",
       "message": "shorts_follow_conv 0.42% < 목표 1.5%"}
    ],
    "recommendations": [
      "Shorts CTA에 '풀영상 링크' 삽입 A/B 테스트 착수",
      "블로그 RPM <$5 → AdSense Auto Ads 실험"
    ]
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_PERIOD_INVALID` | 422 | period 허용 외 |
| `E_PARTIAL_DATA` | 206 | 일부 채널 데이터 결손 → `details.missing_channels` |

#### Python 구현 skeleton

```python
@router.get("/kpi/dashboard")
@ttl_cache(ttl_sec=900)
def kpi_dashboard(
    period: Literal["7d", "30d", "90d"] = "7d",
    channels: str = "blog,youtube,newsletter",
):
    wanted = set(channels.split(","))
    out = {"period": period, "as_of": _now_iso(), "channels": {},
            "alerts": [], "recommendations": []}
    from auto_publisher.kpi import (
        collect_blog_kpi, collect_youtube_kpi, collect_newsletter_kpi,
        evaluate_single_decision_kpi, generate_recommendations,
    )
    collectors = {
        "blog": collect_blog_kpi, "youtube": collect_youtube_kpi,
        "newsletter": collect_newsletter_kpi,
    }
    missing = []
    for ch, fn in collectors.items():
        if ch not in wanted:
            continue
        try:
            out["channels"][ch] = fn(period=period)
        except Exception as e:
            missing.append({"channel": ch, "error": str(e)[:100]})
    out["single_decision_kpi"] = evaluate_single_decision_kpi(
        newsletter_snapshot=out["channels"].get("newsletter"))
    out["alerts"] = _derive_alerts(out["channels"])
    out["recommendations"] = generate_recommendations(out)
    status = 206 if missing else 200
    if missing:
        out["missing_channels"] = missing
    return Response(content=json.dumps({"success": True, "data": out}),
                    status_code=status, media_type="application/json")
```

---

### 2.11 `POST /social/cross-post` — 다중 플랫폼 동시 포스트

**전략 매핑**: `record/00` S2 (1원본→5플랫폼), `record/06` §5.2 referral.

| 항목 | 값 |
|------|---|
| Method | POST |
| Path | `/social/cross-post` |
| 인증 | HMAC 필수 |
| 실행 시간 | 2~30초 (fan-out 병렬) |

#### Request Body

```json
{
  "source": {"kind": "blog_slug", "value": "schd-vs-voo-2026"},
  "platforms": ["twitter", "threads", "linkedin", "tistory"],
  "variations": {
    "twitter": {"thread_count": 6, "include_chart": true},
    "linkedin": {"max_length": 3000, "include_cta": "newsletter_signup"},
    "tistory": {"as_is": true}
  },
  "lang": "ko",
  "schedule_at": "2026-04-25T08:30:00+09:00",
  "include_utm": true,
  "dry_run": false
}
```

#### Response Body

```json
{
  "success": true,
  "data": {
    "job_id": "xpost_01HWX...",
    "results": [
      {"platform": "twitter", "status": "scheduled",
       "post_url": "https://x.com/i/status/...",
       "scheduled_at": "2026-04-25T08:30:00+09:00"},
      {"platform": "linkedin", "status": "scheduled",
       "post_url": "..."},
      {"platform": "threads", "status": "failed",
       "error": "E_OAUTH_REFRESH_NEEDED"},
      {"platform": "tistory", "status": "published",
       "post_url": "https://investiqs.tistory.com/123"}
    ],
    "success_count": 3, "fail_count": 1
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| `E_SOURCE_NOT_FOUND` | 404 | blog_slug 미존재 |
| `E_PLATFORM_UNSUPPORTED` | 422 | 허용 플랫폼 외 |
| `E_ALL_FAILED` | 502 | 모든 플랫폼 실패 |
| `E_PARTIAL_FAIL` | 207 Multi-Status | 일부 실패 (data에 개별 status) |

#### Python 구현 skeleton

```python
class CrossPostRequest(BaseModel):
    source: dict
    platforms: list[Literal["twitter", "threads", "linkedin",
                             "tistory", "facebook"]]
    variations: dict = Field(default_factory=dict)
    lang: Literal["ko", "en"] = "ko"
    schedule_at: str | None = None
    include_utm: bool = True
    dry_run: bool = False

@router.post("/social/cross-post", dependencies=[Depends(require_hmac)])
async def cross_post(req: CrossPostRequest):
    import asyncio
    from auto_publisher.integrations.social import get_publisher
    from auto_publisher.source_loader import load_source
    src = load_source(req.source)
    if src is None:
        raise HTTPException(404, {"code": "E_SOURCE_NOT_FOUND"})

    async def _one(platform: str):
        try:
            pub = get_publisher(platform)
            variation = req.variations.get(platform, {})
            payload = pub.build_payload(src, variation, lang=req.lang,
                                         include_utm=req.include_utm)
            if req.dry_run:
                return {"platform": platform, "status": "dry_run",
                        "preview": payload}
            res = await pub.publish_async(payload,
                                           schedule_at=req.schedule_at)
            return {"platform": platform, "status": res["status"],
                    "post_url": res.get("url"),
                    "scheduled_at": res.get("scheduled_at")}
        except Exception as e:
            return {"platform": platform, "status": "failed",
                    "error": str(e)[:200]}
    results = await asyncio.gather(*[_one(p) for p in req.platforms])
    ok = sum(1 for r in results if r["status"] in ("scheduled",
                                                     "published", "dry_run"))
    fail = len(results) - ok
    status = 200
    if fail == len(results):
        status = 502
    elif fail > 0:
        status = 207
    return Response(
        content=json.dumps({"success": ok > 0, "data": {
            "results": results, "success_count": ok, "fail_count": fail,
        }}), status_code=status, media_type="application/json")
```

---

### 2.12 `GET /health` — 확장 헬스체크 (서비스별 상태)

**전략 매핑**: 운영/관측성.

| 항목 | 값 |
|------|---|
| Method | GET |
| Path | `/health` |
| Query | `deep` (bool, true면 외부 의존성 포함) |
| 인증 | 공개 (단, `deep=true`는 토큰 필요) |
| 실행 시간 | 30ms (얕은) / 2~5초 (deep) |

#### Response Body

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "version": "2.0.0",
    "uptime_sec": 81230,
    "checks": {
      "database": {"status": "ok", "latency_ms": 2},
      "hugo_builder": {"status": "ok", "last_build": "2026-04-23T00:40:00+09:00"},
      "openrouter": {"status": "ok", "latency_ms": 420},
      "stibee": {"status": "degraded", "latency_ms": 3120,
                  "message": "slow response"},
      "beehiiv": {"status": "ok"},
      "youtube_api": {"status": "ok", "quota_remaining_pct": 73},
      "gsc_api": {"status": "ok"},
      "cloudflare_pages": {"status": "ok",
                            "last_deploy": "2026-04-23T00:41:12Z"},
      "okx_bot_cache": {"status": "ok", "age_sec": 420}
    },
    "flags": {"paper_trading_only": true}
  }
}
```

#### 에러 케이스

| Code | HTTP | 상황 |
|------|:----:|------|
| (없음, degraded/down은 200에 status로) | 200 | |
| `E_CRITICAL_DEP_DOWN` | 503 | 2개 이상 critical 의존 down |

#### Python 구현 skeleton

```python
@router.get("/health")
def health(deep: bool = Query(False)):
    out = {"status": "ok", "version": __version__,
            "uptime_sec": int(time.monotonic() - _STARTED_AT),
            "checks": {}, "flags": {"paper_trading_only": True}}
    if not deep:
        return {"success": True, "data": out}
    from auto_publisher.healthchecks import (
        check_db, check_hugo, check_openrouter, check_stibee,
        check_beehiiv, check_youtube, check_gsc, check_cf_pages,
        check_okx_cache,
    )
    critical = ["openrouter", "hugo_builder"]
    checks = {
        "database": check_db, "hugo_builder": check_hugo,
        "openrouter": check_openrouter, "stibee": check_stibee,
        "beehiiv": check_beehiiv, "youtube_api": check_youtube,
        "gsc_api": check_gsc, "cloudflare_pages": check_cf_pages,
        "okx_bot_cache": check_okx_cache,
    }
    down_critical = 0
    for name, fn in checks.items():
        try:
            out["checks"][name] = fn()
            if name in critical and out["checks"][name].get("status") == "down":
                down_critical += 1
        except Exception as e:
            out["checks"][name] = {"status": "error", "message": str(e)[:120]}
            if name in critical:
                down_critical += 1
    if down_critical >= 2:
        out["status"] = "critical"
        return Response(content=json.dumps({"success": False, "data": out}),
                        status_code=503, media_type="application/json")
    if any(c.get("status") == "degraded" for c in out["checks"].values()):
        out["status"] = "degraded"
    return {"success": True, "data": out}
```

---

## 3. 아키텍처 개선 제안

### 3.1 HTTPServer → FastAPI 전환

| 항목 | HTTPServer (현) | FastAPI (제안) |
|------|:---------------:|:--------------:|
| 비동기 | 단일 스레드 | ASGI (uvicorn), 자동 async |
| 스키마 | 수동 (query string만) | Pydantic 자동 검증 + OpenAPI |
| 인증 | 없음 | `Depends(require_hmac)` 주입 |
| 문서 | 없음 | `/docs` Swagger UI 자동 |
| 테스트 | requests로 E2E | `TestClient`로 단위 테스트 |
| 에러 포맷 | 수동 `_respond(500, ...)` | `HTTPException` + Handler |
| 미들웨어 | 없음 | CORS/GZip/로깅 미들웨어 |
| 의존 패키지 추가 | — | `fastapi`, `uvicorn[standard]`, `pydantic>=2` |

**마이그레이션 비용**:
- 코드 재작성: 398줄 → 약 600~800줄 (분할 후 routes/ 하위 6~7 파일). **실소요 3~4일** (1인 풀타임).
- 기존 엔드포인트 호환성: `/health`, `/publish`, `/analyze`, `/translate`, `/make-video`는 GET alias 유지.
- n8n 워크플로우 영향: **없음**. 쿼리스트링 경로 동일하게 유지(FastAPI가 query/body 둘 다 받음).

**권장 도입 순서**:
1. 기존 `bridge_api.py`를 `bridge_api_legacy.py`로 리네임하고 병행 기동 (포트 8765 → 8766 임시).
2. FastAPI 신규 서버를 8765에 띄우고 기존 경로를 통째 위임.
3. 신규 12개 엔드포인트를 점진 추가.
4. 2주 shadow 운영 후 legacy 제거.

### 3.2 비동기 작업 큐

| 옵션 | 장점 | 단점 | 권장 |
|------|------|------|:----:|
| **FastAPI BackgroundTasks** | 별도 인프라 0, 즉시 도입 | 프로세스 재시작 시 작업 유실 | ✅ **1단계** |
| RQ (Redis Queue) | 가볍다, 재시도 내장 | Redis 운영 | ⏸️ 2단계 |
| Celery | 강력, 스케일 | 복잡, 모니터링 부담 | ❌ 과설계 |
| APScheduler | 이미 auto_publisher 사용 | 단일 프로세스 | ✅ 스케줄만 |

**권장 단계**:
1. **Phase 1 (즉시)**: `BackgroundTasks` + 파일 기반 `.omc/jobs/{job_id}.json` 저장소. `/jobs/{job_id}` 상태조회 엔드포인트 추가.
2. **Phase 2 (3개월 후)**: 주 50+ job/day 도달 시 RQ+Redis로 이관. `bridge_api`는 producer만, worker는 별도 컨테이너.

### 3.3 로깅/메트릭/트레이싱

- **로깅**: `structlog` JSON 출력 → stdout → docker log driver → Loki(옵션).
  필수 필드: `request_id`, `route`, `method`, `status`, `elapsed_ms`, `user_agent`, `signature_valid`, `hmac_keyid`.
- **메트릭**: `prometheus-client` 활용해 `/metrics` 노출.
  - `bridge_requests_total{route,status}` (counter)
  - `bridge_request_duration_seconds{route}` (histogram)
  - `bridge_subprocess_duration_seconds{cmd}` (histogram)
  - `bridge_llm_tokens_total{model}` (counter)
  - `bridge_compliance_violations_total{severity}` (counter)
- **트레이싱**: OpenTelemetry SDK 선택적. LLM 호출·외부 API 호출·subprocess 호출을 span으로 묶어 지연 원인 시각화. 초기엔 request_id만으로 충분.

### 3.4 인증 (HMAC Shared Secret)

**헤더 규약**:
```
X-Bridge-KeyId: n8n-primary
X-Bridge-Timestamp: 1714204800
X-Bridge-Signature: sha256=<hex>
```
`signature = HMAC_SHA256(secret, f"{method}\n{path}\n{timestamp}\n{body_sha256}")`.

**Python 의존성**:

```python
# n8n/deps.py
import hmac, hashlib, time, os
from fastapi import Header, HTTPException, Request

SECRETS = {"n8n-primary": os.environ["BRIDGE_SECRET_N8N"]}

async def require_hmac(
    request: Request,
    x_bridge_keyid: str = Header(...),
    x_bridge_timestamp: str = Header(...),
    x_bridge_signature: str = Header(...),
):
    secret = SECRETS.get(x_bridge_keyid)
    if not secret:
        raise HTTPException(401, {"code": "E_HMAC_KEYID_UNKNOWN"})
    try:
        ts = int(x_bridge_timestamp)
    except ValueError:
        raise HTTPException(401, {"code": "E_HMAC_TS_INVALID"})
    if abs(time.time() - ts) > 300:
        raise HTTPException(401, {"code": "E_HMAC_TS_EXPIRED"})
    body = await request.body()
    body_sha = hashlib.sha256(body).hexdigest()
    msg = f"{request.method}\n{request.url.path}\n{ts}\n{body_sha}".encode()
    expected = "sha256=" + hmac.new(secret.encode(), msg,
                                     hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_bridge_signature):
        raise HTTPException(401, {"code": "E_HMAC_INVALID"})
```

n8n 측에서는 Function 노드로 동일 알고리즘으로 서명 생성 → HTTP Request 노드 헤더에 주입.

---

## 4. docker-compose.yml 변경사항

```yaml
version: "3.9"

services:
  bridge_api:
    build:
      context: ./n8n
      dockerfile: Dockerfile.bridge
    image: investiqs/bridge-api:2.0.0
    container_name: bridge_api
    restart: unless-stopped
    ports:
      - "127.0.0.1:8765:8765"          # 로컬호스트만 바인딩 (공개 X)
    environment:
      - BRIDGE_PORT=8765
      - BRIDGE_SECRET_N8N=${BRIDGE_SECRET_N8N}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - STIBEE_API_KEY=${STIBEE_API_KEY}
      - BEEHIIV_API_KEY=${BEEHIIV_API_KEY}
      - BEEHIIV_PUB_ID=${BEEHIIV_PUB_ID}
      - GSC_SERVICE_ACCOUNT_JSON=/run/secrets/gsc_sa.json
      - YOUTUBE_OAUTH_JSON=/run/secrets/yt_oauth.json
      - YOUTUBE_API_KEY=${YOUTUBE_API_KEY}
      - REDIS_URL=redis://redis:6379/1       # Phase 2
      - BRIDGE_LOG_LEVEL=INFO
      - BRIDGE_ENV=prod
    volumes:
      - /home/mh/ocstorage/workspace/nichproject:/workspace/nichproject:rw
      - /home/mh/ocstorage/workspace/.backtest_cache:/workspace/.backtest_cache:ro
      - /home/mh/ocstorage/workspace/.env:/workspace/.env:ro
      - bridge_jobs:/var/lib/bridge/jobs       # job store
    secrets:
      - gsc_sa
      - yt_oauth
    depends_on:
      - redis
    networks:
      - n8n_network
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8765/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G

  redis:                                   # Phase 2에서 RQ 전환 시
    image: redis:7-alpine
    container_name: bridge_redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - n8n_network

  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - BRIDGE_URL=http://bridge_api:8765   # 컨테이너 간 통신으로 이관
      - BRIDGE_KEY_ID=n8n-primary
      - BRIDGE_SECRET_N8N=${BRIDGE_SECRET_N8N}
    networks:
      - n8n_network

volumes:
  bridge_jobs:
  redis_data:

secrets:
  gsc_sa:
    file: ./secrets/gsc_service_account.json
  yt_oauth:
    file: ./secrets/youtube_oauth.json

networks:
  n8n_network:
    driver: bridge
```

**주요 변경점**:

| 항목 | 현 | 변경 후 | 이유 |
|------|---|--------|------|
| 바인딩 | `0.0.0.0:8765` | `127.0.0.1:8765` + 내부 네트워크 | 외부 노출 차단 |
| n8n 호출 | `host.docker.internal` | `bridge_api:8765` | 컨테이너 네트워크로 직접 |
| 시크릿 | env 평문 | Docker secrets | GSC/YouTube OAuth JSON 보호 |
| healthcheck | 없음 | `/health` curl | 오토 재시작 |
| 리소스 제한 | 없음 | 2 CPU / 2GB | LLM 콜 폭주 방어 |

---

## 5. 환경변수 목록

### 기존 .env 키 (그대로 유지)

| Key | 용도 |
|-----|------|
| `OPENROUTER_API_KEY` | Gemini/Claude 호출 |
| `BRIDGE_PORT` | 기본 8765 |
| `TISTORY_BLOG_NAME` | Tistory 발행 |
| `TISTORY_KAKAO_ID` | Tistory 로그인 |
| `TISTORY_KAKAO_PW` | Tistory 로그인 |
| `CLOUDFLARE_API_TOKEN` | CF Pages 배포 |
| `DISCORD_WEBHOOK_URL` | 알림 |

### 신규 필요 키

| Key | 엔드포인트 | 설명 |
|-----|-----------|------|
| `BRIDGE_SECRET_N8N` | 모든 HMAC | n8n 전용 공유 시크릿 (min 32 bytes, openssl rand -hex 32) |
| `BRIDGE_SECRET_ADMIN` | (옵션) 운영자 | 개인 CLI 호출용 별도 시크릿 |
| `BRIDGE_ENV` | 전체 | `dev`/`staging`/`prod` |
| `BRIDGE_LOG_LEVEL` | 전체 | DEBUG/INFO/WARNING |
| `STIBEE_API_KEY` | `/newsletter/send` | Stibee API 키 |
| `STIBEE_ADDRESS_BOOK_ID` | `/newsletter/send` | 기본 주소록 |
| `BEEHIIV_API_KEY` | `/newsletter/send` | Beehiiv v2 API |
| `BEEHIIV_PUB_ID` | `/newsletter/send` | Publication ID |
| `GSC_SERVICE_ACCOUNT_JSON` | `/analytics/gsc` | 서비스 계정 JSON 경로 |
| `GSC_SITE_URL` | `/analytics/gsc` | 기본 `sc-domain:investiqs.net` |
| `YOUTUBE_OAUTH_JSON` | `/analytics/youtube`, `/social/cross-post` | OAuth 클라이언트 JSON 경로 |
| `YOUTUBE_API_KEY` | `/benchmark/channels` | Public Data API 키 |
| `TWITTER_BEARER_TOKEN` | `/social/cross-post` | 읽기용 |
| `TWITTER_OAUTH2_CLIENT_ID` | `/social/cross-post` | 포스트용 |
| `TWITTER_OAUTH2_CLIENT_SECRET` | `/social/cross-post` | 포스트용 |
| `LINKEDIN_ACCESS_TOKEN` | `/social/cross-post` | UGC API |
| `LINKEDIN_AUTHOR_URN` | `/social/cross-post` | `urn:li:person:xxx` |
| `THREADS_ACCESS_TOKEN` | `/social/cross-post` | Meta Graph API |
| `REDIS_URL` | Phase 2 작업 큐 | `redis://redis:6379/1` |
| `BRIDGE_JOB_DIR` | Phase 1 작업 저장소 | `/var/lib/bridge/jobs` |
| `BRIDGE_RATE_LIMIT_PER_MIN` | 전체 | 기본 120 |
| `BENCHMARK_CHANNELS_CONFIG` | `/benchmark/channels` | JSON 파일 경로 |
| `COMPLIANCE_RULESET_DIR` | `/compliance/check` | `auto_publisher/compliance/rules/` |

### `.env` 예시 추가 블록

```bash
# --- Bridge API v2 ---
BRIDGE_SECRET_N8N=0a1b2c3d4e5f...  # openssl rand -hex 32
BRIDGE_ENV=prod
BRIDGE_LOG_LEVEL=INFO

# --- Newsletter ---
STIBEE_API_KEY=stibee_...
STIBEE_ADDRESS_BOOK_ID=AB_xxx
BEEHIIV_API_KEY=bh_...
BEEHIIV_PUB_ID=pub_xxx

# --- Analytics ---
GSC_SERVICE_ACCOUNT_JSON=/workspace/secrets/gsc_sa.json
GSC_SITE_URL=sc-domain:investiqs.net
YOUTUBE_OAUTH_JSON=/workspace/secrets/yt_oauth.json
YOUTUBE_API_KEY=AIza...

# --- Social ---
TWITTER_OAUTH2_CLIENT_ID=...
TWITTER_OAUTH2_CLIENT_SECRET=...
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_AUTHOR_URN=urn:li:person:abc
THREADS_ACCESS_TOKEN=...
```

---

## 6. 테스트 전략

### 6.1 Pytest 구조

```
n8n/tests/
├── conftest.py            # TestClient, HMAC 헬퍼, mock fixtures
├── unit/
│   ├── test_hmac.py
│   ├── test_compliance.py
│   └── test_pydantic_models.py
├── integration/
│   ├── test_generate_pillar.py
│   ├── test_generate_comparison.py
│   ├── test_news_react.py
│   ├── test_monthly_dividend.py
│   ├── test_analytics_gsc.py
│   ├── test_analytics_youtube.py
│   ├── test_benchmark_channels.py
│   ├── test_compliance_check.py
│   ├── test_newsletter_send.py
│   ├── test_kpi_dashboard.py
│   ├── test_cross_post.py
│   └── test_health.py
└── e2e/
    ├── test_n8n_workflow_weekly_pillar.py
    └── test_n8n_workflow_daily_shorts.py
```

### 6.2 핵심 Fixture (conftest.py)

```python
import pytest, hmac, hashlib, time, json
from fastapi.testclient import TestClient
from n8n.app import create_app

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("BRIDGE_SECRET_N8N", "test_secret_32chars_long_xxxxxxxx")
    return TestClient(create_app())

@pytest.fixture
def sign():
    def _sign(method: str, path: str, body: dict | None = None):
        body_bytes = json.dumps(body or {}).encode() if body else b""
        ts = str(int(time.time()))
        body_sha = hashlib.sha256(body_bytes).hexdigest()
        msg = f"{method}\n{path}\n{ts}\n{body_sha}".encode()
        sig = "sha256=" + hmac.new(b"test_secret_32chars_long_xxxxxxxx",
                                    msg, hashlib.sha256).hexdigest()
        return {"X-Bridge-KeyId": "n8n-primary",
                "X-Bridge-Timestamp": ts,
                "X-Bridge-Signature": sig}
    return _sign
```

### 6.3 curl 예시 12개 (엔드포인트별)

> `SIG=$(python scripts/sign_request.py POST /generate/pillar '<body>')` 헬퍼 전제.

```bash
# 1) POST /generate/pillar
curl -sSX POST http://localhost:8765/generate/pillar \
  -H "Content-Type: application/json" \
  -H "X-Bridge-KeyId: n8n-primary" \
  -H "X-Bridge-Timestamp: $(date +%s)" \
  -H "X-Bridge-Signature: sha256=$SIG" \
  -d '{"category":"etf","primary_keyword":"SCHD ETF 배당 완벽 가이드",
       "long_tail_keywords":["SCHD 배당성장률 10년"],
       "target_length_chars":8000,"lang":"ko","publish_immediately":false}'

# 2) POST /generate/comparison
curl -sSX POST http://localhost:8765/generate/comparison \
  -H "X-Bridge-Signature: sha256=$SIG" ... \
  -d '{"item_a":{"ticker":"SCHD"},"item_b":{"ticker":"VOO"},
       "comparison_dimensions":["dividend_yield","total_return_10y"],
       "lang":"ko","include_live_data":true}'

# 3) POST /generate/news-react
curl -sSX POST http://localhost:8765/generate/news-react ... \
  -d '{"news":{"headline":"연준 금리 동결",
               "source_url":"https://...","published_at":"2026-04-23T06:00:00Z",
               "summary":"FOMC가 3.5~3.75%..."},
       "target_platform":"youtube_shorts","target_duration_sec":45,
       "angle":"portfolio_impact","lang":"ko"}'

# 4) POST /generate/monthly-dividend
curl -sSX POST http://localhost:8765/generate/monthly-dividend ... \
  -d '{"universe":["JEPI","JEPQ","SCHD","DIVO","QYLD","SCHY"],
       "target_month":"2026-05",
       "ranking_criteria":{"dividend_yield_weight":0.4,
                            "stability_weight":0.3,"tax_efficiency_kr_weight":0.3},
       "lang":"ko"}'

# 5) GET /analytics/gsc
curl -sS "http://localhost:8765/analytics/gsc?days=7&lang=ko" \
  -H "X-Bridge-Token: $TOKEN"

# 6) GET /analytics/youtube
curl -sS "http://localhost:8765/analytics/youtube?channel=@investiqs&days=7&kind=shorts"

# 7) GET /benchmark/channels
curl -sS "http://localhost:8765/benchmark/channels?since_hours=24&group=korean_youtube"

# 8) POST /compliance/check
curl -sSX POST http://localhost:8765/compliance/check ... \
  -d '{"content":{"title":"100% 수익 보장 ETF",
                   "html":"<p>따라사세요, 리딩 드립니다</p>"},
       "lang":"ko","channel":"blog","strictness":"strict","auto_fix":true}'

# 9) POST /newsletter/send  (dry-run)
curl -sSX POST http://localhost:8765/newsletter/send ... \
  -d '{"provider":"stibee","list_id":"L_xxx",
       "subject":{"a":"3%만 알고 있는 월배당 ETF 5선"},
       "content_html":"<html>...</html>",
       "test_email_list":["ops@investiqs.net"],"dry_run":true}'

# 10) GET /kpi/dashboard
curl -sS "http://localhost:8765/kpi/dashboard?period=7d&channels=blog,youtube,newsletter"

# 11) POST /social/cross-post (dry-run)
curl -sSX POST http://localhost:8765/social/cross-post ... \
  -d '{"source":{"kind":"blog_slug","value":"schd-vs-voo-2026"},
       "platforms":["twitter","linkedin"],
       "variations":{"twitter":{"thread_count":6}},
       "lang":"ko","dry_run":true}'

# 12) GET /health (deep)
curl -sS "http://localhost:8765/health?deep=true" \
  -H "X-Bridge-Token: $TOKEN"
```

### 6.4 테스트 원칙

1. **HMAC 단위 테스트 우선**: 서명 생성·검증을 먼저 pin (모든 엔드포인트의 공통 경로).
2. **Pydantic 경계값**: 각 필드의 min/max/enum을 `pytest.mark.parametrize`로 전수 검증.
3. **외부 API는 monkeypatch**: `responses`(requests mock) 또는 `respx`(httpx)로 Stibee/YouTube/GSC 응답 고정.
4. **LLM 호출은 record/replay**: `pytest-vcr`로 첫 실행 시 실제 LLM 응답을 `cassettes/*.yaml`에 기록, 이후 재생.
5. **서브프로세스 호출은 subprocess mock**: `monkeypatch.setattr("subprocess.run", fake_run)`.
6. **CI 게이트**: `pytest -m "not llm_real"`로 기본 CI 실행, 주 1회 `pytest -m llm_real` 별도 스케줄.
7. **E2E**: n8n의 실제 워크플로우 JSON을 `n8n execute --file workflow.json`으로 실행, 결과 artifact 비교.

---

## 7. 마이그레이션 로드맵 (참고)

| Week | 작업 | 산출물 | 검증 |
|------|------|--------|------|
| W1 | FastAPI 앱 스캐폴드, HMAC, 기존 6개 라우트 이관 | `bridge_api/app.py`, `deps.py`, `routes/legacy.py` | 기존 n8n 워크플로우 전수 통과 |
| W2 | `/generate/pillar`, `/comparison`, `/monthly-dividend`, `/news-react` | `routes/generate.py` + 신규 생성자 함수 | unit + integration 16개 |
| W3 | `/analytics/gsc`, `/analytics/youtube`, `/benchmark/channels`, `/kpi/dashboard` | `integrations/gsc.py`, `youtube_analytics.py` | GSC/YouTube 쿼터 검증 |
| W4 | `/compliance/check`, `/newsletter/send`, `/social/cross-post`, `/health` (deep) | `compliance/`, `integrations/stibee.py`, `social/` | 컴플라이언스 규칙셋 100+, 발송 dry-run |
| W5 | 관측성 (Prometheus, structlog), job store, 문서화 | `/metrics`, `/jobs/{id}`, OpenAPI | SLO 초안: p95 < 1s (cached), < 8s (gen) |
| W6 | 2주 shadow 운영 → legacy 제거 | `bridge_api_legacy.py` 삭제 | n8n 워크플로우 에러율 < 0.5% |

---

## 8. 결론 및 의사결정 요청

본 설계서는 현 `bridge_api.py`의 10개 결함(보안·동시성·스키마·관측성)을 식별하고, FastAPI + HMAC + BackgroundTasks 기반으로 재구축하며, `record/00` S1~S3 전략과 1:1 매핑된 12개 신규 엔드포인트를 명세했다. 의사결정자가 답해야 할 질문 3가지:

1. **마이그레이션 시기**: 즉시 vs 90일 로드맵 M2(Week 5~8)와 동기화? → **권장: M2 동기화**. 뉴스레터 파이프라인과 KPI 대시보드는 `/newsletter/send`와 `/kpi/dashboard`가 필수 선행 조건.
2. **플랫폼 우선순위**: `/social/cross-post`의 초기 타깃을 Twitter·LinkedIn에 한정 vs Threads·Facebook까지 포함? → **권장: Twitter + LinkedIn + Tistory 3개로 시작**. Threads API는 불안정.
3. **유료 티어 결제 게이트웨이**: `/newsletter/send`가 네이버 프리미엄콘텐츠 연동을 포함해야 하는가? → **권장: Phase 2로 유예**. 초기엔 Stibee 무료 발송만, 유료 티어는 `record/06` 시나리오 C 진입 시점(6개월차)에 추가.

본 문서는 구현 시 `planner`/`executor` 에이전트에 투입 가능한 수준의 사양으로 작성되었으며, 각 엔드포인트의 Python skeleton은 실제 모듈 경로(`auto_publisher.*`, `auto_publisher.integrations.*`)와 정합하도록 설계되었다.

---

**문서 버전**: v1.0 (2026-04-23)
**다음 리뷰 권장**: 마이그레이션 Week 2 완료 시점 (신규 엔드포인트 4개 구현 후 실측 응답시간 기반 v1.1 갱신)
**연계 문서**: `record/00`, `record/02`, `record/05`, `record/06`, `n8n/bridge_api.py` (현 구현)
