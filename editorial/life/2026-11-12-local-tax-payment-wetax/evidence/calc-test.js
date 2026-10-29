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
const c = window.localTaxCalc;
const iso = d => d.toISOString().slice(0, 10);
// 가산세 (지방세기본법 제55조, 시행령 제34조)
const cases = [
  ['고지 30만 9/30 기한 20일 늦음 -> 3%만(45만 미만)', 300000, 'notice', '2026-09-30', 20, { g3: 9000, g4: 0, total: 9000, noMonthly: true }],
  ['고지 30만 1년 늦어도 3%에서 멈춤', 300000, 'notice', '2026-09-30', 365, { total: 9000 }],
  ['고지 100만 7/31 기한 11/12 납부 -> 3개월', 1000000, 'notice', '2026-07-31', 104, { months: 3, g3: 30000, g4: 19800, total: 49800 }],
  ['경계: 7/31 기한 8/31 납부 -> 0개월', 1000000, 'notice', '2026-07-31', 31, { months: 0, total: 30000 }],
  ['경계: 7/31 기한 9/1 납부 -> 1개월', 1000000, 'notice', '2026-07-31', 32, { months: 1, total: 36600 }],
  ['상한: 고지 100만 6000일 -> 60개월 426,000', 1000000, 'notice', '2020-01-31', 6000, { months: 60, total: 426000 }],
  ['경계: 45만 정확히 -> 월 가산 적용', 450000, 'notice', '2026-06-30', 40, { months: 1, g3: 13500, g4: 2970, total: 16470 }],
  ['신고납부 취득세 300만 30일 -> 19,800', 3000000, 'self', '2026-09-30', 30, { g1: 19800, total: 19800 }],
  ['신고납부 하루 100만 -> 220', 1000000, 'self', '2026-09-30', 1, { g1: 220 }],
  ['신고납부 75% 한도: 100만 4000일', 1000000, 'self', '2015-01-31', 4000, { g1: 750000, capped: true }],
  ['기한 내 0일 -> 0', 1000000, 'notice', '2026-09-30', 0, { total: 0 }],
];
for (const [name, amt, type, dl, days, exp] of cases) {
  const r = c.late(amt, type, dl, days);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ pay: iso(r.pay), months: r.months, g1: r.g1, g3: r.g3, g4: r.g4, total: r.total }));
}
assert.strictEqual(iso(c.late(1000000, 'notice', '2026-07-31', 104).pay), '2026-11-12');
// 납기 조회 (위택스 일정 + 지방세법, 토·일 이월)
const show = (y, t, m) => c.list(y, t, m).map(o => o.label + ' ' + iso(o.d.end) + '->' + iso(o.d.real));
const reg27 = c.list(2027, 'reg', 1)[0];
assert.strictEqual(iso(reg27.d.real), '2027-02-01'); // 2027-01-31 일요일
const car26 = c.list(2026, 'car', 12)[0];
assert.strictEqual(iso(car26.d.real), '2026-12-31'); // 목요일
const prop27 = c.list(2027, 'prop', 7)[0];
assert.strictEqual(iso(prop27.d.real), '2027-08-02'); // 2027-07-31 토요일
const res24 = c.list(2024, 'res', 8);
assert.ok(res24.every(o => iso(o.d.real) === '2024-09-02')); // 행안부 2024 주민세 9.2.과 일치
assert.strictEqual(c.list(2026, 'inc', 0).length, 14); // 매월 12 + 4월 + 5월
assert.strictEqual(c.list(2026, 'prop', 3).length, 0);
console.log('PASS 납기:', show(2027, 'reg', 1), show(2027, 'prop', 7), show(2024, 'res', 8), show(2026, 'car', 12));
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'lt-year': '2027', 'lt-tax': 'all', 'lt-month': '0', 'lt-amt': '1000000', 'lt-type': 'notice', 'lt-dl': '2026-09-30', 'lt-days': '45' };
const outs = { 'lt-due': [], 'lt-out': [] };
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { if (outs[id]) outs[id].length = 0; }, appendChild(p) { outs[id].push(p.textContent); } });
const els = {}; [...Object.keys(vals), ...Object.keys(outs)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 납기 출력 줄 수:', outs['lt-due'].length, '| 첫 줄:', outs['lt-due'][0]);
console.log('UI 가산세 출력:', outs['lt-out'].join(' | '));
assert.ok(outs['lt-out'].join().includes('36,600원')); // 9/30+45일=11/14 -> 1개월: 30,000+6,600
