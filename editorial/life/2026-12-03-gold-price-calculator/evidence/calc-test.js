// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.map(q => q.name);
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>([^<]*)<\/h3>/g).map(s => s.replace(/<\/?h3>/g, ''));
assert.deepStrictEqual(h3faq, faq);
console.log('JSON-LD OK, FAQ h3 == JSON-LD Q:', faq.length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.goldPriceCalc;
const base = { price: 200000, priceUnit: 'g', basis: 'pure', karat: '24', weight: 1, weightUnit: 'don', mode: 'buy', labor: 0, addVat: false };
const cases = [
  ['예시1 순금 1돈 살 때(부가세 없음)', {}, { grams: 3.75, gold: 750000, total: 750000 }],
  ['예시1 순금 1돈 + 부가세 10%', { addVat: true }, { vat: 75000, total: 825000 }],
  ['예시2 18K 1돈 팔 때', { karat: '18', mode: 'sell', addVat: true, labor: 50000 }, { gold: 562500, vat: 0, labor: 0, total: 562500 }],
  ['예시3 순금 1돈 + 공임 5만 + 부가세', { labor: 50000, addVat: true }, { total: 880000 }],
  ['14K 1돈', { karat: '14' }, { gold: 438750, pureGrams: 3.75 * 0.585 }],
  ['돈 시세 750,000원/돈 입력 = 1g 200,000', { price: 750000, priceUnit: 'don' }, { perGram: 200000, gold: 750000 }],
  ['g 무게 10g 14K', { weight: 10, weightUnit: 'g', karat: '14' }, { gold: 1170000, don: 10 / 3.75 }],
  ['매장 18K 시세 직접 입력(순도 재적용 안 함)', { price: 150000, basis: 'karat', karat: '18' }, { ratio: 1, gold: 562500 }],
  ['반 돈 순금', { weight: 0.5 }, { grams: 1.875, gold: 375000 }],
];
for (const [name, over, exp] of cases) {
  const r = calc(Object.assign({}, base, over));
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-9, name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 예시표 15칸 검산
const table = { 1: [200000, 150000, 117000], 1.875: [375000, 281250, 219375], 3.75: [750000, 562500, 438750], 11.25: [2250000, 1687500, 1316250], 10: [2000000, 1500000, 1170000] };
for (const g of Object.keys(table)) ['24', '18', '14'].forEach((k, i) => assert.strictEqual(calc(Object.assign({}, base, { weight: +g, weightUnit: 'g', karat: k })).gold, table[g][i]));
console.log('PASS 예시표 15칸');
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'gc-price': '200000', 'gc-punit': 'g', 'gc-basis': 'pure', 'gc-karat': '18', 'gc-weight': '1', 'gc-wunit': 'don', 'gc-mode': 'buy', 'gc-labor': '0' };
const outP = [];
const el = id => ({ value: vals[id], checked: id === 'gc-vat', style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['gc-out', 'gc-buyopts', 'gc-vat', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(18K 1돈, 1g 20만, 부가세 체크):', outP.join(' | '));
assert.ok(outP.join().includes('살 때 예상 금액: 618,750원'));
// 본문 통계
const body = html.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
console.log('visible chars:', body.length, 'H2:', (html.match(/<h2/g) || []).length, 'H3:', (html.match(/<h3/g) || []).length);
