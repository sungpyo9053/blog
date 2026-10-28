// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('< inside string literal');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const J = window.kacptaJudge, N = window.kacptaNext;
const jc = [
  ['이론 22 + 실무 50 = 72 합격', 22, 50, { ok: true, total: 72, pass: true, need: 0 }],
  ['경계 70점 합격', 30, 40, { total: 70, pass: true }],
  ['69점 1점 부족', 20, 49, { total: 69, pass: false, need: 1 }],
  ['이론 0 + 실무 70 = 70 합격(과목 최저점 규정 없음)', 0, 70, { pass: true }],
  ['이론 31 입력 오류', 31, 50, { ok: false }],
  ['실무 71 입력 오류', 20, 71, { ok: false }],
  ['음수 오류', -1, 50, { ok: false }],
  ['빈칸(NaN) 오류', NaN, 50, { ok: false }],
];
for (const [name, t, p, exp] of jc) {
  const r = J(t, p);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
const nc = [
  ['발행일 2026-11-07 -> 129회 접수중 D-28', '2026-11-07', { no: 129, dday: 28, state: 'open' }],
  ['확인일 2026-10-28 -> 129회 접수 전 D-38', '2026-10-28', { no: 129, dday: 38, state: 'before' }],
  ['접수 마감일 11-11 -> open', '2026-11-11', { no: 129, state: 'open' }],
  ['마감 다음날 11-12 -> closed', '2026-11-12', { no: 129, state: 'closed', dday: 23 }],
  ['시험 당일 12-05 -> D-0', '2026-12-05', { no: 129, dday: 0 }],
  ['128회 당일 10-03', '2026-10-03', { no: 128, dday: 0 }],
  ['128회 다음날 10-04 -> 129회', '2026-10-04', { no: 129, dday: 62 }],
  ['연초 2026-01-01 -> 124회 D-30', '2026-01-01', { no: 124, dday: 30, state: 'before' }],
];
for (const [name, d, exp] of nc) {
  const r = N(d);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.strictEqual(N('2026-12-06'), null); console.log('PASS 12-06 이후 -> null (2027 미공고 문구)');
// 표 값 대조: 본문 일정표와 스크립트 배열 일치
const rows = [...html.matchAll(/<tr><td>제(12\d)회<\/td><td>([\d.~]+)<\/td><td>[\d.~]+<\/td><td>([\d.]+)\.\(.\)<\/td><td>([\d.]+)\.\(.\)<\/td><\/tr>/g)];
assert.strictEqual(rows.length, 6);
for (const m of rows) {
  const [mm, dd] = m[3].split('.'); const iso = '2026-' + mm.padStart(2, '0') + '-' + dd.padStart(2, '0');
  assert.ok(src.includes("'" + iso + "'"), '시험일 ' + iso + ' 배열에 없음');
}
console.log('PASS 본문 일정표 6회차 시험일 = 스크립트 배열');
// UI 기본값 렌더 (기준일 2026-11-07)
const vals = { 'ca-theory': '22', 'ca-practice': '50', 'ca-date': '2026-11-07' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = v; }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ca-out', 'ca-today', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('72점'));
assert.ok(outP.join().includes('제129회 12월 5일(토), D-28'));
assert.ok(outP.join().includes('11월 11일(수) 18:00 마감'));
