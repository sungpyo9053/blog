// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^'\n]*'/g)) if (s.indexOf('<') >= 0) throw new Error('raw < in string ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.housingBenefitCalc, own = window.housingBenefitOwn;
const cases = [
  ['마이홈 예시: 서울 3인 소득 80만 월세 30만 -> 30만', [2026, 1, 3, 800000, 0, 300000], { eligible: true, ded: 0, pay: 300000 }],
  ['마이홈 예시: 보증금 1,000만+월세 10만 -> 실제임차료 133,333', [2026, 4, 1, 0, 10000000, 100000], { actual: 133333, pay: 133340 }],
  ['본문 예: 경기 1인 소득 100만 보증금 500만 월세 30만 -> 246,170', [2026, 2, 1, 1000000, 5000000, 300000], { actual: 316666, cap: 300000, ded: 53833.2, pay: 246170 }],
  ['생계 기준 경계: 1인 소득 820,556 -> 공제 0', [2026, 1, 1, 820556, 0, 500000], { ded: 0, pay: 369000 }],
  ['주거 기준 경계: 1인 1,230,834 -> 대상', [2026, 4, 1, 1230834, 0, 300000], { eligible: true, pay: 88920 }],
  ['주거 기준 초과: 1인 1,230,835 -> 불가', [2026, 4, 1, 1230835, 0, 300000], { eligible: false, pay: 0 }],
  ['최저 1만원: 4급지 1인 소득 120만 월세 5만', [2026, 4, 1, 1200000, 0, 50000], { pay: 10000, reason: 'min' }],
  ['5배 규칙: 서울 1인 월세 1,845,001 -> 1만원', [2026, 1, 1, 500000, 0, 1845001], { pay: 10000, reason: 'fivex' }],
  ['5배 경계: 서울 1인 월세 1,845,000 -> 369,000', [2026, 1, 1, 500000, 0, 1845000], { pay: 369000 }],
  ['임차료 0원 -> 지급 제외', [2026, 1, 1, 500000, 0, 0], { eligible: true, pay: 0, reason: 'norent' }],
  ['전세 6,000만 -> 월 20만', [2026, 3, 2, 0, 60000000, 0], { actual: 200000, pay: 200000 }],
  ['2027 서울 1인 소득 0 월세 50만 -> 381,000', [2027, 1, 1, 0, 0, 500000], { pay: 381000 }],
  ['2027 4급지 6인 -> 452,000', [2027, 4, 6, 0, 0, 900000], { pay: 452000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.ok(r[k] === exp[k] || Math.abs(r[k] - exp[k]) < 1e-6, name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 기준임대료 표 대조 (2026 마이홈 원 단위, 2027 보건복지부 만 원 단위)
const t26 = [[369000,414000,492000,571000,591000,699000],[300000,335000,401000,463000,479000,568000],[247000,275000,327000,381000,394000,463000],[212000,238000,283000,329000,340000,402000]];
const t27 = [[38.1,43.1,51.4,59.6,61.8,73.1],[31.3,35.2,42.2,48.8,50.5,59.9],[25.9,29.1,34.7,40.3,41.8,49.2],[23.4,26.5,31.8,36.9,38.2,45.2]];
for (let g = 1; g <= 4; g++) for (let n = 1; n <= 6; n++) {
  assert.strictEqual(calc(2026, g, n, 0, 0, 9e6 / 10).base, t26[g - 1][n - 1]);
  assert.strictEqual(calc(2027, g, n, 0, 0, 9e5).base, Math.round(t27[g - 1][n - 1] * 10000));
}
console.log('PASS 기준임대료 48칸');
// 자가가구
const o1 = own(2026, 1, 1100000, 16010000); assert.strictEqual(o1.rate, 80); assert.strictEqual(o1.amount, 12808000);
const o2 = own(2026, 3, 800000, 10950000); assert.strictEqual(o2.rate, 100);
const o3 = own(2026, 1, 1000000, 5900000); assert.strictEqual(o3.rate, 90); assert.strictEqual(o3.amount, 5310000);
assert.strictEqual(own(2026, 1, 1300000, 5900000).eligible, false);
console.log('PASS 자가가구: 대보수 80% 12,808,000 / 3인 소득 80만 100% / 1인 100만 90% 5,310,000 / 초과 불가');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'hb-year': '2026', 'hb-type': 'rent', 'hb-grade': '1', 'hb-n': '1', 'hb-income': '1000000', 'hb-deposit': '5000000', 'hb-rent': '300000', 'hb-repair': '5900000' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['hb-out', 'hb-rentrow', 'hb-ownrow', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('262,840원'));
vals['hb-type'] = 'own'; vals['hb-repair'] = '16010000'; vals['hb-income'] = '1100000';
eval(src);
console.log('UI 자가 출력:', outP.join(' | '));
assert.ok(outP.join().includes('12,808,000원'));
