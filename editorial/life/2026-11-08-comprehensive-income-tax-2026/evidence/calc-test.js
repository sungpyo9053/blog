// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.incomeTaxCalc;
const cases = [
  ['국세청 예시 과표 3,000만 -> 324만', 30000000, { rate: 15, tax: 3240000, local: 324000 }],
  ['1,000만 6%', 10000000, { rate: 6, tax: 600000, local: 60000, effTotal: 6.6 }],
  ['경계 1,400만 = 6%', 14000000, { rate: 6, tax: 840000 }],
  ['경계 1,400만+1 = 15%', 14000001, { rate: 15, tax: 840000 }],
  ['1,410만 = 84만+1.5만', 14100000, { tax: 855000 }],
  ['5,000만', 50000000, { rate: 15, tax: 6240000, effTotal: 13.73 }],
  ['8,000만', 80000000, { rate: 24, tax: 13440000, effTotal: 18.48 }],
  ['1억', 100000000, { rate: 35, tax: 19560000, effTotal: 21.52 }],
  ['2억', 200000000, { rate: 38, tax: 56060000, local: 5606000, effTotal: 30.83 }],
  ['10억 초과', 2000000000, { rate: 45, tax: 834060000 }],
  ['0원', 0, { tax: 0 }],
];
for (const [name, base, exp] of cases) {
  const r = calc(base);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 누진공제 방식 = 구간별 누적 방식 (모든 경계에서 연속)
const edges = [0, 14e6, 50e6, 88e6, 150e6, 300e6, 500e6, 1e9], rates = [6, 15, 24, 35, 38, 40, 42, 45];
function stepwise(b) { let t = 0; for (let i = 0; i < edges.length; i++) { const hi = i + 1 < edges.length ? edges[i + 1] : Infinity; if (b > edges[i]) t += (Math.min(b, hi) - edges[i]) * rates[i] / 100; } return Math.floor(t); }
for (let b = 1e6; b <= 1.2e9; b += 7e6 + 13) assert.ok(Math.abs(calc(b).tax - stepwise(b)) <= 1, 'stepwise ' + b);
for (const e of edges.slice(1)) assert.ok(Math.abs(calc(e).tax - stepwise(e)) <= 1 && Math.abs(calc(e + 1).tax - stepwise(e + 1)) <= 1, 'edge ' + e);
console.log('PASS 누진공제 방식 = 구간 누적 방식 (172개 표본 + 경계 14개)');
// UI 기본값 렌더 (과표 3,000만)
const outP = [];
const els = {
  'cit-base': { value: '30000000', addEventListener() {} },
  'cit-out': { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } },
};
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }), querySelectorAll: () => [{ addEventListener() {}, getAttribute: () => '14000000' }] };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('3,240,000원'));
