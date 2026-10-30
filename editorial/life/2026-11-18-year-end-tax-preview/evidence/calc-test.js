// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error("raw '<' inside a string literal");
for (const m of html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
  if (/[&<]/.test(m[1])) throw new Error('& or < in JSON-LD');
  JSON.parse(m[1]);
}
global.window = {};
global.document = { getElementById: () => null };
try { eval(src); } catch (e) { /* UI 바인딩은 아래에서 따로 */ }
const { calc, compare } = window.yearEndPreviewCalc;
const W = 10000; // 만 원
const cases = [
  // name, G, C, D, M, T, Q, kids, credit, check
  ['예시1 총급여 4천, 9월까지 신용 900', 4000, 900, 150, 0, 40, 300, 0, 910000, 1210000],
  ['예시2 총급여 6천, 신용 1,300', 6000, 1300, 100, 50, 30, 450, 0, 995000, 1370000],
  ['예시3 총급여 5천, 한도 초과 -> 차이 0', 5000, 2500, 800, 0, 60, 600, 0, 3240000, 3240000],
  ['기본값 총급여 5천, Q 400 -> 차이 60만', 5000, 1300, 200, 30, 60, 400, 0, 1635000, 2235000],
  ['25% 미달 -> 둘 다 0', 5000, 600, 100, 0, 0, 300, 0, 0, 0],
  ['7천 초과 자녀2 한도 300 + 추가 200 cap', 10000, 3000, 3000, 800, 400, 0, 2, 5000000, 5000000],
];
for (const [name, G, C, D, M, T, Q, kids, ea, eb] of cases) {
  const x = compare(G * W, C * W, D * W, M * W, T * W, Q * W, kids);
  assert.strictEqual(x.credit.result, ea, name + ' credit=' + x.credit.result);
  assert.strictEqual(x.check.result, eb, name + ' check=' + x.check.result);
  console.log('PASS', name, '신용', x.credit.result, '체크', x.check.result, '차이', x.diff);
}
// '25%까지 신용, 나머지 체크' == '전부 체크' (제6호가 신용카드분부터 차감)
{
  const G = 4000 * W, C = 900 * W, D = 150 * W, Q = 300 * W, fill = 1000 * W - C;
  const mixed = calc(G, C + fill, D + Q - fill, 0, 40 * W, 0).result;
  assert.strictEqual(mixed, compare(G, C, D, 0, 40 * W, Q, 0).check.result);
  console.log('PASS 25%까지 신용 후 체크 = 전부 체크', mixed);
}
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'yp-g': '5000', 'yp-c': '1300', 'yp-d': '200', 'yp-m': '30', 'yp-t': '60', 'yp-q': '400', 'yp-kids': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['yp-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('600,000원 더 늘어납니다'));
console.log('ALL PASS');
