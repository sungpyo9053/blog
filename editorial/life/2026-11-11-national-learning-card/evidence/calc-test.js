// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산 (운영규정 제46조·별표 4)
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.learningCardCalc;
const cases = [
  ['일반 과정 50~60%, 일반 훈련생, 100만', [1000000, 'gen', 2, 'gen', 3000000], { rate: 0.65, support: 650000, self: 350000, balAfter: 2350000 }],
  ['일반 과정 70%+, 일반 훈련생', [1000000, 'gen', 0, 'gen', 3000000], { support: 850000, self: 150000 }],
  ['일반 과정 40% 미만, 일반 훈련생 (자부담 55%)', [1000000, 'gen', 4, 'gen', 3000000], { support: 450000, self: 550000 }],
  ['근로장려금 수급자 70%+ 92.5%', [1000000, 'gen', 0, 'eitc', 3000000], { support: 925000, self: 75000 }],
  ['국취II 청년 50~60% 70%', [1000000, 'gen', 2, 'kua2', 3000000], { support: 700000 }],
  ['특정계층 40%이상 100%', [1000000, 'gen', 3, 'spec', 3000000], { support: 1000000, self: 0 }],
  ['특정계층 40% 미만 80%', [1000000, 'gen', 4, 'spec', 3000000], { support: 800000, self: 200000 }],
  ['잔액 부족: 지원 65만 > 잔액 50만', [1000000, 'gen', 2, 'gen', 500000], { support: 500000, self: 500000, overBal: 150000, balAfter: 0 }],
  ['돌봄 일반 10%', [1000000, 'care', 0, 'gen', 3000000], { support: 100000, self: 900000 }],
  ['돌봄 특정계층 90%', [1000000, 'care', 0, 'spec', 3000000], { support: 900000 }],
  ['외국어 50%', [400000, 'lang', 0, 'eitc', 3000000], { support: 200000, self: 200000 }],
  ['KDT 800만 일반: 자부담 상한 60만, 300만 차감', [8000000, 'kdt', 0, 'gen', 3000000], { support: 7400000, self: 600000, used: 3000000, balAfter: 0 }],
  ['KDT 400만 일반: 자부담 40만(10%)', [4000000, 'kdt', 0, 'gen', 3000000], { support: 3600000, self: 400000, used: 3000000 }],
  ['국가기간 150만: 지원 135만 < 200만 → 135만 차감', [1500000, 'nat', 0, 'gen', 3000000], { support: 1350000, used: 1350000, balAfter: 1650000 }],
  ['KDT 단기 국취I 전액, 150만 차감', [2000000, 'kdts', 0, 'spec', 3000000], { support: 2000000, self: 0, used: 1500000, balAfter: 1500000 }],
  ['산업구조 단기 100만 차감, 잔액 50만 → 0', [1500000, 'inds', 0, 'gen', 500000], { used: 1000000, balAfter: 0, support: 1350000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-9, name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 (100만, 일반, 50~60%, 일반 훈련생, 잔액 300만)
const vals = { 'lc-fee': '1000000', 'lc-course': 'gen', 'lc-band': '2', 'lc-who': 'gen', 'lc-bal': '3000000' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['lc-out', 'lc-band-row', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('650,000원') && outP.join().includes('2,350,000원'));
