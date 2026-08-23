---
title: "Dividend ETF Calculator — SCHD, JEPI, VYM, JEPQ, QYLD Reinvestment"
description: "Pick a dividend ETF and project future income from principal, holding period, dividend growth and reinvestment. Includes how each fund actually generates its distributions and what the projection leaves out."
date: 2026-06-14T00:00:00+09:00
lastmod: 2026-08-23T00:00:00+09:00
draft: false
type: "tools"
tool: "dividend-calculator"
ticker: "SCHD"
tickers_all: ["SCHD", "JEPI", "VYM", "JEPQ", "QYLD"]
schema: "Article"
author: "InvestIQs Editorial"
tags: ["dividend ETF", "DRIP", "SCHD", "JEPI", "VYM", "JEPQ", "QYLD"]
data_as_of: "2026-06-14"
disclaimer: true
tickers: [SCHD, JEPI, VYM, JEPQ, QYLD]
---

## Pick a ticker and project the income

Switching the ticker above swaps in that fund's distribution yield. Enter principal, holding period, dividend growth rate and whether you reinvest, and the calculator returns annual income, cumulative distributions and ending balance.

## The five funds pay you in different ways

They are all called dividend ETFs, but the money comes from different places. That difference matters more than the headline yield.

| Ticker | Source of distributions | Character |
|---|---|---|
| SCHD | Actual corporate dividends | Dividend growth focus, very low fee |
| VYM | Actual corporate dividends | Broad diversification, ultra-low cost |
| JEPI | Equity dividends + option premium (ELN) | High, low-volatility income; capped upside |
| JEPQ | Nasdaq-100 style + option premium | More growth exposure and more volatility than JEPI |
| QYLD | Mostly covered-call premium | Maximum distribution, limited principal growth |

### SCHD — dividend growth

SCHD (Schwab U.S. Dividend Equity ETF) holds quality U.S. companies with a record of raising dividends, at a very low expense ratio. Because it screens for quality and growth, the headline yield is moderate. In exchange it concentrates on businesses able to keep raising payouts, and it behaves differently from covered-call products.

**The higher you set the dividend growth rate, the better SCHD-type funds look.** That assumption drives the result more than anything else, so avoid projecting past growth rates indefinitely into the future.

### VYM — diversification and low cost

VYM (Vanguard High Dividend Yield ETF) holds a wide basket of higher-yielding U.S. stocks at an ultra-low fee. It prioritises breadth and cost over concentration. Diversification reduces single-name risk, but both yield and growth sit between pure growth and pure income products.

### JEPI — income from option premium

JEPI (JPMorgan Equity Premium Income ETF) combines a low-volatility U.S. equity portfolio with an option overlay (ELNs). It delivers high, relatively steady distributions, but upside is capped in strong rallies.

Most of JEPI's yield comes from option premium, **not from dividend growth.** Entering a SCHD-like growth rate will produce results far from reality. Option premium tracks volatility, so distributions shrink when markets are calm.

### JEPQ — the Nasdaq-100 version

JEPQ (JPMorgan Nasdaq Equity Premium Income ETF) applies the same equity-premium-income approach to a Nasdaq-100 style portfolio. More growth exposure means both higher distributions and higher volatility. Its heavier tech weighting makes it swing more than JEPI, and with a 2022 inception the long-run figures are still short history.

### QYLD — maximum distribution

QYLD (Global X NASDAQ 100 Covered Call ETF) sells calls against the full index to generate very high distributions, giving up most price appreciation in exchange. The yield is high, but writing calls on the entire index caps upside and limits long-term principal growth. Its fee is also higher than broad index ETFs.

When you model QYLD, note **why ticking "reinvest" does not grow the balance as much as you would expect** — the distributions are large, but the principal is held back.

## What this calculator does not do

Check these assumptions before trusting the output.

- **No taxes.** U.S. ETF distributions are generally subject to withholding at source, and may be taxable again in your country of residence. Your net income is lower than shown.
- **Fixed exchange rate.** Non-USD display uses the rate at data time and ignores currency moves.
- **Constant dividend growth.** Real distributions can be cut. Option-premium products in particular swing with the volatility regime.
- **No price movement.** The ending balance reflects reinvested distributions only, not capital gains or losses.
- **Figures are periodically refreshed reference values, not real time.**

## Related tools

- [Ticker comparison calculator](/en/tools/compare/) — two ETFs side by side
- [Portfolio income calculator](/en/tools/portfolio-income/) — combined income across holdings
- [Study](/en/study/) — data-driven articles on dividends, tax and accounts
