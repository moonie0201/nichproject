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
