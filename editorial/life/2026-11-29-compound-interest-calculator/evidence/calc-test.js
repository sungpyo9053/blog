// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
assert.strictEqual(faq, (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length, 'FAQ JSON-LD 개수 = 본문 h3 개수');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.compoundInterestCalc, rows = window.compoundYearRows;
const cases = [
  ['한국은행 예시 1억 3% 2년 6개월복리 = 106.14백만', [1e8, 0, 3, 2, 2, 'normal'], { pre: 6136355, simple: 6000000 }],
  ['1천만 4% 10년 연복리', [1e7, 0, 4, 10, 1, 'normal'], { pre: 4802442, simple: 4000000, diff: 802442 }],
  ['1천만 4% 20년 연복리', [1e7, 0, 4, 20, 1, 'normal'], { pre: 11911231, diff: 3911231 }],
  ['1천만 4% 30년 연복리', [1e7, 0, 4, 30, 1, 'normal'], { pre: 22433975, simple: 12000000, diff: 10433975 }],
  ['1천만 4% 20년 월복리', [1e7, 0, 4, 20, 12, 'normal'], { pre: 12225820, simple: 8000000, diff: 4225820 }],
  ['1천만 4% 20년 일복리', [1e7, 0, 4, 20, 365, 'normal'], { pre: 12254433, diff: 4254433 }],
  ['월30만 4% 10년 월복리', [0, 3e5, 4, 10, 12, 'normal'], { principal: 36000000, pre: 8322191, simple: 7260000, diff: 1062191 }],
  ['월30만 4% 20년 월복리', [0, 3e5, 4, 20, 12, 'normal'], { principal: 72000000, pre: 38399162, simple: 28920000 }],
  ['월30만 4% 30년 월복리', [0, 3e5, 4, 30, 12, 'normal'], { principal: 108000000, pre: 100908870, simple: 64980000 }],
  ['기본값 1천만+월30만 4% 10년 월복리 일반', [1e7, 3e5, 4, 10, 12, 'normal'], { principal: 46000000, pre: 13230518, diff: 1970518, it: 1852270, lt: 185220, post: 11193028, total: 57193028 }],
  ['세금우대 9% + 농특세 (14-9)x10%', [1e7, 3e5, 4, 10, 12, 'pref'], { it: 1190740, lt: 0, rt: 66150 }],
  ['상호금융 2026 가입 5% + 농특세 0.9%', [1e7, 3e5, 4, 10, 12, 'coop5'], { it: 661520, rt: 119070 }],
  ['비과세 0%', [1e7, 3e5, 4, 10, 12, 'none'], { tax: 0, post: 13230518 }],
  ['금리 0%', [1e7, 1e5, 0, 5, 12, 'normal'], { pre: 0, simple: 0, tax: 0, total: 16000000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 예금·적금 글(11-03)의 1년 숫자와 교차 검산: 예금 1천만 3% 12개월 월복리 304,159 / 적금 월10만 3% 12개월 월복리 19,679, 단리 19,500
assert.strictEqual(calc(1e7, 0, 3, 1, 12, 'normal').pre, 304159);
assert.strictEqual(calc(0, 1e5, 3, 1, 12, 'normal').pre, 19679);
assert.strictEqual(calc(0, 1e5, 3, 1, 12, 'normal').simple, 19500);
console.log('PASS 1년 예금·적금 숫자 = 예금·적금 세후 이자 글과 일치');
// 일반과세 세율 = 15.4% (10원 미만 절사 오차 이내)
const r1 = calc(1e8, 0, 4, 20, 12, 'normal');
assert.ok(Math.abs(r1.tax - r1.pre * 0.154) <= 20, 'tax 15.4%');
console.log('PASS 1억 4% 20년 월복리 세금 = 세전 이자의 15.4%', r1.tax, r1.pre);
// 월복리 실효 연 4.07%
assert.strictEqual(Math.round((Math.pow(1 + 0.04 / 12, 12) - 1) * 10000) / 100, 4.07);
// 72의 법칙 표
for (const [rate, r72, ex] of [[2, 36, '35.0'], [3, 24, '23.4'], [4, 18, '17.7'], [5, 14.4, '14.2'], [6, 12, '11.9'], [8, 9, '9.0']]) {
  const r = calc(1e7, 0, rate, 1, 1, 'normal');
  assert.strictEqual(Math.round(r.r72 * 10) / 10, r72); assert.strictEqual(r.exact.toFixed(1), ex);
}
console.log('PASS 72의 법칙 표(72/r, 연복리 ln2/ln(1+r))');
// 세후 72의 법칙: 4% x 0.846 = 3.384%, 72/3.384 = 21.3년
assert.strictEqual(Math.round(72 / (4 * 0.846)), 21);
// 0.1%p 뒤집힘: 4.1% 월복리 20년 > 4% 일복리 20년
assert.ok(calc(1e7, 0, 4.1, 20, 12, 'normal').pre > calc(1e7, 0, 4, 20, 365, 'normal').pre);
console.log('PASS 4.1% 월복리', calc(1e7, 0, 4.1, 20, 12, 'normal').pre, '> 4% 일복리', calc(1e7, 0, 4, 20, 365, 'normal').pre);
// 복리 = 회차별 직접 누적(월복리, 매월 초 납입)과 일치
for (const n of [1, 7, 12, 60, 240]) {
  let b = 1e7; for (let k = 0; k < n; k++) { b = (b + 3e5) * (1 + 0.04 / 12); }
  assert.strictEqual(calc(1e7, 3e5, 4, n / 12, 12, 'normal').pre, Math.floor(b - 1e7 - 3e5 * n + 1e-6), 'n=' + n);
}
console.log('PASS 월복리 = 매월 (잔액+납입)x(1+r/12) 누적 (n=1,7,12,60,240개월)');
// 연도별 표: 10년 이하 매년, 10년 초과 5년 단위 + 마지막 해
assert.deepStrictEqual(rows(1e7, 3e5, 4, 10, 12).map(x => x.year), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
assert.deepStrictEqual(rows(1e7, 3e5, 4, 12, 12).map(x => x.year), [5, 10, 12]);
assert.deepStrictEqual(rows(0, 3e5, 4, 30, 12).map(x => x.year), [5, 10, 15, 20, 25, 30]);
assert.strictEqual(rows(0, 3e5, 4, 30, 12)[5].compound, 108000000 + 100908870);
console.log('PASS 연도별 표 구간', JSON.stringify(rows(0, 3e5, 4, 30, 12)));
// UI 렌더 — 최소 DOM 스텁
function render(vals) {
  const outP = [], tableCells = [];
  const mk = () => ({ style: {}, textContent: '', children: [], appendChild(c) { this.children.push(c); if (c.textContent) tableCells.push(c.textContent); } });
  const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { if (id === 'ci-out') outP.length = 0; }, appendChild(p) { if (id === 'ci-out') outP.push(p.textContent); } });
  const els = {}; ['ci-out', 'ci-table', ...Object.keys(vals)].forEach(id => els[id] = el(id));
  global.document = { getElementById: id => els[id], createElement: mk };
  eval(src);
  return { outP, tableCells };
}
let u = render({ 'ci-p': '10000000', 'ci-m': '300000', 'ci-rate': '4', 'ci-years': '10', 'ci-freq': '12', 'ci-tax': 'normal' });
console.log('UI 기본값 출력:', u.outP.join(' | '));
assert.ok(u.outP.join().includes('57,193,028원'));
assert.ok(!u.outP.join().includes('종합과세'));
u = render({ 'ci-p': '0', 'ci-m': '300000', 'ci-rate': '4', 'ci-years': '30', 'ci-freq': '12', 'ci-tax': 'normal' });
console.log('UI 월30만 30년 출력:', u.outP.join(' | '));
assert.ok(u.outP.join().includes('100,908,870원')); assert.ok(u.outP.join().includes('종합과세'));
u = render({ 'ci-p': '', 'ci-m': '-5', 'ci-rate': 'abc', 'ci-years': '0', 'ci-freq': '1', 'ci-tax': 'none' });
console.log('UI 빈값/음수 입력 출력:', u.outP.join(' | '));
assert.ok(u.outP.join().includes('납입 원금 합계: 0원'));
console.log('ALL PASS');
