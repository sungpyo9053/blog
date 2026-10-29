// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g)) if (lit.indexOf('<') >= 0) throw new Error('< in string literal ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.birthSupportCalc;
const B = '2026-11-14';
const cases = [
  ['2026.11.1 첫째 가정양육: 60일 안, 24개월 1,800만', '2026-11-01', 1, 'home', B,
    { fmAmount: 2000000, fmDays: 718, deadlineDays: 46, withinSixty: true, months: 24, total: 18000000, cash: 18000000, voucher: 0, currentMonthly: 1000000 }],
  ['2026.3.10 둘째 가정양육: 8개월, 16개월 1,000만', '2026-03-10', 2, 'home', B,
    { fmAmount: 3000000, withinSixty: false, ageNow: 8, months: 16, total: 10000000, missed: 8000000 }],
  ['2025.12.20 첫째 어린이집: 11개월, 13개월 700만, 현금 416,000 바우처 6,764,000', '2025-12-20', 1, 'daycare', B,
    { ageNow: 11, months: 13, total: 7000000, cash: 416000, voucher: 6764000, currentCash: 416000, currentVoucher: 584000 }],
  ['2024.11.20 첫째: 24개월 종료, 첫만남 D-6', '2024-11-20', 1, 'home', B,
    { ageNow: 24, months: 0, total: 0, fmDays: 6, currentMonthly: 0 }],
  ['경계: 출생일+59일 = 마감 D-day', '2026-09-16', 1, 'home', '2026-11-14', { deadlineDays: 0, withinSixty: true, months: 24 }],
  ['경계: 출생일+60일 = 마감 지남, 2개월 놓침', '2026-09-15', 1, 'home', '2026-11-14', { deadlineDays: -1, withinSixty: false, ageNow: 2, months: 22, missed: 2000000 }],
  ['경계: 12개월째 50만원', '2025-11-30', 1, 'home', B, { ageNow: 12, currentMonthly: 500000 }],
  ['2월 29일생 사용기한 2026.2.28', '2024-02-29', 2, 'home', B, { fmAmount: 3000000, fmEnd: Date.UTC(2026, 1, 28) }],
  ['2023년생: 사용기간 1년 지남', '2023-06-01', 1, 'home', B, { fmNew: false }],
];
for (const [name, birth, order, care, base, exp] of cases) {
  const r = calc(birth, order, care, base);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 (출생 2026-11-01, 기준일 고정)
const vals = { 'bs-birth': '2026-11-01', 'bs-order': '1', 'bs-care': 'home', 'bs-base': '' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = v; }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['bs-out', 'bs-today', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값(기준일=오늘) 출력:', outP.join(' | '));
assert.ok(outP.join().includes('2,000,000원'));
