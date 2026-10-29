// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string literal: ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.pensionDbDcCalc;
const cases = [
  ['상승률 0, 수익률 0 -> 둘 다 M x n', 3000000, 10, 0, 0, { db: 30000000, dc: 30000000, diff: 0 }],
  ['g=r=3% -> DB=DC', 3000000, 10, 0.03, 0.03, { db: 39143196, dc: 39143196, diff: 0 }],
  ['g=3% r=2% -> DB가 큼', 3000000, 10, 0.03, 0.02, { db: 39143196, dc: 37476588 }],
  ['g=3% r=5% -> DC가 큼', 3000000, 10, 0.03, 0.05, { db: 39143196, dc: 42746737 }],
  ['g=3% r=0 -> DC = 부담금 합계', 3000000, 10, 0.03, 0, { dc: 34391638, paid: 34391638 }],
  ['1년 근속 -> 둘 다 월 임금 1개월분', 3500000, 1, 0.05, 0.1, { db: 3500000, dc: 3500000, lastWage: 3500000 }],
  ['연봉 4,200만 원 -> 첫해 부담금 350만 원', 3500000, 1, 0, 0, { paid: 3500000 }],
];
for (const [name, w, n, g, r, exp] of cases) {
  const x = calc(w, n, g, r);
  for (const k of Object.keys(exp)) assert.strictEqual(x[k], exp[k], name + ' ' + k + '=' + x[k]);
  console.log('PASS', name, JSON.stringify(x));
}
// UI 기본값(300만 원, 10년, 3%, 5%) 렌더 확인 — 최소 DOM 스텁
const vals = { 'pd-wage': '3000000', 'pd-years': '10', 'pd-g': '3', 'pd-r': '5' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['pd-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('39,143,196원'));
assert.ok(outP.join().includes('42,746,737원'));
console.log('PASS UI');
