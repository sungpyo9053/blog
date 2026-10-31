// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'[^'\n]*'/g)) if (m[0].includes('<')) throw new Error('< in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD'); JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.koreanAgeCalc;
const cases = [
  ['2000.11.26생 @2026.11.1 (본문 표)', '2000-11-26', '2026-11-01', { man: 25, yearAge: 26, koreanAge: 27, beforeBirthday: true, dday: 25, nextAge: 26 }],
  ['1990.5.10생 @2026.5.9', '1990-05-10', '2026-05-09', { man: 35, dday: 1 }],
  ['1990.5.10생 @2026.5.10 생일 당일', '1990-05-10', '2026-05-10', { man: 36, dday: 0, nextAge: 36 }],
  ['1990.5.10생 @2026.11.1', '1990-05-10', '2026-11-01', { man: 36 }],
  ['2026.3.15생 @2026.11.1 → 0세 7개월', '2026-03-15', '2026-11-01', { man: 0, months: 7 }],
  ['2004.2.29생 @2027.2.28 → 22', '2004-02-29', '2027-02-28', { man: 22, dday: 1, nextAge: 23 }],
  ['2004.2.29생 @2027.3.1 → 23', '2004-02-29', '2027-03-01', { man: 23, dday: 0 }],
  ['2004.2.29생 @2028.2.29 윤년 → 24', '2004-02-29', '2028-02-29', { man: 24, dday: 0 }],
  ['2007.12.31생 @2026.1.1 청소년 아님', '2007-12-31', '2026-01-01', { man: 18, adult: true, youthFreeYear: 2026 }],
  ['2008.1.1생 @2026.11.1 청소년', '2008-01-01', '2026-11-01', { adult: false, youthFreeYear: 2027, militaryYear: 2026 }],
  ['2019.6.1생 초등 입학', '2019-06-01', '2026-11-01', { schoolYear: 2026, schoolEarly: 2025, schoolLate: 2027 }],
  ['생일 지난 뒤 다음 생일은 내년', '2000-01-05', '2026-11-01', { man: 26, nextAge: 27, dday: 65 }],
  ['태어난 날 1일째', '2026-11-01', '2026-11-01', { man: 0, months: 0, daysLived: 1 }],
];
for (const [name, b, r, exp] of cases) {
  const x = calc(b, r);
  for (const k of Object.keys(exp)) assert.strictEqual(x[k], exp[k], name + ' ' + k + '=' + x[k]);
  console.log('PASS', name, JSON.stringify(x));
}
assert.ok(calc('2026-11-02', '2026-11-01').error); assert.ok(calc('2026-02-30', '2026-11-01').error); assert.ok(calc('', '2026-11-01').error);
console.log('PASS 오류 입력 3개');
// 본문 나이표 검산: 생일 전/후/연/세는
const rows = [...html.matchAll(/<tr><td>(\d{4})년생<\/td><td>(\d+)세<\/td><td>(\d+)세<\/td><td>(\d+)세<\/td><td>(\d+)살<\/td><\/tr>/g)];
assert.strictEqual(rows.length, 18);
for (const [, y, pre, post, ya, ka] of rows) {
  const a = calc(y + '-12-31', '2026-06-01'), c = calc(y + '-01-01', '2026-06-01');
  assert.deepStrictEqual([a.man, c.man, c.yearAge, c.koreanAge], [+pre, +post, +ya, +ka], y);
}
console.log('PASS 나이표 ' + rows.length + '행');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'ka-birth': '2000-11-26', 'ka-ref': '2026-11-01' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ka-out', 'ka-today', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('만 나이: 25세'));
