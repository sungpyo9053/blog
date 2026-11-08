// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.watchaCalc, refund = window.watchaRefund;
// 공식 API 가격과 일치하는지
const api = JSON.parse(fs.readFileSync(path.join(__dirname, 'watcha-api-tickets-types.json'), 'utf8'));
const map = { web: '', google: 'TicketSingular::GoogleIAB::', apple: 'TicketSingular::AppleIAP::' };
for (const pay of Object.keys(map)) for (const [plan, key] of [['basic', 'Tall'], ['premium', 'Grande']]) {
  const pre = pay === 'web' ? 'Ticket::' : map[pay];
  const r = calc(plan, pay, 'monthly', 1, 1);
  assert.strictEqual(r.monthPrice, api[pre + key].sale_price, pay + plan + ' month');
  assert.strictEqual(r.yearPrice, api[pre + key + 'Yearly'].sale_price, pay + plan + ' year');
  console.log('PASS API 가격', pay, plan, r.monthPrice, r.yearPrice);
}
const cases = [
  ['웹 프리미엄 1개월권 4명 12개월', ['premium', 'web', 'monthly', 4, 12], { total: 154800, perPersonMonth: 3225, annual: 154800, alt: 129900, breakEven: 11 }],
  ['웹 프리미엄 12개월권 4명 12개월', ['premium', 'web', 'yearly', 4, 12], { total: 129900, perPersonTotal: 32475, perPersonMonth: 2706 }],
  ['웹 프리미엄 12개월권 2명', ['premium', 'web', 'yearly', 2, 12], { perPersonTotal: 64950, perPersonMonth: 5413 }],
  ['웹 베이직 10개월 매달 = 79,000 (12개월권보다 900 싸다)', ['basic', 'web', 'monthly', 1, 10], { total: 79000, alt: 79900 }],
  ['웹 베이직 11개월 매달 = 86,900', ['basic', 'web', 'monthly', 1, 11], { total: 86900, breakEven: 11 }],
  ['베이직 3명 입력 -> 1명으로 제한', ['basic', 'web', 'monthly', 3, 1], { people: 1, capped: true, total: 7900 }],
  ['프리미엄 6명 입력 -> 4명으로 제한', ['premium', 'web', 'monthly', 6, 1], { people: 4, capped: true }],
  ['앱(애플) 프리미엄 12개월권 13개월 -> 2장', ['premium', 'apple', 'yearly', 1, 13], { total: 320000, breakEven: 11 }],
  ['앱(구글) 베이직 12개월 매달 = 114,000', ['basic', 'google', 'monthly', 1, 12], { total: 114000, alt: 95900 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 약관 제15조 예시 2개
let f = refund('premium', 'monthly', 0, 1); assert.strictEqual(f.refund, 9610); console.log('PASS 약관 예: 프리미엄 1개월권 1편 -> 9,610', JSON.stringify(f));
f = refund('premium', 'yearly', 2, 1); assert.strictEqual(f.refund, 89110); console.log('PASS 약관 예: 12개월권 3월 해지 1편 -> 89,110', JSON.stringify(f));
f = refund('basic', 'monthly', 0, 10); assert.strictEqual(f.refund, 0); console.log('PASS 음수 방지 0원');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'wc-plan': 'premium', 'wc-pay': 'web', 'wc-cycle': 'monthly', 'wc-people': '4', 'wc-months': '12', 'wc-used': '2', 'wc-vod': '1' };
const outs = { 'wc-out': [], 'wc-refund': [] };
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
Object.keys(outs).forEach(id => els[id] = { style: {}, set innerHTML(v) { outs[id].length = 0; }, appendChild(p) { outs[id].push(p.textContent); } });
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outs['wc-out'].join(' | '));
console.log('UI 환불 출력:', outs['wc-refund'].join(' | '));
assert.ok(outs['wc-out'].join().includes('3,225원'));
assert.ok(outs['wc-refund'].join().includes('9,610원'));
console.log('ALL PASS');
