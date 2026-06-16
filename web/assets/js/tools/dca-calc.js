/* InvestIQs DCA calculator — DOM binding. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-dca");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var defaultCurrency = root.getAttribute("data-currency") || "USD";
  var copiedMsg = root.getAttribute("data-copied-msg") || "Copied";
  var storeKey = "iq-dca";

  var fxRates = { USD: 1 };
  var fxEl = document.getElementById("iq-fx");
  if (fxEl) { try { fxRates = JSON.parse(fxEl.textContent).rates || fxRates; } catch (e) {} }

  var $ = function (id) { return document.getElementById(id); };
  var elInitial = $("iq-initial");
  var elMonthly = $("iq-monthly");
  var elPeriod = $("iq-period");
  var elReturn = $("iq-return");
  var elCurrency = $("iq-currency");
  var elResult = $("iq-result");

  function currentState() {
    return {
      i: IQ.num(elInitial.value, 0),
      m: IQ.num(elMonthly.value, 0),
      y: IQ.num(elPeriod.value, 1),
      r: IQ.num(elReturn.value, 0),
      c: elCurrency.value
    };
  }

  function render() {
    var s = currentState();
    var cur = s.c || "USD";
    var proj = IQ.projectDCA({
      initialUsd: s.i,
      monthlyUsd: s.m,
      years: s.y,
      annualReturnPct: s.r
    });
    var fmt = function (usd) { return IQ.formatMoney(IQ.convert(usd, cur, fxRates), cur); };

    $("iq-res-final").textContent = fmt(proj.finalBalanceUsd);
    $("iq-res-contributed").textContent = fmt(proj.totalContributedUsd);
    $("iq-res-gain").textContent = fmt(proj.totalGainUsd);

    var tbody = $("iq-tbody");
    tbody.innerHTML = "";
    proj.rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + row.year + "</td>" +
        "<td>" + fmt(row.balanceUsd) + "</td>" +
        "<td>" + fmt(row.contributedUsd) + "</td>" +
        "<td>" + fmt(row.gainUsd) + "</td>";
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
