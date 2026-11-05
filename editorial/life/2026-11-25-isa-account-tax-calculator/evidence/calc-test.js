// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.isaCalc, limit = window.isaLimit;
const M = 10000;
const cases = [
  ['일반형 수익 500만', 200*M, 500*M, 0, 0, 0.165, { over: 300*M, isaTax: 297000, normalTax: 770000, saving: 473000 }],
  ['서민형 수익 500만', 400*M, 500*M, 0, 0, 0.165, { over: 100*M, isaTax: 99000, normalTax: 770000, saving: 671000 }],
  ['일반형 수익 200만 -> 0원', 200*M, 200*M, 0, 0, 0.165, { isaTax: 0, normalTax: 308000 }],
  ['서민형 300만 -> 0원', 400*M, 300*M, 0, 0, 0.165, { isaTax: 0, normalTax: 462000 }],
  ['일반형 1000만', 200*M, 1000*M, 0, 0, 0.165, { isaTax: 792000, normalTax: 1540000 }],
  ['서민형 1000만', 400*M, 1000*M, 0, 0, 0.165, { isaTax: 594000 }],
  ['일반형 2000만', 200*M, 2000*M, 0, 0, 0.165, { isaTax: 1782000, normalTax: 3080000 }],
  ['서민형 2000만', 400*M, 2000*M, 0, 0, 0.165, { isaTax: 1584000 }],
  ['손실 차감: 수익 500만 손실 200만 일반형', 200*M, 500*M, 200*M, 0, 0.165, { net: 300*M, over: 100*M, isaTax: 99000, normalTax: 770000 }],
  ['손실이 수익보다 큼', 200*M, 100*M, 300*M, 0, 0.165, { net: 0, isaTax: 0 }],
  ['연금 전환 3000만 16.5%', 200*M, 500*M, 0, 3000*M, 0.165, { extraBase: 300*M, extraCredit: 495000 }],
  ['연금 전환 3000만 13.2%', 200*M, 500*M, 0, 3000*M, 0.132, { extraCredit: 396000 }],
  ['연금 전환 2000만', 200*M, 500*M, 0, 2000*M, 0.165, { extraBase: 200*M, extraCredit: 330000 }],
  ['연금 전환 5000만 -> 상한 300만', 200*M, 500*M, 0, 5000*M, 0.132, { extraBase: 300*M, extraCredit: 396000 }],
];
for (const [name, lim, p, l, mv, rt, exp] of cases) {
  const r = calc(lim, p, l, mv, rt);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 서민형-일반형 차이 상한 198,000원
for (const p of [400, 500, 1000, 3000]) assert.strictEqual(calc(200*M, p*M, 0, 0, 0.165).isaTax - calc(400*M, p*M, 0, 0, 0.165).isaTax, 198000);
console.log('PASS 서민형-일반형 차이 198,000원(수익 400만 이상)');
const lims = [[0, 0, 2000*M], [1, 500*M, 3500*M], [1, 0, 4000*M], [1, 2000*M, 2000*M], [4, 0, 10000*M], [4, 6000*M, 4000*M], [7, 0, 10000*M], [3, 7000*M, 1000*M], [4, 9500*M, 500*M], [2, 7000*M, 0], [0, 2500*M, 0]];
for (const [y, paid, exp] of lims) { assert.strictEqual(limit(y, paid), exp, 'limit ' + y + ',' + paid); }
console.log('PASS 납입한도 ' + lims.length + '건');
// UI 기본값 렌더 (일반형, 수익 500만)
const vals = { 'isa-type': '200', 'isa-profit': '5000000', 'isa-loss': '0', 'isa-move': '', 'isa-rate': '0.165', 'isa-years': '0', 'isa-paid': '0' };
const outs = { 'isa-out': [], 'isa-out2': [] };
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { if (outs[id]) outs[id].length = 0; }, appendChild(p) { outs[id].push(p.textContent); } });
const els = {}; ['isa-out', 'isa-out2', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outs['isa-out'].join(' | '), '||', outs['isa-out2'].join(' | '));
assert.ok(outs['isa-out'].join().includes('297,000원'));
assert.ok(outs['isa-out'].join().includes('473,000원'));
assert.ok(outs['isa-out2'].join().includes('20,000,000원'));
console.log('ALL PASS');
