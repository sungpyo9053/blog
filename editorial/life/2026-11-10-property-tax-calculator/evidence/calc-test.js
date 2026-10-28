// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.propertyTaxCalc;
const cases = [
  ['행안부 2025.4 예: 1주택 공시 4억 -> 44%, 재산세 17만2천', [4e8, true, true, 0, 0], { pct: 44, base: 176000000, tax: 172000, special: true }],
  ['1주택 4억 도시지역분·교육세·합계', [4e8, true, true, 0, 0], { urban: 246400, edu: 34400, total: 452800, july: 226400, sep: 226400 }],
  ['다주택 4억 -> 60%, 표준세율 42만', [4e8, false, true, 0, 0], { pct: 60, base: 240000000, tax: 420000, total: 840000 }],
  ['경계 3억 1주택 -> 43%', [3e8, true, true, 0, 0], { pct: 43, base: 129000000, tax: 99000 }],
  ['경계 3억1원 1주택 -> 44%', [300000001, true, true, 0, 0], { pct: 44 }],
  ['경계 6억 -> 44%, 6억 초과 -> 45%', [6e8, true, true, 0, 0], { pct: 44, tax: 348000 }],
  ['9억 1주택 -> 45%, 특례세율', [9e8, true, true, 0, 0], { pct: 45, base: 405000000, tax: 787500, special: true }],
  ['9억 초과 1주택 -> 45% + 표준세율', [12e8, true, true, 0, 0], { pct: 45, base: 540000000, tax: 1530000, special: false }],
  ['1억 1주택 -> 20만 이하 7월 일괄 대상', [1e8, true, true, 0, 0], { tax: 21500, urban: 60200, edu: 4300, total: 86000, oneShot: true }],
  ['도시지역분 미적용', [4e8, true, false, 0, 0], { urban: 0, total: 206400 }],
  ['비율 직접 입력 50%', [4e8, false, true, 50, 0], { pct: 50, base: 200000000 }],
  ['과세표준상한: 작년 3억 -> 올해 4억(1주택 44%)', [4e8, true, true, 0, 3e8], { base: 140800000, capped: true }],
  ['과세표준상한 미적용(작년 4억)', [4e8, true, true, 0, 4e8], { base: 176000000, capped: false }],
  ['분할납부: 다주택 공시 30억 회차 재산세 250만 초과', [30e8, false, true, 0, 0], { base: 1800000000, tax: 6570000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 표 값 검산
const table = { 1: [21500, 86000, 60000, 156000], 2: [56000, 187600, 150000, 348000], 3: [99000, 299400, 270000, 576000], 4: [172000, 452800, 420000, 840000], 6: [348000, 787200, 810000, 1476000], 9: [787500, 1512000, 1530000, 2592000], 12: [1530000, 2592000, 2250000, 3708000] };
for (const [e, row] of Object.entries(table)) {
  const a = calc(e * 1e8, true, true, 0, 0), b = calc(e * 1e8, false, true, 0, 0);
  assert.deepStrictEqual([a.tax, a.total, b.tax, b.total], row, e + '억');
  assert.ok(html.includes(row[1].toLocaleString('ko-KR') + '원'));
}
console.log('PASS 표 값 7행');
// 분할납부 금액: 30억 다주택 회차 재산세 (6,570,000+2,520,000)/2=4,545,000 -> 250만 초과분 2,045,000
assert.strictEqual(calc(30e8, false, true, 0, 0).split, 2045000);
console.log('PASS 분할납부 2,045,000');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'pt-price': '400000000', 'pt-one': '1', 'pt-ratio': '', 'pt-prev': '' };
const outP = [];
const el = id => ({ value: vals[id], checked: true, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['pt-out', 'pt-urban', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('452,800원'));
