// ko.html의 체크기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { grades: G, judge } = window.fireMgrCheck;
// 별표 5·9 숫자
assert.deepStrictEqual([G['1'].hours, G['2'].hours, G['3'].hours], [80, 40, 24]);
assert.deepStrictEqual([G['1'].fee, G['2'].fee, G['3'].fee], [480000, 240000, 144000]);
console.log('PASS 강습 시간·교육비 (별표 5·9)');
const cases = [
  ['만점 25/25', 25, 25, { s1: 100, s2: 100, avg: 100, pass: true }],
  ['경계 합격 20/15 -> 평균 70', 20, 15, { s1: 80, s2: 60, avg: 70, pass: true }],
  ['경계 합격 25/10 -> 2과목 40', 25, 10, { s2: 40, avg: 70, pass: true }],
  ['평균 미달 18/16 -> 68', 18, 16, { avg: 68, pass: false, needTotal: 1 }],
  ['과락 25/9 -> 평균 68, 2과목 36', 25, 9, { s2: 36, pass: false, fail2: true }],
  ['과락 9/25 -> 1과목 36', 9, 25, { s1: 36, pass: false, fail1: true }],
  ['과락이지만 평균은 넘음 24/9', 24, 9, { avg: 66, pass: false, fail2: true }],
  ['0/0', 0, 0, { pass: false, fail1: true, fail2: true, needTotal: 35 }],
];
for (const [name, c1, c2, exp] of cases) {
  const r = judge(c1, c2);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 전수: 합격 = 각 10문항 이상 그리고 합계 35 이상
for (let a = 0; a <= 25; a++) for (let b = 0; b <= 25; b++)
  assert.strictEqual(judge(a, b).pass, a >= 10 && b >= 10 && a + b >= 35, a + '/' + b);
console.log('PASS 전수 676조합 (과목별 10문항, 합계 35문항 규칙과 일치)');
// UI 렌더 (기본값 2급, 18/17) — 최소 DOM 스텁
const vals = { 'fs-grade': '2', 'fs-c1': '18', 'fs-c2': '17' };
const boxes = {};
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { boxes[id] = []; }, appendChild(p) { boxes[id].push(p.textContent); } });
const els = {}; ['fs-out', 'fs-info', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 등급 정보:', boxes['fs-info'].join(' | '));
console.log('UI 판정:', boxes['fs-out'].join(' | '));
assert.ok(boxes['fs-info'].join().includes('40시간, 교육비 240,000원'));
assert.ok(boxes['fs-out'].join().includes('합격 기준 충족'));
