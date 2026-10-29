// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'(?:[^'\\]|\\.)*'/g) || []) if (s.indexOf('<') >= 0) throw new Error('< inside string: ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.resignCalc;
const cases = [
  ['고용노동부 예: 7.9 제출, 1일~말일 -> 9.1', ['2025-07-09', 'month', 1, ''], { main: '2025-09-01', mainLast: '2025-08-31', settle: '2025-09-15' }],
  ['고용노동부 예: 2023.4.15 통고, 1일~말일 -> 2023.6.1', ['2023-04-15', 'month', 1, ''], { main: '2023-06-01' }],
  ['일수계산기 글과 일치: 11.2 통고 1개월 -> 12.3', ['2026-11-02', 'day', 1, ''], { main: '2026-12-03', m1End: '2026-12-02' }],
  ['1개월, 해당일 없음: 1.30 -> 2월 말 만료 -> 3.1', ['2026-01-30', 'day', 1, ''], { main: '2026-03-01', m1End: '2026-02-28' }],
  ['1개월, 1.31 -> 기산 2.1 -> 3.1', ['2026-01-31', 'day', 1, ''], { main: '2026-03-01' }],
  ['1개월, 연말 넘김: 12.15 -> 2027.1.16', ['2026-12-15', 'day', 1, ''], { main: '2027-01-16' }],
  ['월급제 산정기간 21일~20일: 11.14 제출 -> 12.21', ['2026-11-14', 'month', 21, ''], { main: '2026-12-21' }],
  ['월급제 21일 시작, 11.25 제출 -> 2027.1.21', ['2026-11-25', 'month', 21, ''], { main: '2027-01-21' }],
  ['월급제 1일, 말일 제출 11.30 -> 2027.1.1', ['2026-11-30', 'month', 1, ''], { main: '2027-01-01' }],
  ['기본값: 11.16 제출, 희망 마지막 근무일 11.30', ['2026-11-16', 'month', 1, '2026-11-30'], { main: '2027-01-01', m1: '2026-12-17', wishRetire: '2026-12-01', wishSettle: '2026-12-15', settle: '2027-01-15', wishLaterThanMain: false }],
  ['희망일이 더 늦음', ['2026-11-16', 'day', 1, '2027-02-27'], { main: '2026-12-17', wishLaterThanMain: true }],
  ['희망일이 제출일보다 앞섬', ['2026-11-16', 'day', 1, '2026-11-10'], { wishBeforeSubmit: true }],
  ['말일 주말 표시: 2026.11.6(금) 통고 -> 말일 12.6(일)', ['2026-11-06', 'day', 1, ''], { m1End: '2026-12-06', m1Weekend: true }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(exp));
}
assert.strictEqual(calc('', 'day', 1, ''), null);
console.log('PASS 빈 입력 -> null');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'rs-submit': '2026-11-16', 'rs-pay': 'month', 'rs-start': '1', 'rs-wish': '2026-11-30' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['rs-out', 'rs-start-row', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n' + outP.join('\n'));
assert.ok(outP.join().includes('2027년 1월 1일(금)'));
assert.ok(outP.join().includes('2026년 12월 15일(화)'));
