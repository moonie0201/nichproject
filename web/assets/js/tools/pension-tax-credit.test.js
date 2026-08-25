/* 연금저축·IRP 세액공제 계산기 자체 점검.
   실행: node assets/js/tools/pension-tax-credit.test.js
   실제 pension-tax-credit.js 를 최소 DOM 스텁 위에서 구동해 한도·공제율 처리를 검증한다. */
"use strict";
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const SRC = path.join(__dirname, "pension-tax-credit.js");

function makeEl(id) {
  return { id, value: "", textContent: "", hidden: true, addEventListener() {} };
}

/** 입력값(만원 단위)을 넣고 스크립트를 돌려 결과 텍스트를 돌려준다. */
function run({ salary, pension, irp }) {
  const els = {};
  const ids = [
    "iq-pension", "iq-salary", "iq-pension-amt", "iq-irp-amt", "iq-result",
    "iq-res-refund", "iq-res-rate", "iq-res-eligible",
    "iq-row-pension", "iq-row-irp", "iq-row-wasted", "iq-row-room", "iq-note",
    "iq-calc", "iq-reset", "iq-share",
  ];
  ids.forEach((id) => (els[id] = makeEl(id)));
  els["iq-pension"].getAttribute = () => null;
  els["iq-salary"].value = String(salary);
  els["iq-pension-amt"].value = String(pension);
  els["iq-irp-amt"].value = String(irp);

  const sandbox = {
    document: { getElementById: (id) => els[id] || null },
    window: {
      IQ: {
        num: (v, fb) => (Number.isFinite(parseFloat(v)) ? parseFloat(v) : fb),
        formatMoney: (n) => String(Math.round(n)),
        save() {},
        load: () => null,
        readParams: () => ({}),
        copyShare() {},
      },
    },
  };
  sandbox.window.document = sandbox.document;

  const vm = require("vm");
  const ctx = vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(SRC, "utf8"), ctx);

  return {
    refund: Number(els["iq-res-refund"].textContent),
    rate: els["iq-res-rate"].textContent,
    eligible: Number(els["iq-res-eligible"].textContent),
    wasted: Number(els["iq-row-wasted"].textContent),
    room: Number(els["iq-row-room"].textContent),
    note: els["iq-note"].textContent,
  };
}

/* 총급여 5,500만 이하 + 합산 900만 → 16.5%, 최대 환급 148.5만 */
let r = run({ salary: 5000, pension: 600, irp: 300 });
assert.strictEqual(r.rate, "16.5%");
assert.strictEqual(r.eligible, 9_000_000);
assert.strictEqual(r.refund, 1_485_000);
assert.strictEqual(r.room, 0);

/* 총급여 5,500만 초과 → 13.2%, 118.8만 */
r = run({ salary: 6000, pension: 600, irp: 300 });
assert.strictEqual(r.rate, "13.2%");
assert.strictEqual(r.refund, 1_188_000);

/* 경계값: 정확히 5,500만원은 이하 구간(16.5%) */
r = run({ salary: 5500, pension: 600, irp: 300 });
assert.strictEqual(r.rate, "16.5%");

/* 연금저축 단독 한도 600만 초과분은 공제 제외 */
r = run({ salary: 5000, pension: 900, irp: 0 });
assert.strictEqual(r.eligible, 6_000_000, "연금저축은 600만원까지만 인정");
assert.strictEqual(r.wasted, 3_000_000);
assert.strictEqual(r.refund, 990_000);
assert.ok(/IRP로 옮기면/.test(r.note), "IRP 이전 안내가 있어야 한다");

/* 합산 900만 한도 초과분도 공제 제외 */
r = run({ salary: 5000, pension: 600, irp: 600 });
assert.strictEqual(r.eligible, 9_000_000);
assert.strictEqual(r.wasted, 3_000_000);

/* 리서치가 인용한 사례: 합산 700만 납입 → 115.5만 */
r = run({ salary: 5000, pension: 600, irp: 100 });
assert.strictEqual(r.refund, 1_155_000);
assert.strictEqual(r.room, 2_000_000);

/* 미납입 → 환급 0, 한도 안내 */
r = run({ salary: 5000, pension: 0, irp: 0 });
assert.strictEqual(r.refund, 0);
assert.strictEqual(r.room, 9_000_000);

/* 음수 입력은 0으로 처리 */
r = run({ salary: 5000, pension: -100, irp: -50 });
assert.strictEqual(r.eligible, 0);
assert.strictEqual(r.wasted, 0);

console.log("pension-tax-credit: 모든 검증 통과");
