// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld);
assert.strictEqual(faq.mainEntity.length, (html.match(/<h2 id="faq">[\s\S]*?<script type/)[0].match(/<h3>/g) || []).length, 'FAQ h3 count = JSON-LD count');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.corpTaxCalc;
// [이름, 과세표준, 시작연도, 소규모, 월수, 기대값]
const cases = [
  ['2026 과표 1억 10%', 1e8, 2026, false, 12, { tax: 10000000, local: 1000000, total: 11000000 }],
  ['2026 경계 2억 = 법조문 2천만원', 2e8, 2026, false, 12, { tax: 20000000, local: 2000000, topRate: 10 }],
  ['2026 2억+1원 20%', 2e8 + 1, 2026, false, 12, { tax: 20000000, topRate: 20 }],
  ['2026 3억', 3e8, 2026, false, 12, { tax: 40000000, local: 4000000, total: 44000000, eff: 13.33, effTotal: 14.67 }],
  ['2026 5억 (누진공제 5억x20%-2천만)', 5e8, 2026, false, 12, { tax: 80000000 }],
  ['2026 경계 200억 = 39억8천만원', 2e10, 2026, false, 12, { tax: 3980000000, local: 398000000 }],
  ['2026 경계 3천억 = 655억8천만원', 3e11, 2026, false, 12, { tax: 65580000000, local: 6558000000 }],
  ['2026 4천억 (25%, 누진공제 94.2억)', 4e11, 2026, false, 12, { tax: 4e11 * 0.25 - 9420000000 }],
  ['2025 과표 1억 9%', 1e8, 2025, false, 12, { tax: 9000000, local: 900000 }],
  ['2025 경계 200억 = 37억8천만원', 2e10, 2025, false, 12, { tax: 3780000000, local: 378000000 }],
  ['2025 경계 3천억 = 625억8천만원', 3e11, 2025, false, 12, { tax: 62580000000, local: 6258000000 }],
  ['2026 소규모 3억 20%', 3e8, 2026, true, 12, { tax: 60000000, local: 6000000 }],
  ['2026 소규모 경계 200억 = 40억', 2e10, 2026, true, 12, { tax: 4000000000, local: 400000000 }],
  ['2026 소규모 경계 3천억 = 656억', 3e11, 2026, true, 12, { tax: 65600000000, local: 6560000000 }],
  ['2025 소규모 200억 = 38억', 2e10, 2025, true, 12, { tax: 3800000000, local: 380000000 }],
  ['2025 소규모 3천억 = 626억', 3e11, 2025, true, 12, { tax: 62600000000, local: 6260000000 }],
  ['6개월 과표 2억 -> 연환산 4억 -> 3천만', 2e8, 2026, false, 6, { annualBase: 4e8, tax: 30000000, local: 3000000 }],
  ['0원', 0, 2026, false, 12, { tax: 0, local: 0 }],
  ['연도 미입력 = 2026 표', 1e8, NaN, false, 12, { key: 'g2026', tax: 10000000 }],
  ['2024 개시 미지원', 1e8, 2024, false, 12, { ok: false }],
];
for (const [name, base, y, s, m, exp] of cases) {
  const r = calc(base, y, s, m);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ tax: r.tax, local: r.local, total: r.total, key: r.key }));
}
// 법인지방소득세 = 법인세의 정확히 1/10 (표준세율, 원 미만 절사 오차 1원)
for (let b = 1e6; b <= 5e11; b = Math.floor(b * 1.37) + 12345) for (const k of [[2026, false], [2025, false], [2026, true], [2025, true]]) {
  const r = calc(b, k[0], k[1], 12);
  assert.ok(Math.abs(r.local - r.tax / 10) <= 1, 'local 1/10 ' + b);
  assert.ok(Math.abs(r.rows.reduce((a, w) => a + w.tax, 0) - r.tax) <= r.rows.length, 'rows sum ' + b);
}
// 2026 일반 = 2025 일반 + 과세표준의 1%
for (let b = 1e6; b <= 5e11; b = Math.floor(b * 1.29) + 777) assert.ok(Math.abs(calc(b, 2026, false, 12).tax - calc(b, 2025, false, 12).tax - b / 100) <= 1, '1%p ' + b);
console.log('PASS 지방소득세 1/10, 구간 합계 = 산출세액, 2026-2025 = 과세표준 1%');
// 본문 예시표 숫자 재현
const tbl = [[5e7, 5000000, 5500000, 4950000], [1e8, 10000000, 11000000, 9900000], [2e8, 20000000, 22000000, 19800000], [3e8, 40000000, 44000000, 40700000], [5e8, 80000000, 88000000, 82500000], [1e9, 180000000, 198000000, 187000000], [5e9, 980000000, 1078000000, 1023000000], [2e10, 3980000000, 4378000000, 4158000000]];
for (const [b, t26, tot26, tot25] of tbl) { const a = calc(b, 2026, false, 12), c = calc(b, 2025, false, 12); assert.strictEqual(a.tax, t26); assert.strictEqual(a.total, tot26); assert.strictEqual(c.total, tot25); }
console.log('PASS 본문 예시표 8행');
// UI 기본값 렌더 (과표 3억, 2026-01-01, 12개월, 일반)
const outP = [];
function el(tag) { return { tag, style: {}, children: [], appendChild(c) { this.children.push(c); }, set textContent(v) { this._t = v; }, get textContent() { return this._t || this.children.map(c => c.textContent).join(' / '); } }; }
const vals = { 'cit-base': '300000000', 'cit-start': '2026-01-01', 'cit-months': '12', 'cit-type': 'g' };
const els = { 'cit-out': { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } } };
for (const k of Object.keys(vals)) els[k] = { value: vals[k], addEventListener() {} };
global.document = { getElementById: id => els[id], createElement: el, querySelectorAll: () => [{ addEventListener() {}, getAttribute: () => '200000000' }] };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('법인세 산출세액: 40,000,000원'));
assert.ok(outP.join().includes('법인지방소득세(표준세율): 4,000,000원'));
// 2025-07-01 시작 6월 결산법인
els['cit-start'].value = '2025-07-01'; eval(src);
console.log('2025-07-01 시작:', outP[0], '|', outP[2]);
assert.ok(outP.join().includes('37,000,000원'));
