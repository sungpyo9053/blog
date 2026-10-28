// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.promissoryCalc, text = window.promissoryText, hangul = window.promissoryHangul;
const cases = [
  ['1천만원 연5% 12개월', 10000000, 5, 12, false, { capped: false, interest: 500000, monthly: 41667, total: 10500000 }],
  ['연 24% -> 20%로 제한', 10000000, 24, 12, false, { capped: true, validRate: 20, interest: 2000000, total: 12000000 }],
  ['원금 10만원 미만은 상한 미적용', 90000, 30, 12, false, { capped: false, validRate: 30, interest: 27000 }],
  ['경계: 연 20% 정확히는 허용', 10000000, 20, 6, false, { capped: false, interest: 1000000 }],
  ['국세청 예시1: 5억 연2% -> 1,300만 과세', 500000000, 2, 12, true, { giftGap: 13000000, giftTaxable: true }],
  ['국세청 예시2: 3억 무이자 -> 1,380만 과세', 300000000, 0, 12, true, { giftGap: 13800000, giftTaxable: true, interest: 0, total: 300000000 }],
  ['국세청 예시3: 2억 무이자 -> 920만 비과세', 200000000, 0, 12, true, { giftGap: 9200000, giftTaxable: false, minRate: 0 }],
  ['경계: 무이자 217,391,304원 -> 9,999,999.98원 비과세', 217391304, 0, 12, true, { giftGap: 9999999, giftTaxable: false }],
  ['경계: 무이자 217,391,305원 -> 10,000,000.03원 과세', 217391305, 0, 12, true, { giftTaxable: true }],
  ['가족 아님: 증여 계산 안 함', 300000000, 0, 12, false, { giftGap: 0, giftTaxable: false }],
];
for (const [name, a, r, m, f, exp] of cases) {
  const out = calc(a, r, m, f);
  for (const k of Object.keys(exp)) assert.strictEqual(out[k], exp[k], name + ' ' + k + '=' + out[k]);
  console.log('PASS', name, JSON.stringify(out));
}
// 3억 무이자: 차액 1천만원 미만 되는 최소 이율 = 4.6 - 1000만/3억*100 = 1.2667 -> 1.27%
const r3 = calc(300000000, 0, 12, true); assert.strictEqual(r3.minRate, 1.27);
assert.strictEqual(calc(300000000, 1.27, 12, true).giftTaxable, false);
console.log('PASS 3억 최소 이율 1.27%');
assert.strictEqual(hangul(10000000), '일천만'); assert.strictEqual(hangul(217391304), '이억일천칠백삼십구만일천삼백사');
assert.strictEqual(hangul(1050000), '일백오만');
console.log('PASS 한글 금액');
const t = text({ r: calc(10000000, 5, 12, false), amount: 10000000, months: 12, pay: 'monthly', lender: '홍길동', borrower: '김철수', date: '2026-01-31' });
assert.ok(t.includes('금 일천만원정 (₩10,000,000)')); assert.ok(t.includes('2026년 1월 31일')); assert.ok(t.includes('2027년 1월 31일까지'));
assert.ok(t.includes('매월 31일에 41,667원'));
const t2 = text({ r: calc(5000000, 0, 1, false), amount: 5000000, months: 1, pay: 'maturity', lender: 'A', borrower: 'B', date: '2026-01-31' });
assert.ok(t2.includes('2026년 2월 28일까지')); assert.ok(t2.includes('3. 이자: 없음.'));
console.log('PASS 문안 (말일 처리 포함)');
console.log('--- 문안 예시 ---\n' + t);
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'pn-amount': '10000000', 'pn-rate': '25', 'pn-months': '12', 'pn-pay': 'monthly', 'pn-rel': 'family', 'pn-lender': '홍길동', 'pn-borrower': '김철수', 'pn-date': '2026-11-08' };
const outP = [];
const el = id => ({ value: vals[id] !== undefined ? vals[id] : '', style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['pn-out', 'pn-text', 'pn-copy', 'pn-copied', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(연 25%, 가족):', outP.join(' | '));
assert.ok(outP[0].startsWith('경고')); assert.ok(outP.join().includes('12,000,000원'));
assert.ok(els['pn-text'].value.includes('연 20%(단리)'));
console.log('ALL PASS');
