// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.includes('<')) throw new Error('< in string literal: ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faqN = JSON.parse(ld).mainEntity.length;
const bodyFaq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faqN, bodyFaq); assert.ok(faqN >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const P = window.pertussisCheck, f = P.fmt, D = (s) => { const a = s.split('-').map(Number); return P.dn(a[0], a[1], a[2]); };
const REF = D('2026-10-31');
const cases = [
  ['2026-09-15생 0회 -> 1차 2개월 11/15~12/14, before 15일', () => { const r = P.child('2026-09-15', REF, '0'); assert.strictEqual(r.next.n, 1); assert.strictEqual(f(r.next.start), '2026년 11월 15일'); assert.strictEqual(f(r.next.end), '2026년 12월 14일'); assert.strictEqual(r.next.status, 'before'); assert.strictEqual(r.next.days, 15); assert.ok(r.free); }],
  ['2026-06-30생 2회 -> 3차 6개월 12/30 시작', () => { const r = P.child('2026-06-30', REF, '2'); assert.strictEqual(r.next.n, 3); assert.strictEqual(f(r.next.start), '2026년 12월 30일'); }],
  ['월말 보정: 2025-08-31생 3회 -> 4차 15개월 2026-11-30, 끝 2027-03-30', () => { const r = P.child('2025-08-31', REF, '3'); assert.strictEqual(r.next.n, 4); assert.strictEqual(f(r.next.start), '2026년 11월 30일'); assert.strictEqual(f(r.next.end), '2027년 3월 30일'); }],
  ['2021-05-01생 4회 -> 5차 만4~6세 now', () => { const r = P.child('2021-05-01', REF, '4'); assert.strictEqual(r.next.n, 5); assert.strictEqual(r.next.status, 'now'); assert.strictEqual(f(r.next.end), '2028년 4월 30일'); }],
  ['2015-03-01생 5회 -> 6차 만11~12세 now, 무료', () => { const r = P.child('2015-03-01', REF, '5'); assert.strictEqual(r.next.n, 6); assert.strictEqual(r.next.status, 'now'); assert.strictEqual(r.age, 11); assert.ok(r.free); }],
  ['2013-01-01생 경계 -> 무료, 만 13세', () => { const r = P.child('2013-01-01', REF, '5'); assert.ok(r.free); assert.strictEqual(r.age, 13); assert.strictEqual(r.next.status, 'late'); }],
  ['2012-12-31생 경계 -> 유료', () => assert.strictEqual(P.child('2012-12-31', REF, '6').free, false)],
  ['6회 이상 -> booster', () => assert.strictEqual(P.child('2010-01-01', REF, '6').mode, 'booster')],
  ['횟수 모름 2024-01-10생 -> 나이로 5차(4차 시기 지난 뒤)', () => { const r = P.child('2024-01-10', REF, ''); assert.strictEqual(r.mode, 'unknown'); assert.strictEqual(r.next.n, 5); assert.strictEqual(f(r.next.start), '2028년 1월 10일'); }],
  ['횟수 모름 성인 -> adult', () => assert.strictEqual(P.child('1990-06-15', REF, '').mode, 'adult')],
  ['0회 만 10세 -> catchup', () => assert.strictEqual(P.child('2016-01-01', REF, '0').mode, 'catchup')],
  ['0회 3세 -> 1차 late', () => { const r = P.child('2023-05-05', REF, '0'); assert.strictEqual(r.next.n, 1); assert.strictEqual(r.next.status, 'late'); }],
  ['생일 미래 -> 오류', () => assert.strictEqual(P.child('2027-01-01', REF, '0').ok, false)],
  ['임신 20주 -> 27주 7주 뒤 12/19, 36주 끝 2027-02-26', () => { const r = P.preg(20, REF); assert.strictEqual(r.status, 'before'); assert.strictEqual(f(r.start), '2026년 12월 19일'); assert.strictEqual(f(r.end), '2027년 2월 26일'); }],
  ['임신 27주 -> now', () => assert.strictEqual(P.preg(27, REF).status, 'now')],
  ['임신 36주 -> now', () => assert.strictEqual(P.preg(36, REF).status, 'now')],
  ['임신 37주 -> after', () => assert.strictEqual(P.preg(37, REF).status, 'after')],
  ['임신 0주 -> 오류', () => assert.strictEqual(P.preg(0, REF).ok, false)],
  ['돌보미 예정일 2027-01-20 -> 2027-01-06까지', () => { const r = P.care('2027-01-20', REF); assert.strictEqual(f(r.deadline), '2027년 1월 6일'); assert.strictEqual(r.passed, false); }],
  ['돌보미 이미 출생 2026-11-05 -> passed', () => assert.strictEqual(P.care('2026-11-05', REF).passed, true)],
];
for (const [name, fn] of cases) { fn(); console.log('PASS', name); }
// UI 렌더 — 최소 DOM 스텁
const vals = { 'pv-type': 'child', 'pv-birth': '2026-09-15', 'pv-done': '0', 'pv-week': '20', 'pv-baby': '', 'pv-ref': '' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = v; }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['pv-out', 'pv-row-birth', 'pv-row-week', 'pv-row-baby', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
vals['pv-ref'] = '2026-10-31';
const ui = (t) => { vals['pv-type'] = t; outP.length = 0; let run; els['pv-type'].addEventListener = (e, fn) => { run = fn; }; eval(src); vals['pv-ref'] = '2026-10-31'; run(); return outP.join(' | '); };
const a = ui('child'); console.log('UI 아이:', a); assert.ok(a.includes('2026년 11월 15일')); assert.ok(a.includes('무료'));
const b = ui('preg'); console.log('UI 임신부:', b); assert.ok(b.includes('2026년 12월 19일'));
vals['pv-baby'] = '2027-01-20';
const c = ui('care'); console.log('UI 돌보미:', c); assert.ok(c.includes('2027년 1월 6일'));
console.log('ALL PASS', cases.length + 3, 'checks; FAQ', faqN);
