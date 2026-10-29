// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const cost = window.dlCost, judge = window.dlJudge;
const costCases = [
  ['2종 보통 독학 한 번에 (표 합계 86,000)', ['2n', 'self', 'center', 'card', 0, 0, 0], 86000],
  ['1종 보통 독학 한 번에', ['1n', 'self', 'center', 'card', 0, 0, 0], 86000],
  ['2종 소형 독학 (표 합계 41,000)', ['2s', 'self', 'center', 'card', 0, 0, 0], 41000],
  ['원동기 독학 (표 합계 35,000)', ['mo', 'self', 'center', 'card', 0, 0, 0], 35000],
  ['2종 보통 학원 (본문 31,000)', ['2n', 'academy', 'center', 'card', 0, 0, 0], 31000],
  ['2종 보통 독학 모바일 면허증 +5,000', ['2n', 'self', 'center', 'mobile', 0, 0, 0], 91000],
  ['2종 보통 독학 건강검진 활용 -7,000', ['2n', 'self', 'checkup', 'card', 0, 0, 0], 79000],
  ['재응시 학과1 기능2 도로1 = 86,000+10,000+50,000+30,000', ['2n', 'self', 'center', 'card', 1, 2, 1], 176000],
  ['원동기 학과 재응시 1회 +8,000', ['mo', 'self', 'center', 'card', 1, 0, 0], 43000],
  ['원동기에 학원 선택 -> 독학 기준 + 안내', ['mo', 'academy', 'center', 'card', 0, 0, 0], 35000],
  ['학원은 기능·도로 재응시 무시', ['2n', 'academy', 'center', 'card', 0, 3, 3], 31000],
  ['음수·빈칸 재응시는 0회', ['2n', 'self', 'center', 'card', -2, '', 'x'], 86000],
];
for (const [name, args, total] of costCases) {
  const r = cost(...args);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  console.log('PASS', name, '->', r.total.toLocaleString('ko-KR') + '원', r.notes.length ? '| ' + r.notes.join(' ') : '');
}
const judgeCases = [
  ['1종 보통 학과 70 합격', ['1n', 70, NaN, NaN], [true]],
  ['1종 보통 학과 69 불합격', ['1n', 69, NaN, NaN], [false]],
  ['2종 보통 학과 60 합격', ['2n', 60, NaN, NaN], [true]],
  ['2종 보통 학과 58 불합격', ['2n', 58, NaN, NaN], [false]],
  ['2종 보통 기능 80 도로 70 합격', ['2n', NaN, 80, 70], [true, true]],
  ['2종 보통 기능 78 도로 68 불합격', ['2n', NaN, 78, 68], [false, false]],
  ['2종 소형 학과 60 기능 85(90 기준) / 도로 없음', ['2s', 60, 85, 90], [true, false]],
  ['원동기 학과 59', ['mo', 59, NaN, NaN], [false]],
];
for (const [name, args, exp] of judgeCases) {
  const r = judge(...args);
  assert.deepStrictEqual(r.map(x => x.pass), exp, name);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 (최소 DOM 스텁) + 학과 64점 입력 시 2종 보통 판정
const vals = { 'dl-type': '2n', 'dl-route': 'self', 'dl-phys': 'center', 'dl-card': 'card', 'dl-rw': '0', 'dl-rf': '0', 'dl-rr': '0', 'dl-sw': '64', 'dl-sf': '', 'dl-sr': '' };
const boxes = { 'dl-out': [], 'dl-judge': [] };
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
Object.keys(boxes).forEach(id => els[id] = { set innerHTML(v) { boxes[id].length = 0; }, appendChild(p) { boxes[id].push(p.textContent); } });
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 비용:', boxes['dl-out'].join(' | '));
console.log('UI 판정:', boxes['dl-judge'].join(' | '));
assert.ok(boxes['dl-out'].join().includes('86,000원'));
assert.ok(boxes['dl-judge'].join().includes('합격 (기준 60점'));
console.log('ALL PASS');
