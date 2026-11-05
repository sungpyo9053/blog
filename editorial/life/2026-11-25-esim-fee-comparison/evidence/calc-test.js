// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('raw < in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.esimFeeCalc;
const base = { esimFee: 2750, usimFee: 7700, months: 24, changes: 0, haveUsim: false, dual: false, dualFee: 8800, ktMember: false };
const cases = [
  ['기기변경 0회: eSIM 2,750 vs 유심 7,700', {}, { esimTotal: 2750, usimTotal: 7700, diff: 4950, cheaper: 'esim' }],
  ['1회: 5,500 vs 7,700', { changes: 1 }, { esimTotal: 5500, diff: 2200, cheaper: 'esim' }],
  ['2회: 8,250 vs 7,700 -> 유심', { changes: 2 }, { esimTotal: 8250, diff: -550, cheaper: 'usim' }],
  ['3회: 11,000 vs 7,700', { changes: 3 }, { esimTotal: 11000, diff: -3300, cheaper: 'usim' }],
  ['유심 보유: 0원', { haveUsim: true }, { usimTotal: 0, cheaper: 'usim' }],
  ['듀얼 24개월: +2,750+211,200', { dual: true }, { dualCost: 213950, esimTotal: 216700, usimTotal: 221650 }],
  ['KT 멤버십 2개월 할인', { dual: true, ktMember: true }, { dualDiscount: 17600, dualCost: 196350 }],
  ['KT 멤버십 1개월만 사용', { dual: true, ktMember: true, months: 1 }, { dualDiscount: 8800, dualCost: 2750 }],
  ['같은 금액', { esimFee: 3850, usimFee: 7700, changes: 1 }, { cheaper: 'same', diff: 0 }],
];
for (const [name, over, exp] of cases) {
  const r = calc(Object.assign({}, base, over));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 손익분기 표 검산
[[0, 2750], [1, 5500], [2, 8250], [3, 11000]].forEach(([n, v]) => assert.strictEqual(calc(Object.assign({}, base, { changes: n })).esimTotal, v));
console.log('PASS 손익분기 표 4행');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'es-carrier': 'kt', 'es-efee': '2750', 'es-ufee': '7700', 'es-months': '24', 'es-changes': '0', 'es-dfee': '8800' };
const checks = { 'es-have': false, 'es-dual': true, 'es-ktm': true };
const outP = [];
const el = id => ({ value: vals[id], checked: checks[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['es-out', 'es-ktwrap', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(KT, 24개월, 듀얼+멤버십):', outP.join(' | '));
assert.ok(outP.join().includes('199,100원'));
assert.ok(outP.join().includes('eSIM이 4,950원 저렴합니다'));
