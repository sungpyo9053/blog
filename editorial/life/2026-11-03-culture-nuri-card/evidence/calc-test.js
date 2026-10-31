// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.cultureNuriCalc, check = window.cultureNuriCheck;
const cases = [
  ['성인 1980년생, 2/2 발급, 0원 사용, 11/3 기준', [1980, '2026-02-02', 0, '2026-11-03'], { eligible: true, extra: false, amount: 150000, remain: 150000, daysLeft: 59, usableDays: 333, perDay: 2542, issueOk: true, auto2026Rule: false }],
  ['청소년 2010년생 16만, 4만 사용', [2010, '2026-03-10', 40000, '2026-11-03'], { extra: true, amount: 160000, remain: 120000, auto2026Rule: true, minorLodging: true }],
  ['경계 2008년생 추가+숙박제한', [2008, '2026-02-02', 0, '2026-11-03'], { extra: true, amount: 160000, minorLodging: true }],
  ['경계 2007년생 추가 없음', [2007, '2026-02-02', 0, '2026-11-03'], { extra: false, amount: 150000, minorLodging: false }],
  ['경계 2013년생 추가', [2013, '2026-02-02', 0, '2026-11-03'], { extra: true, amount: 160000 }],
  ['경계 2014년생 추가 없음', [2014, '2026-02-02', 0, '2026-11-03'], { extra: false, amount: 150000 }],
  ['경계 1962년생 추가', [1962, '2026-02-02', 0, '2026-11-03'], { extra: true, amount: 160000 }],
  ['경계 1966년생 추가', [1966, '2026-02-02', 0, '2026-11-03'], { extra: true, amount: 160000 }],
  ['경계 1961·1967년생 추가 없음', [1961, '2026-02-02', 0, '2026-11-03'], { extra: false, amount: 150000 }],
  ['1967년생', [1967, '2026-02-02', 0, '2026-11-03'], { extra: false }],
  ['2020년생 대상', [2020, '2026-02-02', 0, '2026-11-03'], { eligible: true }],
  ['2021년생 대상 아님', [2021, '2026-02-02', 0, '2026-11-03'], { eligible: false, amount: 0 }],
  ['3만 원 정확히 사용 -> 2026 규칙 충족', [1980, '2026-02-02', 30000, '2026-11-03'], { auto2026Rule: true, remain: 120000 }],
  ['29,900원 사용 -> 미충족', [1980, '2026-02-02', 29900, '2026-11-03'], { auto2026Rule: false }],
  ['초과 사용 -> 잔액 0', [1980, '2026-02-02', 200000, '2026-11-03'], { over: true, remain: 0 }],
  ['12/31 당일 -> 1일 남음', [1980, '2026-11-30', 0, '2026-12-31'], { daysLeft: 1, usableDays: 32, issueOk: true, perDay: 150000 }],
  ['2027/1/1 -> 소멸', [1980, '2026-02-02', 0, '2027-01-01'], { expired: true, remain: 0, daysLeft: 0 }],
  ['12/1 발급 -> 발급 기간 밖', [1980, '2026-12-01', 0, '2026-12-01'], { issueOk: false }],
  ['2/1 발급 -> 발급 기간 밖', [1980, '2026-02-01', 0, '2026-11-03'], { issueOk: false }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
const chk = [['book', 1980, 'ok'], ['movie', 1980, 'ok'], ['hotel', 1980, 'cond'], ['hotel', 2008, 'no'], ['hotel', 2007, 'cond'], ['food', 1980, 'no'], ['cloth', 1980, 'no'], ['voucher', 1980, 'no'], ['abroad', 1980, 'no'], ['spa', 1980, 'ok'], ['beauty', 1980, 'no'], ['zzz', 1980, 'unknown']];
for (const [k, b, s] of chk) { const c = check(k, b); assert.strictEqual(c.status, s, k + b); console.log('PASS 업종', k, b, c.status, c.text.slice(0, 30)); }
// 모든 select 옵션이 RULES에 있는지
const opts = [...html.matchAll(/<option value="([a-z]+)"/g)].map(m => m[1]);
for (const o of opts) assert.notStrictEqual(check(o, 1980).status, 'unknown', 'missing rule ' + o);
console.log('PASS select 옵션', opts.length, '개 모두 규칙 있음');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'cn-birth': '1980', 'cn-issue': '2026-02-02', 'cn-used': '0', 'cn-today': '2026-11-03', 'cn-type': 'hotel' };
const outs = { 'cn-out': [], 'cn-check': [] };
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { if (outs[id]) outs[id].length = 0; }, appendChild(p) { outs[id].push(p.textContent); } });
const els = {}; [...Object.keys(outs), ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력:', outs['cn-out'].join(' | '));
console.log('UI 업종:', outs['cn-check'].join(' | '));
assert.ok(outs['cn-out'].join().includes('150,000원'));
assert.ok(outs['cn-out'].join().includes('59일'));
assert.ok(outs['cn-check'][0].startsWith('조건부'));
console.log('ALL PASS');
