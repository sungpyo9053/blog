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
const calc = window.brokerageFeeCalc;
const M = 10000;
const cases = [
  ['매매 5억 0.4%', 'sale', 'house', 50000 * M, 0, { rate: 4, fee: 2000000, both: 4000000 }],
  ['매매 10억 0.5% (보도자료 ~500만)', 'sale', 'house', 100000 * M, 0, { rate: 5, fee: 5000000 }],
  ['매매 9억 경계 0.5%', 'sale', 'house', 90000 * M, 0, { rate: 5, fee: 4500000 }],
  ['매매 2억 경계 0.4%', 'sale', 'house', 20000 * M, 0, { rate: 4, fee: 800000, capped: false }],
  ['매매 1.8억 한도 80만', 'sale', 'house', 18000 * M, 0, { rate: 5, raw: 900000, fee: 800000, capped: true }],
  ['매매 4,500만 한도 25만', 'sale', 'house', 4500 * M, 0, { rate: 6, raw: 270000, fee: 250000 }],
  ['매매 15억 0.7%', 'sale', 'house', 150000 * M, 0, { rate: 7, fee: 10500000 }],
  ['전세 3억 0.3%', 'jeonse', 'house', 30000 * M, 0, { rate: 3, fee: 900000 }],
  ['전세 8천만 한도 30만', 'jeonse', 'house', 8000 * M, 0, { rate: 4, raw: 320000, fee: 300000 }],
  ['전세 6억 0.4% (보도자료 240만)', 'jeonse', 'house', 60000 * M, 0, { rate: 4, fee: 2400000 }],
  ['월세 1천/50 -> 6천만 x100', 'monthly', 'house', 1000 * M, 50 * M, { amount: 60000000, used70: false, rate: 4, fee: 240000 }],
  ['월세 500/40 -> x70 3,300만', 'monthly', 'house', 500 * M, 40 * M, { amount: 33000000, used70: true, rate: 5, fee: 165000 }],
  ['월세 x100 정확히 5천만 -> x100 유지', 'monthly', 'house', 0, 50 * M, { amount: 50000000, used70: false, rate: 4 }],
  ['오피스텔 매매 3억 0.5%', 'sale', 'officetel', 30000 * M, 0, { rate: 5, cap: 0, fee: 1500000 }],
  ['오피스텔 전세 2억 0.4%', 'jeonse', 'officetel', 20000 * M, 0, { rate: 4, fee: 800000 }],
  ['상가 매매 3억 0.9% 이내', 'sale', 'other', 30000 * M, 0, { rate: 9, fee: 2700000 }],
];
for (const [name, k, p, a, r, exp] of cases) {
  const o = calc(k, p, a, r);
  for (const key of Object.keys(exp)) assert.strictEqual(o[key], exp[key], name + ' ' + key + '=' + o[key]);
  console.log('PASS', name, JSON.stringify(o));
}
// 본문 표 값 검산 (만원)
const rows = [[1, 50, 30], [2, 80, 60], [3, 120, 90], [5, 200, 150], [7, 280, 280], [9, 450, 360], [10, 500, 400], [12, 720, 600], [15, 1050, 900], [20, 1400, 1200]];
for (const [eok, s, l] of rows) {
  assert.strictEqual(calc('sale', 'house', eok * 1e8, 0).fee, s * M, eok + '억 매매');
  assert.strictEqual(calc('jeonse', 'house', eok * 1e8, 0).fee, l * M, eok + '억 임대');
}
console.log('PASS 본문 표 값 20개');
// UI 기본값(매매·주택·5억) 렌더 — 최소 DOM 스텁
const vals = { 'bf-kind': 'sale', 'bf-prop': 'house', 'bf-price': '50000', 'bf-rent': '50' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, textContent: '', addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['bf-out', 'bf-rent-row', 'bf-price-label', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('2,000,000원'));
vals['bf-kind'] = 'monthly'; vals['bf-price'] = '500'; vals['bf-rent'] = '40';
['bf-kind', 'bf-price', 'bf-rent'].forEach(id => els[id].value = vals[id]);
eval(src);
console.log('UI 월세 500/40 출력:', outP.join(' | '));
assert.ok(outP.join().includes('33,000,000원'));
assert.ok(outP.join().includes('165,000원'));
