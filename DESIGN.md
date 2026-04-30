---
version: alpha
name: InvestIQs
description: 데이터 기반 투자 분석 채널 — 신뢰·정확·간결을 시각 언어로 표현

colors:
  # Base
  bg:          "#0f172a"   # 영상 기본 배경 (slate-900)
  bg-shorts:   "#1e293b"   # 쇼츠 배경 (slate-800)
  bg-panel:    "#020617"   # 패널/오버레이 (slate-950)
  bg-risk:     "#7f1d1d"   # 리스크 패널 (red-900)

  # Brand
  primary:     "#38BDF8"   # InvestIQs 블루 (sky-400)
  accent:      "#FACC15"   # 핵심 수치 강조 (yellow-400)
  success:     "#22C55E"   # 긍정 지표 (green-500)
  warning:     "#FFD54F"   # 리스크 경고 (amber-300)

  # Text
  text:        "#FFFFFF"   # 본문 흰색
  text-sub:    "#CBD5E1"   # 보조 텍스트 (slate-300)
  text-muted:  "#D7E3F4"   # 흐린 텍스트
  text-risk:   "#FDE68A"   # 리스크 섹션 텍스트 (amber-200)

  # Hugo (웹)
  web-bg:      "#FFFFFF"
  web-primary: "#0369A1"   # sky-700 (웹 링크/CTA)
  web-border:  "#E2E8F0"   # slate-200

typography:
  # 영상 카드
  card-brand:
    fontFamily: Noto Sans CJK KR
    fontSize: 28px
    fontWeight: "700"
  card-headline:
    fontFamily: Noto Sans CJK KR
    fontSize: 52px
    fontWeight: "700"
    lineHeight: "1.2"
  card-headline-short:
    fontFamily: Noto Sans CJK KR
    fontSize: 46px
    fontWeight: "700"
    lineHeight: "1.2"
  card-subhead:
    fontFamily: Noto Sans CJK KR
    fontSize: 30px
    fontWeight: "400"
    lineHeight: "1.4"
  card-accent:
    fontFamily: Noto Sans CJK KR
    fontSize: 72px
    fontWeight: "800"
  card-label:
    fontFamily: Noto Sans CJK KR
    fontSize: 34px
    fontWeight: "600"

  # 자막 (SRT)
  subtitle-longform:
    fontFamily: Noto Sans CJK KR
    fontSize: 18px
    fontWeight: "700"
  subtitle-shorts:
    fontFamily: Noto Sans CJK KR
    fontSize: 32px
    fontWeight: "700"

spacing:
  card-margin:  64px
  card-padding: 96px

components:
  thesis-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.primary}"
    highlightColor: "{colors.accent}"
    typography: "{typography.card-headline}"

  number-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.accent}"
    typography: "{typography.card-accent}"

  risk-card:
    backgroundColor: "{colors.bg-risk}"
    textColor: "{colors.text}"
    accentColor: "{colors.warning}"
    typography: "{typography.card-headline}"

  cta-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.accent}"
    typography: "{typography.card-headline}"

  comparison-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.accent}"
    typography: "{typography.card-headline}"

  market-dashboard-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text}"
    accentColor: "{colors.accent}"
    primaryPanel: "{colors.primary}"
    secondaryPanel: "#1D4ED8"
    typography: "{typography.card-label}"
---

## Overview

InvestIQs는 AI 멀티에이전트 분석 결과를 한국어 투자 콘텐츠로 자동 발행하는 채널입니다.
**신뢰, 정확, 간결**이 핵심 가치입니다.

- 감정보다 데이터를 우선합니다.
- 불확실성을 항상 명시합니다.
- 디자인은 정보를 방해하지 않습니다.

## Colors

배경은 어두운 Navy(#0f172a)로 차트·수치의 대비를 극대화합니다.
브랜드 블루(#38BDF8)는 헤더·레이블 등 정보 계층을 표시하고,
노란 강조(#FACC15)는 핵심 수치 한 가지에만 사용합니다.
리스크 섹션은 독립적인 붉은 패널(#7f1d1d)로 즉각 식별 가능하게 합니다.

## Typography

한국어 콘텐츠이므로 Noto Sans CJK KR을 기본 서체로 사용합니다.
시스템에서 찾지 못할 경우 DejaVu Sans로 폴백합니다.
영상 카드는 큰 서체(52–72px)로 모바일 가독성을 보장합니다.

## Layout

- 영상 카드 여백: 64px (margin), 96px (padding)
- 롱폼: 1920×1080 (16:9)
- 쇼츠: 1080×1920 (9:16), 상단 960px 차트 / 하단 960px 자막

## Components

### thesis-card
분석 핵심 주장 카드. 좌상단 InvestIQs Research 레이블 + 대형 헤드라인 + 노란 accent 수치.

### number-card
단일 핵심 수치를 72px accent로 중앙 표시. 쇼츠 첫 카드에 사용.

### risk-card
붉은 배경 + 노란 좌측 세로줄로 리스크 섹션 즉각 식별.

### market-dashboard-card
복수 시장 지표를 두 개의 패널에 나열. 스캔바 3개로 시각적 분리.

### cta-card
채널명과 블로그 링크 유도. 중앙 정렬, accent 색상으로 강조.

## Do's and Don'ts

- ✅ 핵심 수치는 노란색(#FACC15) 하나에만 적용
- ✅ 리스크 정보는 반드시 별도 카드로 분리
- ✅ 모든 수치는 소수점 1자리 이하로 반올림
- ❌ 브랜드 블루와 노란 강조를 같은 요소에 동시 사용하지 않음
- ❌ 흰 배경 카드 사용 금지 (차트 가독성 저하)
- ❌ 1인칭 표현, 투자 권유 문구 화면 표시 금지
