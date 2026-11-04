// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'[^'\n]*'/g)) if (m[0].includes('<')) throw new Error('< in string literal ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.financialIncomeTaxCalc, T = window.financialIncomeBasicTax;
const M = 10000;
// 기본세율 구간 경계 (소득세법 제55조)
[[14000000, 840000], [50000000, 6240000], [88000000, 15360000], [150000000, 37060000], [300000000, 94060000], [500000000, 174060000], [1000000000, 384060000], [1100000000, 429060000]]
  .forEach(([x, t]) => assert.strictEqual(T(x), t, 'T(' + x + ')'));
console.log('PASS 기본세율 경계 8개');
const cases = [
  ['예시1 이자1500+배당400 분리과세', [1500, 400, 0, 4000, 0.10], { over: false, wh: 2660000, whLocal: 266000, extra: 0 }],
  ['경계 정확히 2천만원 -> 분리', [2000, 0, 0, 10000, 0.10], { over: false, extra: 0 }],
  ['예시2 이자3000+다른4000 -> +10만', [3000, 0, 0, 4000, 0.10], { over: true, t1: 9040000, t2: 8940000, extra: 100000, extraLocal: 10000 }],
  ['예시3 이자5000+다른1억 -> +630만', [5000, 0, 0, 10000, 0.10], { t1: 32860000, t2: 26560000, extra: 6300000, extraLocal: 630000 }],
  ['예시4 배당G5000+다른1억 10% -> +435만', [0, 5000, 0, 10000, 0.10], { grossUp: 3000000, t1: 33910000, final: 30910000, extra: 4350000 }],
  ['예시4 11% -> +415.5만', [0, 5000, 0, 10000, 0.11], { grossUp: 3300000, extra: 4155000 }],
  ['예시5 이자5000 다른소득0 -> 0', [5000, 0, 0, 0, 0.10], { t1: 6040000, t2: 7000000, extra: 0 }],
  ['배당G3000+다른4000 -> 공제로 0', [0, 3000, 0, 4000, 0.10], { grossUp: 1000000, t1: 9280000, t2: 8940000, extra: 0 }],
  ['합산순서: 이자1500+배당G1000 -> 초과500 전부 G', [1500, 1000, 0, 10000, 0.10], { excess: 5000000, divGEx: 5000000, grossUp: 500000 }],
  ['합산순서: 이자1500+해외1000+G300 -> G는 초과분 300 전부', [1500, 300, 1000, 10000, 0.10], { excess: 8000000, divGEx: 3000000 }],
];
for (const [name, a, exp] of cases) {
  const r = calc(a[0] * M, a[1] * M, a[2] * M, a[3] * M, a[4]);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, 'extra=' + r.extra, 'method=' + r.method);
}
// UI 기본값 렌더 (이자 1500, 배당G 1500, 다른 4000, 10%)
const vals = { 'fi-int': '1500', 'fi-divg': '1500', 'fi-divn': '0', 'fi-other': '4000', 'fi-rate': '0.10' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['fi-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('30,000,000원'));
