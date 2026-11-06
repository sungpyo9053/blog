// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.fuelSurchargeCalc;
const cases = [
  ['아시아나 11월 후쿠오카 350mi 편도 1명', 'oz11', 350, 1, 1, 62400, 62400],
  ['아시아나 11월 경계 499mi', 'oz11', 499, 1, 1, 62400, 62400],
  ['아시아나 11월 경계 500mi', 'oz11', 500, 1, 1, 92200, 92200],
  ['아시아나 11월 오사카 535mi 왕복 2명', 'oz11', 535, 2, 2, 92200, 368800],
  ['아시아나 11월 다낭 1849mi 왕복 4명', 'oz11', 1849, 2, 4, 149100, 1192800],
  ['아시아나 11월 뉴욕 6906mi 왕복 1명', 'oz11', 6906, 2, 1, 351100, 702200],
  ['아시아나 10월 뉴욕 왕복 1명', 'oz10', 6906, 2, 1, 301200, 602400],
  ['아시아나 11월 이스탄불 4944mi', 'oz11', 4944, 1, 1, 294200, 294200],
  ['트리니티 11월 오사카 535mi 왕복 2명', 'tw11', 535, 2, 2, 43400, 173600],
  ['트리니티 11월 경계 600mi', 'tw11', 600, 1, 1, 76000, 76000],
  ['트리니티 11월 다낭 왕복 4명', 'tw11', 1849, 2, 4, 123500, 988000],
  ['트리니티 11월 싱가포르 2867mi', 'tw11', 2867, 1, 1, 133000, 133000],
  ['트리니티 11월 시드니 5164mi', 'tw11', 5164, 1, 1, 299800, 299800],
  ['국내선 11월 제주 왕복 2명', 'dom11', 0, 2, 2, 25300, 101200],
  ['국내선 12월 제주 왕복 2명', 'dom12', 0, 2, 2, 24200, 96800],
];
for (const [name, key, mile, trip, pax, one, total] of cases) {
  const r = calc(key, mile, trip, pax);
  assert.ok(r.ok, name + ' ok'); assert.strictEqual(r.one, one, name + ' one=' + r.one); assert.strictEqual(r.total, total, name + ' total=' + r.total);
  console.log('PASS', name, JSON.stringify(r));
}
const r6 = calc('tw11', 4577, 1, 1); assert.ok(!r6.ok); console.log('PASS 트리니티 6군(4,000~5,000 미만) 금액 없음', JSON.stringify(r6));
const r0 = calc('oz11', 0, 1, 1); assert.ok(!r0.ok); console.log('PASS 마일 0 입력 거부');
// 표 값 검산: 아시아나 11월 9개 구간 대표 마일
[[350,62400],[535,92200],[1284,120600],[1615,149100],[2277,178900],[2867,207400],[3261,235900],[4577,294200],[5561,351100]].forEach(([m,a]) => assert.strictEqual(calc('oz11', m, 1, 1).one, a));
console.log('PASS 아시아나 11월 구간 9개');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'fs-table': 'oz11', 'fs-city': '', 'fs-mile': '535', 'fs-trip': '2', 'fs-pax': '2', 'fs-inf': '1' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['fs-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('368,800원'));
