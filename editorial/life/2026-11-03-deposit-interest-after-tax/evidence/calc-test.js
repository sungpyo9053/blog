// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.depositInterestCalc;
const cases = [
  ['예금 1천만 3% 12개월 단리 일반', ['dep', 1e7, 3, 12, false, 'normal'], { pre: 300000, it: 42000, lt: 4200, tax: 46200, post: 253800, total: 10253800 }],
  ['예금 1천만 3% 12개월 월복리 일반', ['dep', 1e7, 3, 12, true, 'normal'], { pre: 304159, it: 42580, lt: 4250, post: 257329 }],
  ['예금 1천만 3% 24개월 단리/월복리', ['dep', 1e7, 3, 24, false, 'normal'], { pre: 600000 }],
  ['예금 1천만 3% 24개월 월복리', ['dep', 1e7, 3, 24, true, 'normal'], { pre: 617570 }],
  ['예금 1억 3% 12개월 단리 (FAQ)', ['dep', 1e8, 3, 12, false, 'normal'], { pre: 3000000, it: 420000, lt: 42000, post: 2538000 }],
  ['적금 월10만 3% 12개월 단리 = 10만x0.0025x78', ['sav', 1e5, 3, 12, false, 'normal'], { principal: 1200000, pre: 19500, it: 2730, lt: 270, post: 16500, total: 1216500 }],
  ['적금 월10만 3% 12개월 월복리', ['sav', 1e5, 3, 12, true, 'normal'], { pre: 19679, post: 16659 }],
  ['세금우대 9.5%: 9% + 농특세 (14-9)x10%', ['dep', 1e7, 3, 12, false, 'pref'], { it: 27000, lt: 0, rt: 1500, tax: 28500, post: 271500 }],
  ['상호금융 2026 가입 5% + 농특세 0.9%', ['dep', 1e7, 3, 12, false, 'coop5'], { it: 15000, rt: 2700, tax: 17700 }],
  ['상호금융 비과세분 농특세 1.4%', ['dep', 1e7, 3, 12, false, 'coop0'], { it: 0, rt: 4200, tax: 4200, post: 295800 }],
  ['비과세종합저축 0%', ['dep', 1e7, 3, 12, false, 'none'], { tax: 0, post: 300000 }],
  ['금리 0%', ['sav', 1e5, 0, 12, true, 'normal'], { pre: 0, tax: 0, total: 1200000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 적금 단리 공식 n(n+1)/2 를 회차별 합과 대조 (n=1..36)
for (let n = 1; n <= 36; n++) {
  let s = 0; for (let k = 1; k <= n; k++) s += 100000 * 0.05 / 12 * k;
  assert.strictEqual(calc('sav', 100000, 5, n, false, 'normal').pre, Math.floor(s + 1e-6), 'n=' + n);
}
console.log('PASS 적금 단리 n(n+1)/2 = 회차별 합 (n=1..36, 연 5%)');
// 적금 실효: 연 5% 12개월 = 5 x 13/24 = 2.7083%
assert.strictEqual(Math.round(calc('sav', 100000, 5, 12, false, 'normal').pre / 1200000 * 10000) / 100, 2.71);
console.log('PASS 적금 연 5% 12개월 실효 2.71%');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'di-kind': 'dep', 'di-amt': '10000000', 'di-rate': '3', 'di-months': '12', 'di-comp': '0', 'di-tax': 'normal' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, textContent: '', addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['di-out', 'di-amt-label', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('253,800원'));
