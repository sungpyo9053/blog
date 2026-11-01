// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.carInstallCalc;
const base = { price: 30000000, down: 0, months: 36, rate: 5, balloonPct: 0, taxType: 'none', taxBase: 0, addTax: false };
const C = o => calc(Object.assign({}, base, o));
// 독립 검산: 원리금균등 표준식
function ref(P, rate, n, B) { const r = rate / 1200; const M = Math.round(r === 0 ? (P - B) / n : (P - B / (1 + r) ** n) * r / (1 - (1 + r) ** -n)); return M; }
const cases = [
  ['본문 표 3,000만 5% 12개월', {}, { months: 12 }, { monthly: 2568224, interest: 818688 }],
  ['본문 표 3,000만 5% 36개월', {}, {}, { monthly: 899127, interest: 2368572, totalPaid: 32368572 }],
  ['본문 표 3,000만 5% 60개월', {}, { months: 60 }, { monthly: 566137, interest: 3968220 }],
  ['본문 표 3,000만 7% 60개월', {}, { rate: 7, months: 60 }, { monthly: 594036, interest: 5642160 }],
  ['본문 예시 3,500만-500만 5.5% 36개월', {}, { price: 35000000, down: 5000000, rate: 5.5 }, { principal: 30000000, monthly: 905877, interest: 2611572, totalPaid: 32611572 }],
  ['유예 60%: 5,000만 선수 1,500만 5% 36개월', {}, { price: 50000000, down: 15000000, balloonPct: 60 }, { principal: 35000000, balloon: 30000000, monthly: 274854, interest: 4894744 }],
  ['같은 차 일반 할부', {}, { price: 50000000, down: 15000000 }, { monthly: 1048981, interest: 2763316 }],
  ['무이자 0%: 원금/개월', {}, { rate: 0, months: 24 }, { monthly: 1250000, interest: 0 }],
  ['취득세 승용 7% 3,000만', {}, { taxType: 'car' }, { tax: 2100000, cashAtStart: 2100000 }],
  ['경차 1,500만 4%=60만 -> 면제', {}, { price: 15000000, taxType: 'light' }, { tax: 0 }],
  ['경차 2,000만 4%=80만 -> 5만', {}, { price: 20000000, taxType: 'light' }, { tax: 50000 }],
  ['승용 외 5%', {}, { taxType: 'other' }, { tax: 1500000 }],
  ['과세표준 직접 입력 2,727만 7%', {}, { taxType: 'car', taxBase: 27270000 }, { tax: 1908900 }],
  ['취득세 할부원금 포함', {}, { taxType: 'car', addTax: true }, { principal: 32100000, cashAtStart: 0 }],
];
for (const [name, _, o, exp] of cases) {
  const r = C(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ principal: r.principal, monthly: r.monthly, balloon: r.balloon, interest: r.interest, tax: r.tax }));
}
// 기간 비교 행 5개가 독립식과 일치
const rr = C({ rate: 7 });
assert.deepStrictEqual(rr.rows.map(x => x.months), [12, 24, 36, 48, 60]);
rr.rows.forEach(x => assert.strictEqual(x.monthly, ref(30000000, 7, x.months, 0)));
console.log('PASS 기간 비교 5행 독립식 일치');
// 오류 처리
assert.ok(C({ down: 40000000 }).error); assert.ok(C({ down: 30000000 }).error); assert.ok(C({ balloonPct: 100 }).error);
console.log('PASS 오류 입력 3종');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'ci-price': '35000000', 'ci-down': '5000000', 'ci-months': '36', 'ci-rate': '5.5', 'ci-balloon': '0', 'ci-tax': 'none', 'ci-base': '', 'ci-addtax': '' };
const outP = []; let rows = 0;
const mk = () => ({ style: {}, children: [], appendChild(c) { this.children.push(c); } });
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { if (id === 'ci-out') outP.length = 0; }, appendChild(p) { if (id === 'ci-out') outP.push(p.textContent); else rows = p.children.length; } });
const els = {}; ['ci-out', 'ci-table', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => mk() };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('905,877원')); assert.strictEqual(rows, 6);
console.log('PASS UI 표 6행(헤더+5)');
