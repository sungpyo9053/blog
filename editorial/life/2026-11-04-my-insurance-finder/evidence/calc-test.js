// ko.html의 체커·소멸시효 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const ex = window.insExpiry, left = window.insDaysLeft, guide = window.insFinderGuide;
const cases = [
  ['기본: 2023-11-04 -> 2026-11-04', '2023-11-04', '2023-11-05', '2026-11-04'],
  ['연말: 2023-12-31 -> 2026-12-31', '2023-12-31', '2024-01-01', '2026-12-31'],
  ['윤일 발생: 2024-02-29 -> 기산 03-01 -> 2027-02-28', '2024-02-29', '2024-03-01', '2027-02-28'],
  ['윤일 기산(제160조3항): 2024-02-28 -> 기산 02-29 -> 2027-02-28', '2024-02-28', '2024-02-29', '2027-02-28'],
  ['윤년 도착: 2025-02-28 -> 기산 03-01 -> 2028-02-29', '2025-02-28', '2025-03-01', '2028-02-29'],
  ['월말: 2023-01-31 -> 2026-01-31', '2023-01-31', '2023-02-01', '2026-01-31'],
];
for (const [name, occ, start, end] of cases) {
  const r = ex(occ);
  assert.strictEqual(r.start, start, name + ' start');
  assert.strictEqual(r.end, end, name + ' end');
  console.log('PASS', name, JSON.stringify({ start: r.start, end: r.end }));
}
assert.strictEqual(ex('2023-02-30'), null); assert.strictEqual(ex(''), null); console.log('PASS 잘못된 날짜 null');
const r = ex('2023-11-04');
assert.strictEqual(left(r.endMs, '2026-10-29'), 6); assert.strictEqual(left(r.endMs, '2026-11-04'), 0); assert.strictEqual(left(r.endMs, '2026-11-05'), -1);
console.log('PASS 남은 일수 2026-10-29 기준 6일, 당일 0, 다음 날 -1');
for (const k of ['list', 'hidden', 'heir', 'silson']) { const g = guide(k); assert.ok(g.svc.length > 0 && g.need.length > 0 && g.path.length > 0 && g.warn.length > 0); }
assert.ok(guide('heir').warn.includes('청구를 지원하지 않는다')); assert.ok(guide('hidden').path.includes('cont.insure.or.kr'));
assert.strictEqual(guide('none'), null);
console.log('PASS 체커 4개 상황 필드 완비');
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'ins-case': 'heir', 'ins-date': '2023-11-04' };
const boxes = {};
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { boxes[id] = []; }, appendChild(p) { boxes[id].push(p.textContent); } });
const els = {}; ['ins-out', 'ins-guide', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 체커 출력:', boxes['ins-guide'].join(' | '));
console.log('UI 계산기 출력:', boxes['ins-out'].join(' | '));
assert.ok(boxes['ins-out'].join().includes('2026-11-04'));
assert.ok(boxes['ins-guide'].join().includes('상속인 금융거래조회'));
console.log('ALL PASS');
