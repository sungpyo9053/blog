// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.includes('<')) throw new Error('< in JS string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD'); JSON.parse(ld);
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const calc = window.evChargeCalc;
const base = { pay: 'member', price: NaN, kwh: NaN, bat: NaN, from: NaN, to: NaN, eff: NaN, month: 0, mpg: NaN, fuel: NaN };
const cases = [
  ['100~200kW 40kWh = 13,936', { type: '348.4', kwh: 40 }, { fee: 13936 }],
  ['완속 40kWh = 11,800', { type: '295.0', kwh: 40 }, { fee: 11800 }],
  ['초급속 40kWh = 15,724', { type: '393.1', kwh: 40 }, { fee: 15724 }],
  ['배터리 64kWh 20->80% = 38.4kWh', { type: '348.4', bat: 64, from: 20, to: 80 }, { kwh: 38.4, fee: 13379 }],
  ['전비 5 완속 1km 59.0원', { type: '295.0', kwh: 10, eff: 5 }, { perKm: 59, range: 50 }],
  ['전비 5 초급속 1km 78.6원', { type: '393.1', kwh: 10, eff: 5 }, { perKm: 78.6 }],
  ['손익분기 연비12 완속 708원', { type: '295.0', kwh: 10, eff: 5, mpg: 12 }, { breakEven: 708, gas: false }],
  ['손익분기 연비12 초급속 943원', { type: '393.1', kwh: 10, eff: 5, mpg: 12 }, { breakEven: 943 }],
  ['직접 입력 446원 x 20kWh', { type: 'custom', price: 446, kwh: 20 }, { fee: 8920 }],
  ['직접 입력 빈칸 -> 계산 안 함', { type: 'custom', kwh: 20 }, { ok: false }],
  ['휘발유 비교 1000km 연비 10 리터 2000(임의 입력)', { type: '295.0', kwh: 10, eff: 5, month: 1000, mpg: 10, fuel: 2000 }, { month: 59000, gasMonth: 200000, diff: 141000, gas: true }],
  ['목표%가 현재%보다 낮으면 0', { type: '295.0', bat: 64, from: 80, to: 20 }, { ok: false }],
];
for (const [name, o, exp] of cases) {
  const r = calc(Object.assign({}, base, o));
  for (const k of Object.keys(exp)) assert.ok(r[k] === exp[k] || Math.abs(r[k] - exp[k]) < 1e-9, name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 표 값 검산
const tiers = [295.0, 325.6, 348.4, 393.1];
const table = { 10: [2950, 3256, 3484, 3931], 20: [5900, 6512, 6968, 7862], 30: [8850, 9768, 10452, 11793], 40: [11800, 13024, 13936, 15724], 60: [17700, 19536, 20904, 23586] };
let n = 0;
for (const k in table) tiers.forEach((t, i) => { assert.strictEqual(calc(Object.assign({}, base, { type: String(t), kwh: +k })).fee, table[k][i]); n++; });
assert.strictEqual(Math.round(40 * 324.4), 12976); assert.strictEqual(Math.round(40 * 347.2), 13888);
[[4, 295.0, 73.8], [4, 393.1, 98.3], [6, 295.0, 49.2], [6, 393.1, 65.5]].forEach(([e, t, v]) => assert.strictEqual(calc(Object.assign({}, base, { type: String(t), kwh: 1, eff: e })).perKm, v));
console.log('PASS 표 값 ' + n + '개 + 개편 전 2개 + 전비별 4개');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'evc-type': '348.4', 'evc-pay': 'nonmember', 'evc-price': '', 'evc-kwh': '', 'evc-bat': '64', 'evc-from': '20', 'evc-to': '80', 'evc-eff': '5', 'evc-month': '1000', 'evc-mpg': '', 'evc-fuel': '' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['evc-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값(비회원 선택) 출력:', outP.join(' | '));
assert.ok(outP[0].includes('13,379원')); assert.ok(outP.join().includes('확인하지 못했다'));
