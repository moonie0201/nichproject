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

  /* 쌍마다 페이지를 따로 두면 본문이 51~62% 겹쳐 중복 콘텐츠가 된다.
     한 페이지에서 두 티커를 고르게 하고, 표와 결과를 다시 그린다. */
  var elA = $("iq-cmp-a");
  var elB = $("iq-cmp-b");
  var allData = {};
  var dataEl = $("iq-cmp-data");
  if (dataEl) { try { allData = JSON.parse(dataEl.textContent) || {}; } catch (e) {} }

  function cell(v, suffix) {
    return (v === undefined || v === null || v === "") ? "–" : v + (suffix || "");
  }

  function applyPair(a, b) {
    if (!allData[a] || !allData[b]) return;
    tickerA = a; tickerB = b;
    tickerData = {};
    tickerData[a] = { yield_pct: allData[a].yield_pct, expense_ratio_pct: allData[a].expense_ratio_pct };
    tickerData[b] = { yield_pct: allData[b].yield_pct, expense_ratio_pct: allData[b].expense_ratio_pct };
    storeKey = "iq-compare:" + a + "-" + b;

    ["th-a", "head-a"].forEach(function (id) { var e = $("iq-cmp-" + id); if (e) e.textContent = a; });
    ["th-b", "head-b"].forEach(function (id) { var e = $("iq-cmp-" + id); if (e) e.textContent = b; });

    var tbody = $("iq-cmp-tbody");
    if (tbody) {
      Array.prototype.forEach.call(tbody.querySelectorAll("[data-m]"), function (td) {
        var sym = td.getAttribute("data-side") === "a" ? a : b;
        var field = td.getAttribute("data-m");
        var suffix = field === "risk_note" ? "" : "%";
        td.textContent = cell(allData[sym][field], suffix);
      });
    }
    /* 쌍별 해설도 서버가 다 그려두고 선택된 것만 보여준다. */
    var notes = document.getElementById("iq-cmp-notes");
    if (notes) {
      var key = a + "-" + b, rev = b + "-" + a;
      Array.prototype.forEach.call(notes.children, function (c) {
        var p = c.getAttribute("data-pair");
        c.hidden = (p !== key && p !== rev);
      });
    }
  }

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
  if (elA && elB) {
    function onPair() {
      if (elA.value === elB.value) return;   // 같은 티커끼리 비교는 의미 없다
      applyPair(elA.value, elB.value);
      render();
    }
    applyPair(elA.value, elB.value);
    elA.addEventListener("change", onPair);
    elB.addEventListener("change", onPair);
  }

  render();
})();
