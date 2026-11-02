// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.welaaaCalc, refund = window.welaaaRefund;
const cases = [
  ['베이직 월간 12개월', { plan: 'bm', price: 12500, months: 12, people: 1, books: 2, bookPrice: 10000 }, { total: 150000, perMonth: 12500, perBook: 6250, breakEven: 1.25, buyTotal: 240000, buyDiff: 90000, millie: 142800 }],
  ['베이직 연간 12개월', { plan: 'by', price: 125000, months: 12, people: 1, books: 0, bookPrice: 0 }, { total: 125000, payments: 1, perMonth: 10417, millie: 119000 }],
  ['베이직 연간 13개월 -> 2회', { plan: 'by', price: 125000, months: 13, people: 1, books: 0, bookPrice: 0 }, { total: 250000, payments: 2, millie: 238000 }],
  ['베이직 월간 10개월 = 연간', { plan: 'bm', price: 12500, months: 10, people: 1, books: 0, bookPrice: 0 }, { total: 125000 }],
  ['패밀리 월간 2명', { plan: 'fm', price: 16900, months: 1, people: 2, books: 0, bookPrice: 0 }, { total: 16900, perPerson: 8450 }],
  ['패밀리 연간 2명', { plan: 'fy', price: 169000, months: 12, people: 2, books: 0, bookPrice: 0 }, { total: 169000, perPerson: 84500, perMonth: 14083 }],
  ['전자책 8,900 x 6', { plan: 'em', price: 8900, months: 6, people: 1, books: 1, bookPrice: 8900 }, { total: 53400, perBook: 8900, breakEven: 1, buyDiff: 0 }],
  ['앱 아이폰 16,000 x 12', { plan: 'bm', price: 16000, months: 12, people: 1, books: 0, bookPrice: 0 }, { total: 192000 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 연간 환불 표(베이직 125,000 / 월 12,500)
const tbl = { 1: [101250, 11250, 23750], 3: [78750, 8750, 46250], 6: [45000, 5000, 80000], 9: [11250, 1250, 113750], 10: [0, 0, 125000], 12: [0, 0, 125000] };
for (const u of Object.keys(tbl)) { const f = refund(125000, 12500, +u); assert.deepStrictEqual([f.refund, f.penalty, f.cost], tbl[u], 'refund ' + u); }
console.log('PASS 환불 표 6행');
// 본문 표 값: 월간/연간 총액
[[6, 75000, 101400], [10, 125000, 169000], [12, 150000, 202800], [24, 300000, 405600]].forEach(([m, b, f]) => {
  assert.strictEqual(calc({ plan: 'bm', price: 12500, months: m, people: 1 }).total, b);
  assert.strictEqual(calc({ plan: 'fm', price: 16900, months: m, people: 1 }).total, f);
});
assert.strictEqual(calc({ plan: 'fy', price: 169000, months: 24, people: 1 }).total, 338000);
console.log('PASS 월간·연간 표 값');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'wl-plan': 'bm', 'wl-months': '12', 'wl-price': '12500', 'wl-people': '1', 'wl-books': '2', 'wl-bookprice': '', 'wl-used': '3' };
const outs = {};
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outs[id] = []; }, appendChild(p) { outs[id].push(p.textContent); } });
const els = {}; ['wl-out', 'wl-cmp', 'wl-refund', 'wl-reset', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
for (const k of ['wl-out', 'wl-cmp', 'wl-refund']) console.log('UI', k, ':', outs[k].join(' | '));
assert.ok(outs['wl-out'].join().includes('150,000원'));
assert.ok(outs['wl-refund'].join().includes('78,750원'));
console.log('ALL PASS');
