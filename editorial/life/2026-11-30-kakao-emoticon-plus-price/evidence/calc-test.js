// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faqN = JSON.parse(ld).mainEntity.length;
assert.ok(faqN >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.emoticonPlusCalc;
const cases = [
  ['기본: 2개 x 2,500 / 3,900 / 12개월', 2, 2500, 3900, 12, { buyMonth: 5000, diffMonth: 1100, breakEven: 2, buyTotal: 60000, feeTotal: 46800, owned: 24, cheaper: 'plus' }],
  ['1개 x 2,500 -> 구매가 1,400 쌈', 1, 2500, 3900, 1, { diffMonth: -1400, cheaper: 'buy' }],
  ['1개 x 3,750 -> 구매가 150 쌈', 1, 3750, 3900, 1, { diffMonth: -150, breakEven: 2, cheaper: 'buy' }],
  ['1개 x 5,000 -> 구독이 1,100 쌈', 1, 5000, 3900, 1, { diffMonth: 1100, breakEven: 1, cheaper: 'plus' }],
  ['3개 x 3,750 -> 7,350', 3, 3750, 3900, 1, { buyMonth: 11250, diffMonth: 7350 }],
  ['4개 x 5,000 -> 16,100', 4, 5000, 3900, 1, { diffMonth: 16100 }],
  ['같음: 1개 x 3,900', 1, 3900, 3900, 1, { diffMonth: 0, breakEven: 1, cheaper: 'same' }],
  ['가격 0 -> 본전 null', 2, 0, 3900, 1, { breakEven: null, cheaper: 'buy' }],
  ['0개', 0, 2500, 3900, 12, { buyMonth: 0, owned: 0, cheaper: 'buy' }],
];
for (const [name, n, p, f, m, exp] of cases) {
  const r = calc(n, p, f, m);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본전 표 검산 (1~4개 x 2,500/3,750/5,000)
const table = { 2500: [-1400, 1100, 3600, 6100], 3750: [-150, 3600, 7350, 11100], 5000: [1100, 6100, 11100, 16100] };
for (const p of Object.keys(table)) table[p].forEach((d, i) => assert.strictEqual(calc(i + 1, +p, 3900, 1).diffMonth, d));
assert.strictEqual(Math.floor(46800 / 2500), 18);
console.log('PASS 본전 표 12칸 + 1년 18개');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'ep-count': '2', 'ep-preset': '2500', 'ep-price': '2500', 'ep-fee': '3900', 'ep-months': '12' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ep-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('구독이 한 달 1,100원 싸다'));
assert.ok(outP.join().includes('60,000원'));
assert.ok(outP.join().includes('24개'));
console.log('FAQ JSON-LD 항목:', faqN);
