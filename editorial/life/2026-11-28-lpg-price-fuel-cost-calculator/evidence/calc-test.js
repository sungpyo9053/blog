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
console.log('JSON-LD FAQ', faq); assert.ok(faq >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const fuel = window.lpgFuel, be = window.lpgBreakeven;
const cases = [
  ['예시 LPG 1250km 9km/L @1177.82', [1250, 9, 1177.82], { liters: 138.89, monthly: 163586, annual: 1963033, perKm: 130.87 }],
  ['예시 휘발유 12km/L @1855.29', [1250, 12, 1855.29], { monthly: 193259, annual: 2319113, perKm: 154.61 }],
  ['예시 경유 14km/L @1841.68', [1250, 14, 1841.68], { monthly: 164436, annual: 1973229 }],
  ['연비 0 -> ok false', [1250, 0, 1177.82], { ok: false, monthly: 0 }],
  ['빈 입력', ['', '', ''], { ok: false, annual: 0 }],
  ['주행 0', [0, 9, 1177.82], { monthly: 0, annual: 0, ok: true }],
];
for (const [name, args, exp] of cases) {
  const r = fuel(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.strictEqual(be(12, 1855.29, 1177.82), 7.62);
assert.strictEqual(be(14, 1841.68, 1177.82), 8.95);
assert.strictEqual(be(12, 0, 1177.82), 0);
console.log('PASS 손익분기 연비 7.62 / 8.95');
// 본문 값 검산
const R = window.lpgRegions; assert.strictEqual(R.length, 17);
assert.strictEqual(Math.round((1855.29 - 1177.82) * 100) / 100, 677.47);
assert.strictEqual((1177.82 / 1855.29 * 100).toFixed(1), '63.5');
assert.strictEqual((1177.82 / 1841.68 * 100).toFixed(1), '64.0');
assert.strictEqual(Math.round(1250 * 12 / 9 * (1238.14 - 1140.53)), 162683);
assert.strictEqual(Math.round(1177.82 * 50), 58891);
assert.strictEqual(Math.round(2812.26 * 20), 56245);
assert.strictEqual(Math.round(3244.40 * 13), 42177);
for (const r of R.slice(1)) { const pct = (r[1] / r[2] * 100).toFixed(1); assert.ok(html.includes('\x3ctd>' + r[0] + '\x3c/td>\x3ctd>' + r[1].toLocaleString('en-US', { minimumFractionDigits: 2 }) + '\x3c/td>'), r[0]); assert.ok(html.includes(pct + '%'), r[0] + pct); }
console.log('PASS 본문 표·차이 값');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'lp-km': '1250', 'lp-price': '1177.82', 'lp-eff': '9', 'lp-gprice': '1855.29', 'lp-geff': '12', 'lp-dprice': '1841.68', 'lp-deff': '14' };
const outP = []; let opts = 0; let onChange;
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = String(v); }, style: {}, addEventListener(t, f) { if (id === 'lp-region') onChange = f; }, set innerHTML(v) { outP.length = 0; }, appendChild(p) { if (id === 'lp-region') opts++; else outP.push(p.textContent); } });
const els = {}; ['lp-out', 'lp-region', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('지역 옵션', opts); assert.strictEqual(opts, 17);
console.log('UI 기본값 출력:\n ' + outP.join('\n '));
assert.ok(outP.join().includes('163,586원')); assert.ok(outP.join().includes('7.62km/L'));
vals['lp-region'] = '1'; onChange();
console.log('서울 선택 후:', vals['lp-price'], vals['lp-gprice'], vals['lp-dprice'], '|', outP[0]);
assert.strictEqual(vals['lp-price'], '1238.14');
