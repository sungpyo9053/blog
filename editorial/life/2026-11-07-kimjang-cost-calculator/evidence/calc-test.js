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
const h3faq = html.split('<h2 id="faq">')[1].split('<script type')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq, 'FAQ JSON-LD count = body h3 count');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.kimjangCalc;
const DEF = [61280,9835,56932,11847,2090,6170,1538,2549,7251,5668,7365,12119,10466,6041];
assert.strictEqual(DEF.reduce((a, b) => a + b, 0), 201151, 'aT 합계 201,151');
const cases = [
  ['aT 20포기 = 201,151원', { mode: 'raw', heads: 20, people: 4 }, { total: 201151, perHead: 10058, rawKg: 66.7, suggest: 23.4 }],
  ['예시1 10포기 = 100,576원', { mode: 'raw', heads: 10 }, { total: 100576, rawKg: 33.3 }],
  ['예시2 23.4포기 = 235,347원', { mode: 'raw', heads: 23.4 }, { total: 235347, perHead: 10058 }],
  ['예시2 배추 56,580원 대입 = 229,848원', { mode: 'raw', heads: 23.4, prices: [56580].concat(DEF.slice(1)) }, { total: 229848 }],
  ['예시3 절임 40kg, 8포기 표기 = 162,002원', { mode: 'salted', kg: 40, box: 29900, label: 8 }, { saltedCost: 59800, basket: 102202, total: 162002, heads: 16 }],
  ['절임 20kg 표기 없음 = 절임값만', { mode: 'salted', kg: 20, box: 29900, label: 0 }, { saltedCost: 29900, basket: 0, total: 29900, heads: 0 }],
  ['0포기 = 0원', { mode: 'raw', heads: 0 }, { total: 0, perHead: 0 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(o);
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-9, name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ total: r.total, basket: r.basket, saltedCost: r.saltedCost, perHead: r.perHead, heads: r.heads, rawKg: r.rawKg }));
}
// 농사로 배합: 절인 배추 5kg -> 고추 220g(4.5%면 225g, 원문 반올림), 20kg -> 900/400/200/1000g
const s20 = calc({ mode: 'salted', kg: 20, box: 29900 }).seasoning;
assert.deepStrictEqual(s20.slice(0, 4).map(x => x[1]), [900, 400, 200, 1000]);
const s40 = calc({ mode: 'salted', kg: 40, box: 29900 }).seasoning;
assert.deepStrictEqual(s40.map(x => x[1]), [1800, 800, 400, 2000, 200, 200, 3400, 8000]);
console.log('PASS 농사로 배합 20kg/40kg', JSON.stringify(s40));
// 1포기당 aT 재료량
const one = calc({ mode: 'raw', heads: 1 }).items.map(x => [x[0], Math.round(x[1] * 1000) / 1000]);
console.log('1포기당', JSON.stringify(one));
// 본문 표 검산
for (const [n, won] of [[1, 58837], [2, 117673], [3, 176510], [4, 235347], [5, 294183]]) assert.strictEqual(calc({ mode: 'raw', heads: n * 23.4 / 4 }).total, won, 'people ' + n);
console.log('PASS 가구원 수 표 5행');
for (const [lab, per] of [[6, 4983], [8, 3738], [10, 2990]]) assert.strictEqual(Math.round(29900 / lab), per);
assert.strictEqual(Math.round((61280 + 12119) / 20), 3670);
console.log('PASS 생배추 vs 절임배추 표');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'kj-mode': 'raw', 'kj-people': '4', 'kj-heads': '20', 'kj-kg': '20', 'kj-box': '29900', 'kj-label': '' };
DEF.forEach((p, i) => vals['kj-p' + i] = String(p));
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['kj-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('201,151원'));
vals['kj-mode'] = 'salted'; ['kj-out', ...Object.keys(vals)].forEach(id => els[id] = el(id)); eval(src);
console.log('UI 절임배추 출력:', outP.join(' | '));
assert.ok(outP.join().includes('29,900원'));
console.log('ALL PASS');
