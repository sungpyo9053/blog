// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^'\n]*'/g) || []) if (s.indexOf('<') >= 0) throw new Error('< in string literal: ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.lotteryTaxCalc;
const cases = [
  ['5천원 비과세', 5000, 1000, 1, { exempt: true, totalTax: 0, net: 5000 }],
  ['200만원 경계 비과세', 2000000, 1000, 1, { exempt: true, totalTax: 0, net: 2000000 }],
  ['200만1원 과세(전액)', 2000001, 1000, 1, { exempt: false, income: 1999001, incomeTax: 399800, localTax: 39980 }],
  ['300만원', 3000000, 1000, 1, { incomeTax: 599800, localTax: 59980, totalTax: 659780, net: 2340220 }],
  ['6천만원', 60000000, 1000, 1, { incomeTax: 11999800, localTax: 1199980, net: 46800220 }],
  ['3억 경계', 300000000, 1000, 1, { incomeTax: 59999800, localTax: 5999980, net: 234000220 }],
  ['20억', 2000000000, 1000, 1, { incomeTax: 569999700, localTax: 56999970, totalTax: 626999670, net: 1373000330 }],
  ['30억', 3000000000, 1000, 1, { incomeTax: 869999700, localTax: 86999970, totalTax: 956999670, net: 2043000330 }],
  ['구입비 0 20억', 2000000000, 0, 1, { incomeTax: 570000000, localTax: 57000000, net: 1373000000 }],
  ['연금 1등 700만x240', 7000000, 1000, 240, { exempt: false, incomeTax: 1400000, localTax: 140000, net: 5460000, total: 1680000000 }],
  ['연금 2등 100만x120 합계 과세', 1000000, 0, 120, { exempt: false, incomeTax: 200000, localTax: 20000, net: 780000 }],
  ['분할 합계 200만 이하 비과세', 100000, 0, 20, { exempt: true, totalTax: 0 }],
];
for (const [name, a, c, m, exp] of cases) {
  const r = calc(a, c, m);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 (20억, 구입비 1,000원, 일시금)
const vals = { 'lt-mode': '1', 'lt-amt': '2000000000', 'lt-cost': '1000', 'lt-months': '240' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, textContent: '', addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['lt-out', 'lt-cost-row', 'lt-months-row', 'lt-amt-label', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('1,373,000,330원'));
