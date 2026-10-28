// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('raw < inside string literal');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.nhcCalc;
const T = Date.UTC(2026, 9, 28); // 2026-10-28
const cases = [
  ['단태아·일반지역·2027-03-15', [1, false, false, 2027, 3, 15, T], { base: 1000000, extra: 0, total: 1000000, end: '2029-03-15' }],
  ['쌍태아 기본140+추가60 (복지부 "추가 지급금 60만원")', [2, false, false, 2027, 1, 10, T], { base: 1400000, extra: 600000, total: 2000000 }],
  ['쌍태아+분만취약지 220만원', [2, true, false, 2026, 11, 2, T], { total: 2200000, end: '2028-11-02' }],
  ['삼태아 300만원', [3, false, false, 2026, 5, 1, T], { total: 3000000, end: '2028-05-01' }],
  ['사태아 400만원 (정책브리핑 "400만 원")', [4, false, false, 2026, 5, 1, T], { total: 4000000 }],
  ['단태아+취약지+청소년산모 = 100+20+120', [1, true, true, 2026, 12, 1, T], { total: 2400000 }],
  ['윤일 2028-02-29 -> 2030-02-28', [1, false, false, 2028, 2, 29, T], { end: '2030-02-28' }],
  ['남은 일수: 2024-10-28 출산 -> 2026-10-28 0일', [1, false, false, 2024, 10, 28, T], { left: 0 }],
  ['기한 경과: 2024-01-01 출산 -> 음수', [1, false, false, 2024, 1, 1, T], { end: '2026-01-01' }],
  ['날짜 없음 -> end 빈 값', [1, false, false, 0, 0, 0, T], { end: '', left: null }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.ok(calc(1, false, false, 2024, 1, 1, T).left < 0);
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'nhc-n': '2', 'nhc-date': '2027-03-15' };
const outP = [];
const el = id => ({ value: vals[id], checked: id === 'nhc-rural', style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['nhc-out', 'nhc-n', 'nhc-rural', 'nhc-teen', 'nhc-date'].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(쌍태아+취약지):', outP.join(' | '));
assert.ok(outP.join().includes('2,200,000원'));
assert.ok(outP.join().includes('2029-03-15'));
console.log('ALL PASS');
