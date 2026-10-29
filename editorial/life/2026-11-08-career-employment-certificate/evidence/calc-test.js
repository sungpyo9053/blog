// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const dl = window.careerCertDeadline, chk = window.careerCertCheck;
// 민법 제157조(초일 불산입)·제160조②③ 기준 3년 기한
for (const [end, exp] of [
  ['2026-09-30', '2029-09-30'], ['2026-12-31', '2029-12-31'], ['2026-01-31', '2029-01-31'],
  ['2025-02-28', '2028-02-29'], ['2027-02-28', '2030-02-28'], ['2028-02-28', '2031-02-28'], ['2028-02-29', '2031-02-28'],
]) { assert.strictEqual(dl(end), exp, end); console.log('PASS 기한', end, '->', exp); }
const base = { type: 'emp', purpose: 'job', today: '2026-10-29' };
let r = chk(Object.assign({}, base, { status: 'left', start: '2024-03-04', end: '2026-09-30' }));
assert.ok(r.right); assert.strictEqual(r.deadline, '2029-09-30'); assert.strictEqual(r.daysLeft, 1067);
assert.ok(r.docs[0].includes('제39조')); console.log('PASS 퇴사 후 기한 안', JSON.stringify(r.docs), r.daysLeft);
r = chk(Object.assign({}, base, { status: 'left', start: '2020-01-02', end: '2023-06-30' }));
assert.ok(!r.right); assert.ok(r.daysLeft < 0); assert.ok(r.docs[0].includes('의무는 없음')); console.log('PASS 3년 경과', r.deadline, r.daysLeft);
r = chk(Object.assign({}, base, { status: 'left', start: '2026-09-02', end: '2026-09-30' }));
assert.strictEqual(r.tenure, 29); assert.ok(!r.right); console.log('PASS 29일 근무 -> 청구권 없음');
r = chk(Object.assign({}, base, { status: 'left', start: '2026-09-01', end: '2026-09-30' }));
assert.strictEqual(r.tenure, 30); assert.ok(r.right); console.log('PASS 30일 근무 -> 청구권 있음');
r = chk(Object.assign({}, base, { status: 'work', start: '2026-10-01', end: '' }));
assert.ok(r.right); assert.strictEqual(r.deadline, null); assert.ok(r.notes[0].includes('재직 중에도')); console.log('PASS 재직 중');
r = chk(Object.assign({}, base, { status: 'left', type: 'free', start: '2024-01-01', end: '2026-06-30' }));
assert.ok(!r.right); assert.ok(r.notes.some(s => s.includes('노동기준조사과'))); console.log('PASS 3.3% 프리랜서');
r = chk(Object.assign({}, base, { status: 'gone', start: '2022-01-03', end: '2025-12-31', purpose: 'visa' }));
assert.ok(r.notes.some(s => s.includes('확인하지 못했습니다'))); assert.ok(r.notes.some(s => s.includes('영문'))); console.log('PASS 폐업·연락두절 + 비자');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'cc-status': 'left', 'cc-type': 'emp', 'cc-start': '2024-03-04', 'cc-end': '2026-09-30', 'cc-purpose': 'job' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['cc-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('2029-09-30'));
