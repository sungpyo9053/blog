// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.cmaCalc;
const cases = [
  ['1천만 2% 30일 단리', 1e7, 2, 30, 'simple', { pre: 16438, incTax: 2301, locTax: 230, post: 13907 }],
  ['1천만 2% 30일 일복리', 1e7, 2, 30, 'daily', { pre: 16451, post: 13918 }],
  ['1천만 2% 365일 단리', 1e7, 2, 365, 'simple', { pre: 200000, post: 169200 }],
  ['1천만 2% 365일 일복리', 1e7, 2, 365, 'daily', { pre: 202007, post: 170899 }],
  ['1천만 2.5% 30일', 1e7, 2.5, 30, 'simple', { post: 17384 }],
  ['1천만 3% 30일', 1e7, 3, 30, 'simple', { post: 20861 }],
  ['1억 2% 30일', 1e8, 2, 30, 'simple', { pre: 164383, post: 139069 }],
  ['0% -> 0원', 1e7, 0, 30, 'simple', { pre: 0, post: 0 }],
  ['1일 1천만 2%', 1e7, 2, 1, 'daily', { pre: 547, post: 464 }],
];
for (const [name, P, r, d, m, exp] of cases) {
  const a = calc(P, r, d, m);
  for (const k of Object.keys(exp)) assert.strictEqual(a[k], exp[k], name + ' ' + k + '=' + a[k]);
  console.log('PASS', name, JSON.stringify(a));
}
// 본문 예시 표 검산 (연 2%)
const t30 = [[1e6, 1643, 1390, 1392], [5e6, 8219, 6954, 6959], [1e7, 16438, 13907, 13918], [3e7, 49315, 41721, 41755], [5e7, 82191, 69535, 69591], [1e8, 164383, 139069, 139180]];
const t365 = [[1e6, 20000, 16920, 17090], [1e7, 200000, 169200, 170899], [5e7, 1000000, 846000, 854494], [1e8, 2000000, 1692000, 1708987]];
for (const [d, rows] of [[30, t30], [365, t365]]) for (const [P, pre, post, postD] of rows) {
  const s = calc(P, 2, d, 'simple'), y = calc(P, 2, d, 'daily');
  assert.strictEqual(s.pre, pre); assert.strictEqual(s.post, post); assert.strictEqual(y.post, postD);
}
console.log('PASS 예시 표 10행');
// 표에 쓴 숫자가 ko.html 안에 실제로 있는지
for (const n of ['16,438원', '13,907원', '13,918원', '170,899원', '1,708,987원', '17,384원', '20,861원', '2,531원']) assert.ok(html.includes(n), n);
// UI 기본값 렌더 (1천만, 30일, 다섯 유형 모두 2%)
const vals = { 'cma-amt': '10000000', 'cma-days': '30', 'cma-r-rp': '2', 'cma-r-bill': '2', 'cma-r-mmf': '2', 'cma-r-mmw': '2', 'cma-r-jong': '' };
function node(tag) { return { tag, style: {}, kids: [], textContent: '', appendChild(c) { this.kids.push(c); } }; }
const out = node('div'); Object.defineProperty(out, 'innerHTML', { set() { out.kids = []; } });
const els = { 'cma-out': out }; Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
global.document = { getElementById: id => els[id], createElement: node };
eval(src);
function flat(n) { return n.kids.length ? n.kids.map(flat).join(n.tag === 'tr' ? ' | ' : '\n') : n.textContent; }
const shown = flat(out);
console.log('UI 기본값 출력(종금형 비움):\n' + shown);
assert.ok(shown.includes('13,907원')); assert.ok(shown.includes('13,918원')); assert.ok(!shown.includes('종금형'));
assert.ok(shown.includes('차이는 11원'));
console.log('FAQ JSON-LD 질문 수:', faq);
