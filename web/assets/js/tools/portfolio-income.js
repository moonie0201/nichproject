/* InvestIQs portfolio income calculator — DOM binding. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-pi");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var defaultCurrency = root.getAttribute("data-currency") || "USD";
  var copiedMsg = root.getAttribute("data-copied-msg") || "Copied";
  var lblAdd = root.getAttribute("data-lbl-add") || "Add row";
  var lblRemove = root.getAttribute("data-lbl-remove") || "Remove";
  var storeKey = "iq-portfolio-income";

  var fxRates = { USD: 1 };
  var fxEl = document.getElementById("iq-fx");
  if (fxEl) { try { fxRates = JSON.parse(fxEl.textContent).rates || fxRates; } catch (e) {} }

  var tickerData = {};
  var tickersEl = document.getElementById("iq-tickers");
  if (tickersEl) { try { tickerData = JSON.parse(tickersEl.textContent).tickers || {}; } catch (e) {} }

  var TICKER_LIST = Object.keys(tickerData).length
    ? Object.keys(tickerData)
    : ["SCHD", "JEPI", "VYM", "JEPQ", "QYLD", "VOO", "SPY"];

  var $ = function (id) { return document.getElementById(id); };
  var elRowsContainer = $("iq-pi-rows");
  var elResult = $("iq-pi-result");
  var elCurrency = $("iq-pi-currency");
  var elTbody = $("iq-pi-tbody");

  var DEFAULTS = [
    { ticker: "SCHD", amountUsd: 10000 },
    { ticker: "JEPI", amountUsd: 5000 },
    { ticker: "VYM",  amountUsd: 5000 }
  ];

  function buildTickerOptions(selected) {
    return TICKER_LIST.map(function (t) {
      return '<option value="' + t + '"' + (t === selected ? ' selected' : '') + '>' + t + '</option>';
    }).join("");
  }

  function buildRow(ticker, amountUsd) {
    var div = document.createElement("div");
    div.className = "iq-tool__grid iq-pi-row";
    div.style.cssText = "align-items:center;gap:0.5rem;margin-bottom:0.5rem";
    div.innerHTML =
      '<div class="iq-field" style="flex:1">' +
        '<label>' + (root.getAttribute("data-lbl-ticker") || "Ticker") + '</label>' +
        '<select class="pi-ticker">' + buildTickerOptions(ticker || TICKER_LIST[0]) + '</select>' +
      '</div>' +
      '<div class="iq-field" style="flex:2">' +
        '<label>' + (root.getAttribute("data-lbl-amount") || "Amount (USD)") + '</label>' +
        '<input type="number" class="pi-amount" min="0" step="1000" value="' + (amountUsd || 0) + '">' +
      '</div>' +
      '<div class="iq-field" style="flex:0 0 auto;padding-top:1.4rem">' +
        '<button type="button" class="iq-btn iq-btn--ghost pi-remove" style="padding:0.3rem 0.7rem">' + lblRemove + '</button>' +
      '</div>';
    div.querySelector(".pi-remove").addEventListener("click", function () {
      if (elRowsContainer.querySelectorAll(".iq-pi-row").length > 1) {
        div.remove();
        renderIfVisible();
      }
    });
    div.querySelector(".pi-ticker").addEventListener("change", renderIfVisible);
    div.querySelector(".pi-amount").addEventListener("input", renderIfVisible);
    return div;
  }

  function addRow(ticker, amountUsd) {
    elRowsContainer.appendChild(buildRow(ticker, amountUsd));
  }

  function getPositions() {
    var rows = elRowsContainer.querySelectorAll(".iq-pi-row");
    var positions = [];
    rows.forEach(function (row) {
      positions.push({
        ticker: row.querySelector(".pi-ticker").value || "",
        amountUsd: IQ.num(row.querySelector(".pi-amount").value, 0)
      });
    });
    return positions;
  }

  function currentState() {
    return { rows: getPositions(), c: elCurrency.value };
  }

  function renderIfVisible() {
    if (!elResult.hidden) render();
  }

  function render() {
    var s = currentState();
    var cur = s.c || "USD";
    var result = IQ.portfolioIncome({ positions: s.rows, tickerData: tickerData });
    var fmt = function (usd) { return IQ.formatMoney(IQ.convert(usd, cur, fxRates), cur); };
    var fmtPct = function (p) { return (isFinite(p) ? p.toFixed(2) : "0.00") + "%"; };

    $("iq-pi-total-invested").textContent = fmt(result.totalAmountUsd);
    $("iq-pi-annual-div").textContent = fmt(result.totalAnnualDivUsd);
    $("iq-pi-monthly-div").textContent = fmt(result.monthlyDivUsd);
    $("iq-pi-blended-yield").textContent = fmtPct(result.blendedYieldPct);
    $("iq-pi-blended-expense").textContent = fmtPct(result.blendedExpensePct);

    elTbody.innerHTML = "";
    result.rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + row.ticker + "</td>" +
        "<td>" + fmt(row.amountUsd) + "</td>" +
        "<td>" + fmtPct(row.weightPct) + "</td>" +
        "<td>" + fmt(row.annualDivUsd) + "</td>" +
        "<td>" + fmtPct(row.yieldPct) + "</td>";
      elTbody.appendChild(tr);
    });

    elResult.hidden = false;
    IQ.save(storeKey, { rows: s.rows, c: s.c });
  }

  function applyState(s) {
    if (!s) return;
    if (s.rows && Array.isArray(s.rows) && s.rows.length) {
      elRowsContainer.innerHTML = "";
      s.rows.forEach(function (r) { addRow(r.ticker, r.amountUsd); });
    }
    if (s.c) elCurrency.value = s.c;
  }

  /* init default rows */
  DEFAULTS.forEach(function (d) { addRow(d.ticker, d.amountUsd); });

  /* restore */
  var urlParams = IQ.readParams();
  if (urlParams.rows) {
    try {
      var parsed = JSON.parse(decodeURIComponent(urlParams.rows));
      if (parsed && parsed.length) {
        elRowsContainer.innerHTML = "";
        parsed.forEach(function (r) { addRow(r.ticker, r.amountUsd); });
      }
    } catch (e) {}
    if (urlParams.c) elCurrency.value = urlParams.c;
  } else {
    applyState(IQ.load(storeKey));
  }
  if (!elCurrency.value) elCurrency.value = defaultCurrency;

  $("iq-pi-add").addEventListener("click", function () { addRow(TICKER_LIST[0], 0); });
  $("iq-pi-calc").addEventListener("click", render);
  $("iq-pi-reset").addEventListener("click", function () {
    elRowsContainer.innerHTML = "";
    DEFAULTS.forEach(function (d) { addRow(d.ticker, d.amountUsd); });
    elCurrency.value = defaultCurrency;
    render();
  });
  $("iq-pi-share").addEventListener("click", function () {
    var s = currentState();
    IQ.copyShare({ rows: JSON.stringify(s.rows), c: s.c }, copiedMsg);
  });
  elCurrency.addEventListener("change", function () {
    if (!elResult.hidden) render();
  });

  render();
})();
