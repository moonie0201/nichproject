/* InvestIQs portfolio rebalance calculator — DOM binding. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-rebalance");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var defaultCurrency = root.getAttribute("data-currency") || "USD";
  var copiedMsg = root.getAttribute("data-copied-msg") || "Copied";
  var lblAdd = root.getAttribute("data-lbl-add") || "Add row";
  var lblRemove = root.getAttribute("data-lbl-remove") || "Remove";
  var storeKey = "iq-portfolio-rebalance";

  var fxRates = { USD: 1 };
  var fxEl = document.getElementById("iq-fx");
  if (fxEl) { try { fxRates = JSON.parse(fxEl.textContent).rates || fxRates; } catch (e) {} }

  var $ = function (id) { return document.getElementById(id); };
  var elRowsContainer = $("iq-rb-rows");
  var elResult = $("iq-rb-result");
  var elCurrency = $("iq-rb-currency");
  var elTbody = $("iq-rb-tbody");

  var DEFAULTS = [
    { label: "SCHD", currentUsd: 5000, targetPct: 50 },
    { label: "VYM",  currentUsd: 3000, targetPct: 30 },
    { label: "VOO",  currentUsd: 2000, targetPct: 20 }
  ];

  function buildRow(label, currentUsd, targetPct) {
    var div = document.createElement("div");
    div.className = "iq-tool__grid iq-rb-row";
    div.style.cssText = "align-items:center;gap:0.5rem;margin-bottom:0.5rem";
    div.innerHTML =
      '<div class="iq-field" style="flex:2">' +
        '<label>' + (root.getAttribute("data-lbl-label") || "Label") + '</label>' +
        '<input type="text" class="rb-label" value="' + (label || "") + '" placeholder="e.g. SCHD">' +
      '</div>' +
      '<div class="iq-field" style="flex:2">' +
        '<label>' + (root.getAttribute("data-lbl-current") || "Current (USD)") + '</label>' +
        '<input type="number" class="rb-current" min="0" step="100" value="' + (currentUsd || 0) + '">' +
      '</div>' +
      '<div class="iq-field" style="flex:1">' +
        '<label>' + (root.getAttribute("data-lbl-target") || "Target %") + '</label>' +
        '<input type="number" class="rb-target" min="0" max="100" step="1" value="' + (targetPct || 0) + '">' +
      '</div>' +
      '<div class="iq-field" style="flex:0 0 auto;padding-top:1.4rem">' +
        '<button type="button" class="iq-btn iq-btn--ghost rb-remove" style="padding:0.3rem 0.7rem">' + lblRemove + '</button>' +
      '</div>';
    div.querySelector(".rb-remove").addEventListener("click", function () {
      if (elRowsContainer.querySelectorAll(".iq-rb-row").length > 1) {
        div.remove();
        renderIfVisible();
      }
    });
    return div;
  }

  function addRow(label, currentUsd, targetPct) {
    elRowsContainer.appendChild(buildRow(label, currentUsd, targetPct));
  }

  function getHoldings() {
    var rows = elRowsContainer.querySelectorAll(".iq-rb-row");
    var holdings = [];
    rows.forEach(function (row) {
      holdings.push({
        label: row.querySelector(".rb-label").value || "",
        currentUsd: IQ.num(row.querySelector(".rb-current").value, 0),
        targetPct: IQ.num(row.querySelector(".rb-target").value, 0)
      });
    });
    return holdings;
  }

  function currentState() {
    return { rows: getHoldings(), c: elCurrency.value };
  }

  function renderIfVisible() {
    if (!elResult.hidden) render();
  }

  function render() {
    var s = currentState();
    var cur = IQ.safeCurrency(s.c || "USD", fxRates);
    var result = IQ.rebalance({ holdings: s.rows });
    var fmt = function (usd) { return IQ.formatMoney(IQ.convert(usd, cur, fxRates), cur); };
    var fmtPct = function (p) { return (isFinite(p) ? p.toFixed(2) : "0.00") + "%"; };
    var fmtTrade = function (usd) {
      var converted = IQ.convert(usd, cur, fxRates);
      var prefix = converted >= 0 ? "+" : "";
      return prefix + IQ.formatMoney(converted, cur);
    };

    $("iq-rb-total").textContent = fmt(result.totalUsd);

    elTbody.innerHTML = "";
    result.rows.forEach(function (row) {
      var tr = document.createElement("tr");
      var tradeClass = row.tradeUsd > 0.005 ? "style='color:var(--entry-color,#2a9d5c)'" :
                       row.tradeUsd < -0.005 ? "style='color:var(--entry-color-red,#e53935)'" : "";
      tr.innerHTML =
        "<td>" + row.label + "</td>" +
        "<td>" + fmt(row.currentUsd) + "</td>" +
        "<td>" + fmtPct(row.currentPct) + "</td>" +
        "<td>" + fmtPct(row.targetPct) + "</td>" +
        "<td>" + fmt(row.targetUsd) + "</td>" +
        "<td " + tradeClass + ">" + fmtTrade(row.tradeUsd) + "</td>" +
        "<td>" + fmtPct(row.driftPct) + "</td>";
      elTbody.appendChild(tr);
    });

    elResult.hidden = false;
    IQ.save(storeKey, { rows: s.rows, c: s.c });
  }

  function applyState(s) {
    if (!s) return;
    if (s.rows && Array.isArray(s.rows) && s.rows.length) {
      elRowsContainer.innerHTML = "";
      s.rows.forEach(function (r) { addRow(r.label, r.currentUsd, r.targetPct); });
    }
    if (s.c) elCurrency.value = s.c;
  }

  /* init default rows */
  DEFAULTS.forEach(function (d) { addRow(d.label, d.currentUsd, d.targetPct); });

  /* restore */
  var urlParams = IQ.readParams();
  if (urlParams.rows) {
    try {
      var parsed = JSON.parse(decodeURIComponent(urlParams.rows));
      if (parsed && parsed.length) {
        elRowsContainer.innerHTML = "";
        parsed.forEach(function (r) { addRow(r.label, r.currentUsd, r.targetPct); });
      }
    } catch (e) {}
    if (urlParams.c) elCurrency.value = urlParams.c;
  } else {
    applyState(IQ.load(storeKey));
  }
  if (!elCurrency.value) elCurrency.value = defaultCurrency;

  /* set currency select to default if not set by restore */
  if (elCurrency.value !== "KRW" && elCurrency.value !== "JPY" &&
      elCurrency.value !== "VND" && elCurrency.value !== "IDR" &&
      elCurrency.value !== "USD") {
    elCurrency.value = defaultCurrency;
  }

  $("iq-rb-add").addEventListener("click", function () { addRow("", 0, 0); });
  $("iq-rb-calc").addEventListener("click", render);
  $("iq-rb-reset").addEventListener("click", function () {
    elRowsContainer.innerHTML = "";
    DEFAULTS.forEach(function (d) { addRow(d.label, d.currentUsd, d.targetPct); });
    elCurrency.value = defaultCurrency;
    render();
  });
  $("iq-rb-share").addEventListener("click", function () {
    var s = currentState();
    IQ.copyShare({ rows: JSON.stringify(s.rows), c: s.c }, copiedMsg);
  });
  elCurrency.addEventListener("change", function () {
    if (!elResult.hidden) render();
  });

  render();
})();
