/* InvestIQs inflation calculator — DOM binding. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-inflation");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var defaultCurrency = root.getAttribute("data-currency") || "USD";
  var copiedMsg = root.getAttribute("data-copied-msg") || "Copied";
  var storeKey = "iq-inflation";

  var fxRates = { USD: 1 };
  var fxEl = document.getElementById("iq-fx");
  if (fxEl) { try { fxRates = JSON.parse(fxEl.textContent).rates || fxRates; } catch (e) {} }

  var $ = function (id) { return document.getElementById(id); };
  var elAmount = $("iq-amount");
  var elPeriod = $("iq-period");
  var elRate = $("iq-rate");
  var elCurrency = $("iq-currency");
  var elResult = $("iq-result");

  function currentState() {
    return {
      a: IQ.num(elAmount.value, 0),
      y: IQ.num(elPeriod.value, 1),
      f: IQ.num(elRate.value, 0),
      c: elCurrency.value
    };
  }

  function render() {
    var s = currentState();
    var cur = IQ.safeCurrency(s.c || "USD", fxRates);
    var proj = IQ.inflation({
      amountUsd: s.a,
      years: s.y,
      annualInflationPct: s.f
    });
    var fmt = function (usd) { return IQ.formatMoney(IQ.convert(usd, cur, fxRates), cur); };

    $("iq-res-future").textContent = fmt(proj.futureCostUsd);
    $("iq-res-pv").textContent = fmt(proj.presentValueUsd);
    $("iq-res-lost").textContent = proj.lostPct.toFixed(1) + "%";

    var tbody = $("iq-tbody");
    tbody.innerHTML = "";
    proj.rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + row.year + "</td>" +
        "<td>" + fmt(row.futureCostUsd) + "</td>" +
        "<td>" + fmt(row.presentValueUsd) + "</td>";
      tbody.appendChild(tr);
    });

    elResult.hidden = false;
    IQ.save(storeKey, s);
  }

  function applyState(s) {
    if (!s) return;
    if (s.a !== undefined) elAmount.value = s.a;
    if (s.y !== undefined) elPeriod.value = s.y;
    if (s.f !== undefined) elRate.value = s.f;
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
    elAmount.value = 10000;
    elPeriod.value = 20;
    elRate.value = 3;
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
