// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산 (누리집 사업안내·교육부 붙임·서울시 2차 공고 기준)
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.lifelongVoucherCalc;
// calc(birth, income, disabled, type, selected, excellent, used)
const cases = [
  ['2007년생(19세) 일반, 신청 전', [2007, 'none', false, 'gen', false, false, 0], { age: 19, ok: true, priority: false, incomeNote: true, grant: 0 }],
  ['2008년생(18세) 일반 불가', [2008, 'basic', false, 'gen', false, false, 0], { age: 18, ok: false }],
  ['1996년생(30세) AI·디지털 가능', [1996, 'none', false, 'aid', false, false, 0], { age: 30, ok: true }],
  ['1997년생(29세) AI·디지털 불가', [1997, 'none', false, 'aid', false, false, 0], { age: 29, ok: false }],
  ['1961년생(65세) 노인 가능', [1961, 'none', false, 'old', false, false, 0], { age: 65, ok: true }],
  ['1962년생(64세) 노인 불가', [1962, 'none', false, 'old', false, false, 0], { ok: false }],
  ['장애인 이용권: 등록장애인 아니면 불가', [1990, 'none', false, 'dis', false, false, 0], { ok: false }],
  ['장애인 이용권: 등록장애인 19세+ 가능, 정부24', [1990, 'near', true, 'dis', false, false, 0], { ok: true, priority: true }],
  ['수급자 일반 선정, 12만 사용 -> 잔액 23만', [1980, 'basic', false, 'gen', true, false, 120000], { grant: 350000, remain: 230000, priority: true, incomeNote: false, excellentHint: false }],
  ['35만 전액 사용 -> 잔액 0, 우수이용자 안내', [1980, 'near', false, 'gen', true, false, 350000], { remain: 0, over: 0, excellentHint: true }],
  ['우수이용자 70만, 40만 사용 -> 30만', [1980, 'none', false, 'aid', true, true, 400000], { grant: 700000, remain: 300000, excellentHint: false }],
  ['초과 입력 38만 -> 잔액 0, 초과 3만', [1980, 'none', false, 'old', true, false, 380000], { remain: 0, over: 30000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.ok(calc(1990, 'near', true, 'dis', false, false, 0).where.includes('정부24'));
assert.deepStrictEqual(calc(1950, 'none', true, 'gen', false, false, 0).types, ['gen', 'aid', 'old', 'dis']);
console.log('PASS 신청처·유형 목록');
// UI 기본값 렌더 (1985년생, 일반, 신청 전) + 선정 후 렌더 — 최소 DOM 스텁
function render(vals) {
  const outP = [];
  const el = id => ({ value: vals[id], checked: vals[id] === true, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
  const els = {}; ['lv-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
  global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
  eval(src);
  return outP.join(' | ');
}
const ui1 = render({ 'lv-birth': '1985', 'lv-income': 'none', 'lv-dis': false, 'lv-type': 'gen', 'lv-sel': 'no', 'lv-exc': false, 'lv-used': '0' });
console.log('UI 기본값 출력:', ui1);
assert.ok(ui1.includes('41세') && ui1.includes('신청 가능'));
const ui2 = render({ 'lv-birth': '1958', 'lv-income': 'basic', 'lv-dis': false, 'lv-type': 'old', 'lv-sel': 'yes', 'lv-exc': false, 'lv-used': '150000' });
console.log('UI 선정 후 출력:', ui2);
assert.ok(ui2.includes('200,000원') && ui2.includes('12월 31일'));
