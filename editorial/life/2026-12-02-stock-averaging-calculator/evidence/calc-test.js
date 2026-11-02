// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const C = window.stockAvgCalc;
const near = (a, b, e = 1e-6) => Math.abs(a - b) < e;
// 1. 평단가
let r = C.avg(100, 10000, [[7000, 100]]);
assert.ok(r.qty === 200 && r.cost === 1700000 && r.avg === 8500); console.log('PASS 100주@10,000 + 100주@7,000 -> 8,500', JSON.stringify(r));
[[50, 9000, 1350000], [100, 8500, 1700000], [200, 8000, 2400000], [400, 7600, 3800000]].forEach(([q, a, c]) => {
  const x = C.avg(100, 10000, [[7000, q]]); assert.ok(x.avg === a && x.cost === c); });
console.log('PASS 예시 표 4행');
r = C.avg(100, 10000, [[8000, 50], [7000, 100], [6000, 150]]);
assert.ok(r.qty === 400 && r.cost === 3000000 && r.avg === 7500); console.log('PASS 3회 분할 -> 7,500');
r = C.avg(100, 10000, [[7000, 300]]); assert.strictEqual(r.avg, 7750); console.log('PASS 가중평균 7,750 (단순평균 8,500 아님)');
r = C.avg(100, 10000, [[0, 50], [7000, 0], [7000, 100]]); assert.strictEqual(r.avg, 8500); console.log('PASS 빈 회차 건너뜀');
// 2. 손실 금액 불변
for (const n of [1, 100, 1234]) { const x = C.avg(100, 10000, [[7000, n]]); assert.ok(near(x.qty * (7000 - x.avg), -300000)); }
console.log('PASS 현재가 매수 시 평가손익 -300,000 불변');
assert.ok(near(100 * (6000 - 10000), -400000) && near(200 * (6000 - 8500), -500000)); console.log('PASS 6,000원 하락 시 40만 vs 50만');
// 3. 역계산
[[9000, 50], [8500, 100], [8000, 200], [7500, 500], [7100, 2900]].forEach(([t, n]) => {
  const x = C.need(100, 10000, t, 7000); assert.ok(x.ok && x.qty === n && x.cost === n * 7000 && x.newAvg <= t, t + ' ' + JSON.stringify(x)); });
console.log('PASS 역계산 표 5행');
let x = C.need(100, 10000, 8333, 7000); assert.ok(x.qty === 126 && x.newAvg <= 8333); console.log('PASS 올림 처리', JSON.stringify(x));
assert.ok(!C.need(100, 10000, 7000, 7000).ok && !C.need(100, 10000, 11000, 7000).ok); console.log('PASS 불가능한 목표 거부');
// 4. 매도 손익
let s = C.sell(8500, 200, 9000, 0.015, 0.05, 0.15);
assert.ok(s.sellAmt === 1800000 && s.st === 900 && s.nt === 2700 && s.tax === 3600 && s.sellFee === 270 && s.buyFee === 255 && s.profit === 95875, JSON.stringify(s));
assert.strictEqual(Math.ceil(s.be), 8520); console.log('PASS 매도 예시 95,875 / 손익분기', s.be.toFixed(2));
const be = C.sell(8500, 200, Math.ceil(s.be), 0.015, 0.05, 0.15); assert.ok(be.profit >= 0); console.log('PASS 손익분기가 매도 시 손익', be.profit);
assert.ok(C.sell(8500, 200, 8500, 0.015, 0.05, 0.15).profit < 0); console.log('PASS 평단가 매도는 손실');
for (const [k, tot] of [['kospi', 20000], ['kosdaq', 20000], ['konex', 10000]]) { const m = C.MKT[k]; assert.strictEqual(C.sell(10000, 1000, 10000, 0, m[0], m[1]).tax, tot); }
console.log('PASS 1,000만원 매도 세금 표 3행');
// 5. UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'sa-q0': '100', 'sa-p0': '10000', 'sa-now': '7000', 'sa-bp1': '7000', 'sa-bq1': '100', 'sa-target': '8000', 'sa-rp': '7000', 'sa-sp': '9000', 'sa-sq': '', 'sa-mkt': 'kospi', 'sa-fee': '0.015' };
for (let i = 2; i <= 5; i++) { vals['sa-bp' + i] = ''; vals['sa-bq' + i] = ''; }
const outs = {};
const mk = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outs[id] = []; }, appendChild(p) { outs[id].push(p.textContent); } });
const els = {}; ['sa-out1', 'sa-out2', 'sa-out3', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
for (const k of ['sa-out1', 'sa-out2', 'sa-out3']) console.log('UI', k + ':', outs[k].join(' | '));
assert.ok(outs['sa-out1'].join().includes('8,500원') && outs['sa-out1'].join().includes('-300,000원'));
assert.ok(outs['sa-out2'].join().includes('200주'));
assert.ok(outs['sa-out3'].join().includes('+95,875원') && outs['sa-out3'].join().includes('8,520원'));
console.log('ALL PASS');
