// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^'\n]*'/g) || []) if (s.indexOf('<') >= 0) throw new Error('< in string literal: ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
const h3faq = html.split('<h2 id="faq">')[1].split('<h2')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq, 'FAQ JSON-LD count = h3 count');
console.log('PASS JSON-LD FAQ', faq, '개 = 본문 h3', h3faq, '개');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.healthRefundCalc, tierOf = window.healthRefundTier;
// 공식 표(공단 누리집·복지부 2026.8.30.) 전체 대조
const T = { 2026: [[90,112,173,326,446,536,843],[143,181,245,404,580,698,1096]], 2025: [[89,110,170,320,437,525,826],[141,178,240,396,569,684,1074]] };
for (const y of [2026, 2025]) for (const l of [0, 1]) T[y][l].forEach((m, i) => assert.strictEqual(calc(y, i, !!l, 0).cap, m * 10000));
console.log('PASS 상한액 28개 값 = 공식 표');
const cases = [
  ['2026 4~5분위 300만', 2026, 2, false, 3000000, { cap: 1730000, refund: 1270000 }],
  ['2026 4~5분위 요양병원120일 300만', 2026, 2, true, 3000000, { cap: 2450000, refund: 550000 }],
  ['2025 1분위 200만', 2025, 0, false, 2000000, { cap: 890000, refund: 1110000 }],
  ['2026 1분위 경계 90만 -> 0', 2026, 0, false, 900000, { refund: 0 }],
  ['2026 10분위 1,000만 -> 157만, 최고상한 초과', 2026, 6, false, 10000000, { cap: 8430000, refund: 1570000, overTop: true }],
  ['2026 6~7분위 200만 -> 0', 2026, 3, false, 2000000, { refund: 0, overTop: false }],
];
for (const [name, y, t, l, p, exp] of cases) {
  const r = calc(y, t, l, p);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 2025 기준보험료 경계('이하'는 아래 분위)
[['work',57790,0],['work',57791,1],['work',100000,2],['work',114100,2],['work',282570,5],['work',282571,6],
 ['region',13850,0],['region',13851,1],['region',34520,2],['region',217541,6],['region',0,0]].forEach(([ty, pr, ex]) =>
  assert.strictEqual(tierOf(ty, pr), ex, ty + ' ' + pr));
console.log('PASS 기준보험료 경계 11건');
// UI 기본값 렌더 (2026, 4~5분위, 300만)
const vals = { 'hr-year': '2026', 'hr-tier': '2', 'hr-type': 'work', 'hr-prem': '100000', 'hr-paid': '3000000' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['hr-out', 'hr-auto-row', 'hr-long', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('1,270,000원'));
// 자동 추정 모드 (지역 20,000원 -> 4~5분위)
vals['hr-tier'] = 'auto'; vals['hr-type'] = 'region'; vals['hr-prem'] = '20000';
Object.keys(vals).forEach(id => els[id].value = vals[id]);
eval(src);
console.log('UI 자동추정 출력:', outP.join(' | '));
assert.ok(outP.join().includes('4~5분위') && outP.join().includes('1,270,000원'));
