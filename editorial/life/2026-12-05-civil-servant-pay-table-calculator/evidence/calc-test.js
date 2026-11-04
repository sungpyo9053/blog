// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string literal ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.civilPayCalc, D = window.civilPayData;
// 1) 내장 표 전체 == law.go.kr 별표 PDF 텍스트(evidence/law-bosu-byl*.txt) 전체 셀
function lawCells(fn) {
  const nums = [];
  for (const ln of fs.readFileSync(path.join(__dirname, fn), 'utf8').split('\n').slice(1))
    if (/^\s*\d{1,2}\s+\d,\d{3},\d{3}/.test(ln)) nums.push(...ln.match(/\d,\d{3},\d{3}/g).map(s => +s.replace(/,/g, '')));
  return nums.sort((a, b) => a - b);
}
for (const [k, fn] of [['g', 'law-bosu-byl3.txt'], ['a', 'law-bosu-byl4.txt'], ['p', 'law-bosu-byl10.txt'], ['t', 'law-bosu-byl11.txt']]) {
  const mine = D.tab[k].flat().sort((a, b) => a - b);
  assert.deepStrictEqual(mine, lawCells(fn), k);
  console.log('PASS 표 ' + k + ' 셀 ' + mine.length + '개 = ' + fn + ' 숫자 전체');
}
// 2) 별표에서 직접 읽은 표본 셀 (계급, 호봉 위치까지 확인)
const cells = [
  ['g', 8, 1, 2133000, '일반직 9급 1호봉'], ['g', 7, 1, 2162100, '8급 1호봉'], ['g', 6, 1, 2317100, '7급 1호봉'],
  ['g', 5, 1, 2389500, '6급 1호봉'], ['g', 4, 1, 2896400, '5급 1호봉'], ['g', 0, 23, 8001400, '1급 23호봉(최고)'],
  ['g', 5, 32, 4967800, '6급 32호봉(최고)'], ['g', 8, 31, 3731100, '9급 31호봉(최고)'], ['g', 6, 20, 3968400, '7급 20호봉'],
  ['g', 8, 20, 3257000, '9급 20호봉'], ['g', 6, 10, 3133300, '7급 10호봉'], ['g', 3, 28, 6058300, '4급 28호봉(최고)'],
  ['a', 6, 1, 2472100, '공안 7급 1호봉'], ['a', 5, 32, 5146400, '공안 6급 32호봉'],
  ['p', 9, 1, 2133000, '순경 1호봉'], ['p', 6, 1, 2507700, '경위 1호봉'], ['p', 5, 32, 5372500, '경감 32호봉'], ['p', 0, 23, 8250400, '치안정감 23호봉'],
  ['t', 0, 1, 2041500, '교원 1호봉'], ['t', 0, 40, 6205700, '교원 40호봉'], ['t', 0, 9, 2495600, '교원 9호봉'],
];
for (const [t, g, s, v, name] of cells) { assert.strictEqual(calc(t, g, s, 1).pay, v, name); }
console.log('PASS 표본 셀 ' + cells.length + '개');
assert.strictEqual(calc('g', 0, 24, 1), null); // 1급 24호봉 없음
assert.strictEqual(calc('g', 6, 32, 1), null); // 7급 32호봉 없음
console.log('PASS 없는 호봉 null');
// 3) 수당 공식
let r = calc('g', 8, 1, 1);
assert.deepStrictEqual([r.payYear, r.jg, r.jgAddMonth, r.holiday, r.meal, r.total], [25596000, 213300, 30000, 1279800, 160000, 30862200]);
console.log('PASS 9급 1호봉 1년:', JSON.stringify(r));
r = calc('g', 6, 1, 1); assert.strictEqual(r.holiday, 1390260); console.log('PASS 7급 1호봉 명절휴가비 1,390,260');
const rate = [[0, .1], [1.9, .1], [2, .2], [4, .2], [5, .25], [6, .3], [7, .35], [8, .4], [9, .45], [10, .5], [30, .5]];
for (const [y, p] of rate) assert.strictEqual(calc('g', 8, 1, y).jg, Math.round(2133000 * p), 'rate ' + y);
const add = [[4, 30000], [5, 50000], [9, 50000], [10, 60000], [15, 80000], [20, 110000], [24, 110000], [25, 130000]];
for (const [y, a] of add) assert.strictEqual(calc('g', 8, 1, y).jgAddMonth, a, 'add ' + y);
console.log('PASS 정근수당 지급률 ' + rate.length + '개, 가산금 ' + add.length + '개 경계');
// 4) UI 기본값 렌더 (최소 DOM 스텁)
const outP = [];
function mkSel(id) { return { id, value: '', style: {}, opts: [], addEventListener() {}, set innerHTML(v) { if (id === 'cs-out') outP.length = 0; else this.opts = []; }, appendChild(o) { if (id === 'cs-out') outP.push(o.textContent); else { this.opts.push(o); if (this.opts.length === 1) this.value = o.value; } } }; }
const els = {}; ['cs-out', 'cs-type', 'cs-grade', 'cs-step', 'cs-years', 'cs-grade-row'].forEach(id => els[id] = mkSel(id));
els['cs-type'].value = 'g'; els['cs-years'].value = '1';
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('9급 1호봉 월 봉급: 2,133,000원'));
assert.ok(outP.join().includes('30,862,200원'));
els['cs-type'].value = 't';
eval(src); // 교원 선택 상태로 초기화 재실행
console.log('UI 교원 출력:', outP[0]);
assert.ok(outP[0].includes('교원 1호봉 월 봉급: 2,041,500원'));
console.log('ALL PASS');
