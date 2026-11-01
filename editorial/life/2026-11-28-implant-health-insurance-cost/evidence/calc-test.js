// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'[^'\n]*'/g)) if (m[0].includes('<')) throw new Error('< in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); console.log('JSON-LD OK, Q', faq.mainEntity.length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.implantCalc;
const base = { age: 67, elig: 'nhi', inst: 0, done: 0, want: 1, edentulous: false, crown: false, fixture: 105520, abutment: 69420 };
const cases = [
  ['치과의원 행위료 합계 1,351,040', {}, { ok: true, actFee: 1351040, perTotal: 1525980, perOop: 457700 }],
  ['치과의원 2개 30%', { want: 2 }, { covered: 2, totalFee: 3051960, totalOop: 915500, payer: 3051960 - 915500 }],
  ['3개 요청 -> 급여 2 + 비급여 1', { want: 3 }, { covered: 2, nonCovered: 1 }],
  ['이미 1개 -> 이번 2개 중 1개만', { done: 1, want: 2 }, { covered: 1, nonCovered: 1 }],
  ['이미 2개 -> 급여 없음', { done: 2 }, { ok: false, reason: 'used', covered: 0, nonCovered: 1 }],
  ['64세 -> 비급여', { age: 64 }, { ok: false, reason: 'age' }],
  ['65세 경계 -> 급여', { age: 65 }, { ok: true }],
  ['완전무치악 -> 비급여', { edentulous: true }, { ok: false, reason: 'full' }],
  ['비급여 보철 -> 전체 비급여', { crown: true }, { ok: false, reason: 'crown' }],
  ['차상위 C 10%', { elig: 'c' }, { rate: 10, perOop: 152500 }],
  ['차상위 E,F 20%', { elig: 'ef' }, { rate: 20, perOop: 305100 }],
  ['의료급여 1종 10%', { elig: 'aid1' }, { rate: 10, perOop: 152500 }],
  ['의료급여 2종 20%', { elig: 'aid2' }, { rate: 20, perOop: 305100 }],
  ['치과병원', { inst: 1 }, { actFee: 1409790, perTotal: 1584730, perOop: 475400 }],
  ['병원 내 치과', { inst: 2 }, { actFee: 1168550, perOop: 403000 }],
  ['요양·정신병원 내 치과', { inst: 3 }, { actFee: 1174130 }],
  ['한방병원 내 치과', { inst: 4 }, { actFee: 1454420 }],
  ['종합병원 내 치과', { inst: 5 }, { actFee: 1217230, perOop: 417600 }],
  ['부속치과병원(상급종합 제외)', { inst: 6 }, { actFee: 1468530 }],
  ['상급종합병원 내 치과', { inst: 7 }, { actFee: 1265930, perOop: 432200 }],
  ['부속치과병원(상급종합)', { inst: 8 }, { actFee: 1527280, perOop: 510600 }],
  ['보건의료원', { inst: 9 }, { actFee: 1317640 }],
  ['재료 0원이면 행위료만', { fixture: 0, abutment: 0 }, { perTotal: 1351040, perOop: 405300 }],
];
for (const [name, over, exp] of cases) {
  const r = calc(Object.assign({}, base, over));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표 값 검산 (30/20/10%)
const tbl = [[0, 1525980, 457700, 305100, 152500], [1, 1584730, 475400, 316900, 158400], [2, 1343490, 403000, 268600, 134300], [5, 1392170, 417600, 278400, 139200], [7, 1440870, 432200, 288100, 144000], [8, 1702220, 510600, 340400, 170200]];
for (const [inst, tot, a, b, c] of tbl) {
  assert.strictEqual(calc(Object.assign({}, base, { inst })).perTotal, tot);
  assert.strictEqual(calc(Object.assign({}, base, { inst })).perOop, a);
  assert.strictEqual(calc(Object.assign({}, base, { inst, elig: 'aid2' })).perOop, b);
  assert.strictEqual(calc(Object.assign({}, base, { inst, elig: 'aid1' })).perOop, c);
}
console.log('PASS 예시표 6행 x 4열');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'ip-age': '67', 'ip-elig': 'nhi', 'ip-inst': '0', 'ip-done': '0', 'ip-want': '1', 'ip-fix': '105520', 'ip-abt': '69420' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ip-out', 'ip-full', 'ip-crown', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('457,700원'));
