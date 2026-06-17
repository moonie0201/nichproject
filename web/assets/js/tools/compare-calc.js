/* InvestIQs ticker compare calculator — DOM binding. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-compare");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var tickerA = root.getAttribute("data-ticker-a") || "";
  var tickerB = root.getAttribute("data-ticker-b") || "";
  var yieldA = IQ.num(root.getAttribute("data-yield-a"), 0);
  var yieldB = IQ.num(root.getAttribute("data-yield-b"), 0);
  var feeA = IQ.num(root.getAttribute("data-fee-a"), 0);
  var feeB = IQ.num(root.getAttribute("data-fee-b"), 0);
  var defaultCurrency = root.getAttribute("data-currency") || "USD";
  var copiedMsg = root.getAttribute("data-copied-msg") || "Copied";
  var storeKey = "iq-compare:" + tickerA + "-" + tickerB;

  var fxRates = { USD: 1 };
  var fxEl = document.getElementById("iq-fx");
  if (fxEl) { try { fxRates = JSON.parse(fxEl.textContent).rates || fxRates; } catch (e) {} }

  var $ = function (id) { return document.getElementById(id); };
  var elAmount = $("iq-cmp-amount");
  var elCurrency = $("iq-cmp-currency");
  var elResult = $("iq-cmp-result");

  /* Build a synthetic tickerData map from data-attrs so IQ.compareTickerIncome works */
  var tickerData = {};
  tickerData[tickerA] = { yield_pct: yieldA, expense_ratio_pct: feeA };
  tickerData[tickerB] = { yield_pct: yieldB, expense_ratio_pct: feeB };

  function currentState() {
    return {
      a: IQ.num(elAmount.value, 0),
      c: elCurrency.value
    };
  }

  function render() {
    var s = currentState();
    var cur = s.c || "USD";
    var cmp = IQ.compareTickerIncome({
      amountUsd: s.a,
      tickerA: tickerA,
      tickerB: tickerB,
      tickerData: tickerData
    });
    var fmt = function (usd) { return IQ.formatMoney(IQ.convert(usd, cur, fxRates), cur); };

    $("iq-cmp-a-annual").textContent = fmt(cmp.a.annualDivUsd);
    $("iq-cmp-a-monthly").textContent = fmt(cmp.a.monthlyDivUsd);
    $("iq-cmp-b-annual").textContent = fmt(cmp.b.annualDivUsd);
    $("iq-cmp-b-monthly").textContent = fmt(cmp.b.monthlyDivUsd);

    elResult.hidden = false;
    IQ.save(storeKey, s);
  }

  function applyState(s) {
    if (!s) return;
    if (s.a !== undefined) elAmount.value = s.a;
    if (s.c) elCurrency.value = s.c;
  }

  /* restore: URL params win over localStorage */
  var urlParams = IQ.readParams();
  if (Object.keys(urlParams).length) {
    applyState(urlParams);
  } else {
    applyState(IQ.load(storeKey));
  }
  if (!elCurrency.value) elCurrency.value = defaultCurrency;

  $("iq-cmp-calc").addEventListener("click", render);
  $("iq-cmp-reset").addEventListener("click", function () {
    elAmount.value = 10000;
    elCurrency.value = defaultCurrency;
    render();
  });
  $("iq-cmp-share").addEventListener("click", function () {
    IQ.copyShare(currentState(), copiedMsg);
  });
  elCurrency.addEventListener("change", function () {
    if (!elResult.hidden) render();
  });

  render();
})();
