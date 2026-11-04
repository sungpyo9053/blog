// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.silverPriceCalc;
const near = (a, b) => Math.abs(a - b) < 1e-6;
const cases = [
  ['원/g 2000, 1kg', [2000, 'g', 0, 1, 'kg', 1000, false], { grams: 1000, amount: 2000000, total: 2000000 }],
  ['원/g 2000, 1kg + 부가세', [2000, 'g', 0, 1, 'kg', 1000, true], { amount: 2000000, vat: 200000, total: 2200000 }],
  ['원/돈 7500 -> 1g 2000', [7500, 'don', 0, 1, 'g', 1000, false], { pricePerGram: 2000, amount: 2000 }],
  ['원/kg 2,000,000 -> 1돈 7500', [2000000, 'kg', 0, 1, 'don', 1000, false], { pricePerGram: 2000, grams: 3.75, amount: 7500 }],
  ['1트로이온스 = 31.1034768g, 62,207원', [2000, 'g', 0, 1, 'toz', 1000, false], { grams: 31.1034768, amount: 62207 }],
  ['1트로이온스 + 부가세 68,428', [2000, 'g', 0, 1, 'toz', 1000, true], { total: 68428 }],
  ['USD 30 x 1400 -> 1kg 1,350,331', [30, 'usdoz', 1400, 1, 'kg', 1000, false], { amount: 1350331 }],
  ['925 제품 10g -> 18,500 (+VAT 20,350)', [2000, 'g', 0, 10, 'g', 925, true], { pure: 9.25, amount: 18500, total: 20350 }],
  ['999 100g -> 199,800', [2000, 'g', 0, 100, 'g', 999, false], { pure: 99.9, amount: 199800 }],
  ['1kg -> 32.1507 toz, 266.67돈', [2000, 'g', 0, 1, 'kg', 1000, false], {}],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.ok(near(r[k], exp[k]), name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
const k = calc(2000, 'g', 0, 1, 'kg', 1000, false);
assert.ok(Math.abs(k.toz - 32.1507) < 1e-4 && Math.abs(k.don - 266.6667) < 1e-4);
assert.ok(Math.abs(calc(1, 'g', 0, 1, 'toz', 1000, false).don - 8.2943) < 1e-4);
console.log('PASS 본문 환산값(1kg=32.15toz=266.67돈, 1toz=8.29돈)');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'ag-price': '2000', 'ag-mode': 'g', 'ag-fx': '', 'ag-weight': '1', 'ag-unit': 'kg', 'ag-purity': '1000' };
function run(v, vat) {
  const outP = [];
  const el = id => ({ value: v[id], checked: id === 'ag-vat' ? vat : false, style: {}, addEventListener() {}, set innerHTML(x) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
  const els = {}; ['ag-out', 'ag-fx-row', 'ag-vat', ...Object.keys(v)].forEach(id => els[id] = el(id));
  global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
  eval(src);
  return { text: outP.join(' | '), fxRow: els['ag-fx-row'].style.display };
}
let u = run(vals, false);
console.log('UI 기본값 출력:', u.text);
assert.ok(u.text.includes('은 값: 2,000,000원') && u.fxRow === 'none');
u = run({ ...vals, 'ag-mode': 'usdoz', 'ag-price': '30', 'ag-fx': '' }, false);
console.log('UI 달러 모드, 환율 없음:', u.text);
assert.ok(u.text.includes('환율을 입력') && u.fxRow === 'block');
u = run({ ...vals, 'ag-mode': 'usdoz', 'ag-price': '30', 'ag-fx': '1400' }, true);
console.log('UI 달러 30 x 1400, 1kg, 부가세:', u.text);
assert.ok(u.text.includes('1,350,331원'));
u = run({ ...vals, 'ag-unit': 'g', 'ag-weight': '10', 'ag-purity': '925' }, false);
console.log('UI 925 10g:', u.text);
assert.ok(u.text.includes('18,500원') && u.text.includes('순은 함량: 9.25g'));
console.log('ALL PASS');
