// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.eitcCalc;
const M = 10000;
const cases = [
  ['단독 1,000만 점감: 165만-(100만)x165/1300', 's', 1000*M, 0, 1e8, 1, { zone: '점감', amount: 1523077 }],
  ['단독 500만 평탄 165만', 's', 500*M, 0, 1e8, 1, { zone: '평탄', amount: 1650000 }],
  ['홑벌이 1,000만 평탄 285만', 'h', 1000*M, 0, 1e8, 1, { zone: '평탄', amount: 2850000 }],
  ['홑벌이 500만 점증 500x285/700', 'h', 500*M, 0, 1e8, 1, { zone: '점증', amount: 2035714 }],
  ['맞벌이 2,000만 점감', 'd', 2000*M, 0, 1e8, 1, { zone: '점감', amount: 2933333 }],
  ['맞벌이 2,000만 재산 2억 -> 50%', 'd', 2000*M, 0, 2e8, 1, { amount: 1466667, halved: true }],
  ['재산 1.7억 정확히 -> 50%', 'd', 1000*M, 0, 1.7e8, 1, { amount: 1650000 }],
  ['재산 2.4억 -> 대상 아님', 'd', 1000*M, 0, 2.4e8, 1, { ok: false, amount: 0 }],
  ['단독 2,200만 -> 기준 미만 아님', 's', 2200*M, 0, 1e8, 1, { ok: false, amount: 0 }],
  ['단독 1,900만 + 이자 300만 -> 총소득 2,200만, 대상 아님', 's', 1900*M, 300*M, 1e8, 1, { ok: false }],
  ['맞벌이 합산 500만 -> 맞벌이 불가', 'd', 500*M, 0, 1e8, 1, { ok: false }],
  ['기한후 95%: 홑벌이 1,000만', 'h', 1000*M, 0, 1e8, 0.95, { amount: 2707500 }],
  ['최소액 점증: 단독 10만 -> 41,250 -> 10만원', 's', 10*M, 0, 1e8, 1, { amount: 100000 }],
  ['최소액 점감: 단독 2,185만 -> 19,038 -> 3만원', 's', 2185*M, 0, 1e8, 1, { amount: 30000 }],
  ['최소액 미달: 단독 2,190만 -> 12,692 -> 0원', 's', 2190*M, 0, 1e8, 1, { ok: false, amount: 0 }],
];
for (const [name, t, pay, o, pr, rate, exp] of cases) {
  const r = calc(t, pay, o, pr, rate);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표 값(공식) 검산
const tbl = { s: [[500,1650000],[1000,1523077],[1500,888462],[2000,253846],[2500,0]], h: [[500,2035714],[1000,2850000],[1500,2691667],[2000,1900000],[2500,1108333],[3000,316667],[4000,0]], d: [[1000,3300000],[1500,3300000],[2000,2933333],[2500,2322222],[3000,1711111],[4000,488889]] };
let n = 0;
for (const t of Object.keys(tbl)) for (const [x, v] of tbl[t]) { assert.strictEqual(calc(t, x*M, 0, 1e8, 1).amount, v, t + x); n++; }
console.log('PASS 본문 표 값 ' + n + '개');
// 시행령 별표 11 산정표와 비교 (구간 하한·중간값)
const B = JSON.parse(fs.readFileSync(path.join(__dirname, 'eitc-table-b11.json'), 'utf8'));
const col = { s: 2, h: 3, d: 4 };
for (const t of ['s', 'h', 'd']) {
  let worst = 0, worstAt = 0, worstFlat = 0, cnt = 0;
  for (const row of B) {
    if (!(row[col[t]] > 0)) continue;
    const x = Math.round((row[0] + row[1]) / 2);
    const r = calc(t, x, 0, 1e8, 1);
    if (!r.zone) continue;
    const d = Math.abs(r.base - row[col[t]]); cnt++; // 최소액 보정 전 공식값 vs 산정표 원값
    if (d > worst) { worst = d; worstAt = x; }
    if (r.zone !== '점증' && d > worstFlat) worstFlat = d;
  }
  console.log('산정표 비교', t, '구간', cnt, '최대차', worst, '(at', worstAt + ')', '평탄·점감 최대차', worstFlat);
  assert.ok(worst < 70000);
}
// UI 기본값 렌더(홑벌이 1,500만, 재산 1억, 정기)
const vals = { 'ec-type': 'h', 'ec-pay': '1500', 'ec-other': '0', 'ec-prop': '10000', 'ec-when': '1' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ec-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('2,691,667원'));
