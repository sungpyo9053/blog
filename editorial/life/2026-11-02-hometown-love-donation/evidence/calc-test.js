// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^'\n]*'/g) || []) if (s.indexOf('<') >= 0) throw new Error('< in string ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.hometownDonationCalc;
const cases = [
  ['고향사랑e음 예: 10만 -> 소득세 90,909 + 지방 9,090', 100000, false, -1, { incomeTax: 90909, localTax: 9090, total: 99999, gift: 30000 }],
  ['고향사랑e음 예: 20만 -> 14.4만', 200000, false, -1, { incomeTax: 130909, total: 143999, gift: 60000 }],
  ['행안부 예: 50만 -> 19만 3,500 (원 단위 버림 193,499)', 500000, false, -1, { total: 193499, gift: 150000 }],
  ['고향사랑e음 예: 100만 -> 27.6만', 1000000, false, -1, { incomeTax: 250909, localTax: 25090, total: 275999, gift: 300000, net: 424001 }],
  ['고향사랑e음 예: 100만 특별재난 -> 40.8만', 1000000, true, -1, { incomeTax: 370909, total: 407999 }],
  ['한도: 2,500만 -> 2,000만까지', 25000000, false, -1, { over: true, base: 20000000, total: 3410999, gift: 6000000 }],
  ['산출세액 한도 5만', 200000, false, 50000, { incomeTax: 50000, localTax: 5000, capped: true }],
  ['산출세액 0', 100000, false, 0, { incomeTax: 0, total: 0, capped: true, gift: 30000 }],
  ['0원', 0, false, -1, { total: 0, gift: 0 }],
];
for (const [name, a, d, cap, exp] of cases) {
  const r = calc(a, d, cap);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표 값 검산
const table = [[100000, 99999, 30000], [200000, 143999, 60000], [300000, 160499, 90000, 49501], [500000, 193499, 150000, 156501],
  [1000000, 275999, 300000, 424001], [5000000, 935999, 1500000, 2564001], [20000000, 3410999, 6000000, 10589001]];
for (const [a, tot, g, net] of table) {
  const r = calc(a, false, -1);
  assert.strictEqual(r.total, tot); assert.strictEqual(r.gift, g);
  if (net !== undefined) assert.strictEqual(r.net, net); else assert.ok(r.net <= 0);
  assert.ok(html.includes(tot.toLocaleString('en-US') + '원'), 'table missing ' + tot);
}
console.log('PASS 표 값 7행');
// UI 기본값(20만 원, 답례품 받음) 렌더 확인 — 최소 DOM 스텁
const vals = { 'hl-amt': { value: '200000' }, 'hl-dis': { checked: false }, 'hl-gift': { checked: true }, 'hl-cap': { value: '' } };
const outP = [];
const el = id => Object.assign({ style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } }, vals[id] || {});
const els = {}; ['hl-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }), querySelectorAll: () => [] };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('143,999원'));
