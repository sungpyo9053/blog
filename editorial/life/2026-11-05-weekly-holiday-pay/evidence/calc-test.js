// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.weeklyHolidayCalc;
const cases = [
  ['고용노동부 예: 주20h(8+8+4) 시급 10,000', 10000, 20, 5, { holHours: 4, holPay: 40000 }],
  ['고용노동부 예②: 월수금 6h 18h 시급 10,000', 10000, 18, 5, { holHours: 3.6, holPay: 36000 }],
  ['고용노동부 예①: 6일제 사업장 6h x 6일', 10000, 36, 6, { holHours: 6, holPay: 60000 }],
  ['2026 최저 주40h -> 월 209h 2,156,880', 10320, 40, 5, { holHours: 8, holPay: 82560, monthHours: 209, monthPay: 2156880 }],
  ['2027 최저 주40h -> 월 2,236,300', 10700, 40, 5, { holPay: 85600, monthPay: 2236300 }],
  ['경계: 주 14.5h -> 0', 10320, 14.5, 5, { eligible: false, holPay: 0 }],
  ['경계: 주 15h -> 3h 30,960', 10320, 15, 5, { eligible: true, holHours: 3, holPay: 30960 }],
  ['상한: 주 50h -> 8h, 주급은 40h까지', 10320, 50, 5, { holHours: 8, holPay: 82560, weekPay: 412800 + 82560, over: true }],
];
for (const [name, wage, weekly, nd, exp] of cases) {
  const r = calc(wage, weekly, nd);
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-9 || r[k] === exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 표 값 검산
for (const [wage, row] of [[10320, [30960, 41280, 51600, 61920, 72240, 82560]], [10700, [32100, 42800, 53500, 64200, 74900, 85600]]])
  [15, 20, 25, 30, 35, 40].forEach((h, i) => assert.strictEqual(calc(wage, h, 5).holPay, row[i]));
console.log('PASS 표 값 12개');
// UI 기본값(시급 10,320, 4h x 5일) 렌더 확인 — 최소 DOM 스텁
const vals = { 'wh-wage': '10320', 'wh-day': '4', 'wh-days': '5', 'wh-week': '', 'wh-normal': '5' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['wh-out', 'wh-y2026', 'wh-y2027', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('41,280원'));
