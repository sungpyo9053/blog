// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('< inside string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.ipoAllocCalc;
// calc(price, qty, minQty, general, eqPct, count, ratio, mrate, fee)
const cases = [
  ['금융위 예시: 공모가 2만, 증거금 50% 1억, 1000:1 -> 비례 10주', [20000, 10000, 10, 1000000, 0, 200000, 1000, 50, 0], { margin: 100000000, eqBase: 0, prop: 10, sure: 10, refundSure: 99800000 }],
  ['예시1: 10주, 균등 50만/20만건 -> 2주+50%', [20000, 10, 10, 1000000, 50, 200000, 1000, 50, 0], { margin: 100000, eqPool: 500000, eqBase: 2, eqProb: 0.5, prop: 0, sure: 2, refundSure: 60000, refundWin: 40000 }],
  ['예시2: 1만주 -> 균등2+비례10=12주, 환불 99,760,000', [20000, 10000, 10, 1000000, 50, 200000, 1000, 50, 0], { sure: 12, refundSure: 99760000, expected: 12.5 }],
  ['예시3: 균등 50만/80만건 -> 1주 62.5%', [20000, 10, 10, 1000000, 50, 800000, 1000, 50, 0], { eqBase: 0, eqProb: 0.625, sure: 0, refundSure: 100000 }],
  ['균등 25만건 -> 2주 딱, 추첨 없음', [20000, 10, 10, 1000000, 50, 250000, 1000, 50, 0], { eqBase: 2, eqProb: 0 }],
  ['최소 미만 5주 -> 배정 없음', [20000, 5, 10, 1000000, 50, 200000, 1000, 50, 0], { ok: false, sure: 0, margin: 50000 }],
  ['미달: 경쟁률 0.5 -> 넣은 만큼, 추가 납입', [20000, 100, 10, 1000000, 50, 1000, 0.5, 50, 0], { sure: 100, extraPay: 1000000 }],
  ['수수료 2,000원 차감', [20000, 10, 10, 1000000, 50, 200000, 1000, 50, 2000], { refundSure: 58000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.ok(r[k] === exp[k] || Math.abs(r[k] - exp[k]) < 1e-9, name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'ipo-price': '20000', 'ipo-mrate': '50', 'ipo-qty': '10', 'ipo-min': '10', 'ipo-general': '1000000', 'ipo-eq': '50', 'ipo-count': '200000', 'ipo-ratio': '1000', 'ipo-fee': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ipo-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('100,000원'));
assert.ok(outP.join().includes('60,000원'));
console.log('ALL PASS');
// 본문 표(균등 50만 주, 최소 10주, 비례 없음) 검산
for (const [cnt, sure, prob] of [[100000,5,0],[200000,2,0.5],[250000,2,0],[400000,1,0.25],[500000,1,0],[800000,0,0.625],[1000000,0,0.5],[2000000,0,0.25]]) {
  const r = calc(20000, 10, 10, 1000000, 50, cnt, 0, 50, 0);
  assert.strictEqual(r.sure, sure, 'table sure ' + cnt); assert.ok(Math.abs(r.eqProb - prob) < 1e-9, 'table prob ' + cnt);
}
console.log('PASS 균등배정 표 8행');
