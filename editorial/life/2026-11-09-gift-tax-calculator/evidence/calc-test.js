// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if ((src.match(/'(?:[^'\\\n]|\\.)*'/g) || []).some(s => s.includes('<'))) throw new Error('< inside string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.giftTaxCalc;
const base = { prior: 0, marriage: false, skip: false, filed: true };
const M = 10000;
const cases = [
  ['성인 자녀 5천만 -> 0', { rel: 'parent', amount: 5000 * M }, { base: 0, pay: 0 }],
  ['성인 자녀 1억 -> 485만', { rel: 'parent', amount: 10000 * M }, { base: 5000 * M, tax: 500 * M, filing: 15 * M, pay: 485 * M }],
  ['미성년 5천만 -> 291만', { rel: 'parentMinor', amount: 5000 * M }, { base: 3000 * M, tax: 300 * M, pay: 291 * M }],
  ['혼인 3억 -> 1,940만', { rel: 'parent', amount: 30000 * M, marriage: true }, { mded: 10000 * M, base: 15000 * M, tax: 2000 * M, pay: 1940 * M }],
  ['혼인 1.5억 -> 0', { rel: 'parent', amount: 15000 * M, marriage: true }, { base: 0, pay: 0 }],
  ['배우자 6억 -> 0', { rel: 'spouse', amount: 60000 * M }, { base: 0, pay: 0 }],
  ['배우자 7억 -> 970만', { rel: 'spouse', amount: 70000 * M }, { base: 10000 * M, tax: 1000 * M, pay: 970 * M }],
  ['삼촌 3천만 -> 194만', { rel: 'relative', amount: 3000 * M }, { base: 2000 * M, pay: 194 * M }],
  ['타인 1천만 -> 97만', { rel: 'other', amount: 1000 * M }, { base: 1000 * M, pay: 97 * M }],
  ['자녀->부모 1억 -> 485만', { rel: 'child', amount: 10000 * M }, { pay: 485 * M }],
  ['손자 1억 -> 할증 150만, 630.5만', { rel: 'parent', amount: 10000 * M, skip: true }, { tax: 500 * M, sur: 150 * M, filing: 195000, pay: 6305000 }],
  ['미성년 손자 21억 -> 40% 할증', { rel: 'parentMinor', amount: 210000 * M, skip: true }, { surRate: 0.4 }],
  ['미성년 손자 20억 -> 30% 할증', { rel: 'parentMinor', amount: 200000 * M, skip: true }, { surRate: 0.3 }],
  ['10년 합산: 1억+1억 -> 1,455만', { rel: 'parent', amount: 10000 * M, prior: 10000 * M }, { aggregated: true, value: 20000 * M, base: 15000 * M, tax: 2000 * M, credit: 500 * M, filing: 45 * M, pay: 1455 * M }],
  ['합산: 과거 5천만(공제 다 씀)+1억 -> 970만', { rel: 'parent', amount: 10000 * M, prior: 5000 * M }, { base: 10000 * M, credit: 0, pay: 970 * M }],
  ['합산 제외: 과거 900만 -> 남은 공제 4,100만', { rel: 'parent', amount: 10000 * M, prior: 900 * M }, { aggregated: false, ded: 4100 * M, base: 5900 * M }],
  ['미신고 -> 3% 없음', { rel: 'parent', amount: 10000 * M, filed: false }, { filing: 0, pay: 500 * M }],
  ['과세최저한: 과표 40만 -> 0', { rel: 'other', amount: 400000 }, { tax: 0, pay: 0 }],
  ['30억 초과: 과표 31억 -> 10.9억', { rel: 'other', amount: 310000 * M }, { tax: 109000 * M }],
  ['혼인 공제는 배우자 증여에 미적용', { rel: 'spouse', amount: 70000 * M, marriage: true }, { mded: 0 }],
];
for (const [name, inp, exp] of cases) {
  const r = calc(Object.assign({}, base, inp));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 세율표: 조문식(누적)과 누진공제식 대조
const law = b => b <= 1e8 ? b * 0.1 : b <= 5e8 ? 1e7 + (b - 1e8) * 0.2 : b <= 1e9 ? 9e7 + (b - 5e8) * 0.3 : b <= 3e9 ? 2.4e8 + (b - 1e9) * 0.4 : 1.04e9 + (b - 3e9) * 0.5;
for (const b of [5e5, 1e8, 1e8 + 1e6, 3e8, 5e8, 7e8, 1e9, 2e9, 3e9, 5e9]) {
  const r = calc({ rel: 'other', amount: b, prior: 0, filed: false });
  assert.strictEqual(r.tax, Math.floor(law(b)), 'rate ' + b);
}
console.log('PASS 세율 경계 10건 조문식 일치');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'gt-rel': 'parent', 'gt-amount': '100000000', 'gt-prior': '0' };
const checks = { 'gt-marriage': false, 'gt-skip': false, 'gt-filed': true };
const outP = [];
const el = id => ({ value: vals[id], checked: checks[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['gt-out', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('납부할 증여세: 4,850,000원'));
