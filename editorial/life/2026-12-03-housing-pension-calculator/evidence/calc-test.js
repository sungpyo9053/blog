// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/<[A-Za-z\/!]/.test(src)) throw new Error('tag-like < found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.housingPensionCalc;
const cases = [
  ['HF 예시: 70세 3억 일반주택 -> 월 923천원', 'house', 70, NaN, 30000, false, { status: 'ok', monthly: 923000, exact: true, fee: 3000000 }],
  ['백문백답: 65세 3억 -> 약 75만원(758천원)', 'house', 65, NaN, 30000, false, { monthly: 758000 }],
  ['백문백답: 70세 5억 -> 약 153만원(1,539천원)', 'house', 70, NaN, 50000, false, { monthly: 1539000 }],
  ['HF 예시: 오피스텔 70세 3억 -> 746천원', 'officetel', 70, NaN, 30000, false, { monthly: 746000 }],
  ['일람표: 55세 1억 156천원, 인출한도 1,500만원', 'house', 55, NaN, 10000, false, { monthly: 156000, withdraw: 15000000 }],
  ['연소자 기준: 본인 60 배우자 58 -> 58세 행', 'house', 60, 58, 30000, false, { base: 58, monthly: 560000 }],
  ['보간: 70세 3.5억 -> (923+1231)/2=1,077천원', 'house', 70, NaN, 35000, false, { exact: false, lo: 3, hi: 4, monthly: 1077000 }],
  ['시세 12억 초과: 80세 15억 -> 12억 칸 4,060천원', 'house', 80, NaN, 150000, false, { capped: true, monthly: 4060000, fee: null }],
  ['1억 미만: 65세 5천만원 -> 1억 칸 표시+경고', 'house', 65, NaN, 5000, false, { below: true, monthly: 252000 }],
  ['우대형: 65세 1억 -> 297천원', 'house', 65, NaN, 10000, true, { pref: 297000, monthly: 252000 }],
  ['우대형: 65세 2억 -> 568천원', 'house', 65, NaN, 20000, true, { pref: 568000 }],
  ['우대형: 1.5억은 일람표 칸 없음', 'house', 65, NaN, 15000, true, { pref: null, prefNote: 'grid' }],
  ['우대형: 3억은 대상 아님', 'house', 65, NaN, 30000, true, { prefNote: 'over' }],
  ['가입 불가: 부부 모두 55세 미만', 'house', 54, 50, 30000, false, { status: 'age' }],
  ['가입 가능, 연소자 52세 -> 표 없음', 'house', 65, 52, 30000, false, { status: 'young', base: 52 }],
  ['90세 초과 -> 표 없음', 'house', 92, NaN, 30000, false, { status: 'old' }],
  ['90세 7억 상한 6,072천원', 'house', 90, NaN, 70000, false, { monthly: 6072000 }],
];
for (const [name, ty, a1, a2, pr, pf, exp] of cases) {
  const r = calc(ty, a1, a2, pr, pf);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표(일반주택 55~90세 8행 x 7열)가 계산기 데이터와 같은지
const tb = html.match(/<h2 id="table">[\s\S]*?<tbody>([\s\S]*?)<\/tbody>/)[1];
let n = 0;
for (const tr of tb.match(/<tr>[\s\S]*?<\/tr>/g)) {
  const c = tr.match(/<td>([^<]*)<\/td>/g).map(x => x.replace(/<\/?td>/g, '').replace(/[,세]/g, ''));
  const age = +c[0];
  [1, 2, 3, 5, 7, 9, 12].forEach((e, i) => { assert.strictEqual(calc('house', age, NaN, e * 10000, false).monthly, +c[i + 1] * 1000, age + '세 ' + e + '억'); n++; });
}
console.log('PASS 본문 표 ' + n + '칸 = 계산기 데이터');
// UI 기본값(70세, 3억, 일반주택) 렌더 확인 — 최소 DOM 스텁
const vals = { 'hp-a1': '70', 'hp-a2': '', 'hp-price': '30000', 'hp-type': 'house' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['hp-out', 'hp-p3', 'hp-p5', 'hp-p9', 'hp-pref', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('923,000원'));
