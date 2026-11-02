// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^'\n]*'/g) || []) if (s.includes('<')) throw new Error('raw < in string ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.parkingCalc;
const cases = [
  ['1천만 2% 30일 만기', 1e7, 2, 30, { pay: 'end' }, { daily0: 547, pre: 16438, incTax: 2301, locTax: 230, post: 13907 }],
  ['300만 2% 30일', 3e6, 2, 30, { pay: 'end' }, { pre: 4931, post: 4172 }],
  ['1천만 2% 1일', 1e7, 2, 1, { pay: 'end' }, { pre: 547, incTax: 76, locTax: 7, post: 464 }],
  ['구간 5천만 500만까지 4% 초과 1.5% 30일', 5e7, 4, 30, { limit: 5e6, rate2: 1.5, pay: 'end' }, { daily0: 2397, pre: 71917, effRate: 1.75 }],
  ['1천만 2% 1년 만기', 1e7, 2, 365, { pay: 'end' }, { pre: 200000, post: 169200 }],
  ['1천만 2% 1년 월지급', 1e7, 2, 365, { pay: 'month' }, { post: 170530, payments: 13 }],
  ['1억 2.5% 1년 만기', 1e8, 2.5, 365, { pay: 'end' }, { pre: 2500000, post: 2115000 }],
  ['1억 2.5% 1년 월지급', 1e8, 2.5, 365, { pay: 'month' }, { post: 2135676, end: 102135676 }],
  ['1천만 2% 182일 월지급', 1e7, 2, 182, { pay: 'month' }, { post: 84671 }],
  ['비과세', 1e7, 2, 30, { pay: 'end', tax: 0 }, { incTax: 0, locTax: 0, post: 16438 }],
  ['한도보다 적은 잔액은 우대 금리만', 3e6, 4, 365, { limit: 5e6, rate2: 1.5, pay: 'end' }, { pre: 120000, effRate: 4 }],
];
for (const [name, P, r, d, o, exp] of cases) {
  const a = calc(P, r, d, o);
  for (const k of Object.keys(exp)) assert.strictEqual(a[k], exp[k], name + ' ' + k + '=' + a[k]);
  console.log('PASS', name, JSON.stringify(a));
}
// 구간 금리 표
[[5e6, 4, 200000], [1e7, 2.75, 275000], [3e7, 1.92, 575000], [5e7, 1.75, 875000], [1e8, 1.63, 1625000]].forEach(([P, eff, pre]) => {
  const a = calc(P, 4, 365, { limit: 5e6, rate2: 1.5, pay: 'end' });
  assert.strictEqual(a.effRate, eff); assert.strictEqual(a.pre, pre);
});
console.log('PASS 구간 금리 표 5행');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'pk-amt': '10000000', 'pk-rate': '2', 'pk-days': '30', 'pk-limit': '', 'pk-rate2': '', 'pk-pay': 'month', 'pk-tax': '1' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['pk-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('13,907원'));
console.log('FAQ JSON-LD 질문 수:', faq);
