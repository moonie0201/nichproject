/* InvestIQs 연금저축·IRP 세액공제 계산기 — DOM binding. Depends on window.IQ (calc-core.js). */
(function () {
  "use strict";
  var root = document.getElementById("iq-pension");
  if (!root || !window.IQ) return;
  var IQ = window.IQ;

  var copiedMsg = root.getAttribute("data-copied-msg") || "Copied";
  var storeKey = "iq-pension";

  /* 2026 기준. 조세특례제한법 §86의4 / 소득세법 §59의3.
     법 개정 시 이 블록과 partial 의 안내 문구를 함께 고친다. */
  var PENSION_CAP = 6000000;   // 연금저축 단독 한도
  var TOTAL_CAP = 9000000;     // 연금저축 + IRP 합산 한도
  var RATE_HIGH = 0.165;       // 총급여 5,500만원 이하 (지방소득세 포함)
  var RATE_LOW = 0.132;        // 총급여 5,500만원 초과
  var SALARY_THRESHOLD = 55000000;

  var $ = function (id) { return document.getElementById(id); };
  var elSalary = $("iq-salary");
  var elPension = $("iq-pension-amt");
  var elIrp = $("iq-irp-amt");
  var elResult = $("iq-result");

  function currentState() {
    return {
      s: IQ.num(elSalary.value, 0) * 10000,   // 입력은 만원 단위
      p: IQ.num(elPension.value, 0) * 10000,
      i: IQ.num(elIrp.value, 0) * 10000
    };
  }

  /* 공제 대상 납입액 계산. 연금저축은 600만원까지만 인정되고,
     합산은 900만원이 상한이다. IRP 는 남은 한도를 모두 채울 수 있다. */
  function eligible(pension, irp) {
    var p = Math.min(Math.max(pension, 0), PENSION_CAP);
    var i = Math.min(Math.max(irp, 0), TOTAL_CAP - p);
    return { pension: p, irp: i, total: p + i };
  }

  function fmt(won) {
    return IQ.formatMoney(won, "KRW");
  }

  function render() {
    var s = currentState();
    var rate = s.s <= SALARY_THRESHOLD ? RATE_HIGH : RATE_LOW;
    var el = eligible(s.p, s.i);
    var refund = Math.round(el.total * rate);
    var paid = Math.max(s.p, 0) + Math.max(s.i, 0);
    var wasted = Math.max(paid - el.total, 0);
    var room = Math.max(TOTAL_CAP - el.total, 0);

    $("iq-res-refund").textContent = fmt(refund);
    $("iq-res-rate").textContent = (rate * 100).toFixed(1) + "%";
    $("iq-res-eligible").textContent = fmt(el.total);

    $("iq-row-pension").textContent = fmt(el.pension);
    $("iq-row-irp").textContent = fmt(el.irp);
    $("iq-row-wasted").textContent = fmt(wasted);
    $("iq-row-room").textContent = fmt(room);

    var note = $("iq-note");
    if (wasted > 0) {
      note.textContent =
        "납입액 중 " + fmt(wasted) + "은 한도를 넘어 세액공제를 받지 못합니다." +
        (s.p > PENSION_CAP ? " 연금저축은 600만원까지만 공제되므로, 초과분은 IRP로 옮기면 공제받을 수 있습니다." : "");
      note.hidden = false;
    } else if (room > 0) {
      note.textContent =
        "한도가 " + fmt(room) + " 남아 있습니다. 추가로 채우면 " +
        fmt(Math.round(room * rate)) + "을 더 돌려받습니다.";
      note.hidden = false;
    } else {
      note.textContent = "한도를 모두 채웠습니다. 이 소득 구간에서 받을 수 있는 최대 환급액입니다.";
      note.hidden = false;
    }

    elResult.hidden = false;
    IQ.save(storeKey, { s: s.s / 10000, p: s.p / 10000, i: s.i / 10000 });
  }

  function applyState(st) {
    if (!st) return;
    if (st.s !== undefined) elSalary.value = st.s;
    if (st.p !== undefined) elPension.value = st.p;
    if (st.i !== undefined) elIrp.value = st.i;
  }

  /* restore: URL params win over localStorage */
  var urlParams = IQ.readParams();
  if (Object.keys(urlParams).length) {
    applyState(urlParams);
  } else {
    applyState(IQ.load(storeKey));
  }

  $("iq-calc").addEventListener("click", render);
  $("iq-reset").addEventListener("click", function () {
    elSalary.value = 5000;
    elPension.value = 600;
    elIrp.value = 300;
    render();
  });
  $("iq-share").addEventListener("click", function () {
    var s = currentState();
    IQ.copyShare({ s: s.s / 10000, p: s.p / 10000, i: s.i / 10000 }, copiedMsg);
  });

  render();
})();
