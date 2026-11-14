// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.energyVoucherExtraCalc;
// 1) ko.html 금액표(기본·추가·합계)와 계산기 결과 대조 — 누리집 2026년도 총액 + 147,000
const rows = [...html.matchAll(/<tr><td>(\d)인[^<]*<\/td><td>([\d,]+)원<\/td><td>([\d,]+)원<\/td><td>([\d,]+)원<\/td><\/tr>/g)];
assert.strictEqual(rows.length, 4);
const n = s => parseInt(s.replace(/,/g, ''), 10);
for (const m of rows) {
  const r = calc(+m[1], 'kerosene', 'yes', 'none', 'no', 'half');
  assert.strictEqual(r.base, n(m[2])); assert.strictEqual(r.extra, n(m[3])); assert.strictEqual(r.total, n(m[4]));
  assert.strictEqual(n(m[2]) + n(m[3]), n(m[4]));
  console.log('PASS 표', m[1] + '인', JSON.stringify(r));
}
const cases = [
  ['1인 LPG 이사 없음 절반 이상 -> 유형1 442,200', [1, 'lpg', 'yes', 'none', 'no', 'half'], { base: 295200, extra: 147000, total: 442200, type: 1 }],
  ['2인 등유 이사 있음 일부 -> 유형2', [2, 'kerosene', 'yes', 'none', 'yes', 'some'], { extra: 147000, total: 554500, type: 2 }],
  ['3인 등유 이사 없음 일부 -> 유형3', [3, 'kerosene', 'yes', 'none', 'no', 'some'], { total: 679700, type: 3 }],
  ['4인 등유 이력 없음 -> 유형3', [4, 'kerosene', 'yes', 'none', 'yes', 'none'], { total: 848300, type: 3 }],
  ['도시가스 -> 추가 0', [1, 'citygas', 'yes', 'none', 'no', 'half'], { extra: 0, total: 295200, type: 0 }],
  ['연탄쿠폰 등유 -> 제외, 하절기 금액만', [2, 'kerosene', 'yes', 'coupon', 'no', 'half'], { base: 58800, extra: 0, excluded: true }],
  ['긴급복지 연료비 LPG -> 제외', [4, 'lpg', 'yes', 'emergency', 'no', 'half'], { base: 102000, extra: 0 }],
  ['연탄전환 등유 -> 포함, 하절기 금액+추가', [3, 'kerosene', 'yes', 'coalconv', 'no', 'half'], { base: 75800, extra: 147000, total: 222800 }],
  ['비수급 -> 0', [1, 'kerosene', 'no', 'none', 'no', 'half'], { total: 0 }],
  ['신청 예정 4인 LPG', [4, 'lpg', 'apply', 'none', 'no', 'half'], { total: 848300 }],
];
for (const [name, a, exp] of cases) {
  const r = calc(...a);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 2) UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'ev-recv': 'yes', 'ev-size': '1', 'ev-fuel': 'kerosene', 'ev-other': 'none', 'ev-move': 'no', 'ev-use': 'half' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ev-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('442,200원'));
console.log('ALL PASS');
