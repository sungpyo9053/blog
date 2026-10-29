// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^'\n]*'/g)) if (s.includes('<')) throw new Error('< in string ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.climateCardCalc;
const cases = [
  ['1일 3회 지하철 -> 일반이 쌈', 1, 3, 1550, 'general', { normal: 4650, shortCost: 5000, beTrips: 4 }],
  ['1일 4회 지하철 -> 1일권 이득', 1, 4, 1550, 'general', { normal: 6200, shortCost: 5000 }],
  ['7일 출퇴근 10회', 7, 10, 1550, 'general', { normal: 15500, shortCost: 20000, beTrips: 13 }],
  ['7일 13회', 7, 13, 1550, 'general', { normal: 20150, shortCost: 20000 }],
  ['버스 7일 손익분기 14', 7, 0, 1500, 'general', { beTrips: 14 }],
  ['버스 5일 손익분기 11', 5, 0, 1500, 'general', { beTrips: 11, shortCost: 15000 }],
  ['2일 8,000 / 3일 10,000', 2, 0, 1550, 'general', { shortCost: 8000, beTrips: 6 }],
  ['3일권', 3, 0, 1550, 'general', { shortCost: 10000, beTrips: 7 }],
  ['30일 단기권 88,000', 30, 44, 1550, 'general', { normal: 68200, shortCost: 88000 }],
  ['청소년 7일 13,000 / 900원 15회', 7, 0, 900, 'teen', { shortCost: 13000, beTrips: 15 }],
  ['청소년 30일 60,000', 30, 40, 900, 'teen', { shortCost: 60000, pass: null }],
];
for (const [name, d, t, f, ty, exp] of cases) {
  const r = calc(d, t, f, ty);
  for (const k of Object.keys(exp)) assert.deepStrictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 기후동행패스: 일반 44회 68,200 -> 20% 13,640 환급, 실부담 54,560
let p = calc(30, 44, 1550, 'general').pass;
assert.strictEqual(p.refund, 13640); assert.strictEqual(p.pay, 54560);
// 77,500 경계: 20% = 초과분 15,500
p = calc(30, 50, 1550, 'general').pass; assert.strictEqual(p.refund, 15500);
// 100,000원 -> 정액 초과분 38,000 > 20% 20,000
p = calc(30, 100, 1000, 'general').pass; assert.strictEqual(p.refund, 38000); assert.strictEqual(p.pay, 62000);
// 청년 30% vs 55,000
p = calc(30, 40, 1550, 'youth').pass; assert.strictEqual(p.refund, 18600);
p = calc(30, 100, 1000, 'youth').pass; assert.strictEqual(p.refund, 45000); assert.strictEqual(p.pay, 55000);
// 15회 미만 환급 없음
p = calc(30, 14, 1550, 'general').pass; assert.strictEqual(p.refund, 0); assert.strictEqual(p.eligible, false);
// 28일 미만은 패스 비교 안 함
assert.strictEqual(calc(27, 40, 1550, 'general').pass, null);
console.log('PASS 기후동행패스 환급 7건');
// UI 기본값(7일, 14회, 1,550원, 일반) 렌더 확인 — 최소 DOM 스텁
const vals = { 'cc-days': '7', 'cc-trips': '14', 'cc-fare': '1550', 'cc-type': 'general' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['cc-out', 'cc-sub', 'cc-bus', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('21,700원'));
assert.ok(outP.join().includes('7일권 1장'));
