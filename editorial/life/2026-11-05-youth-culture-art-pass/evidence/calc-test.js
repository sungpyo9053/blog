// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('raw < in string literal');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const check = window.youthCulturePassCheck;
const T = { y: 2026, m: 10, d: 31 };
const base = { birth: 2007, region: 'non', status: 'add', used731: true, used2025: false, spent: 0, ...T };
const cases = [
  ['2007 비수도권 추가발급 5만 사용', { spent: 50000 }, { eligible: true, amount: 200000, left: 150000, daysLeft: 61, movies: 4 }],
  ['2007 수도권 추가발급 0 사용', { region: 'metro' }, { eligible: true, amount: 150000, left: 150000, movies: 2 }],
  ['미신청 10/31 -> 신청 가능, 마감 30일', { status: 'none', region: 'metro' }, { eligible: true, canApply: true, amount: 150000, applyDaysLeft: 30 }],
  ['미신청 12/1 -> 신청 마감', { status: 'none', m: 12, d: 1 }, { eligible: false, reason: 'closed' }],
  ['상반기 발급 7/31 미사용 -> 회수', { status: 'first', used731: false }, { eligible: false, reason: 'reclaimed' }],
  ['상반기 발급 사용 중 12만', { status: 'first', region: 'metro', spent: 120000 }, { eligible: true, left: 30000 }],
  ['2006 2025 사용, 미신청 -> 제외', { birth: 2006, used2025: true, status: 'none' }, { eligible: false, reason: 'used2025' }],
  ['2006 2025 미사용 미신청', { birth: 2006, status: 'none' }, { eligible: true, canApply: true }],
  ['2008년생 -> 대상 아님', { birth: 2008 }, { eligible: false, reason: 'age' }],
  ['2005년생 -> 대상 아님', { birth: 2005 }, { eligible: false, reason: 'age' }],
  ['사용액 초과 -> 0, over', { spent: 250000 }, { left: 0, over: true }],
  ['12/31 당일 -> 0일 남음', { m: 12, d: 31 }, { daysLeft: 0, reason: '' }],
  ['2027-01-01 -> 기한 지남', { y: 2027, m: 1, d: 1 }, { reason: 'expired', left: 0 }],
];
for (const [name, over, exp] of cases) {
  const r = check({ ...base, ...over });
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'ycp-birth': '2007', 'ycp-region': 'non', 'ycp-status': 'add', 'ycp-spent': '50000' };
const chk = { 'ycp-used731': true, 'ycp-used2025': false };
const outP = [];
const el = id => ({ value: vals[id], checked: chk[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ycp-out', ...Object.keys(vals), ...Object.keys(chk)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('150,000원'));
