// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^'\n]*'/g) || []) if (s.indexOf('<') >= 0) throw new Error('< in string literal: ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { buy, ded } = window.onnuriCalc;
// 구매 할인
const b1 = buy(1000000, 7, 1000000); assert.deepStrictEqual([b1.pay, b1.disc, b1.over], [930000, 70000, false]); console.log('PASS 디지털 100만 7% -> 930,000 / 70,000');
const b2 = buy(500000, 5, 500000); assert.deepStrictEqual([b2.pay, b2.disc], [475000, 25000]); console.log('PASS 지류 50만 5% -> 475,000 / 25,000');
const b3 = buy(1200000, 10, 1000000); assert.deepStrictEqual([b3.pay, b3.disc, b3.over], [1080000, 120000, true]); console.log('PASS 120만 10% 한도 100만 초과 경고');
// 소득공제 (조특법 제126조의2)
const cases = [
  ['총급여 4천, 신용 1,500만, 전통 300만', [40e6, 3e6, 0, 0, 15e6, 0], { min: 10e6, before: 1950000, base: 1950000, extra: 0, ded: 1950000 }],
  ['총급여 5천, 신용 1천만, 체크 500만, 전통 500만 (최저사용금액이 체크까지)', [50e6, 5e6, 0, 5e6, 10e6, 0], { before: 2750000, ded: 2750000 }],
  ['총급여 6천, 신용 3천만, 전통 1천만 -> 기본 300 + 추가 300', [60e6, 10e6, 0, 0, 30e6, 0], { before: 6250000, base: 3e6, extra: 3e6, ded: 6e6 }],
  ['총급여 8천, 신용 4천만, 전통 600만 -> 기본 250 + 추가 200', [80e6, 6e6, 0, 0, 40e6, 0], { before: 5400000, base: 2.5e6, extra: 2e6, ded: 4.5e6 }],
  ['총사용액이 25% 이하 -> 0', [40e6, 3e6, 0, 0, 5e6, 0], { ded: 0 }],
  ['최저사용금액이 전통시장까지 -> 초과분만 40%', [40e6, 5e6, 0, 2e6, 5e6, 0], { before: 800000, ded: 800000 }],
  ['자녀 2명, 7천 이하 한도 400만', [60e6, 2e6, 0, 0, 50e6, 2], { limit: 4e6, before: 6050000, base: 4e6, extra: 800000, ded: 4.8e6 }],
  ['자녀 1명, 7천 초과 한도 275만', [90e6, 0, 0, 0, 60e6, 1], { limit: 2.75e6, before: 5625000, base: 2.75e6, extra: 0, ded: 2.75e6 }],
  ['대중교통 포함 추가 풀', [60e6, 3e6, 1e6, 0, 40e6, 0], { before: 5350000, pool: 1.6e6, ded: 4.6e6 }],
];
for (const [name, args, exp] of cases) {
  const r = ded(...args);
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-6, name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'on-type': 'd', 'on-amt': '1000000', 'on-rate': '7', 'on-g': '40000000', 'on-kids': '0', 'on-m': '3000000', 'on-t': '0', 'on-dc': '0', 'on-c': '15000000' };
const outs = { 'on-out1': [], 'on-out2': [] };
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
Object.keys(outs).forEach(id => els[id] = { set innerHTML(v) { outs[id].length = 0; }, appendChild(p) { outs[id].push(p.textContent); } });
els['onnuri-calc'] = {};
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 구매:', outs['on-out1'].join(' | '));
console.log('UI 공제:', outs['on-out2'].join(' | '));
assert.ok(outs['on-out1'].join().includes('930,000원'));
assert.ok(outs['on-out2'].join().includes('1,950,000원'));
console.log('PASS UI 기본값');
