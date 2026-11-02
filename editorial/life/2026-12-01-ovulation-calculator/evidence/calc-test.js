// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g) || []) if (lit.indexOf('<') >= 0) throw new Error('< in string literal ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.ovulationCalc;
// 독립 검산: 로컬 Date의 setDate로 날짜를 더한다 (계산기는 UTC 밀리초 덧셈)
function addDays(s, n) { const [y, m, d] = s.split('-').map(Number); const t = new Date(y, m - 1, d, 12); t.setDate(t.getDate() + n); return t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' + String(t.getDate()).padStart(2, '0'); }
const cases = [
  ['28일 기본', '2026-11-01', 28, { ovulation: '2026-11-15', next: '2026-11-29', dayOfCycle: 15 }],
  ['연말 넘김 28일', '2026-12-20', 28, { ovulation: '2027-01-03', next: '2027-01-17' }],
  ['21일 하한, 배란 1월 1일', '2026-12-25', 21, { ovulation: '2027-01-01', next: '2027-01-15', dayOfCycle: 8 }],
  ['35일 상한, 12월 31일 시작', '2026-12-31', 35, { ovulation: '2027-01-21', next: '2027-02-04', dayOfCycle: 22 }],
  ['윤년: 다음 생리 2028-02-29', '2028-02-01', 28, { ovulation: '2028-02-15', next: '2028-02-29' }],
  ['윤년: 배란 2028-02-29', '2028-02-15', 28, { ovulation: '2028-02-29', next: '2028-03-14' }],
  ['윤년 2월 29일 시작 30일', '2028-02-29', 30, { ovulation: '2028-03-16', next: '2028-03-30' }],
  ['평년 2027-02 넘김', '2027-02-15', 28, { ovulation: '2027-03-01', next: '2027-03-15' }],
  ['평년 2029-02', '2029-02-01', 28, { ovulation: '2029-02-15', next: '2029-03-01' }],
  ['1월 31일 시작 30일(2월 28일까지)', '2026-01-31', 30, { ovulation: '2026-02-16', next: '2026-03-02' }],
  ['4월 30일 시작 31일', '2026-04-30', 31, { ovulation: '2026-05-17', next: '2026-05-31' }],
];
for (const [name, lmp, c, exp] of cases) {
  const r = calc(lmp, c);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  assert.strictEqual(r.next, addDays(lmp, c), name + ' 독립검산 next');
  assert.strictEqual(r.ovulation, addDays(lmp, c - 14), name + ' 독립검산 ovulation');
  console.log('PASS', name, '배란', r.ovulation, '다음 생리', r.next);
}
// 3주기 이어 붙이기 (2028→2029 연도 넘김 포함)
let r = calc('2028-12-10', 32);
assert.deepStrictEqual(r.cycles[2], { start: '2029-02-12', ovulation: '2029-03-02', next: '2029-03-16' });
console.log('PASS 3주기 연도 넘김', JSON.stringify(r.cycles));
r = calc('2026-11-01', 28);
assert.deepStrictEqual(r.cycles.map(c => c.ovulation), ['2026-11-15', '2026-12-13', '2027-01-10']);
assert.strictEqual(r.cycles[2].next, '2027-01-24');
console.log('PASS 3주기 28일', r.cycles.map(c => c.ovulation).join(', '));
// 최단·최장 주기 범위 (본문 예: 26~32일 -> 11/13~11/19, 7일)
r = calc('2026-11-01', 28, 32, 26);
assert.strictEqual(r.rangeFrom, '2026-11-13'); assert.strictEqual(r.rangeTo, '2026-11-19'); assert.strictEqual(r.rangeDays, 7);
console.log('PASS 범위 26~32일', r.rangeFrom, '~', r.rangeTo);
// 표 값 검산: 11월 1일 시작
[[21, '2026-11-08', 8], [24, '2026-11-11', 11], [26, '2026-11-13', 13], [28, '2026-11-15', 15], [30, '2026-11-17', 17], [32, '2026-11-19', 19], [35, '2026-11-22', 22]]
  .forEach(([c, d, n]) => { const x = calc('2026-11-01', c); assert.strictEqual(x.ovulation, d); assert.strictEqual(x.dayOfCycle, n); });
console.log('PASS 표 값 7개');
// 입력 오류
assert.strictEqual(calc('2026-11-01', 20).error, 'cycle');
assert.strictEqual(calc('2026-11-01', 36).error, 'cycle');
assert.strictEqual(calc('2027-02-29', 28).error, 'date');
assert.strictEqual(calc('', 28).error, 'date');
assert.ok(!calc('2028-02-29', 28).error);
console.log('PASS 오류 처리 5개 (주기 20·36, 2027-02-29 없음, 빈 값, 2028-02-29 있음)');
// UI 렌더 확인 — 최소 DOM 스텁
function node(tag) { return { tag, children: [], style: {}, textContent: '', set innerHTML(v) { this.children = []; }, appendChild(c) { this.children.push(c); }, addEventListener() {} }; }
const els = { 'ov-out': node('div'), 'ov-cal': node('div'), 'ov-lmp': node('input'), 'ov-cycle': node('input'), 'ov-min': node('input'), 'ov-max': node('input') };
els['ov-lmp'].value = '2026-11-01'; els['ov-cycle'].value = '28'; els['ov-min'].value = '26'; els['ov-max'].value = '32';
global.document = { getElementById: id => els[id], createElement: node };
eval(src);
const lines = els['ov-out'].children.map(p => p.textContent);
console.log('UI 출력:', lines.join(' | '));
assert.ok(lines[0].includes('2026년 11월 15일(일)'));
assert.ok(lines[1].includes('2026년 11월 29일(일)'));
const months = els['ov-cal'].children.map(t => t.children[0].textContent);
console.log('달력 월:', months.join(', '));
assert.deepStrictEqual(months, ['2026년 11월', '2026년 12월', '2027년 1월']);
const marks = [];
els['ov-cal'].children.forEach(t => t.children.slice(2).forEach(tr => tr.children.forEach(td => { if (td.title) marks.push(t.children[0].textContent + ' ' + td.textContent + '일 ' + td.title); })));
console.log('달력 표시:', marks.filter(m => !m.endsWith('범위')).join(' / '));
assert.strictEqual(marks.filter(m => m.endsWith('배란 예정')).length, 3);
assert.strictEqual(marks.filter(m => m.endsWith('범위')).length, 6);
// 2026년 11월 1일은 일요일 -> 첫 주 빈칸 0개
assert.strictEqual(els['ov-cal'].children[0].children[2].children[0].textContent, '1');
console.log('PASS UI 렌더');
