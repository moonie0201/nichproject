# ULTRAWORK 세션 요약 (2026-05-02)

## 주요 성과

### 자동화 인프라
- TikTok Content Posting API 자동화 완성
- Cloudflare Tunnel + systemd 영구 등록
- n8n 27개 워크플로우 모두 활성화 (이전 25개 비활성)
- Cloudflare Pages Functions callback handler

### 영상 생성 최적화
- ffmpeg NVENC GPU 인코딩 (libx264 -> h264_nvenc)
- Gemini CLI 모델: 2.5-pro -> 2.5-flash (8초 응답)
- OpenRouter 4모델 폴백 + HTTP API 우선
- script_cache 디스크 캐싱
- SKIP_LONG_VIDEO 환경변수

### 콘텐츠 품질
- contrarian angle 1개 글 추가
- 20개 글에 ai_generated/data_source frontmatter 백필
- og-default.png + 기본 hugo.toml images

### 광고/SEO
- Klaro acceptAll: true + cookieName klaro_v2 (이전 거부 쿠키 무효화)
- AdSense In-Article 슬롯 3개 (single.html)
- robots.txt에 GPTBot/Claude/Perplexity 허용 (자동)
- og:image 기본값

### 시스템
- 디스크 23GB 정리 (uv 캐시 + journal vacuum)
- bridge_api: subprocess Popen 실시간 stdout stream
- /health/full 엔드포인트 (9개 메트릭)
- 7개 좀비 gemini 프로세스 정리

## 사용자 액션 필요

| 항목 | 액션 |
|------|------|
| OPENROUTER_API_KEY | .env에 추가 (openrouter.ai 가입) |
| AdSense In-Article slot ID | 대시보드에서 발급 후 single.html 3곳 placeholder 교체 |
| Meta 계정 24h 대기 | Instagram Reels 활성화 |
| Cloudflare Pages Functions 경로 | 미인식 시 Pages 설정에서 functions 디렉토리 지정 |

## 알려진 이슈

- **make-video 30분+** : Gemini Flash로 빨라졌으나 여러 단계 LLM 호출 누적 (script + critique + rewrite)
- **OpenRouter 429 rate limit** : free tier 한도. 4모델 폴백 후 CLI 사용
- **money_printer_v2 5.3GB** : 사용 중인 프로젝트 (삭제 안 함)

## 커밋 카운트
이번 세션 약 12개 커밋:
1. TikTok OAuth 자동화 완성
2. SKIP_LONG_VIDEO + 단계별 시간 측정
3. contrarian angle + ai_generated 백필
4. video script LLM OpenRouter HTTP + 캐싱
5. bridge subprocess stream + ACTIVATION_GUIDE
6. Cloudflare Functions + AdSense + SEO
7. script_cache mkdir + 4모델 폴백
8. functions 위치 이동 + healthcheck
9. choices 안전 처리 + Klaro v2

## 예상 효과

- AdSense 수익: 즉시 노출 (Klaro 우회) + In-Article로 RPM 상승
- 다국어 SEO: n8n 활성화로 EN/JA/VI/ID 자동 발행
- 영상 자동화: TikTok + YouTube 동시 업로드 (Instagram은 Meta 후)
- 시스템 안정성: GPU 사용 + 좀비 정리 + 디스크 여유
