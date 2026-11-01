// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('raw < in string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ', faq, '개 = JSON-LD', faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.millieCalc, refund = window.millieRefund, D = window.millieDefaults;
assert.deepStrictEqual(D, { m: 11900, y: 119000 });
const base = { priceM: 11900, priceY: 119000, books: 0, bookPrice: 0 };
const cases = [
  ['연 12개월', { plan: 'y', months: 12 }, { total: 119000, monthlyTotal: 142800, diff: 23800, perMonth: 9917, years: 1 }],
  ['연 10개월 손익분기', { plan: 'y', months: 10 }, { total: 119000, diff: 0 }],
  ['연 9개월', { plan: 'y', months: 9 }, { monthlyTotal: 107100, diff: -11900 }],
  ['연 13개월 2회 결제', { plan: 'y', months: 13 }, { years: 2, total: 238000, monthlyTotal: 154700 }],
  ['연 24개월', { plan: 'y', months: 24 }, { total: 238000, monthlyTotal: 285600, diff: 47600 }],
  ['월 6개월', { plan: 'm', months: 6 }, { total: 71400, yearlyTotal: 119000, diff: 47600 }],
  ['월 1개월 2권', { plan: 'm', months: 1, books: 2 }, { perBook: 5950, bookCount: 2 }],
  ['연 12개월 월2권', { plan: 'y', months: 12, books: 2 }, { bookCount: 24, perBook: 4958 }],
  ['월 3개월 월2권 권당 9,000원 구매 비교', { plan: 'm', months: 3, books: 2, bookPrice: 9000 }, { total: 35700, buyTotal: 54000, buyDiff: 18300 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(Object.assign({}, base, o));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 중도 해지 표
const table = { 1: [11900, 10710, 96390, 22610], 3: [35700, 8330, 74970, 44030], 6: [71400, 4760, 42840, 76160], 9: [107100, 1190, 10710, 108290], 10: [119000, 0, 0, 119000], 12: [119000, 0, 0, 119000] };
for (const u of Object.keys(table)) {
  const f = refund(119000, 11900, +u), e = table[u];
  assert.deepStrictEqual([f.usedFee, f.penalty, f.refund, f.cost], e, 'refund ' + u);
  console.log('PASS 중도해지', u + '개월', JSON.stringify(f));
}
assert.strictEqual(11900 * 0.9, 10710); assert.strictEqual(119000 * 0.9, 107100);
console.log('PASS 7일 경과 90% 환불 값');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'ml-plan': 'y', 'ml-months': '12', 'ml-mprice': '11900', 'ml-yprice': '119000', 'ml-books': '2', 'ml-bookprice': '', 'ml-used': '3' };
const boxes = {};
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { boxes[id] = []; }, appendChild(p) { boxes[id].push(p.textContent); } });
const els = {}; ['ml-out', 'ml-cmp', 'ml-refund', 'ml-reset', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력:', boxes['ml-out'].join(' | '), '||', boxes['ml-cmp'].join(' | '), '||', boxes['ml-refund'].join(' | '));
assert.ok(boxes['ml-out'].join().includes('119,000원'));
assert.ok(boxes['ml-refund'].join().includes('74,970원'));
console.log('ALL PASS');
