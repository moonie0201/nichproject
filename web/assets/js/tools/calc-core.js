/* InvestIQs calculator core — framework-free shared helpers.
   Exposed on window.IQ for per-calculator scripts. */
(function () {
  "use strict";

  var IQ = {};

  /* ---- number helpers ---- */
  IQ.num = function (v, fallback) {
    var n = parseFloat(v);
    return isFinite(n) ? n : (fallback === undefined ? 0 : fallback);
  };

  IQ.clampNonNeg = function (n) {
    return n < 0 || !isFinite(n) ? 0 : n;
  };

  /* ---- currency ---- */
  IQ.convert = function (amountUsd, currency, rates) {
    var rate = (rates && rates[currency]) ? rates[currency] : 1;
    return amountUsd * rate;
  };

  IQ.formatMoney = function (amount, currency) {
    if (!isFinite(amount)) amount = 0;
    var noDecimals = { JPY: 1, KRW: 1, VND: 1, IDR: 1 };
    var frac = noDecimals[currency] ? 0 : 2;
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: currency,
        maximumFractionDigits: frac,
        minimumFractionDigits: frac
      }).format(amount);
    } catch (e) {
      return amount.toFixed(frac) + " " + currency;
    }
  };

  /* ---- dividend projection (annual compounding) ----
     opts: { principalUsd, yieldPct, growthPct, years, reinvest }
     Returns { rows:[{year, balanceUsd, annualDivUsd}], finalBalanceUsd,
               firstAnnualDivUsd, firstMonthlyDivUsd, cumulativeDivUsd } */
  IQ.projectDividends = function (opts) {
    var principal = IQ.clampNonNeg(opts.principalUsd);
    var yld = IQ.clampNonNeg(opts.yieldPct) / 100;
    var growth = IQ.clampNonNeg(opts.growthPct) / 100;
    var years = Math.max(1, Math.min(60, Math.round(IQ.num(opts.years, 1))));
    var reinvest = !!opts.reinvest;

    var balance = principal;
    var currentYield = yld;
    var cumulative = 0;
    var rows = [];
    var firstAnnualDiv = balance * currentYield;

    for (var y = 1; y <= years; y++) {
      var annualDiv = balance * currentYield;
      cumulative += annualDiv;
      if (reinvest) balance += annualDiv;
      rows.push({
        year: y,
        balanceUsd: balance,
        annualDivUsd: annualDiv
      });
      currentYield = currentYield * (1 + growth);
    }

    return {
      rows: rows,
      finalBalanceUsd: balance,
      firstAnnualDivUsd: firstAnnualDiv,
      firstMonthlyDivUsd: firstAnnualDiv / 12,
      cumulativeDivUsd: cumulative
    };
  };

  /* ---- monthly rate helpers ---- */
  IQ.monthlyReturn = function (annualPct) {
    return Math.pow(1 + IQ.clampNonNeg(annualPct) / 100, 1 / 12) - 1;
  };
  IQ.monthlyFee = function (annualFeePct) {
    return IQ.clampNonNeg(annualFeePct) / 100 / 12;
  };

  /* ---- DCA (적립식) projection ----
     opts: { initialUsd, monthlyUsd, years, annualReturnPct }
     Returns { rows:[{year,balanceUsd,contributedUsd,gainUsd}], finalBalanceUsd,
               totalContributedUsd, totalGainUsd } */
  IQ.projectDCA = function (opts) {
    var balance = IQ.clampNonNeg(opts.initialUsd);
    var monthly = IQ.clampNonNeg(opts.monthlyUsd);
    var years = Math.max(1, Math.min(70, Math.round(IQ.num(opts.years, 1))));
    var mRet = IQ.monthlyReturn(opts.annualReturnPct);
    var contributed = balance;
    var rows = [];
    for (var m = 1; m <= years * 12; m++) {
      balance = balance * (1 + mRet) + monthly;
      contributed += monthly;
      if (m % 12 === 0) {
        rows.push({
          year: m / 12,
          balanceUsd: balance,
          contributedUsd: contributed,
          gainUsd: balance - contributed
        });
      }
    }
    return {
      rows: rows,
      finalBalanceUsd: balance,
      totalContributedUsd: contributed,
      totalGainUsd: balance - contributed
    };
  };

  /* ---- ETF fee comparison (A vs B) ----
     opts: { initialUsd, monthlyUsd, years, annualReturnPct, feeAPct, feeBPct }
     monthly compound minus monthly fee. Returns finals + difference + yearly rows. */
  IQ.compareFees = function (opts) {
    var years = Math.max(1, Math.min(70, Math.round(IQ.num(opts.years, 1))));
    var monthly = IQ.clampNonNeg(opts.monthlyUsd);
    var init = IQ.clampNonNeg(opts.initialUsd);
    var mRet = IQ.monthlyReturn(opts.annualReturnPct);
    var mFeeA = IQ.monthlyFee(opts.feeAPct);
    var mFeeB = IQ.monthlyFee(opts.feeBPct);
    var a = init, b = init, rows = [];
    for (var m = 1; m <= years * 12; m++) {
      a = a * (1 + mRet - mFeeA) + monthly;
      b = b * (1 + mRet - mFeeB) + monthly;
      if (m % 12 === 0) rows.push({ year: m / 12, aUsd: a, bUsd: b, diffUsd: a - b });
    }
    return { rows: rows, finalAUsd: a, finalBUsd: b, differenceUsd: a - b };
  };

  /* ---- FIRE / target-amount: months until balance >= target ----
     opts: { currentUsd, monthlyUsd, annualReturnPct, targetUsd }
     Returns { reached, years, months, rows, finalBalanceUsd } (cap 70y). */
  IQ.projectFIRE = function (opts) {
    var balance = IQ.clampNonNeg(opts.currentUsd);
    var monthly = IQ.clampNonNeg(opts.monthlyUsd);
    var target = IQ.clampNonNeg(opts.targetUsd);
    var mRet = IQ.monthlyReturn(opts.annualReturnPct);
    var rows = [];
    var reached = false, hitMonth = 0;
    for (var m = 1; m <= 70 * 12; m++) {
      balance = balance * (1 + mRet) + monthly;
      if (!reached && target > 0 && balance >= target) { reached = true; hitMonth = m; }
      if (m % 12 === 0) rows.push({ year: m / 12, balanceUsd: balance });
      if (reached && m % 12 === 0 && m >= hitMonth) { /* keep one year past for table */ }
    }
    return {
      reached: reached,
      years: reached ? Math.floor(hitMonth / 12) : null,
      months: reached ? hitMonth % 12 : null,
      hitMonth: reached ? hitMonth : null,
      rows: rows,
      finalBalanceUsd: balance
    };
  };

  /* ---- inflation impact ----
     opts: { amountUsd, years, annualInflationPct }
     futureCostUsd = 같은 구매력 유지에 필요한 미래 명목금액; presentValueUsd = 미래 amount의 현재가치 */
  IQ.inflation = function (opts) {
    var amount = IQ.clampNonNeg(opts.amountUsd);
    var years = Math.max(1, Math.min(100, Math.round(IQ.num(opts.years, 1))));
    var f = IQ.clampNonNeg(opts.annualInflationPct) / 100;
    var factor = Math.pow(1 + f, years);
    var rows = [];
    for (var y = 1; y <= years; y++) {
      var ff = Math.pow(1 + f, y);
      rows.push({ year: y, futureCostUsd: amount * ff, presentValueUsd: amount / ff });
    }
    return {
      rows: rows,
      futureCostUsd: amount * factor,
      presentValueUsd: amount / factor,
      lostPct: (1 - 1 / factor) * 100
    };
  };

  /* ---- ticker income comparison ----
     opts: { amountUsd, tickerA, tickerB, tickerData }
     tickerData: object with ticker symbols as keys, each having yield_pct and expense_ratio_pct.
     Returns {
       a: { ticker, annualDivUsd, monthlyDivUsd, yieldPct, expenseRatioPct },
       b: { ticker, annualDivUsd, monthlyDivUsd, yieldPct, expenseRatioPct },
       higherYield: "A"|"B"|"tie",
       lowerFee: "A"|"B"|"tie"
     } */
  IQ.compareTickerIncome = function (opts) {
    var amount = IQ.clampNonNeg(IQ.num(opts.amountUsd, 0));
    var tdA = (opts.tickerData && opts.tickerA && opts.tickerData[opts.tickerA]) || {};
    var tdB = (opts.tickerData && opts.tickerB && opts.tickerData[opts.tickerB]) || {};
    var yieldA = IQ.clampNonNeg(IQ.num(tdA.yield_pct, 0));
    var yieldB = IQ.clampNonNeg(IQ.num(tdB.yield_pct, 0));
    var feeA = IQ.clampNonNeg(IQ.num(tdA.expense_ratio_pct, 0));
    var feeB = IQ.clampNonNeg(IQ.num(tdB.expense_ratio_pct, 0));
    var annA = amount * yieldA / 100;
    var annB = amount * yieldB / 100;
    var higherYield = yieldA > yieldB ? "A" : yieldB > yieldA ? "B" : "tie";
    var lowerFee = feeA < feeB ? "A" : feeB < feeA ? "B" : "tie";
    return {
      a: { ticker: opts.tickerA || "", annualDivUsd: annA, monthlyDivUsd: annA / 12, yieldPct: yieldA, expenseRatioPct: feeA },
      b: { ticker: opts.tickerB || "", annualDivUsd: annB, monthlyDivUsd: annB / 12, yieldPct: yieldB, expenseRatioPct: feeB },
      higherYield: higherYield,
      lowerFee: lowerFee
    };
  };

  /* ---- URL param share / restore ---- */
  IQ.readParams = function () {
    var out = {};
    var q = window.location.search.replace(/^\?/, "");
    if (!q) return out;
    q.split("&").forEach(function (pair) {
      var kv = pair.split("=");
      if (kv[0]) out[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
    });
    return out;
  };

  IQ.buildShareUrl = function (params) {
    var base = window.location.origin + window.location.pathname;
    var parts = [];
    Object.keys(params).forEach(function (k) {
      parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(params[k]));
    });
    return parts.length ? base + "?" + parts.join("&") : base;
  };

  IQ.copyShare = function (params, toastMsg) {
    var url = IQ.buildShareUrl(params);
    var done = function () { IQ.toast(toastMsg || "Copied"); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(done, function () {
        window.prompt("URL", url);
      });
    } else {
      window.prompt("URL", url);
    }
  };

  /* ---- localStorage ---- */
  IQ.save = function (key, obj) {
    try { window.localStorage.setItem(key, JSON.stringify(obj)); } catch (e) {}
  };
  IQ.load = function (key) {
    try {
      var v = window.localStorage.getItem(key);
      return v ? JSON.parse(v) : null;
    } catch (e) { return null; }
  };

  /* ---- toast ---- */
  IQ.toast = function (msg) {
    var el = document.querySelector(".iq-toast");
    if (!el) {
      el = document.createElement("div");
      el.className = "iq-toast";
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add("iq-toast--show");
    window.setTimeout(function () { el.classList.remove("iq-toast--show"); }, 1800);
  };

  window.IQ = IQ;
})();
