// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.rentCreditCalc;
const M = 10000;
const cases = [
  ['총급여 4,000만 월 60만x12 -> 17%', 4000*M, 720*M, -1, -1, { eligible: true, rate: 0.17, base: 720*M, credit: 1224000 }],
  ['총급여 6,000만 월 100만x12 -> 한도 1,000만 x15%', 6000*M, 1200*M, -1, -1, { rate: 0.15, base: 1000*M, credit: 1500000, overLimit: true }],
  ['국세청 최대 170만: 5,500만 이하 1,000만', 5500*M, 1000*M, -1, -1, { rate: 0.17, credit: 1700000 }],
  ['경계: 총급여 5,500만+1원 -> 15%', 5500*M+1, 1000*M, -1, -1, { rate: 0.15, credit: 1500000 }],
  ['경계: 총급여 8,000만 -> 15% 대상', 8000*M, 600*M, -1, -1, { eligible: true, rate: 0.15, credit: 900000 }],
  ['경계: 총급여 8,000만+1원 -> 제외', 8000*M+1, 600*M, -1, -1, { eligible: false, credit: 0 }],
  ['종합소득금액 4,600만(총급여 5,000만) -> 15%', 5000*M, 600*M, 4600*M, -1, { rate: 0.15, credit: 900000 }],
  ['종합소득금액 4,500만 -> 17% 유지', 5000*M, 600*M, 4500*M, -1, { rate: 0.17, credit: 1020000 }],
  ['종합소득금액 7,000만+1원 -> 제외', 6000*M, 600*M, 7000*M+1, -1, { eligible: false, credit: 0 }],
  ['결정세액 50만 상한', 3000*M, 600*M, -1, 50*M, { credit: 500000, capped: true }],
];
for (const [name, g, r, c, t, exp] of cases) {
  const o = calc(g, r, c, t);
  for (const k of Object.keys(exp)) assert.ok(Math.abs(o[k] - exp[k]) < 1e-9 || o[k] === exp[k], name + ' ' + k + '=' + o[k]);
  console.log('PASS', name, JSON.stringify(o));
}
// UI 기본값(총급여 4,000만, 월세 720만) 렌더 확인 — 최소 DOM 스텁
const vals = { 'rt-gross': '4000', 'rt-rent': '720', 'rt-comp': '', 'rt-tax': '' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['rt-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('1,224,000원'));
