// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('< inside string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.capitalGainsCalc, prog = window.capitalGainsProg;
const E = 100000000; // 1억
const base = { exp: 0, one: false, adjAcq: false };
const cases = [
  ['12억 안분: 15억/5억, 보유10 거주10, 1주택', { sale: 15 * E, acq: 5 * E, hold: 10, res: 10, one: true }, { taxGain: 2 * E, ltcgRate: 80, ltcg: 160000000, base: 37500000, tax: 4365000, local: 436500, table: 2, high: true }],
  ['80% 상한: 보유15 거주12 -> 80%', { sale: 15 * E, acq: 5 * E, hold: 15, res: 12, one: true }, { ltcgRate: 80, tax: 4365000 }],
  ['80% 상한: 보유30 거주30 -> 80%', { sale: 15 * E, acq: 5 * E, hold: 30, res: 30, one: true }, { ltcgRate: 80 }],
  ['12억 정확히 -> 비과세', { sale: 12 * E, acq: 5 * E, hold: 3, res: 0, one: true }, { exempt: true, tax: 0 }],
  ['조정 취득 거주1년 -> 비과세 아님, 표1 10%', { sale: 10 * E, acq: 6 * E, hold: 5, res: 1, one: true, adjAcq: true }, { exempt: false, table: 1, ltcgRate: 10, base: 357500000, tax: 117060000, local: 11706000 }],
  ['조정 취득 거주2년 -> 비과세', { sale: 10 * E, acq: 6 * E, hold: 5, res: 2, one: true, adjAcq: true }, { exempt: true }],
  ['본문 예시: 6억/4억/경비1천만, 5년, 다주택', { sale: 6 * E, acq: 4 * E, exp: 10000000, hold: 5, res: 0 }, { gain: 190000000, ltcgRate: 10, base: 168500000, tax: 44090000, local: 4409000 }],
  ['1년 미만 70%', { sale: 3 * E, acq: 2 * E, hold: 0.5, res: 0 }, { base: 97500000, tax: 68250000 }],
  ['2년 미만 60%(1주택이라도 비과세 아님)', { sale: 3 * E, acq: 2 * E, hold: 1.5, res: 1.5, one: true }, { exempt: false, base: 97500000, tax: 58500000 }],
  ['거주 2.5년 보유5년 1주택 20억: 20%+8%', { sale: 20 * E, acq: 10 * E, hold: 5, res: 2.5, one: true }, { taxGain: 4 * E, ltcgRate: 28, tax: 88550000 }],
  ['표1 상한 30%: 보유20년 다주택', { sale: 3 * E, acq: 1 * E, hold: 20, res: 0 }, { table: 1, ltcgRate: 30 }],
  ['보유 2.9년: 장특 없음', { sale: 3 * E, acq: 2 * E, hold: 2.9, res: 0 }, { table: 0, ltcgRate: 0, ltcg: 0 }],
  ['양도차손 -> 0', { sale: 2 * E, acq: 3 * E, hold: 5, res: 0 }, { tax: 0, gain: -1 * E }],
];
for (const [name, inp, exp] of cases) {
  const r = calc(Object.assign({}, base, inp));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ taxGain: r.taxGain, ltcgRate: r.ltcgRate, base: r.base, tax: r.tax, local: r.local, exempt: r.exempt }));
}
// 기본세율 구간 경계: 누진공제 방식 = 제55조 구간 정액 방식
[[14000000, 840000], [50000000, 6240000], [88000000, 15360000], [150000000, 37060000], [300000000, 94060000], [500000000, 174060000], [1000000000, 384060000], [1100000000, 429060000]]
  .forEach(([b, t]) => assert.strictEqual(prog(b), t, 'prog ' + b));
console.log('PASS 기본세율 경계 8개 (제55조 정액과 일치)');
// UI 기본값(15억/5억/0, 10년/10년, 1주택) 렌더 확인 — 최소 DOM 스텁
const vals = { 'cg-sale': '150000', 'cg-acq': '50000', 'cg-exp': '0', 'cg-hold': '10', 'cg-res': '10' };
const outP = [];
const el = id => ({ value: vals[id], checked: id === 'cg-one', style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['cg-out', 'cg-one', 'cg-adj', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('4,365,000원'));
assert.ok(outP.join().includes('436,500원'));
