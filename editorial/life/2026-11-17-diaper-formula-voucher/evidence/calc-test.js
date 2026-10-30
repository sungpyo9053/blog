// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g) || []) if (lit.indexOf('<') >= 0) throw new Error('< in string literal ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.diaperVoucherCalc;
// 관악구보건소 신청일별 표 + 복지로 2026 책자 예시(4개월째 날~5개월째 날 전날 → 20개월)
const cases = [
  ['출생일 당일', '2026-01-01', '2026-01-01', 90000, 1, { months: 24, total: 2160000 }],
  ['60일째 날(3/1)', '2026-01-01', '2026-03-01', 90000, 1, { dayN: 60, months: 24 }],
  ['61일째 날(3/2) -> 22개월', '2026-01-01', '2026-03-02', 90000, 1, { dayN: 61, months: 22, total: 1980000 }],
  ['3개월째 날 전날(3/31) -> 22', '2026-01-01', '2026-03-31', 90000, 1, { months: 22 }],
  ['3개월째 날(4/1) -> 21', '2026-01-01', '2026-04-01', 90000, 1, { months: 21, total: 1890000 }],
  ['책자 예: 4개월째 날(5/1) -> 20', '2026-01-01', '2026-05-01', 90000, 1, { months: 20, total: 1800000 }],
  ['5개월째 날 전날(5/31) -> 20', '2026-01-01', '2026-05-31', 90000, 1, { months: 20 }],
  ['12개월째 날 -> 12', '2026-01-01', '2027-01-01', 90000, 1, { months: 12, total: 1080000 }],
  ['23개월째 날 -> 1', '2026-01-01', '2027-12-01', 90000, 1, { months: 1, total: 90000 }],
  ['만 2년 전날(신청 마지막 날) -> 1', '2026-01-01', '2027-12-31', 90000, 1, { months: 1 }],
  ['만 2년 되는 날 -> 0', '2026-01-01', '2028-01-01', 90000, 1, { months: 0, total: 0 }],
  ['7/1생 61일째 날(8/30), 2개월째 날 전 -> 표대로 22', '2026-07-01', '2026-08-30', 90000, 1, { dayN: 61, months: 22 }],
  ['기저귀+분유 24개월 -> 480만', '2026-09-01', '2026-09-10', 200000, 1, { months: 24, total: 4800000 }],
  ['쌍둥이 기저귀 24개월 -> 432만', '2026-09-01', '2026-09-10', 90000, 2, { total: 4320000 }],
  ['월말 출생 1/31 +1개월 = 2/28 처리', '2026-01-31', '2026-02-28', 90000, 1, { fullMonths: 1, months: 24 }],
];
for (const [name, b, a, m, k, exp] of cases) {
  const r = calc(b, a, m, k);
  for (const key of Object.keys(exp)) assert.strictEqual(r[key], exp[key], name + ' ' + key + '=' + r[key]);
  console.log('PASS', name, JSON.stringify({ dayN: r.dayN, fullMonths: r.fullMonths, months: r.months, total: r.total }));
}
assert.strictEqual(calc('2026-01-01', '2026-01-01', 90000, 1).deadline60, '2026년 3월 1일');
assert.strictEqual(calc('2026-01-01', '2026-01-01', 90000, 1).deadline, '2027년 12월 31일');
assert.ok(calc('2026-05-01', '2026-04-01', 90000, 1).error);
assert.ok(calc('', '2026-04-01', 90000, 1).error);
console.log('PASS 마감일·오류 입력 4개');
// 표 값 검산: 표 행의 개월 × 9만/20만
for (const [mo, a, b2] of [[24, 2160000, 4800000], [22, 1980000, 4400000], [21, 1890000, 4200000], [18, 1620000, 3600000], [12, 1080000, 2400000], [6, 540000, 1200000], [1, 90000, 200000]]) {
  assert.ok(html.includes(a.toLocaleString('en-US') + '원') && html.includes(b2.toLocaleString('en-US') + '원'), 'table ' + mo);
}
console.log('PASS 표 값 14개');
// UI 렌더 확인 — 최소 DOM 스텁 (출생 2026-08-01, 신청 2026-10-30, 기저귀만)
const vals = { 'dv-birth': '2026-08-01', 'dv-apply': '', 'dv-kind': '90000', 'dv-kids': '1' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { if (id !== 'dv-apply') vals[id] = v; }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['dv-out', 'dv-today', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
vals['dv-apply'] = '2026-10-30';
eval(src);
console.log('UI 출력:', outP.join(' | '));
assert.ok(outP.join().includes('22개월'));
assert.ok(outP.join().includes('1,980,000원'));
