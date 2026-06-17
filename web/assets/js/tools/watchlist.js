/* InvestIQs watchlist — localStorage-based, URL share. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-watchlist");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var STORE_KEY = "iq-watchlist";
  var SHARE_PARAM = "w";

  /* ---- load ticker data from embedded JSON ---- */
  var tickerData = {};
  var tickerOrder = []; /* preserve deterministic order for add buttons */
  var tickersEl = document.getElementById("iq-tickers");
  if (tickersEl) {
    try {
      var parsed = JSON.parse(tickersEl.textContent);
      tickerData = (parsed && parsed.tickers) ? parsed.tickers : {};
      tickerOrder = Object.keys(tickerData);
    } catch (e) {}
  }

  /* ---- state: current watchlist array ---- */
  var watchlist = [];

  function load() {
    /* URL param wins over localStorage */
    var params = IQ.readParams();
    if (params[SHARE_PARAM]) {
      watchlist = IQ.parseWatchlist(params[SHARE_PARAM], tickerData);
    } else {
      var saved = IQ.load(STORE_KEY);
      if (Array.isArray(saved)) {
        watchlist = IQ.parseWatchlist(IQ.serializeWatchlist(saved), tickerData);
      }
    }
  }

  function persist() {
    IQ.save(STORE_KEY, watchlist);
  }

  /* ---- render ---- */
  var tbody = document.getElementById("iq-wl-body");
  var emptyMsg = document.getElementById("iq-wl-empty");
  var table = document.getElementById("iq-wl-table");

  function formatPct(v) {
    if (v === null || v === undefined || !isFinite(Number(v))) return "–";
    return Number(v).toFixed(2) + "%";
  }

  function render() {
    tbody.innerHTML = "";

    if (watchlist.length === 0) {
      table.hidden = true;
      emptyMsg.hidden = false;
      return;
    }

    table.hidden = false;
    emptyMsg.hidden = true;

    for (var i = 0; i < watchlist.length; i++) {
      var sym = watchlist[i];
      var t = tickerData[sym] || {};
      var tr = document.createElement("tr");

      var tdSym = document.createElement("td");
      tdSym.innerHTML = "<strong>" + sym + "</strong><br><small>" + (t.name || "") + "</small>";

      var tdYield = document.createElement("td");
      tdYield.textContent = formatPct(t.yield_pct);

      var tdFee = document.createElement("td");
      tdFee.textContent = formatPct(t.expense_ratio_pct);

      var td1y = document.createElement("td");
      td1y.textContent = formatPct(t.return_1y_pct);

      var td5y = document.createElement("td");
      td5y.textContent = formatPct(t.return_5y_total_pct);

      var tdRisk = document.createElement("td");
      tdRisk.textContent = t.risk_note || "–";

      var tdRemove = document.createElement("td");
      var btnRemove = document.createElement("button");
      btnRemove.type = "button";
      btnRemove.className = "iq-btn iq-btn--sm iq-btn--ghost";
      btnRemove.setAttribute("data-remove", sym);
      btnRemove.textContent = "✕";
      tdRemove.appendChild(btnRemove);

      tr.appendChild(tdSym);
      tr.appendChild(tdYield);
      tr.appendChild(tdFee);
      tr.appendChild(td1y);
      tr.appendChild(td5y);
      tr.appendChild(tdRisk);
      tr.appendChild(tdRemove);
      tbody.appendChild(tr);
    }

    /* update add-button states: disable if already in list */
    var addBtns = root.querySelectorAll(".iq-wl-add-btn");
    for (var k = 0; k < addBtns.length; k++) {
      var btn = addBtns[k];
      var inList = watchlist.indexOf(btn.getAttribute("data-ticker")) !== -1;
      btn.disabled = inList;
      btn.setAttribute("aria-pressed", inList ? "true" : "false");
    }
  }

  /* ---- event: add ticker ---- */
  root.addEventListener("click", function (e) {
    var btn = e.target.closest(".iq-wl-add-btn");
    if (btn) {
      var sym = btn.getAttribute("data-ticker");
      if (sym && watchlist.indexOf(sym) === -1 && tickerData[sym]) {
        watchlist.push(sym);
        persist();
        render();
      }
      return;
    }

    /* remove ticker */
    var rmBtn = e.target.closest("[data-remove]");
    if (rmBtn) {
      var toRemove = rmBtn.getAttribute("data-remove");
      watchlist = watchlist.filter(function (s) { return s !== toRemove; });
      persist();
      render();
      return;
    }
  });

  /* ---- share ---- */
  document.getElementById("iq-wl-share").addEventListener("click", function () {
    var params = {};
    params[SHARE_PARAM] = IQ.serializeWatchlist(watchlist);
    /* reuse IQ.copyShare which builds URL + copies via clipboard */
    IQ.copyShare(params, root.getAttribute("data-copied-msg") || "Copied");
  });

  /* ---- reset ---- */
  document.getElementById("iq-wl-reset").addEventListener("click", function () {
    watchlist = [];
    persist();
    render();
  });

  /* ---- init ---- */
  load();
  render();
})();
