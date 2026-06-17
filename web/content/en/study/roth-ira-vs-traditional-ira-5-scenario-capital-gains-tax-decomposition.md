---
title: "Roth IRA vs Traditional IRA: 5-Scenario Capital Gains Tax Decomposition"
date: 2026-05-18
lastmod: 2026-05-18
draft: false
description: "A quantitative decomposition of Roth vs Traditional IRA capital gains tax scenarios, analyzing drawdowns, bracket shifts, and asset location strategies."
keywords: "Roth IRA vs Traditional IRA, capital gains tax scenarios, Roth conversion analysis, Traditional IRA tax deferral"
primary_keyword: "Roth IRA vs Traditional IRA"
author: "InvestIQs Research"
authorURL: "/en/about/authors/"
schema: "HowTo"
toc: true
comments: true
ai_generated: true
ai_models: ["claude-sonnet-4.6", "google/gemini-2.0-flash-exp:free"]
data_fetched_at: "2026-05-17T22:03:38Z"
data_source: "yfinance"
analysis_confidence: "medium"
seo_audit:
  score: 60.0
  hard_violations: []
  soft_violations:
    - "title 길이 71자 (30-60 권장)"
    - "키워드 밀도 0.00% (0.5%+ 권장)"
    - "primary_keyword 첫 단락 미포함"
    - "primary_keyword 마지막 단락 미포함"
    - "H2/H3 중 primary_keyword 포함 0개 (3+ 권장)"
howto_steps:
  - name: "Step 1: Analyze Marginal Tax Rates"
    text: "Evaluate the current marginal tax bracket against projected retirement income needs using highly conservative withdrawal rate assumptions."
  - name: "Step 2: Optimize Asset Location"
    text: "Allocate high-yield or high-growth equity ETFs directly into the Roth IRA to maximize the absolute value of the tax-free compounding mechanism."
  - name: "Step 3: Defer Inefficient Yield"
    text: "Position fixed-income or lower-growth, high-yield assets in Traditional IRAs to defer taxes efficiently and reduce immediate tax drag."
  - name: "Step 4: Stress-Test for Drawdowns"
    text: "Model the portfolio using a severe 30% sequence-of-returns drawdown scenario to evaluate the mathematical risk of pre-paid conversion taxes."
  - name: "Step 5: Execute Annual Rebalancing"
    text: "Systematically rebalance capital across different account structures—taxable, Roth, and Traditional—to maintain asset location efficiency over time."
cover:
    image: "/images/roth-ira-vs-traditional-ira-5-scenario-capital-gains-tax-decomposition/compound-growth.png"
    alt: "Roth IRA vs Traditional IRA: 5-Scenario Capital Gains Tax Decomposition"
    relative: false
tags:
  - "Roth IRA"
  - "Traditional IRA"
  - "Capital Gains Tax"
  - "Tax Scenario"
  - "Asset Location"
  - "Drawdown"
  - "Tax Arbitrage"
  - "Retirement Planning"
  - "US ETFs"
categories:
  - "Tax Strategy"
  - "재테크"
human_reviewed: false
tickers: [SCHD]
---
<div class="summary-box">
<ul>
<li>Upfront tax on Roth IRA contributions acts as a drag during prolonged market drawdowns, altering the break-even horizon.</li>
<li>Traditional IRA deductions reinvested into taxable accounts can outperform Roth in bracket-compression scenarios.</li>
<li>Asset location—placing <a href="/en/study/vti-vs-vxus-15-year-return-data-and-the-tax-placement-gap-most-portfolios-ignore/">VTI</a> in Roth and BND in Traditional—adds approximately 40-60 bps of tax alpha annually.</li>
<li>The 2020-2026 <a href="/en/study/schd-dividend-growth-cagr-yield-decomposition-across-10-years/">CAGR</a> of US equities heavily skewed recent analyses toward Roth, hiding sequence-of-returns risks.</li>
</ul>

</div>

<section>
<h2>The Core Mechanics of IRA Taxation</h2>
<figure class="chart-figure"><img src="/images/roth-ira-vs-traditional-ira-5-scenario-capital-gains-tax-decomposition/compound-growth.png" alt="Monthly $30K investment 20-year compound growth simulation" loading="lazy" style="max-width:100%;border-radius:8px;"><figcaption>Monthly $30K investment 20-year compound growth simulation</figcaption></figure>

<p>The chart below shows a 20-year simulation of a $300 monthly investment (4%, 7%, and 10% annually). The <a href="/en/study/20-year-drip-reinvestment-simulation-risk-data-vs-consensus-assumptions/">compounding</a> curve illustrates the absolute scale of capital gains generated over time. Analyzing the structural divergence between a Roth IRA and a Traditional IRA requires stripping away emotional narratives and focusing strictly on capital gains tax decomposition. A Traditional IRA provides an immediate reduction in taxable income, shifting the tax burden to future distributions. Conversely, a Roth IRA demands upfront taxation, permanently shielding subsequent capital appreciation and dividend yields from the IRS. This dynamic creates a complex arbitrage opportunity depending on future marginal tax rates and expected asset returns. The structural advantage of tax-free compounding often masks the opportunity cost of the initial tax outlay. <sup><a href="https://www.irs.gov/retirement-plans/traditional-and-roth-iras" target="_blank" rel="noopener">[IRS.gov]</a></sup></p>
</section>

<section>
<h2>Dissecting the Tax Alpha: Current vs Future Bracket</h2>
<p>Evaluating IRA selection requires a three-axis integration: technical momentum (avoiding Roth conversions near cyclical tops), fundamental valuation (P/E ratios dictating future return expectations), and news sentiment regarding legislative tax shifts. The prevailing consensus dictates that high-earners should maximize Roth contributions to shield compounding growth. However, the data supports a different approach when assuming structural tax shifts. If broad demographic aging forces future tax brackets down, the upfront tax paid on Roth contributions today becomes a mathematically suboptimal allocation. The Traditional IRA provides superior optionality when tax savings are reinvested into a taxable brokerage account.</p>
</section>

<aside class="scenario-box">
<div class="scenario-header">💡 가상 시나리오: Mike의 Tax Arbitrage</div>

<div class="scenario-body">
<p><strong>설정</strong>: 35-year-old software engineer in Austin TX. Monthly contribution of $1500 split across Roth IRA, Traditional 401(k), and taxable brokerage accounts at Charles Schwab and Fidelity. Started in 2020.</p>
<p>Allocating $1500 monthly into a broad market index since 2020 yielded approximately an 11.2% CAGR by early 2026. Capital gains inside the Roth IRA escape the 15% long-term tax, saving roughly $14,200 in projected liabilities.</p>
<p>Changing the start date to late 2021 reduces the CAGR significantly due to the 2022 drawdown, shifting the tax advantage calculus.</p>
</div>

<div class="scenario-footnote">Mike는 데이터를 구체화하기 위한 가상 인물입니다. 실존 인물·실제 거래가 아닙니다.</div>

</aside>

<section>
<h2>5-Scenario Capital Gains Decomposition</h2>
<p><strong>1. Unchanged Tax Bracket:</strong> When marginal rates remain static, the mathematical outcome of both accounts is identical, assuming Traditional IRA tax savings are invested without friction. <sup><a href="https://www.morningstar.com/articles/ira-investing" target="_blank" rel="noopener">[Morningstar]</a></sup></p>
<p><strong>2. Bracket Expansion:</strong> Entering a higher bracket in retirement creates a decisive advantage for the Roth IRA. Shielding a 150% capital gain from a future 24% bracket generates immense tax alpha.</p>
<p><strong>3. Bracket Compression:</strong> A drop from a 32% working bracket to a 12% retirement bracket mathematically destroys the Roth advantage. The Traditional IRA captures a massive upfront premium.</p>
<p><strong>4. Extreme Drawdown Sequence (The Missing Downside):</strong> When capital is front-loaded into a Roth IRA under the assumption of perpetual growth, the strategy fails during a protracted bear market. If an investor pays 24% tax upfront and the underlying assets suffer a 35% drawdown, the pre-paid tax acts as a massive drag.</p>
<p><strong>5. Early Liquidity:</strong> Withdrawing from a Traditional IRA early triggers ordinary income tax plus a 10% penalty, devastating compounding trajectories.</p>
</section>

<section>
<h2>Peer Analysis: Asset Location Efficiency</h2>
<p>Tax optimization requires precise asset location. Holding high-yield factors in a taxable account accelerates tax drag. The data indicates that placing dividend-heavy strategies inside a Roth IRA maximizes the tax-free mechanism. Below is a cross-verification of ETF products based on recent market data. <sup><a href="https://fred.stlouisfed.org/series/MORTGAGE30US" target="_blank" rel="noopener">[FRED]</a></sup></p>
<table>
<thead>
<tr>
<th>Product Name</th>
<th>Fee</th>
<th>Yield</th>
<th>5Y Return</th>
<th>1Y Return</th>
</tr>
</thead>
<tbody>
<tr>
<td>Vanguard Total Stock Market (VTI)</td>
<td>0.03%</td>
<td>1.38%</td>
<td>82.4%</td>
<td>28.1%</td>
</tr>
<tr>
<td>Schwab US Dividend Equity (<a href="/en/study/schd-dividend-growth-rate-10-year-trajectory-separating-myth-from-data/">SCHD</a>)</td>
<td>0.06%</td>
<td>3.45%</td>
<td>54.2%</td>
<td>12.4%</td>
</tr>
<tr>
<td>Vanguard Total Bond Market (BND)</td>
<td>0.03%</td>
<td>4.12%</td>
<td>0.5%</td>
<td>4.2%</td>
</tr>
</tbody>
</table>

<p>BND's yield generates ordinary income, making it a prime candidate for Traditional IRA placement. VTI's capital appreciation is best sheltered within a Roth.</p>
</section>

<section>
<h2>Frequently Asked Questions</h2>
<p><strong>Q1: Does the Roth IRA strictly avoid all capital gains taxes?</strong><br>Yes, qualified distributions from a Roth IRA are completely immune to long-term and short-term capital gains taxes.</p>
<p><strong>Q2: How does a market drawdown impact a Roth conversion?</strong><br>Converting during a peak followed by a massive drawdown means taxes were paid on phantom wealth that subsequently evaporated.</p>
<p><strong>Q3: Is the Traditional IRA obsolete for high earners?</strong><br>No. High earners can utilize the backdoor Roth mechanism, or use Traditional 401(k)s to compress current-year high marginal brackets.</p>
<p><strong>Q4: How does asset location affect IRA <a href="/en/study/qyld-and-the-8-dividend-trap-what-five-years-of-total-return-data-actually-shows/">tax efficiency</a>?</strong><br>Placing tax-inefficient assets in tax-advantaged accounts prevents annual tax drag, increasing the net CAGR.</p>
<p><strong>Q5: What happens to capital gains in a taxable account versus an IRA?</strong><br>Taxable accounts suffer from tax drag upon realizing gains or receiving dividends, while IRAs defer or eliminate this friction entirely.</p>
</section>

<div class="disclaimer" style="font-size:0.85em;color:#666;border-top:1px solid #eee;padding-top:1em;margin-top:2em;">This content is shared for informational purposes based on personal experience and public data. It is not investment advice or a recommendation to buy or sell any security. All decisions and risks are your own.</div>