// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.maternityLeaveCalc;
const cases = [
  ['우선지원 300만 단태아 90일', 3000000, 209, true, 'single', 90, { govTotal: 6600000, empFirst: 1600000, total: 8200000, shortfall: 800000, govLater: 2200000 }],
  ['대규모 300만 단태아 90일', 3000000, 209, false, 'single', 90, { govTotal: 2200000, empFirst: 6000000, total: 8200000 }],
  ['우선지원 220만 = 상한', 2200000, 209, true, 'single', 90, { govTotal: 6600000, empFirst: 0, total: 6600000, shortfall: 0 }],
  ['대규모 220만', 2200000, 209, false, 'single', 90, { govTotal: 2200000, empFirst: 4400000, total: 6600000 }],
  ['우선지원 250만', 2500000, 209, true, 'single', 90, { govTotal: 6600000, empFirst: 600000, total: 7200000 }],
  ['대규모 250만', 2500000, 209, false, 'single', 90, { empFirst: 5000000, govTotal: 2200000, total: 7200000 }],
  ['우선지원 400만', 4000000, 209, true, 'single', 90, { empFirst: 3600000, total: 10200000 }],
  ['대규모 400만', 4000000, 209, false, 'single', 90, { empFirst: 8000000, total: 10200000 }],
  ['다태아 우선지원 300만 120일', 3000000, 209, true, 'multi', 120, { govTotal: 8800000, empFirst: 2000000, total: 10800000 }],
  ['다태아 대규모 300만 120일', 3000000, 209, false, 'multi', 120, { empFirst: 7500000, govTotal: 3300000, total: 10800000 }],
  ['미숙아 우선지원 300만 100일 -> 고시 7,333,330', 3000000, 209, true, 'premature', 100, { govTotal: 7333330, empFirst: 1600002 }],
  ['단시간 주20h 120만 우선지원', 1200000, 104, true, 'single', 90, { govTotal: 3600000, empFirst: 0, floorApplied: false }],
  ['하한: 200만/209h -> 최저 2,156,880 x 3', 2000000, 209, true, 'single', 90, { govTotal: 6470640, empFirst: 0, floorApplied: true }],
  ['휴가 중 퇴사 45일 우선지원 300만', 3000000, 209, true, 'single', 45, { days: 45, govTotal: 3300000, empFirst: 1200000, later: 0 }],
  ['일수 초과 입력 -> 90일로 자름', 3000000, 209, true, 'single', 150, { days: 90, govTotal: 6600000 }],
];
for (const [name, w, h, pr, ty, d, exp] of cases) {
  const r = calc(w, h, pr, ty, d);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'ml-wage': '3000000', 'ml-hours': '209', 'ml-size': '1', 'ml-type': 'single', 'ml-days': '90' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = String(v); }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ml-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('8,200,000원'));
console.log('ALL PASS');
