// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { calc, fine } = window.carInspCalc;
// 과태료: 별표 2 소목 (30일 이내 4만, 31일째부터 3일 초과 시마다 2만, 115일 이상 60만)
const fines = [[0, 0], [1, 40000], [30, 40000], [31, 40000], [33, 40000], [34, 60000], [37, 80000], [58, 220000], [60, 220000], [112, 580000], [114, 580000], [115, 600000], [400, 600000]];
for (const [d, w] of fines) assert.strictEqual(fine(d), w, 'fine ' + d);
console.log('PASS 과태료 경계값', fines.map(x => x.join('일=')).join(', '));
const cases = [
  ['자가용 새 차 2025-03-10 등록 -> 첫 만료 5년', { type: 'np', isNew: true, reg: '2025-03-10', last: '', base: '2026-10-29' },
    { first: '2030-03-09', expiry: '2030-03-09', start: '2029-12-09', end: '2030-04-09', status: 'before', next: '2032-03-09' }],
  ['자가용 새 차 2023-05-20 등록 -> 첫 만료 4년', { type: 'np', isNew: true, reg: '2023-05-20', last: '', base: '2026-10-29' },
    { first: '2027-05-19', expiry: '2027-05-19', start: '2027-02-18', end: '2027-06-19' }],
  ['2024-12-31 등록(경계) -> 4년', { type: 'np', isNew: true, reg: '2024-12-31', last: '', base: '2026-10-29' }, { first: '2028-12-30' }],
  ['2025-01-01 등록(경계) -> 5년', { type: 'np', isNew: true, reg: '2025-01-01', last: '', base: '2026-10-29' }, { first: '2029-12-31' }],
  ['2022-05-20 등록, 제때 받았다고 가정 -> 2028 만료, 대상지역 차령 4년 초과라 종합검사', { type: 'np', isNew: true, reg: '2022-05-20', last: '', base: '2026-10-29', region: true },
    { first: '2026-05-19', expiry: '2028-05-19', comp: true }],
  ['본문 예: 만료 2026-10-01 -> 기간 07-03~11-01, 기준 10-29 마감까지 3일', { type: 'np', isNew: true, reg: '', last: '2026-10-01', base: '2026-10-29' },
    { start: '2026-07-03', end: '2026-11-01', status: 'in', days: 3, next: '2028-10-01' }],
  ['본문 예: 만료 2026-08-01, 10-29 -> 58일 지연 22만원', { type: 'np', isNew: true, reg: '', last: '2026-08-01', base: '2026-10-29' },
    { end: '2026-09-01', status: 'late', late: 58, fine: 220000 }],
  ['사업용 새 차 2025-06-01 -> 첫 2년, 다음 1년', { type: 'bp', isNew: true, reg: '2025-06-01', last: '', base: '2026-10-29' },
    { first: '2027-05-31', next: '2028-05-31' }],
  ['그 밖의 차종 만료일 없으면 계산 안 함', { type: 'etc', isNew: true, reg: '2020-01-01', last: '', base: '2026-10-29' }, { ok: false }],
  ['그 밖의 차종 만료 2026-06-30 -> 90일 지연 42만원', { type: 'etc', isNew: true, reg: '', last: '2026-06-30', base: '2026-10-29' },
    { end: '2026-07-31', late: 90, fine: 420000 }],
  ['윤년 2024-02-29 등록 -> 2028-02-28 만료', { type: 'np', isNew: true, reg: '2024-02-29', last: '', base: '2026-10-29' }, { first: '2028-02-28' }],
];
for (const [name, o, exp] of cases) {
  const r = calc(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 렌더 — 최소 DOM 스텁
const vals = { 'ci-type': 'np', 'ci-reg': '', 'ci-last': '2026-08-01', 'ci-base': '2026-10-29', 'ci-late': '' };
const chk = { 'ci-new': true, 'ci-region': false };
const outP = [];
const el = id => ({ value: vals[id], checked: chk[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ci-out', ...Object.keys(vals), ...Object.keys(chk)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력:', outP.join(' | '));
assert.ok(outP.join().includes('220,000원'));
