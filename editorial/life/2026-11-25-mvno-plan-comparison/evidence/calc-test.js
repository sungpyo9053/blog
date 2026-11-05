// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.mvnoCalc;
const base = { cur: 50000, data: 8, calls: 150, months: 24, promo: NaN, promoMonths: 7, after: NaN, oneTime: 0 };
const cases = [
  ['본문 예: 7개월 10원 후 14,300원, 24개월', { promo: 10, after: 14300 }, { total: 243170, avg: 10132, curTotal: 1200000, save: 956830, monthSave: 39868, yearSave: 478415, refUsed: false }],
  ['본문 예: 할인 없이 12,000원, 24개월', { after: 12000 }, { total: 288000, promoUsed: 0 }],
  ['빈 칸이면 구간 중앙값(8GB -> 6~10GB 14,300)', {}, { bandLabel: '6~10GB', after: 14300, refUsed: true, total: 343200 }],
  ['할인 개월이 기간보다 길면 기간까지만', { months: 6, promo: 990, promoMonths: 12, after: 9900 }, { total: 5940, promoUsed: 6 }],
  ['일회성 비용 포함', { promo: 10, after: 14300, oneTime: 100000 }, { total: 343170 }],
  ['더 비싸면 음수 절약', { cur: 10000, after: 30000 }, { save: -480000 }],
  ['구간 경계: 5GB -> 5GB 이하, 근접 경고', { data: 5 }, { bandLabel: '5GB 이하', near: true }],
  ['구간 경계: 20.5GB -> 21~99GB', { data: 20.5 }, { bandLabel: '21~99GB', near: false }],
  ['100GB 이상, 마지막 구간은 근접 경고 없음', { data: 150 }, { bandLabel: '100GB 이상', near: false, after: 50600 }],
  ['통화 100분 -> 100분 이상', { calls: 100 }, { callLabel: '100분 이상' }],
  ['통화 320분 -> 350분 이상', { calls: 320 }, { callLabel: '350분 이상' }],
  ['통화 400분 -> 무제한', { calls: 400 }, { callLabel: '통화 무제한' }],
  ['할인 0원도 유효', { promo: 0, promoMonths: 12, after: 10000, months: 12 }, { total: 0 }],
];
for (const [name, over, exp] of cases) {
  const r = calc(Object.assign({}, base, over));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'mv-cur': '50000', 'mv-data': '8', 'mv-calls': '150', 'mv-months': '24', 'mv-promo': '', 'mv-pm': '7', 'mv-after': '', 'mv-one': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['mv-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('6~10GB'));
assert.ok(outP.join().includes('856,800원'));
