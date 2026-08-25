/* InvestIQs ETF fee comparison calculator — DOM binding. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-fee");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var defaultCurrency = root.getAttribute("data-currency") || "USD";
  var copiedMsg = root.getAttribute("data-copied-msg") || "Copied";
  var storeKey = "iq-fee";

  var fxRates = { USD: 1 };
  var fxEl = document.getElementById("iq-fx");
  if (fxEl) { try { fxRates = JSON.parse(fxEl.textContent).rates || fxRates; } catch (e) {} }

  var $ = function (id) { return document.getElementById(id); };
  var elInitial = $("iq-initial");
  var elMonthly = $("iq-monthly");
  var elPeriod = $("iq-period");
  var elReturn = $("iq-return");
  var elFeeA = $("iq-fee-a");
  var elFeeB = $("iq-fee-b");
  var elCurrency = $("iq-currency");
  var elResult = $("iq-result");

  function currentState() {
    return {
      i: IQ.num(elInitial.value, 0),
      m: IQ.num(elMonthly.value, 0),
      y: IQ.num(elPeriod.value, 1),
      r: IQ.num(elReturn.value, 0),
      a: IQ.num(elFeeA.value, 0),
      b: IQ.num(elFeeB.value, 0),
      c: elCurrency.value
    };
  }

  function render() {
    var s = currentState();
    var cur = IQ.safeCurrency(s.c || "USD", fxRates);
    var proj = IQ.compareFees({
      initialUsd: s.i,
      monthlyUsd: s.m,
      years: s.y,
      annualReturnPct: s.r,
      feeAPct: s.a,
      feeBPct: s.b
    });
    var fmt = function (usd) { return IQ.formatMoney(IQ.convert(usd, cur, fxRates), cur); };

    $("iq-res-a").textContent = fmt(proj.finalAUsd);
    $("iq-res-b").textContent = fmt(proj.finalBUsd);
    $("iq-res-diff").textContent = fmt(proj.differenceUsd);

    var tbody = $("iq-tbody");
    tbody.innerHTML = "";
    proj.rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + row.year + "</td>" +
        "<td>" + fmt(row.aUsd) + "</td>" +
        "<td>" + fmt(row.bUsd) + "</td>" +
        "<td>" + fmt(row.diffUsd) + "</td>";
      tbody.appendChild(tr);
    });

    elResult.hidden = false;
    IQ.save(storeKey, s);
  }

  function applyState(s) {
    if (!s) return;
    if (s.i !== undefined) elInitial.value = s.i;
    if (s.m !== undefined) elMonthly.value = s.m;
    if (s.y !== undefined) elPeriod.value = s.y;
    if (s.r !== undefined) elReturn.value = s.r;
    if (s.a !== undefined) elFeeA.value = s.a;
    if (s.b !== undefined) elFeeB.value = s.b;
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

  $("iq-calc").addEventListener("click", render);
  $("iq-reset").addEventListener("click", function () {
    elInitial.value = 10000;
    elMonthly.value = 500;
    elPeriod.value = 20;
    elReturn.value = 7;
    elFeeA.value = 0.03;
    elFeeB.value = 0.60;
    elCurrency.value = defaultCurrency;
    render();
  });
  $("iq-share").addEventListener("click", function () {
    IQ.copyShare(currentState(), copiedMsg);
  });
  elCurrency.addEventListener("change", function () {
    if (!elResult.hidden) render();
  });

  render();
})();
