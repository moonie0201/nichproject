/* InvestIQs FIRE calculator — DOM binding. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-fire");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var defaultCurrency = root.getAttribute("data-currency") || "USD";
  var copiedMsg = root.getAttribute("data-copied-msg") || "Copied";
  var reachedMsg = root.getAttribute("data-reached-msg") || "Goal reached";
  var notReachedMsg = root.getAttribute("data-not-reached-msg") || "Not reached in 70y";
  var storeKey = "iq-fire";

  var fxRates = { USD: 1 };
  var fxEl = document.getElementById("iq-fx");
  if (fxEl) { try { fxRates = JSON.parse(fxEl.textContent).rates || fxRates; } catch (e) {} }

  var $ = function (id) { return document.getElementById(id); };
  var elCurrent = $("iq-current");
  var elMonthly = $("iq-monthly");
  var elReturn = $("iq-return");
  var elTarget = $("iq-target");
  var elCurrency = $("iq-currency");
  var elResult = $("iq-result");

  function currentState() {
    return {
      cu: IQ.num(elCurrent.value, 0),
      m: IQ.num(elMonthly.value, 0),
      r: IQ.num(elReturn.value, 0),
      t: IQ.num(elTarget.value, 0),
      c: elCurrency.value
    };
  }

  function render() {
    var s = currentState();
    var cur = IQ.safeCurrency(s.c || "USD", fxRates);
    var proj = IQ.projectFIRE({
      currentUsd: s.cu,
      monthlyUsd: s.m,
      annualReturnPct: s.r,
      targetUsd: s.t
    });
    var fmt = function (usd) { return IQ.formatMoney(IQ.convert(usd, cur, fxRates), cur); };

    var statusEl = $("iq-res-status");
    if (proj.reached) {
      statusEl.textContent = reachedMsg + " — " + proj.years + "y " + proj.months + "m";
    } else {
      statusEl.textContent = notReachedMsg;
    }
    $("iq-res-final").textContent = fmt(proj.finalBalanceUsd);

    var tbody = $("iq-tbody");
    tbody.innerHTML = "";
    proj.rows.forEach(function (row) {
      var tr = document.createElement("tr");
      var highlight = proj.reached && proj.hitMonth && row.year === Math.ceil(proj.hitMonth / 12);
      tr.innerHTML =
        "<td>" + row.year + (highlight ? " ★" : "") + "</td>" +
        "<td>" + fmt(row.balanceUsd) + "</td>";
      tbody.appendChild(tr);
    });

    elResult.hidden = false;
    IQ.save(storeKey, s);
  }

  function applyState(s) {
    if (!s) return;
    if (s.cu !== undefined) elCurrent.value = s.cu;
    if (s.m !== undefined) elMonthly.value = s.m;
    if (s.r !== undefined) elReturn.value = s.r;
    if (s.t !== undefined) elTarget.value = s.t;
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
    elCurrent.value = 50000;
    elMonthly.value = 1000;
    elReturn.value = 7;
    elTarget.value = 1000000;
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
