// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/'[^'\n]*</.test(src)) throw new Error('< inside string literal');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.virtualAssetTaxCalc;
// [이름, 양도대가, 2027이후 취득가, 2027전 취득가, 2026말 시가, 부대비용, 기대값]
const cases = [
  ['본문 예시: 1,500만 매수, 2026말 2천만, 3천만 매도, 수수료 10만', 30e6, 0, 15e6, 20e6, 1e5, { oldBasis: 20e6, income: 9.9e6, base: 7.4e6, tax: 1480000, local: 148000, total: 1628000 }],
  ['의제 없을 때 비교: 시가가 취득가보다 낮음', 30e6, 0, 15e6, 6e6, 1e5, { oldBasis: 15e6, income: 14.9e6, total: 2728000 }],
  ['경계: 소득금액 정확히 250만 -> 비과세', 12.5e6, 10e6, 0, 0, 0, { income: 2.5e6, exempt: true, total: 0 }],
  ['경계: 250만 1원 초과 -> 과세표준 1원', 12500001, 10e6, 0, 0, 0, { base: 1, tax: 0, local: 0, exempt: false }],
  ['손실 -> 세금 0', 5e6, 8e6, 0, 0, 5e4, { income: -3050000, loss: true, total: 0 }],
  ['손익 통산: 이익 500만 + 손실 300만 = 200만 -> 비과세', 18e6, 16e6, 0, 0, 0, { income: 2e6, exempt: true, total: 0 }],
];
for (const [name, a, b, c, d, e, exp] of cases) {
  const r = calc(a, b, c, d, e);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표 검산: 소득금액 -> 소득세/지방/합계
const table = [[5e6, 500000, 50000, 550000], [10e6, 1500000, 150000, 1650000], [30e6, 5500000, 550000, 6050000], [100e6, 19500000, 1950000, 21450000]];
for (const [inc, t, l, s] of table) { const r = calc(inc, 0, 0, 0, 0); assert.deepStrictEqual([r.tax, r.local, r.total], [t, l, s]); }
console.log('PASS 표 값 4행');
// UI 기본값 렌더 확인
const vals = { 'va-sale': '30000000', 'va-new': '0', 'va-old': '15000000', 'va-mkt': '20000000', 'va-fee': '100000' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['va-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('세금 합계: 1,628,000원'));
console.log('ALL PASS');
