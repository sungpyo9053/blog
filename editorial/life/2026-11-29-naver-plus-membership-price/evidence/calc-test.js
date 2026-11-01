// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g) || []) if (m.indexOf('<') >= 0) throw new Error('raw < in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.naverPlusCalc;
const cases = [
  ['월간 쇼핑 10만 콘텐츠 없음', 'm', 100000, 0, 0, 0, { fee: 4900, points: 4000, diff: -900, breakEvenShop: 122500 }],
  ['연간 쇼핑 10만 콘텐츠 없음', 'y', 100000, 0, 0, 0, { fee: 3900, points: 4000, diff: 100, breakEvenShop: 97500 }],
  ['월간 본전선 122,500', 'm', 122500, 0, 0, 0, { points: 4900, diff: 0 }],
  ['20만 경계 8,000', 'm', 200000, 0, 0, 0, { points: 8000, diff: 3100 }],
  ['50만 11,000 (공식 16,000 - 기본1% 5,000)', 'm', 500000, 0, 0, 0, { points: 11000 }],
  ['100만 16,000 (공식 26,000 - 10,000)', 'm', 1000000, 0, 0, 0, { points: 16000 }],
  ['300만 36,000 (공식 66,000 - 30,000)', 'm', 3000000, 0, 0, 0, { points: 36000 }],
  ['300만 초과 한도', 'm', 5000000, 0, 0, 0, { points: 36000 }],
  ['넷플릭스 7,000 쇼핑 0', 'm', 0, 7000, 0, 0, { diff: 2100, breakEvenShop: 0 }],
  ['배송비 3,000 x1 월간', 'm', 0, 0, 1, 3000, { diff: -1900, breakEvenShop: 47500 }],
  ['연간 쇼핑 0', 'y', 0, 0, 0, 0, { diff: -3900, breakEvenShop: 97500 }],
];
for (const [name, plan, shop, cval, n, fee, exp] of cases) {
  const r = calc(plan, shop, cval, n, fee);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 표 값 검산 (쇼핑액별 적립, 월간/연간 대비)
const rows = [[50000, 2000, -2900, -1900], [100000, 4000, -900, 100], [150000, 6000, 1100, 2100], [200000, 8000, 3100, 4100], [500000, 11000, 6100, 7100], [1000000, 16000, 11100, 12100]];
for (const [s, p, dm, dy] of rows) {
  assert.strictEqual(calc('m', s, 0, 0, 0).points, p);
  assert.strictEqual(calc('m', s, 0, 0, 0).diff, dm);
  assert.strictEqual(calc('y', s, 0, 0, 0).diff, dy);
}
console.log('PASS 표 값 6행');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'np-plan': 'm', 'np-shop': '100000', 'np-content': '0', 'np-cval': '0', 'np-shipn': '0', 'np-shipfee': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['np-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('900원 손해'));
assert.ok(outP.join().includes('122,500원'));
