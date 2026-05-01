---
title: "About — InvestIQs Research"
url: "/en/about/"
draft: false
reviewed: true
analysis_confidence: "medium"
description: "About InvestIQs Research — a data-driven platform covering US and global ETFs, dividend assets, and long-term allocation with AI-assisted analysis."
keywords: "InvestIQs Research, data-driven ETF analysis, dividend investing research, AI-assisted investment analysis, long-term asset allocation"
ShowToc: false
---

## InvestIQs Research

A data-driven research platform covering **US & global ETFs, dividend assets, and long-term allocation**. Every post combines public market data with AI-assisted analysis and passes a two-stage verification before publishing.

---

## Methodology

1. **Real-time data cross-check**
   - Daily yfinance cache refresh (08:00 KST).
   - Dividend yield is computed directly from `Ticker.dividends` and cross-verified against yfinance.info; >30% divergence triggers the conservative read.
   - Automatic sanity rejection for outliers (negative P/E, yields above 15%, etc.).

2. **AI multi-agent analysis**
   - [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) with five agents: Warren Buffett lens / technical / fundamental / news sentiment / risk.
   - Used as reference signals only — never as a standalone conclusion.

3. **Peer ETF comparison**
   - Single-ticker analysis is avoided. At least one peer is compared on expense ratio, dividend yield, or total return.

4. **Contrarian angle + disconfirming evidence**
   - At least one viewpoint that diverges from market consensus.
   - At least one scenario where the thesis could be wrong.

5. **Two-stage verification**
   - Stage 1 (rule-based): length, comparison table, forbidden phrases, source-data presence.
   - Stage 2 (Gemini semantic): hallucinations, internal contradictions, compliance risks, broken chart refs.

---

## Data Sources

| Item | Source |
|------|--------|
| Price, returns, dividends | yfinance (Yahoo Finance API) |
| AI investor perspectives | ai-hedge-fund multi-agent (Gemini 2.0 Flash) |
| Drafting / verification | Codex (draft) + Gemini (verify) |

---

## Editorial Principles

- **Information, not advice**: All content is research notes on public data — never a buy/sell recommendation.
- **Regulatory awareness**: No categorical directives ("you should buy", "will definitely rise").
- **Transparency**: AI-assisted drafting disclosed via banner + disclaimer on every post.
- **Daily publishing**: Automated 06–08 KST across five languages.

---

## Disclaimer

All content is educational research based on public yfinance data and AI analysis. This is not investment advice, not a solicitation to buy or sell any security. Past performance does not guarantee future results. All investment decisions and risks are your own.
