---
title: "How Our Content Is Produced and Verified"
description: "InvestIQs content is produced with an AI-assisted editorial workflow, then checked by rule-based validation and cross-referenced against public data. We disclose the process and its limits openly."
date: 2026-05-26
lastmod: 2026-07-31
draft: false
layout: "about"
ai_generated: true
human_reviewed: false
---

## Who publishes this site

InvestIQs is published by the **InvestIQs editorial team** — an organization, not an individual analyst. We do not claim a named human analyst behind each article, because that would not be true. This page explains exactly how the content is made, what is checked, and what is not.

## How content is produced (transparency)

All analysis articles, market summaries, and video scripts on InvestIQs are **produced with an AI-assisted editorial workflow using large language models (LLMs)**. They are not written line by line by a human analyst. We state this explicitly rather than implying human authorship.

### Models used
- **Article body**: Anthropic Claude (Haiku 4.5 / Sonnet 4.6)
- **Translation and localization**: Google Gemini, OpenRouter fallback
- **Fact-check assistance**: Gemini 3.1 Pro Preview

Each article's `ai_models` front matter field records the model IDs actually used for that piece.

## Verification process

A human reviewer does not read every article individually. Instead, the following automated steps run on each piece:

1. **Public-data citation**: Figures are drawn from public sources — yfinance, regulatory filings, and ETF issuer materials.
2. **Rule-based validation**: Exaggerated claims, prohibited phrasing, and "guaranteed return" style language are blocked automatically.
3. **Scenario balance check**: Articles covering only positive cases are rejected; downside and risk sections are required.
4. **SEO and structure gate**: Keyword usage, heading structure, and meta description length are checked automatically.

**This does not replace expert human judgment.** AI makes mistakes. Data citation errors, outdated tax rules, and missing market nuance are all possible.

## Limits and disclaimer

- **Not investment advice.** All content is informational and is not a recommendation to buy or sell any security.
- **Not tax or legal advice.** Tax-advantaged accounts and income-tax topics are covered in general terms only. Confirm your own situation with a licensed professional.
- **Point-in-time data**: Figures reflect the time of writing (see the `data_fetched_at` field). Markets change quickly — verify current data independently.
- **Report an error**: If you find a factual or numerical error, or a bad citation, tell us via [Contact](/en/contact/). We verify and correct.

## Editorial principles

1. **Data first**: Only verifiable public data is cited.
2. **Both sides**: Benefits and risks are presented together; one-sided pieces are rejected automatically.
3. **Transparency**: AI use, the models used, and the data timestamp are disclosed in every article's front matter.

---

*Last updated: 2026-07-31*
