// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.carTaxCalc;
// [이름, cc, ev, 등록연도, 등록반기, 과세연도, 연납월, 기대값]
const cases = [
  ['행안부 4.58%: 1월 연납 실질 할인율(평년 334/365x5%)', 1999, false, 2026, 1, 2027, 1, { car: 399800, disc: 18292 }],
  ['1,999cc 새 차 2027 1월', 1999, false, 2026, 1, 2027, 1, { car: 399800, edu: 119940, regTotal: 519740, preTotal: 495960, save: 23780 }],
  ['1,598cc 140원/cc', 1598, false, 2026, 1, 2027, 1, { base: 223720, regTotal: 290836, preTotal: 277530, save: 13306 }],
  ['2,497cc', 2497, false, 2026, 1, 2027, 1, { regTotal: 649220, preTotal: 619516, save: 29704 }],
  ['2,999cc', 2999, false, 2026, 1, 2027, 1, { regTotal: 779740, preTotal: 744065, save: 35675 }],
  ['998cc 10만원 이하: 정기분도 2기분 5% 공제', 998, false, 2026, 1, 2027, 1, { car: 79840, small: true, regCar: 77844, regTotal: 101197, preTotal: 99044, save: 2153 }],
  ['1,000cc 경계 80원', 1000, false, 2026, 1, 2027, 0, { base: 80000 }],
  ['1,600cc 경계 140원', 1600, false, 2026, 1, 2027, 0, { base: 224000 }],
  ['1,601cc 200원', 1601, false, 2026, 1, 2027, 0, { base: 320200 }],
  ['차령 3년(2025 상반기 등록) 5% 경감', 1999, false, 2025, 1, 2027, 1, { age1: 3, h1: 189905, car: 379810, regTotal: 493753, preTotal: 471162, save: 22591 }],
  ['차령 8년 30% 경감', 1999, false, 2020, 1, 2027, 1, { car: 279860, regTotal: 363818, preTotal: 347172 }],
  ['차령 13년 -> 12년 상한 50%', 1999, false, 2015, 1, 2027, 1, { age1: 13, car: 199900, regTotal: 259870, preTotal: 247980 }],
  ['하반기 등록: 1기분 차령 3, 2기분 4', 1999, false, 2024, 2, 2027, 0, { age1: 3, age2: 4, h1: 189905, h2: 179910 }],
  ['3월 연납 275/365', 1999, false, 2026, 1, 2027, 3, { disc: 15060, save: 19578 }],
  ['6월 연납 2기분 5%', 1999, false, 2026, 1, 2027, 6, { disc: 9995, save: 12994 }],
  ['9월 연납 2기분 x 92/184 x 5%', 1999, false, 2026, 1, 2027, 9, { disc: 4997, save: 6497 }],
  ['전기차 10만원, 차령 경감 없음', 0, true, 2010, 1, 2027, 1, { car: 100000, edu: 30000, regTotal: 126750, preTotal: 124052, save: 2698 }],
  ['윤년 2028 1월 335/366', 1999, false, 2027, 1, 2028, 1, { disc: Math.floor(399800 * 335 / 366 * 0.05) }],
  ['연납 안 함', 1999, false, 2026, 1, 2027, 0, { disc: 0, save: 0 }],
];
for (const [name, cc, ev, ry, rh, y, m, exp] of cases) {
  const r = calc(cc, ev, ry, rh, y, m);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.ok(Math.abs(18292 / 399800 * 100 - 4.575) < 0.01);
// 본문 숫자 대조
for (const s of ['519,740원', '495,960원', '23,780원', '101,197원', '99,044원', '2,153원', '290,836원', '277,530원', '13,306원', '649,220원', '619,516원', '29,704원', '779,740원', '744,065원', '35,675원', '126,750원', '124,052원', '2,698원', '493,753원', '471,162원', '363,818원', '347,172원', '259,870원', '247,980원', '19,578원', '12,994원', '6,497원', '18,292원', '5,488원'])
  assert.ok(html.includes(s), 'missing in body ' + s);
assert.strictEqual(119940 - Math.floor((399800 - 18292) * 0.3), 5488);
console.log('PASS 본문 금액 29개 일치');
// UI 기본값(1,999cc, 2026 상반기 등록, 2027년, 1월) 렌더 확인
const vals = { 'ct-type': 'gas', 'ct-cc': '1999', 'ct-regy': '2026', 'ct-regh': '1', 'ct-year': '2027', 'ct-month': '1' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ct-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('495,960원'));
