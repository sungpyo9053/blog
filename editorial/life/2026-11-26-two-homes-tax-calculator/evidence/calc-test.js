// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.twoHomesCalc;
const base = { d0: '2022-03-15', d1: '2026-09-01', dc: '2026-08-20', d2: '2028-06-30', oldAdj: true, newAdj: true, oldBuyAdj: true, resid: 3, price: 15e8, newPrice: 8e8 };
const cases = [
  ['기본값: 둘 다 조정, 8.20 계약 9.1 취득 -> 양도세 2년(2028-09-01), 취득세 3년', {}, { period: 2, inTime: true, exempt: true, ratio: 0.2, acqPeriod: 3, acqRate: 0.0233, acqTax: 18640000 }],
  ['8.3 이전 계약 -> 종전 규정 3년', { dc: '2026-08-03' }, { period: 3 }],
  ['계약일 비움, 취득 8.3 -> 3년', { dc: '', d1: '2026-08-03' }, { period: 3 }],
  ['계약일 비움, 취득 8.4 -> 2년', { dc: '', d1: '2026-08-04' }, { period: 2 }],
  ['종전 주택 9.30 양도(시행 전) -> 3년', { d1: '2026-08-10', dc: '', d2: '2026-09-30' }, { period: 3 }],
  ['신규만 조정 -> 3년', { oldAdj: false }, { period: 3, heavy: false }],
  ['기한 당일 양도 2028-09-01 -> 충족', { d2: '2028-09-01' }, { inTime: true, exempt: true }],
  ['기한 다음날 2028-09-02 -> 미충족, 조정이면 중과', { d2: '2028-09-02' }, { inTime: false, exempt: false, heavy: true }],
  ['1년 요건: 종전 취득 1년 뒤 같은 날 신규 취득 -> 충족', { d0: '2025-09-01' }, { gap: true }],
  ['1년 요건: 하루 모자람 -> 미충족', { d0: '2025-09-02' }, { gap: false, exempt: false }],
  ['보유 2년 미만 -> 미충족', { d0: '2025-03-01', d2: '2026-12-01' }, { hold: false, exempt: false }],
  ['취득 당시 조정, 거주 1.5년 -> 미충족', { resid: 1.5 }, { resid: false, exempt: false }],
  ['취득 당시 비조정이면 거주 무관', { oldBuyAdj: false, resid: 0 }, { resid: true, exempt: true }],
  ['12억 이하 -> 비율 0', { price: 12e8 }, { ratio: 0 }],
  ['취득세: 10.1 이후 취득, 8.26 이후 계약 -> 2년', { d1: '2026-10-05', dc: '2026-09-01', d2: '2028-10-01' }, { acqPeriod: 2, acqInTime: true, period: 2, inTime: true }],
  ['취득세 기한 초과 2028-10-06', { d1: '2026-10-05', dc: '2026-09-01', d2: '2028-10-06' }, { acqInTime: false, inTime: false }],
  ['취득세: 8.26 이전 계약 -> 3년', { d1: '2026-10-05', dc: '2026-08-26' }, { acqPeriod: 3 }],
  ['취득세율 6억 1%, 9억 초과 3%', { newPrice: 6e8 }, { acqRate: 0.01, acqTax: 6000000 }],
  ['취득세율 10억 3%', { newPrice: 10e8 }, { acqRate: 0.03 }],
  ['오류: 양도 예정일이 신규 취득 전', { d2: '2026-05-01' }, { ok: false }],
];
for (const [name, over, exp] of cases) {
  const r = calc(Object.assign({}, base, over));
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-9 || r[k] === exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name);
}
assert.strictEqual(new Date(calc(base).deadline).toISOString().slice(0, 10), '2028-09-01');
console.log('PASS 기한 날짜 2028-09-01');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'tt-d0': '2022-03-15', 'tt-d1': '2026-09-01', 'tt-dc': '2026-08-20', 'tt-d2': '2028-06-30', 'tt-res': '3', 'tt-price': '150000', 'tt-nprice': '80000' };
const checks = { 'tt-oadj': true, 'tt-nadj': true, 'tt-obuy': true };
const outP = [];
const el = id => ({ value: vals[id], checked: checks[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['tt-out', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n' + outP.join('\n'));
assert.ok(outP.join().includes('2028-09-01'));
assert.ok(outP.join().includes('20%'));
