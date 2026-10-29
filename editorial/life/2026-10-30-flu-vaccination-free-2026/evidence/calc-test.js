// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.includes('<')) throw new Error('< in string literal: ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const check = window.fluCheck, fmt = window.fluFmt;
const g = (r, k) => r.groups.find(x => x.key === k);
const cases = [
  ['2018-05-10 9세 미만, 이력 처음 -> 2회', '2018-05-10', false, '2026-10-29', 'none', r => { const c = g(r,'child'); assert.strictEqual(c.doses,'2회'); assert.strictEqual(fmt(c.start),'2026년 9월 21일'); assert.strictEqual(c.days,183); }],
  ['2018-05-10 6월30일까지 1회 -> 2회', '2018-05-10', false, '2026-10-29', 'one', r => assert.strictEqual(g(r,'child').doses,'2회')],
  ['2018-05-10 2회 이상 -> 1회', '2018-05-10', false, '2026-10-29', 'two', r => assert.strictEqual(g(r,'child').doses,'1회')],
  ['2018-05-10 이력 미선택 -> 확인 필요', '2018-05-10', false, '2026-10-29', '', r => assert.strictEqual(g(r,'child').doses,'확인 필요')],
  ['2015-03-01 만 11세 -> 1회', '2015-03-01', false, '2026-10-29', 'none', r => assert.strictEqual(g(r,'child').doses,'1회')],
  ['경계 2012-01-01 -> 대상', '2012-01-01', false, '2026-10-29', '', r => assert.ok(g(r,'child'))],
  ['경계 2011-12-31 -> 비대상', '2011-12-31', false, '2026-10-29', '', r => assert.strictEqual(r.ok,false)],
  ['2026-08-31생 -> 6개월 되는 2027-02-28부터', '2026-08-31', false, '2026-10-29', 'none', r => { const c = g(r,'child'); assert.strictEqual(fmt(c.start),'2027년 2월 28일'); assert.strictEqual(c.status,'before'); assert.strictEqual(c.days,122); }],
  ['2026-09-01생 -> 비대상(범위 밖)', '2026-09-01', false, '2026-10-29', '', r => { assert.strictEqual(r.ok,false); assert.ok(r.note); }],
  ['1951년생 -> 75세 이상 10/6', '1951-12-31', false, '2026-10-29', '', r => assert.strictEqual(fmt(g(r,'senior').start),'2026년 10월 6일')],
  ['1952년생 -> 70~74세 10/12', '1952-01-01', false, '2026-10-29', '', r => assert.strictEqual(fmt(g(r,'senior').start),'2026년 10월 12일')],
  ['1961-12-31생(생일 전 기준일) -> 65~69세 10/15', '1961-12-31', false, '2026-10-01', '', r => { const s = g(r,'senior'); assert.strictEqual(fmt(s.start),'2026년 10월 15일'); assert.strictEqual(s.status,'before'); assert.strictEqual(s.days,14); }],
  ['1962-01-01생 -> 비대상', '1962-01-01', false, '2026-10-29', '', r => assert.strictEqual(r.ok,false)],
  ['1990년생 임신부 -> 9/21~4/30', '1990-06-15', true, '2026-10-29', '', r => { const p = g(r,'preg'); assert.strictEqual(fmt(p.start),'2026년 9월 21일'); assert.strictEqual(fmt(p.end),'2027년 4월 30일'); assert.strictEqual(p.days,183); }],
  ['임신부, 생년월일 없음 -> 대상', '', true, '2026-10-29', '', r => assert.ok(g(r,'preg'))],
  ['마지막 날 2027-04-30 -> 0일', '1950-01-01', false, '2027-04-30', '', r => { const s = g(r,'senior'); assert.strictEqual(s.status,'open'); assert.strictEqual(s.days,0); }],
  ['종료 후 2027-05-01 -> closed', '1950-01-01', false, '2027-05-01', '', r => assert.strictEqual(g(r,'senior').status,'closed')],
  ['생년월일 없음, 임신 아님 -> 오류', '', false, '2026-10-29', '', r => assert.ok(r.error)],
  ['생년월일이 기준일보다 늦음 -> 오류', '2026-11-01', false, '2026-10-29', '', r => assert.ok(r.error)],
];
for (const [name, b, p, ref, h, fn] of cases) { const r = check(b, p, ref, h); fn(r); console.log('PASS', name, JSON.stringify(r.groups.map(x => ({ k: x.key, start: fmt(x.start), doses: x.doses, status: x.status, days: x.days }))), r.note || r.error || ''); }
// UI 렌더 확인 — 최소 DOM 스텁 (2018-05-10생, 이력 처음, 기준일 2026-10-29)
const vals = { 'fv-birth': '2018-05-10', 'fv-ref': '2026-10-29', 'fv-hist': 'none' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['fv-out', 'fv-preg', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력:', outP.join(' | '));
assert.ok(outP.join().includes('접종 횟수: 2회'));
assert.ok(outP.join().includes('183일'));
console.log('ALL PASS');
