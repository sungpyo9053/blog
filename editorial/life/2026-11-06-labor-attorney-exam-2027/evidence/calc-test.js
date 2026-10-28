// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('raw < in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
assert.ok(ld.indexOf('&') < 0 && ld.indexOf('<') < 0); JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { judge, engOk, dday } = window.cplaCalc;
const cases = [
  ['기본값 70/62.5/55/60/57.5 -> 평균 61 합격', [70, 62.5, 55, 60, 57.5], false, { avg: 61, pass: true, need: 0 }],
  ['과락: 38점 한 과목, 평균 70 이상이어도 불합격', [90, 90, 38, 80, 90], false, { pass: false, avgOk: true }],
  ['경계: 모두 40, 평균 60 정확히 -> 합격', [40, 80, 60, 60, 60], false, { avg: 60, pass: true }],
  ['평균 미달: 총 295 -> 5점 부족', [60, 60, 60, 60, 55], false, { avg: 59, pass: false, need: 5 }],
  ['면제자: 노동법 0점 무시, 3과목 60/60/60 합격', [0, 0, 60, 60, 60], true, { count: 3, avg: 60, pass: true }],
  ['면제자 과락: 민법 39', [0, 0, 39, 90, 90], true, { pass: false }],
];
for (const [name, s, ex, exp] of cases) {
  const r = judge(s, ex);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.deepStrictEqual(judge([90, 90, 38, 80, 90], false).fails, [2]);
assert.deepStrictEqual(judge([0, 0, 39, 90, 90], true).fails, [2]);
// 영어 기준점수(공고문)
[['TOEIC', 700, true], ['TOEIC', 695, false], ['TOEFL_PBT', 530, true], ['TOEFL_IBT', 70, false], ['TEPS', 340, true], ['GTELP', 64, false], ['FLEX', 625, true], ['IELTS', 4.5, true], ['IELTS', 4, false]]
  .forEach(([t, s, e]) => assert.strictEqual(engOk(t, s), e, t + s));
console.log('PASS 영어 기준점수 9건');
// D-day
const today = new Date(2026, 9, 28);
assert.strictEqual(dday('2026-11-27', today), 30);
assert.strictEqual(dday('2026-10-28', today), 0);
assert.strictEqual(dday('2026-05-23', today), -158);
assert.strictEqual(dday('2027-05-22', today), 206);
assert.strictEqual(dday('', today), null);
console.log('PASS D-day 5건 (10/28 기준 3차 11/27 = D-30)');
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'cp-s1': '70', 'cp-s2': '62.5', 'cp-s3': '55', 'cp-s4': '60', 'cp-s5': '57.5', 'cp-eng': 'TOEIC', 'cp-engs': '720', 'cp-date': '2026-11-27' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['cp-out', 'cp-ex', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('1차 합격 기준 충족'));
assert.ok(outP.join().includes('기준점수(700) 이상'));
assert.ok(/D-\d+/.test(outP.join()));
console.log('ALL PASS');
