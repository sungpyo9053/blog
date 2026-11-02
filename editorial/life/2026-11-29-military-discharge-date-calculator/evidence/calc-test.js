// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g)) if (lit.indexOf('<') >= 0) throw new Error('< in string literal ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.dischargeCalc;
const T = '2026-11-02';
const cases = [
  ['본문 예: 2026-03-02 육군 18', '2026-03-02', 18, 0, { end: '2027-09-01' }],
  ['1/31 육군 18 -> 7/30', '2026-01-31', 18, 0, { end: '2027-07-30' }],
  ['1/31 해군 20 -> 9월 31일 없음 -> 9/30', '2026-01-31', 20, 0, { end: '2027-09-30' }],
  ['1/30 해군 20 -> 9/29', '2026-01-30', 20, 0, { end: '2027-09-29' }],
  ['1/31 공군 21 -> 10/30', '2026-01-31', 21, 0, { end: '2027-10-30' }],
  ['윤년 2028-02-29 육군 18 -> 2029-08-28', '2028-02-29', 18, 0, { end: '2029-08-28', before: true }],
  ['윤년 2028-02-29 해군 20 -> 2029-10-28', '2028-02-29', 20, 0, { end: '2029-10-28' }],
  ['8/29 육군 -> 2028-02-28', '2026-08-29', 18, 0, { end: '2028-02-28' }],
  ['8/30 육군 -> 2028-02-29(윤년 말일)', '2026-08-30', 18, 0, { end: '2028-02-29' }],
  ['8/31 육군 -> 2028-02-29(윤년 말일)', '2026-08-31', 18, 0, { end: '2028-02-29' }],
  ['5/31 공군 -> 2029-02-28(평년 말일)', '2027-05-31', 21, 0, { end: '2029-02-28' }],
  ['6/30 해군 -> 2028-02-29', '2026-06-30', 20, 0, { end: '2028-02-29' }],
  ['12/31 사회복무 21 -> 2028-09-30', '2026-12-31', 21, 0, { end: '2028-09-30' }],
  ['불산입 10일 -> 9/11', '2026-03-02', 18, 10, { end: '2027-09-11' }],
  ['남은일수·복무율: 2025-06-02 육군 기준일 11/02', '2025-06-02', 18, 0, { end: '2026-12-01', total: 548, served: 519, remain: 29, pct: 94.7 }],
  ['입영 당일 1일차', '2026-11-02', 18, 0, { served: 1, end: '2028-05-01', total: 547 }],
  ['전역 이후 100%', '2024-01-02', 18, 0, { end: '2025-07-01', remain: 0, pct: 100 }],
];
for (const [name, e, m, x, exp] of cases) {
  const r = calc(e, m, x, T);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.strictEqual(calc('2026-02-30', 18, 0, T), null); console.log('PASS 없는 날짜(2/30) 입력 -> null');
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'dc-entry': '2026-03-02', 'dc-type': '18', 'dc-extra': '0', 'dc-today': '' };
const outP = []; let bar = '';
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = v; }, style: { set width(v) { bar = v; } }, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['dc-out', 'dc-bar', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
const RealDate = Date;
global.Date = class extends RealDate { constructor(...a) { if (a.length) super(...a); else super(2026, 10, 2); } static UTC(...a) { return RealDate.UTC(...a); } };
eval(src);
console.log('UI 기본값(입영 2026-03-02 육군, 기준일 2026-11-02) 출력:', outP.join(' | '), '| bar', bar);
assert.ok(outP.join().includes('2027년 9월 1일(수)'));
