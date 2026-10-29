// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src.trim())) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string ' + m);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.elecBillCalc, T = window.elecTariff;
const f = (kwh, season, volt, extra) => calc(Object.assign({ kwh, season, basic: T[volt].basic, rate: T[volt].rate, sup: T[volt].sup, min: T[volt].min, climate: 9.0, fuel: 5.0, vat: 10, fundRate: 2.7 }, extra || {}));
const cases = [
  ['한전 PDF 예시1: 기타 450kWh, 기금 3.7%', f(450, 'other', 'low', { fundRate: 3.7 }), { basic: 7300, energy: 82285, climate: 4050, fuel: 2250, subtotal: 95885, vat: 9589, fund: 3540, bill: 109010 }],
  ['한전 누진제 안내: 기타 300kWh 전력량요금 45,460', f(300, 'other', 'low'), { energy: 45460, basic: 1600 }],
  ['2026 기금 2.7%: 기타 450kWh', f(450, 'other', 'low'), { fund: 2580, bill: 108050 }],
  ['본문 예시: 기타 350kWh', f(350, 'other', 'low'), { basic: 1600, energy: 56190, subtotal: 62690, vat: 6269, fund: 1690, bill: 70640 }],
  ['하계 350kWh', f(350, 'summer', 'low'), { energy: 46730, bill: 59980 }],
  ['경계 400 vs 401 기본요금', f(401, 'other', 'low'), { basic: 7300 }],
  ['하계 경계 450 -> 2단계 기본요금', f(450, 'summer', 'low'), { basic: 1600, bill: 85740 }],
  ['동계 1,200kWh 슈퍼유저', f(1200, 'winter', 'low'), { energy: 398540, bill: 476310 }],
  ['기타 1,200kWh는 슈퍼유저 없음', f(1200, 'other', 'low'), { energy: 312760, bill: 379630 }],
  ['0kWh 저압 최저요금', f(0, 'other', 'low'), { minApplied: true, subtotal: 1000 }],
  ['고압 기타 450kWh', f(450, 'other', 'high'), { basic: 6060, bill: 90460 }],
];
for (const [name, r, exp] of cases) {
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ basic: r.basic, energy: r.energy, subtotal: r.subtotal, vat: r.vat, fund: r.fund, bill: r.bill }));
}
// 본문 표 값 검산
const table = { 100: [16120, 16120, 14230, 14230], 200: [31220, 31220, 27640, 27640], 250: [44880, 38770, 38830, 34340], 300: [57760, 46320, 49420, 41050], 350: [70640, 59980, 60010, 52240], 400: [83530, 72860, 70610, 62830], 450: [108050, 85740, 90460, 73420], 500: [126160, 110280, 104900, 93280], 600: [162370, 146480, 133790, 122160] };
let n = 0;
for (const k of Object.keys(table)) [['other', 'low'], ['summer', 'low'], ['other', 'high'], ['summer', 'high']].forEach(([s, v], i) => { assert.strictEqual(f(+k, s, v).bill, table[k][i], k + s + v); n++; });
for (const k of Object.keys(table)) for (const s of ['other', 'summer']) for (const v of ['low', 'high']) assert.ok(html.includes(f(+k, s, v).bill.toLocaleString('en-US') + '원'));
console.log('PASS 표 값 ' + n + '개');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'eb-season': 'other', 'eb-volt': 'low', 'eb-kwh': '350', 'eb-climate': '9.0', 'eb-fuel': '5.0', 'eb-vatr': '10', 'eb-fundr': '2.7' };
const outP = [];
const els = {};
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = String(v); }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
['eb-out', 'eb-b1', 'eb-b2', 'eb-b3', 'eb-r1', 'eb-r2', 'eb-r3', 'eb-sup', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('청구금액(10원 미만 버림): 70,640원'));
assert.strictEqual(vals['eb-r2'], '214.6');
