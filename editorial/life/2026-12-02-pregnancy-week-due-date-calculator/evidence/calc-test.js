// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산 (TZ를 바꿔 두 번 실행)
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
console.log('TZ=' + (process.env.TZ || '(default)'), 'JSON-LD FAQ', faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.pregCalc;
// 독립 검산: 로컬 Date 생성자로 +n일 (정오 기준이라 서머타임에도 안전)
function plus(s, n) { const [y, m, d] = s.split('-').map(Number); const t = new Date(y, m - 1, d + n, 12); return t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' + String(t.getDate()).padStart(2, '0'); }
const cases = [
  ['기본: LMP 2026-01-01 28일, 오늘 03-12', ['lmp', '2026-01-01', 28, '2026-03-12'], { edd: '2026-10-08', weeks: 10, days: 0, stage: 'tri1', termFrom: '2026-09-17', termTo: '2026-10-21', post42: '2026-10-22', tri2: '2026-04-09', tri3: '2026-07-16' }],
  ['월말 넘김: LMP 2026-03-31 -> 다음 해 01-05', ['lmp', '2026-03-31', 28, '2026-04-01'], { edd: '2027-01-05', weeks: 0, days: 1 }],
  ['연말 넘김 주수: LMP 2026-12-20, 오늘 2027-01-03', ['lmp', '2026-12-20', 28, '2027-01-03'], { weeks: 2, days: 0, edd: '2027-09-26' }],
  ['주기 35일: LMP 2026-12-31 -> 기준일 2027-01-07', ['lmp', '2026-12-31', 35, '2027-02-01'], { base: '2027-01-07', edd: '2027-10-14', weeks: 3, days: 4 }],
  ['주기 21일: LMP 2026-01-01 -> 2026-10-01', ['lmp', '2026-01-01', 21, '2026-01-01'], { base: '2025-12-25', edd: '2026-10-01', weeks: 1, days: 0 }],
  ['윤년: LMP 2027-05-25 -> 예정일 2028-02-29', ['lmp', '2027-05-25', 28, '2028-02-29'], { edd: '2028-02-29', weeks: 40, days: 0, left: 0, stage: 'term' }],
  ['윤년 역계산: 예정일 2028-02-29', ['edd', '2028-02-29', 99, '2027-08-17'], { base: '2027-05-25', weeks: 12, days: 0 }],
  ['윤년 시작: LMP 2028-02-29 -> 2028-12-05', ['lmp', '2028-02-29', 28, '2028-03-14'], { edd: '2028-12-05', weeks: 2, days: 0 }],
  ['윤년 2월 통과 주수: LMP 2028-02-01, 오늘 03-01', ['lmp', '2028-02-01', 28, '2028-03-01'], { weeks: 4, days: 1 }],
  ['평년 2월 통과 주수: LMP 2027-02-01, 오늘 03-01', ['lmp', '2027-02-01', 28, '2027-03-01'], { weeks: 4, days: 0 }],
  ['손 계산과 차이: LMP 2026-05-01 -> 2027-02-05', ['lmp', '2026-05-01', 28, '2026-05-01'], { edd: '2027-02-05' }],
  ['역계산: 예정일 2026-10-08, 오늘 2026-07-16 -> 28주 0일 후기', ['edd', '2026-10-08', 28, '2026-07-16'], { base: '2026-01-01', weeks: 28, days: 0, stage: 'tri3', left: 84 }],
  ['13주 6일은 초기', ['lmp', '2026-01-01', 28, '2026-04-08'], { weeks: 13, days: 6, stage: 'tri1' }],
  ['14주 0일은 중기', ['lmp', '2026-01-01', 28, '2026-04-09'], { weeks: 14, days: 0, stage: 'tri2' }],
  ['27주 6일은 중기', ['lmp', '2026-01-01', 28, '2026-07-15'], { weeks: 27, days: 6, stage: 'tri2' }],
  ['36주 6일은 후기(만삭 전)', ['lmp', '2026-01-01', 28, '2026-09-16'], { weeks: 36, days: 6, stage: 'tri3' }],
  ['41주 6일은 만삭', ['lmp', '2026-01-01', 28, '2026-10-21'], { weeks: 41, days: 6, stage: 'term', left: -13 }],
  ['42주 0일은 과숙', ['lmp', '2026-01-01', 28, '2026-10-22'], { weeks: 42, days: 0, stage: 'post42' }],
  ['기준일 전', ['lmp', '2026-01-10', 28, '2026-01-01'], { stage: 'before' }],
  ['없는 날짜 2027-02-29', ['lmp', '2027-02-29', 28, '2027-03-01'], { error: 'date' }],
  ['주기 20일 거부', ['lmp', '2026-01-01', 20, '2026-03-01'], { error: 'cycle' }],
  ['주기 36일 거부', ['lmp', '2026-01-01', 36, '2026-03-01'], { error: 'cycle' }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  if (!r.error) assert.strictEqual(r.edd, plus(r.base, 280), name + ' 독립 검산');
  console.log('PASS', name, r.error ? r.error : 'edd=' + r.edd + ' ' + (r.ga >= 0 ? r.weeks + '주 ' + r.days + '일' : '') + ' ' + r.stage);
}
// 주요 날짜 표 (LMP 2026-01-01, 오늘 2026-06-20 = 24주 2일)
const r = calc('lmp', '2026-01-01', 28, '2026-06-20');
const want = {
  '임신기 근로시간 단축 신청 가능(12주 이내)': ['2026-01-01', '2026-03-26', '지남'],
  '목덜미투명대 검사(11~14주)': ['2026-03-19', '2026-04-15', '지남'],
  '다태아 진료비 추가지원 대상 주수(20주 이상)': ['2026-05-21', null, '해당'],
  '임신당뇨병 검사(24~28주)': ['2026-06-18', '2026-07-22', '해당'],
  '임신부 Tdap 접종 권장(27~36주)': ['2026-07-09', '2026-09-16', '예정'],
  '임신기 근로시간 단축 신청 가능(32주 이후)': ['2026-08-13', null, '예정'],
  '정기 건강진단 매주(37주 이후)': ['2026-09-17', null, '예정'],
};
for (const m of r.ms) if (want[m.label]) { assert.deepStrictEqual([m.from, m.to, m.state], want[m.label], m.label); delete want[m.label]; }
assert.strictEqual(Object.keys(want).length, 0);
console.log('PASS 주요 날짜 표', r.weeks + '주 ' + r.days + '일', r.ms.length + '개 항목');
// 1년치 매일: 독립 검산과 일치
for (let i = 0; i < 1500; i++) { const l = plus('2026-01-01', i); const x = calc('lmp', l, 28, plus(l, i % 300)); assert.strictEqual(x.edd, plus(l, 280)); assert.strictEqual(x.weeks * 7 + x.days, i % 300); const y = calc('edd', x.edd, 0, plus(l, i % 300)); assert.strictEqual(y.base, l); }
console.log('PASS 2026-01-01부터 1500일 매일 예정일·주수·역계산 일치');
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'pg-date': '', 'pg-cycle': '28', 'pg-today': '' };
const out = [];
const mk = id => ({ id, value: vals[id], checked: id === 'pg-mode-lmp', style: {}, textContent: '', addEventListener() {}, set innerHTML(v) { if (id === 'pg-out') out.length = 0; }, appendChild(c) { if (id === 'pg-out') out.push(c.textContent); } });
const els = {}; ['pg-out', 'pg-table', 'pg-date-label', 'pg-cycle-row', 'pg-mode-lmp', 'pg-mode-edd', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {}, appendChild() {} }) };
eval(src);
console.log('UI 기본값(오늘-70일):', out.join(' | '));
assert.ok(out[0].startsWith('오늘 임신 주수: 10주 0일'));
