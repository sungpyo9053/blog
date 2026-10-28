// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('raw < found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.severanceCalc;
const cases = [
  ['고용노동부 예시 1,080일 · 88,641원 31전', '2014-10-02', '2017-09-16', 7080000, 4000000, 300000, 92, { days: 1080, eligible: true, payable: 7868433 }],
  ['월급 300만 원 3년 7개월', '2023-03-02', '2026-10-01', 9000000, 0, 0, 92, { days: 1309, eligible: true, payable: 10525014 }],
  ['1년 미만(364일) -> 0', '2024-11-01', '2025-10-31', 9000000, 0, 0, 92, { days: 364, eligible: false, payable: 0 }],
  ['경계: 딱 365일 -> 대상', '2024-11-01', '2025-11-01', 9000000, 0, 0, 92, { days: 365, eligible: true }],
];
for (const [name, i, o, a, b, c, n, exp] of cases) {
  const r = calc(i, o, a, b, c, n);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ days: r.days, avg: +r.avg.toFixed(2), payable: r.payable, eligible: r.eligible }));
}
assert.strictEqual(calc('2014-10-02', '2017-09-16', 7080000, 4000000, 300000, 92).avg.toFixed(2), '88641.30');
console.log('PASS 1일 평균임금 88,641.30원(고용노동부 88,641원 31전)');
// UI 렌더 확인 — 최소 DOM 스텁
function ui(vals) {
  const outP = [], h = {};
  const el = id => ({ value: vals[id], style: {}, addEventListener(ev, f) { h[id + ev] = f; }, set innerHTML(v) { outP.length = 0; }, set textContent(v) { outP.push(v); }, appendChild(p) { outP.push(p.textContent); } });
  const els = {}; ['sv-out-box', ...Object.keys(vals)].forEach(id => els[id] = el(id));
  global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
  eval(src);
  return { out: outP, els, h };
}
const base = { 'sv-in': '2014-10-02', 'sv-out': '2017-09-16', 'sv-a': '7080000', 'sv-b': '4000000', 'sv-c': '300000', 'sv-d': '92' };
let u = ui(base);
console.log('UI 기본값 출력:', u.out.join(' | '));
assert.ok(u.out.join().includes('예상 퇴직금 7,868,433원 (세전)'));
u = ui(Object.assign({}, base, { 'sv-in': '2024-11-01', 'sv-out': '2025-10-31', 'sv-a': '9000000', 'sv-b': '0', 'sv-c': '0' }));
console.log('UI 1년 미만 출력:', u.out.join(' | '));
assert.ok(u.out.join().includes('법정 퇴직금 대상이 아니다'));
// 퇴사일 변경 시 3개월 일수 자동 계산 (2026-10-01 -> 7/1~9/30 = 92일)
u = ui(Object.assign({}, base, { 'sv-in': '2023-03-02', 'sv-a': '9000000', 'sv-b': '0', 'sv-c': '0', 'sv-d': '0' }));
u.els['sv-out'].value = '2026-10-01'; u.h['sv-outchange']();
assert.strictEqual(u.els['sv-d'].value, 92);
console.log('PASS 퇴사일 변경 -> 3개월 일수 92 자동 계산:', u.out.join(' | '));
