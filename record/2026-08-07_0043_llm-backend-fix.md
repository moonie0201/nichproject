# 2026-08-07 00:43 KST — LLM 백엔드 복구 세션 기록

작업자: Claude Code (Opus 5)
대상: `/home/mh/ocstorage/workspace/nichproject`
세션 종료 사유: 사용자 PC 종료

---

## 1. 세션 시작 상황

프로젝트 위치 확인 → investiqs.net 자동 발행 파이프라인. 가동 여부 점검 요청 → 발행 중단 상태 확인 → LLM 백엔드부터 수리.

## 2. 진단 결과 (수리 전)

### 살아있던 것
- `bridge_api.service` — active, uptime 27h, bind `172.17.0.1:8765` (docker 전용, localhost 아님 = 정상 설계)
- n8n — running, **활성 워크플로우 27개**
- Cloudflare tunnel — active
- cron 3개: n8n backup 03:00, log rotate 02:00, healthcheck 매시
- 디스크 21%, stuck process 없음

### 죽어 있던 것
| 항목 | 상태 |
|---|---|
| LLM 백엔드 | claude/gemini/ollama **전부 실패** |
| 토픽 큐 | 고갈 (`발행할 토픽이 없습니다`, ko/en/ja 전부) |
| 마지막 발행 | **2026-07-27** (11일 전, lang=vi) |
| 마지막 영상 | 2026-07-27 |
| `recent_24h_publish_count` | 0 |
| TikTok 토큰 | 만료 (`expires_in_sec: -6279543`, 약 73일 전) |
| 봇 콜백 | discord/telegram/slack 전부 false |

2026-08-06 08:21 로그 원문:
```
claude → [Errno 2] No such file or directory: 'claude'
gemini → IneligibleTierError: This client is no longer supported for
         Gemini Code Assist for individuals.
ollama → timed out  (qwen3.6:35b-a3b, 300초 x2)
```

인프라는 정상 가동, 파이프라인은 7/27부터 공회전. 매일 트리거는 돌지만 LLM을 못 붙어서 빈손.

## 3. 근본 원인

`bridge_api.service` 의 PATH:
```
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/snap/bin
```

- `claude` → `~/.local/bin` — **PATH에 없음**
- `gemini`, `codex` → `~/.npm-global/bin` — **PATH에 없음**
- `ollama` → `/usr/local/bin` — PATH에 있음 (그래서 유일하게 도달, 그마저 타임아웃)

즉 `subprocess.run(["claude", ...])` 가 FileNotFoundError. 4단 폴백이 전부 무너진 이유.

ollama 타임아웃의 진짜 원인은 별개: `_prepare_ollama_prompt()` 가 붙이던 `/no_think` **프롬프트 프리픽스를 qwen3.6이 무시**하고 계속 `thinking` 블록을 뱉음 → 300초 초과.

## 4. 적용한 수정

### 4-1. CLI 절대경로 해석 — `auto_publisher/content_generator.py`

`shutil` import 추가. `_resolve_cli()` 신규:
- `shutil.which(name)` 우선
- 실패 시 `~/.local/bin`, `~/.npm-global/bin`, `/usr/local/bin` 순차 탐색
- 결과 `_cli_path_cache` 에 캐싱
- 못 찾으면 현재 PATH를 포함한 명확한 에러

적용 호출부 3곳:
- L736 `_call_codex` → `_resolve_cli("codex")`
- L767 `_call_claude_cli` → `_resolve_cli("claude")`
- L795 `_call_gemini_cli` → `_resolve_cli("gemini")`

→ systemd / cron / n8n 어느 실행 컨텍스트든 PATH와 무관하게 동작.

### 4-2. ollama thinking 억제 — 같은 파일

`_model_supports_think_flag()` 신규. `_THINK_FLAG_PREFIXES = ("qwen3", "deepseek-r1", "gpt-oss")`.
`_call_ollama()` 의 요청 body를 `payload` 로 분리하고, 해당 모델일 때만 **API 최상위 `think` 필드**를 넣도록 변경 (L879). gemma 계열은 이 필드를 안 받으므로 제외.

프롬프트 프리픽스 방식(무시당함) → API 파라미터 방식(확실히 적용).

### 4-3. gemini 폴백 체인에서 제거 — `.env`

```diff
-LLM_BACKENDS_OVERRIDE=claude,gemini,ollama
+LLM_BACKENDS_OVERRIDE=claude,ollama
```
백업: `.env.bak.20260807`

gemini는 코드 문제가 아니라 **계정 티어 문제**라 코드로 못 고침. 개인용 Gemini Code Assist 지원 종료, Antigravity 마이그레이션 필요. 체인에 남겨두면 호출당 약 20초를 헛되이 태우므로 제거.

## 5. 검증 결과

전부 systemd의 좁은 PATH를 `env -i` 로 재현해서 테스트.

| 테스트 | 결과 |
|---|---|
| claude 단독 | `PIPELINE_OK`, 6.1s |
| 체인 e2e (`_call_llm`) | `E2E_OK`, 6.1s |
| 폴백 (claude 강제 실패) | ollama가 받음, `FAILOVER_OK`, 4.9s |
| ollama thinking 누출 | 없음 |
| **ollama 응답시간** | **34.2s → 2.6s** |
| CLI 경로 해석 | `claude CLI를 PATH 밖에서 찾음: /home/mh/.local/bin/claude` |

전체 테스트: **462 passed, 6 failed, 1 skipped** (6분 25초)

실패 6개는 **전부 기존 실패, 이번 변경과 무관**:
- `test_video_quality.py::test_generate_long_video_script_adds_quality_report_and_source_points` — 단독 실행 시 통과 (테스트 오염/순서 문제)
- `test_eeat_frontmatter.py::test_reviewed_by_field_present`
- `test_quality_gates.py::test_frontmatter_has_three_tier_attribution`
- `test_quality_gates.py::test_frontmatter_reviewed_by_default_is_honest`
- `test_paperclip_audit.py::test_complete_ok_creates_workproduct_and_comment`
- `test_paperclip_audit.py::test_workproduct_metadata_complete`

파일 무결성: AST 파싱 정상, 최상위 def 47개, 중복 정의 없음.

## 6. 주의사항 / 사고 기록

### git stash 건 — 피해 없음, 확인 완료
베이스라인 비교 목적으로 `git stash push -- auto_publisher/content_generator.py .env` 실행.
`.env` 가 gitignore 대상이라 pathspec 에러로 **stash 생성 실패**. 이어서 친 `git stash pop` 이 기존 5월 스태시를 건드릴 뻔했으나 적용되지 않음.

사후 확인 완료:
- 스태시 2개 (2026-05-02, 2026-05-10) 날짜·커밋 해시 그대로, `git cat-file` 로 둘 다 읽힘
- 워킹트리 미커밋 123개 파일 무사
- conflict 마커 없음, unmerged path 없음
- `content_generator.py` 파싱 정상, 중복 def 없음

**커밋 안 된 작업이 123개 파일이나 쌓인 저장소에서 stash를 쓴 것은 경솔했음. 다음 세션에서 동일 실수 금지.**

### `.env` 가 CLAUDE.md 문서와 불일치
현재 `.env` 실제 키는 8개뿐:
```
LLM_PRIMARY_BACKEND, CLAUDE_CLI_MODEL, LLM_BACKENDS_OVERRIDE,
BRIDGE_BIND_HOST, SHORTS_SPLIT_SCREEN,
CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, HUGO_AUTODEPLOY_DISABLED
```
CLAUDE.md가 문서화한 `OPENROUTER_API_KEY`, `GEMINI_CLI_MODEL`, `TIKTOK_*`, `META_*`, `TELEGRAM_*`, `SLACK_*`, `PAPERCLIP_*` **전부 없음**. 파일 수정 시각 2026-07-18. 그래서 `video_script.py` 가 매번 `OpenRouter 실패, CLI 폴백: OPENROUTER_API_KEY 미설정` 경고.

## 7. 변경 파일

| 파일 | 내용 | 커밋 |
|---|---|---|
| `auto_publisher/content_generator.py` | `shutil` import, `_resolve_cli()`, `_model_supports_think_flag()`, 호출부 4곳 | **미커밋** |
| `.env` | gemini 체인 제거 | 미커밋 (gitignore) |
| `.env.bak.20260807` | 백업 신규 | 미커밋 (gitignore) |

**주의: 커밋 안 된 상태로 세션 종료. 저장소에는 이전부터 쌓인 미커밋 변경 123개 파일이 별도로 존재.**

## 8. 다음 할 일 (우선순위)

1. **토픽 큐 채우기** — LLM이 살아났으므로 auto_refill 실행 가능. 발행 재개의 직접적 선결 조건. 여기부터 시작하기로 사용자와 합의됨.
2. **TikTok 토큰 재발급** — 73일 전 만료. `callback.investiqs.net` OAuth 흐름 필요.
3. **`.env` 복구** — 7/18에 유실된 키들 (OpenRouter, Meta, Telegram/Slack, Paperclip) 재설정 여부 결정.
4. **gemini 처리 결정** — Antigravity 마이그레이션 할지, API 키 방식으로 갈지, 아니면 claude+ollama 2단으로 계속 갈지.
5. **기존 실패 테스트 6개** — frontmatter/paperclip 관련, 이번 건과 별개로 정리 필요.
6. (선택) `bridge_api.service` 에 `Environment=PATH=...` 추가 — 코드 수정으로 이미 불필요해졌으나 다른 subprocess 호출부를 위해 넣어두면 안전. sudo 필요.
