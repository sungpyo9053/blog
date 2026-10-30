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
const calc = window.careWorkerCalc;
// 양성지침 p.8 교육시간 표 그대로
const hours = [
  ['신규', 'none', 'none', 126, 114, 80, 320],
  ['간호사', 'nurse', 'none', 26, 6, 8, 40],
  ['사회복지사', 'social', 'none', 32, 10, 8, 50],
  ['간호조무사·물리·작업', 'aide', 'none', 31, 11, 8, 50],
  ['경력자 기타일반', 'none', 'general', 126, 57, 40, 223],
  ['경력자 시설', 'none', 'facility', 126, 57, 20, 203],
  ['경력자 재가', 'none', 'home', 126, 57, 20, 203],
  ['경력자 시설+재가', 'none', 'both', 126, 57, 0, 183],
  ['간호사+관련경력', 'nurse', 'licensed', 26, 6, 0, 32],
  ['사회복지사+관련경력', 'social', 'licensed', 32, 10, 0, 42],
  ['간호조무사+관련경력', 'aide', 'licensed', 31, 11, 0, 42],
  ['자격 없음+자격경력 선택 -> 신규로', 'none', 'licensed', 126, 114, 80, 320],
  ['간호사+간병경력(자격 무관) -> 실습 유지', 'nurse', 'general', 26, 6, 8, 40],
];
for (const [name, lic, car, t, s, p, tot] of hours) {
  const r = calc(lic, car, -1, -1);
  assert.deepStrictEqual([r.theory, r.skill, r.practice, r.total], [t, s, p, tot], name);
  assert.strictEqual(r.scored, false);
  console.log('PASS', name, r.total + 'h', r.course, '/', r.fee);
}
assert.strictEqual(calc('none', 'none', -1, -1).days, 30); // 240h / 8
// 합격 판정: 각각 60% (21/35, 27/45)
const scores = [
  [21, 27, true, true, true], [20, 45, false, true, false], [35, 26, true, false, false],
  [0, 0, false, false, false], [35, 45, true, true, true], [36, 30, null, null, false],
];
for (const [w, p, wp, pp, pass] of scores) {
  const r = calc('none', 'none', w, p);
  if (wp === null) { assert.strictEqual(r.scored, false); console.log('PASS 범위 초과 입력', w, p, '-> 판정 안 함'); continue; }
  assert.deepStrictEqual([r.writtenPass, r.practicalPass, r.pass], [wp, pp, pass], w + '/' + p);
  console.log('PASS 점수', w + '/35', p + '/45', pass ? '합격' : '불합격');
}
// UI 렌더(최소 DOM 스텁)
const vals = { 'cw-lic': 'social', 'cw-car': 'licensed', 'cw-w': '22', 'cw-p': '26' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['cw-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력:', outP.join(' | '));
assert.ok(outP.join().includes('총 42시간'));
assert.ok(outP.join().includes('1문항 부족'));
assert.ok(outP.join().includes('판정: 불합격'));
console.log('ALL PASS');
