---
title: "Are Covered-Call ETF Distributions Sustainable Income? A QYLD Case Study"
description: "A source-cited look at where QYLD's ~12% distribution actually comes from — return of capital vs income — plus its cost and performance drag versus low-cost dividend ETFs like SCHD and VYM. Informational only."
date: 2026-06-17T00:00:00+09:00
lastmod: 2026-06-17T00:00:00+09:00
draft: false
author: "InvestIQs Editorial"
schema: "Article"
ShowReadingTime: true
ShowToc: true
tags: ["QYLD", "covered call ETF", "return of capital", "SCHD", "VYM", "distribution yield"]
keywords: ["QYLD return of capital", "covered call ETF sustainable", "QYLD distribution", "QYLD vs SCHD", "is QYLD income real"]
human_reviewed: "manual-required"
disclaimer: true
---

> **In short.** A high *distribution yield* is not the same as a high *income yield*. For Global X's QYLD, the issuer's own SEC filings show the headline ~12% payout has recently been funded almost entirely by **return of capital**, not by portfolio income or realized gains. This report documents that for QYLD with primary sources. It does **not** rank QYLD against JEPI, JEPQ, SCHD, or VYM on total return — every head-to-head return comparison we attempted failed verification, and we say so plainly below. Informational only, not investment advice.

## Distribution yield vs income yield

A fund's **distribution** is simply the cash it pays out. That cash can come from three very different places:

1. **Net investment income** — dividends and interest the portfolio actually earns.
2. **Realized capital gains** — profits from selling holdings.
3. **Return of capital (ROC)** — paying investors back a portion of their own principal.

Only the first is "income" in the everyday sense. A fund can advertise a double-digit *distribution* yield while its underlying *income* yield is near zero — if the rest of the payout is option premium treated as capital or straightforward return of capital. That gap is the heart of the covered-call ETF question.

## Where QYLD's payout actually comes from

Global X's QYLD (NASDAQ-100 Covered Call ETF) is required to file SEC Section 19(a) notices estimating the source of each distribution. The notice for the **record date of 18 November 2024** reads, per share:

| Source | Per share | % of distribution |
|---|---|---|
| Net investment income | $0.0009 | **0.51%** |
| Net realized capital gains | $0.0000 | **0.00%** |
| Return of capital | $0.1795 | **99.49%** |
| **Total** | **$0.1804** | **100.00%** |

The fiscal-year-to-date line on the same notice matched this composition, indicating the pattern was persistent rather than a one-off. ([Global X QYLD Form 19a, 11/18/2024](https://assets.globalxetfs.com/funds/tax_supplements/QYLD_Form-19a_11182024.pdf))

The mechanics behind this are spelled out in Global X's own strategy material: QYLD "distribut[es] half of the premiums it has received or 1% of the fund's net asset value, whichever is lower," each month. ([Global X strategy article](https://www.globalxetfs.com/articles/qyld-exploring-the-case-for-a-nasdaq-100-covered-call-strategy-2))

The clearest single number: QYLD's fact sheet lists a **30-Day SEC Yield of 0.07%** against a **12-Month Trailing Distribution of 12.10%**. The 30-Day SEC Yield is a standardized measure of the portfolio's actual dividend and interest income — and it *excludes* option premium. A ~0.07% income yield paired with a ~12% payout means, by definition, the distribution is **not funded by portfolio income**. ([QYLD Fact Sheet](https://assets.globalxetfs.com/funds/documents/qyld/Fact-Sheet_QYLD.pdf))

## An important caveat: estimates are not final tax treatment

Section 19(a) percentages are **estimates** made during the year, pending the year-end Form 1099-DIV. They can be reclassified. A documented example: QYLD's 2021 distributions were estimated as roughly 98–100% return of capital in the in-year 19(a) notices, but were later reported as **100% ordinary income** on the actual 1099-DIVs.

So "99.49% return of capital" is the issuer's *estimated source of the distribution* at payment time — useful for understanding the mechanics, but **not** a guarantee of how it will be taxed. Treat the ROC figure as evidence about funding mechanics, not as settled tax characterization.

## Performance drag and cost

Two structural facts are well-documented for QYLD:

- **Covered-call drag.** Its fact sheet shows a 5-year NAV total return of **8.05% annualized** (as of 30 April 2026) versus its own underlying Hybrid Index at **8.92% annualized** — a ~0.87 percentage-point annual shortfall. Part of that gap is the expense ratio; part reflects the covered-call strategy capping upside. ([QYLD Fact Sheet](https://assets.globalxetfs.com/funds/documents/qyld/Fact-Sheet_QYLD.pdf))
- **Cost.** QYLD's total expense ratio is **0.60%**, roughly **ten times** the **0.06%** of SCHD and **~0.04%** of VYM. Over long holding periods, that cost difference compounds. ([Global X QYLD page](https://www.globalxetfs.com/funds/qyld); SCHD/VYM ratios corroborated by multiple independent data providers.)

You can model how an expense-ratio gap of this size compounds over time with our [ETF fee comparison calculator](/en/tools/etf-fee-calculator/), and how a given amount's distributions accumulate with the [dividend calculator](/en/tools/dividend-calculator/qyld/).

## What we could NOT verify (and why we're telling you)

We attempted to verify head-to-head **total-return** comparisons among QYLD, JEPI, JEPQ, SCHD, and VYM over 3–5 years. **Every one of those comparison claims failed our verification step.** The figures conflicted across aggregator sites (totalrealreturns.com, stockanalysis.com, etf.com), were highly sensitive to the exact snapshot date, and could not be unanimously confirmed against primary sources — some even claimed covered-call funds *outperformed* on a reinvested basis, contradicting others.

So this report makes **no** total-return ranking claim. If you see a confident "Fund A beat Fund B by X% over 5 years" headline, check the exact dates and whether distributions were reinvested — small changes flip the result. (You can build your own side-by-side starting points with our [ticker comparison pages](/en/tools/compare/qyld-vs-jepq/).)

## Scope limits

Every verified finding above concerns **QYLD specifically**. Do **not** generalize QYLD's return-of-capital profile to JEPI or JEPQ: those funds historically draw more of their distributions from net investment income and equity-linked notes and behave differently. We did not find primary-source verification for JEPI/JEPQ distribution composition in this research and make no claim about them here.

## How to read funds like this

Framed neutrally, the documented characteristics suggest different fund types answer different questions:

- **High-distribution covered-call funds (e.g. QYLD)** convert option premium and capital into a large, smooth monthly payout, at the cost of higher fees and limited long-term price growth. The payout's "income" character depends heavily on its source composition, which varies.
- **Dividend-growth and broad high-yield funds (e.g. SCHD, VYM)** offer a lower headline yield funded primarily by portfolio income, at very low cost, with more exposure to long-term price appreciation.

Which set of trade-offs fits a given situation depends on individual goals, time horizon, and tax circumstances — questions for an investor and, where relevant, a licensed professional, not for a single yield number.

## Sources

- Global X, *QYLD Form 19a (record date 11/18/2024)* — distribution source estimates. [PDF](https://assets.globalxetfs.com/funds/tax_supplements/QYLD_Form-19a_11182024.pdf)
- Global X, *QYLD Fact Sheet* — 30-Day SEC Yield, 12-month distribution, 5-year NAV vs index, expense ratio. [PDF](https://assets.globalxetfs.com/funds/documents/qyld/Fact-Sheet_QYLD.pdf)
- Global X, *"QYLD: Exploring the Case for a NASDAQ-100 Covered Call Strategy"* — distribution policy, return-of-capital note, since-inception framing. [Article](https://www.globalxetfs.com/articles/qyld-exploring-the-case-for-a-nasdaq-100-covered-call-strategy-2)
- Global X, *QYLD fund page* — current 0.60% expense ratio. [Link](https://www.globalxetfs.com/funds/qyld)
- SCHD (0.06%) and VYM (~0.04%) expense ratios corroborated across multiple independent data providers.

---

*Methodology: claims in this report were drawn from a multi-source research pass and an adversarial verification step; only claims that survived verification against primary (issuer/regulatory) sources are stated as findings. Figures are as of the dates cited and change over time. This content is informational and educational only — it is not investment, tax, or financial advice, and is not a recommendation to buy or sell any security.*
