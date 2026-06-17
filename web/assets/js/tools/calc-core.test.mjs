// calc-core.js 회귀 테스트 — node:assert. 실행: node calc-core.test.mjs
// 프레임워크 불필요. window/navigator/document 스텁 후 IIFE 실행 → window.IQ 검증.
import assert from "node:assert/strict";
import fs from "node:fs";

const code = fs.readFileSync(new URL("./calc-core.js", import.meta.url), "utf8");
globalThis.window = {};
globalThis.document = {
  querySelector: () => null,
  createElement: () => ({ classList: { add() {}, remove() {} } }),
  body: { appendChild() {} },
};
new Function(code)(); // executes the IIFE, populates window.IQ
const IQ = globalThis.window.IQ;
assert.ok(IQ, "window.IQ exists");

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass++; console.log("  PASS " + name); }
  catch (e) { fail++; console.log("  FAIL " + name + " :: " + e.message); }
}
const near = (a, b, tol) => assert.ok(Math.abs(a - b) <= (tol ?? Math.abs(b) * 0.01 + 1),
  `expected ~${b}, got ${a}`);
const finite = (x) => assert.ok(Number.isFinite(x), `not finite: ${x}`);

/* ---- helpers ---- */
t("num: parses / falls back", () => {
  assert.equal(IQ.num("12.5"), 12.5);
  assert.equal(IQ.num("", 7), 7);
  assert.equal(IQ.num("abc", 3), 3);
  assert.equal(IQ.num(undefined), 0);
});
t("clampNonNeg: negatives→0", () => {
  assert.equal(IQ.clampNonNeg(-5), 0);
  assert.equal(IQ.clampNonNeg(10), 10);
  assert.equal(IQ.clampNonNeg(NaN), 0);
});
t("monthlyReturn/Fee", () => {
  near(IQ.monthlyReturn(7), Math.pow(1.07, 1 / 12) - 1, 1e-9);
  assert.equal(IQ.monthlyFee(0.6), 0.6 / 100 / 12);
});

/* ---- currency ---- */
t("convert + formatMoney", () => {
  assert.equal(IQ.convert(100, "USD", { USD: 1 }), 100);
  assert.equal(IQ.convert(100, "JPY", { JPY: 160 }), 16000);
  assert.ok(IQ.formatMoney(1234.5, "USD").includes("1,234"));
  assert.ok(!IQ.formatMoney(1000, "JPY").includes(".")); // JPY no decimals
});

/* ---- projectDividends ---- */
t("projectDividends: DRIP compounds, no-DRIP flat", () => {
  const drip = IQ.projectDividends({ principalUsd: 10000, yieldPct: 3.25, growthPct: 5, years: 10, reinvest: true });
  const flat = IQ.projectDividends({ principalUsd: 10000, yieldPct: 3.25, growthPct: 5, years: 10, reinvest: false });
  assert.equal(drip.rows.length, 10);
  near(drip.firstAnnualDivUsd, 325, 0.5);
  assert.ok(drip.finalBalanceUsd > 10000, "DRIP grows principal");
  near(flat.finalBalanceUsd, 10000, 0.01); // no-DRIP principal flat
  assert.ok(drip.cumulativeDivUsd > flat.cumulativeDivUsd);
});

/* ---- projectDCA ---- */
t("projectDCA: known case + accounting identity", () => {
  const r = IQ.projectDCA({ initialUsd: 0, monthlyUsd: 1000, years: 30, annualReturnPct: 7 });
  assert.equal(r.rows.length, 30);
  assert.equal(r.totalContributedUsd, 360000); // 1000*12*30
  near(r.finalBalanceUsd, 1169000, 5000);
  near(r.totalGainUsd, r.finalBalanceUsd - r.totalContributedUsd, 0.01);
});
t("projectDCA: zero return → balance == contributed", () => {
  const r = IQ.projectDCA({ initialUsd: 0, monthlyUsd: 500, years: 5, annualReturnPct: 0 });
  near(r.finalBalanceUsd, 30000, 0.01);
  near(r.totalGainUsd, 0, 0.01);
});

/* ---- compareFees ---- */
t("compareFees: lower fee wins, diff>0", () => {
  const r = IQ.compareFees({ initialUsd: 10000, monthlyUsd: 500, years: 30, annualReturnPct: 7, feeAPct: 0.03, feeBPct: 0.5 });
  assert.ok(r.finalAUsd > r.finalBUsd, "A (lower fee) ends higher");
  assert.ok(r.differenceUsd > 0);
  near(r.differenceUsd, r.finalAUsd - r.finalBUsd, 0.01);
});
t("compareFees: equal fees → diff 0", () => {
  const r = IQ.compareFees({ initialUsd: 1000, monthlyUsd: 100, years: 10, annualReturnPct: 6, feeAPct: 0.2, feeBPct: 0.2 });
  near(r.differenceUsd, 0, 0.01);
});

/* ---- projectFIRE ---- */
t("projectFIRE: reaches target", () => {
  const r = IQ.projectFIRE({ currentUsd: 0, monthlyUsd: 2000, annualReturnPct: 7, targetUsd: 1000000 });
  assert.equal(r.reached, true);
  assert.ok(r.years >= 15 && r.years <= 25, "plausible years: " + r.years);
});
t("projectFIRE: target 0 → not reached flag false", () => {
  const r = IQ.projectFIRE({ currentUsd: 0, monthlyUsd: 0, annualReturnPct: 0, targetUsd: 0 });
  assert.equal(r.reached, false);
});

/* ---- inflation ---- */
t("inflation: future>amount, PV<amount, lost% in (0,100)", () => {
  const r = IQ.inflation({ amountUsd: 1000000, years: 30, annualInflationPct: 3 });
  assert.ok(r.futureCostUsd > 1000000);
  assert.ok(r.presentValueUsd < 1000000);
  assert.ok(r.lostPct > 0 && r.lostPct < 100);
  near(r.futureCostUsd, 1000000 * Math.pow(1.03, 30), 1);
});

/* ---- edge cases: NaN/empty must never produce NaN ---- */
t("edge: NaN/garbage inputs stay finite", () => {
  finite(IQ.projectDCA({ initialUsd: NaN, monthlyUsd: undefined, years: "x", annualReturnPct: null }).finalBalanceUsd);
  finite(IQ.compareFees({ initialUsd: NaN, monthlyUsd: NaN, years: NaN, annualReturnPct: NaN, feeAPct: NaN, feeBPct: NaN }).differenceUsd);
  finite(IQ.inflation({ amountUsd: NaN, years: "x", annualInflationPct: undefined }).futureCostUsd);
  finite(IQ.projectFIRE({ currentUsd: NaN, monthlyUsd: NaN, annualReturnPct: NaN, targetUsd: NaN }).finalBalanceUsd);
  finite(IQ.projectDividends({ principalUsd: NaN, yieldPct: NaN, growthPct: NaN, years: NaN, reinvest: true }).finalBalanceUsd);
});
t("edge: years clamped to >=1 row", () => {
  assert.ok(IQ.projectDCA({ initialUsd: 0, monthlyUsd: 100, years: 0, annualReturnPct: 5 }).rows.length >= 1);
});

/* ---- url params ---- */
t("buildShareUrl round-trips keys", () => {
  globalThis.window.location = { origin: "https://x.com", pathname: "/t/", search: "" };
  const url = IQ.buildShareUrl({ p: 1000, y: 30 });
  assert.ok(url.includes("p=1000") && url.includes("y=30"));
});

/* ---- compareTickerIncome ---- */
const TD = {
  SCHD: { yield_pct: 3.25, expense_ratio_pct: 0.06 },
  JEPI: { yield_pct: 8.45, expense_ratio_pct: 0.35 },
  VYM:  { yield_pct: 2.21, expense_ratio_pct: 0.04 },
};

t("compareTickerIncome: higher-yield detection", () => {
  const r = IQ.compareTickerIncome({ amountUsd: 10000, tickerA: "SCHD", tickerB: "JEPI", tickerData: TD });
  assert.equal(r.higherYield, "B"); // JEPI 8.45 > SCHD 3.25
  near(r.b.annualDivUsd, 845, 0.01);
  near(r.a.annualDivUsd, 325, 0.01);
});
t("compareTickerIncome: lower-fee detection", () => {
  const r = IQ.compareTickerIncome({ amountUsd: 10000, tickerA: "SCHD", tickerB: "JEPI", tickerData: TD });
  assert.equal(r.lowerFee, "A"); // SCHD 0.06 < JEPI 0.35
});
t("compareTickerIncome: tie cases", () => {
  const same = { X: { yield_pct: 5, expense_ratio_pct: 0.1 }, Y: { yield_pct: 5, expense_ratio_pct: 0.1 } };
  const r = IQ.compareTickerIncome({ amountUsd: 1000, tickerA: "X", tickerB: "Y", tickerData: same });
  assert.equal(r.higherYield, "tie");
  assert.equal(r.lowerFee, "tie");
});
t("compareTickerIncome: NaN-safe — garbage inputs stay finite", () => {
  const r = IQ.compareTickerIncome({ amountUsd: NaN, tickerA: "SCHD", tickerB: "VYM", tickerData: TD });
  finite(r.a.annualDivUsd);
  finite(r.b.annualDivUsd);
  assert.equal(r.a.annualDivUsd, 0);
});
t("compareTickerIncome: amount 0 → zero divs", () => {
  const r = IQ.compareTickerIncome({ amountUsd: 0, tickerA: "SCHD", tickerB: "JEPI", tickerData: TD });
  assert.equal(r.a.annualDivUsd, 0);
  assert.equal(r.b.annualDivUsd, 0);
  assert.equal(r.a.monthlyDivUsd, 0);
});

/* ---- IQ.rebalance ---- */
t("rebalance: trades sum to ~0", () => {
  const r = IQ.rebalance({ holdings: [
    { label: "SCHD", currentUsd: 5000, targetPct: 50 },
    { label: "VYM",  currentUsd: 3000, targetPct: 30 },
    { label: "VOO",  currentUsd: 2000, targetPct: 20 },
  ]});
  const tradeSum = r.rows.reduce((s, row) => s + row.tradeUsd, 0);
  near(tradeSum, 0, 0.01);
  assert.equal(r.totalUsd, 10000);
});
t("rebalance: already-balanced → trades ~0", () => {
  const r = IQ.rebalance({ holdings: [
    { label: "A", currentUsd: 5000, targetPct: 50 },
    { label: "B", currentUsd: 5000, targetPct: 50 },
  ]});
  r.rows.forEach(row => near(row.tradeUsd, 0, 0.01));
});
t("rebalance: NaN-safe — all fields finite", () => {
  const r = IQ.rebalance({ holdings: [
    { label: "X", currentUsd: NaN, targetPct: undefined },
    { label: "Y", currentUsd: 1000, targetPct: "abc" },
  ]});
  r.rows.forEach(row => {
    finite(row.currentUsd); finite(row.targetUsd); finite(row.tradeUsd); finite(row.driftPct);
  });
  finite(r.totalUsd);
});
t("rebalance: targets not summing to 100 — no crash", () => {
  const r = IQ.rebalance({ holdings: [
    { label: "A", currentUsd: 4000, targetPct: 60 },
    { label: "B", currentUsd: 6000, targetPct: 60 }, // 120 total — odd but allowed
  ]});
  assert.ok(r.rows.length === 2);
  r.rows.forEach(row => { finite(row.tradeUsd); finite(row.driftPct); });
});

/* ---- IQ.portfolioIncome ---- */
const TDP = {
  SCHD: { yield_pct: 3.25, expense_ratio_pct: 0.06 },
  JEPI: { yield_pct: 8.45, expense_ratio_pct: 0.35 },
  VYM:  { yield_pct: 2.21, expense_ratio_pct: 0.04 },
};
t("portfolioIncome: single position — blended yield == its yield", () => {
  const r = IQ.portfolioIncome({ positions: [{ ticker: "SCHD", amountUsd: 10000 }], tickerData: TDP });
  near(r.blendedYieldPct, 3.25, 0.001);
  near(r.totalAnnualDivUsd, 325, 0.01);
  near(r.monthlyDivUsd, 325 / 12, 0.01);
  assert.equal(r.rows[0].weightPct, 100);
});
t("portfolioIncome: two positions — weighted correctly", () => {
  const r = IQ.portfolioIncome({
    positions: [
      { ticker: "SCHD", amountUsd: 10000 },
      { ticker: "JEPI", amountUsd: 10000 },
    ],
    tickerData: TDP
  });
  // blended = (3.25 + 8.45) / 2 = 5.85
  near(r.blendedYieldPct, (3.25 + 8.45) / 2, 0.001);
  near(r.totalAmountUsd, 20000, 0.01);
  near(r.totalAnnualDivUsd, 325 + 845, 0.01);
  r.rows.forEach(row => near(row.weightPct, 50, 0.001));
});
t("portfolioIncome: empty positions — returns zeros, no crash", () => {
  const r = IQ.portfolioIncome({ positions: [], tickerData: TDP });
  assert.equal(r.totalAmountUsd, 0);
  assert.equal(r.totalAnnualDivUsd, 0);
  assert.equal(r.blendedYieldPct, 0);
  assert.equal(r.rows.length, 0);
});
t("portfolioIncome: NaN/zero-safe — no divide-by-zero, all finite", () => {
  const r = IQ.portfolioIncome({
    positions: [{ ticker: "SCHD", amountUsd: NaN }, { ticker: "VYM", amountUsd: undefined }],
    tickerData: TDP
  });
  finite(r.totalAmountUsd); finite(r.blendedYieldPct); finite(r.blendedExpensePct);
  assert.equal(r.totalAmountUsd, 0);
  assert.equal(r.blendedYieldPct, 0);
});

console.log(`\ncalc-core: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
