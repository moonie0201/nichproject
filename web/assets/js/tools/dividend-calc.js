/* InvestIQs dividend calculator — DOM binding. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-dividend");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var ticker = root.getAttribute("data-ticker") || "";
  var baseYield = IQ.num(root.getAttribute("data-yield"), 0);
  var defaultCurrency = root.getAttribute("data-currency") || "USD";
  var copiedMsg = root.getAttribute("data-copied-msg") || "Copied";
  var storeKey = "iq-dividend:" + ticker;

  var fxRates = { USD: 1 };
  var fxEl = document.getElementById("iq-fx");
  if (fxEl) { try { fxRates = JSON.parse(fxEl.textContent).rates || fxRates; } catch (e) {} }

  var $ = function (id) { return document.getElementById(id); };
  var elPrincipal = $("iq-principal");
  var elGrowth = $("iq-growth");
  var elPeriod = $("iq-period");
  var elReinvest = $("iq-reinvest");
  var elCurrency = $("iq-currency");
  var elResult = $("iq-result");

  function currentState() {
    return {
      p: IQ.num(elPrincipal.value, 0),
      g: IQ.num(elGrowth.value, 0),
      y: IQ.num(elPeriod.value, 1),
      r: elReinvest.checked ? 1 : 0,
      c: elCurrency.value
    };
  }

  function render() {
    var s = currentState();
    var cur = s.c || "USD";
    var proj = IQ.projectDividends({
      principalUsd: s.p,
      yieldPct: baseYield,
      growthPct: s.g,
      years: s.y,
      reinvest: !!s.r
    });
    var fmt = function (usd) { return IQ.formatMoney(IQ.convert(usd, cur, fxRates), cur); };

    $("iq-res-annual").textContent = fmt(proj.firstAnnualDivUsd);
    $("iq-res-monthly").textContent = fmt(proj.firstMonthlyDivUsd);
    $("iq-res-cumulative").textContent = fmt(proj.cumulativeDivUsd);
    $("iq-res-final").textContent = fmt(proj.finalBalanceUsd);

    var tbody = $("iq-tbody");
    tbody.innerHTML = "";
    proj.rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + row.year + "</td>" +
        "<td>" + fmt(row.balanceUsd) + "</td>" +
        "<td>" + fmt(row.annualDivUsd) + "</td>";
      tbody.appendChild(tr);
    });

    elResult.hidden = false;
    IQ.save(storeKey, s);
  }

  function applyState(s) {
    if (!s) return;
    if (s.p !== undefined) elPrincipal.value = s.p;
    if (s.g !== undefined) elGrowth.value = s.g;
    if (s.y !== undefined) elPeriod.value = s.y;
    if (s.r !== undefined) elReinvest.checked = !!Number(s.r);
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
    elPrincipal.value = 10000;
    elGrowth.value = 5;
    elPeriod.value = 10;
    elReinvest.checked = true;
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
