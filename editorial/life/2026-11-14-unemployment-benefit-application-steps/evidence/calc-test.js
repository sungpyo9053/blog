// ko.html의 일정 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const plan = window.unemploymentApplyPlan;
const cases = [
  ['1350 FAQ 대기기간 예: 2022-05-01 신청', '2022-04-25', '2022-05-01', { waitEnd: '2022-05-07', payStart: '2022-05-08', first: '2022-05-15' }],
  ['1350 FAQ 신청기한 예: 2021-12-31 퇴사 -> 2022-12-31 만료', '2021-12-31', '2022-01-03', { loss: '2022-01-01', end: '2022-12-31', reportDue: '2022-02-15' }],
  ['늦은 신청: 2022-10-01 신청 -> 10-08~12-31 85일(약 3개월)', '2021-12-31', '2022-10-01', { maxDays: 85, expired: false }],
  ['말일 퇴사: 2026-10-31 -> 상실 11-01, 신고 12-15, 만료 2027-10-31', '2026-10-31', '2026-11-03', { loss: '2026-11-01', reportDue: '2026-12-15', end: '2027-10-31' }],
  ['윤년: 2024-02-28 퇴사 -> 기산 02-29, 만료 2025-02-28', '2024-02-28', '2024-03-04', { loss: '2024-02-29', end: '2025-02-28' }],
  ['윤년: 2024-02-29 퇴사 -> 기산 03-01, 만료 2025-02-28', '2024-02-29', '2024-03-04', { loss: '2024-03-01', end: '2025-02-28' }],
  ['12월 상실: 2026-12-15 퇴사 -> 신고 2027-01-15', '2026-12-15', '2026-12-20', { reportDue: '2027-01-15', end: '2027-12-15' }],
  ['기본값: 2026-11-13 퇴사, 11-20 신청', '2026-11-13', '2026-11-20', { gap: 7, waitEnd: '2026-11-26', payStart: '2026-11-27', decision: '2026-12-04', first: '2026-12-04', firstPay: '2026-12-09', end: '2027-11-13', maxDays: 352 }],
  ['만료 후 신청 -> expired', '2025-01-10', '2026-01-11', { end: '2026-01-10', expired: true, maxDays: 0 }],
  ['만료일 당일 신청 -> 대기 중 만료, 0일', '2025-01-10', '2026-01-10', { expired: false, maxDays: 0 }],
  ['퇴사일 당일 신청 -> invalid', '2026-11-13', '2026-11-13', { valid: false }],
];
for (const [name, leave, apply, exp] of cases) {
  const r = plan(leave, apply);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 2~4차 4주 간격
assert.deepStrictEqual(plan('2026-11-13', '2026-11-20').next, ['2027-01-01', '2027-01-29', '2027-02-26']);
console.log('PASS 2~4차 실업인정 4주 간격');
// UI 기본값 렌더 — 최소 DOM 스텁
const mk = (v) => ({ value: v, style: {}, checked: false, addEventListener() {}, textContent: '' });
const els = { 'ua-leave': mk('2026-11-13'), 'ua-apply': mk('2026-11-20'), 'ua-reason': mk('vol'), 'ua-extra': mk(''), 'ua-count': mk('') };
const outP = [];
els['ua-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } };
const liN = { style: { display: '' } }, liX = els['ua-extra'];
const cks = [ { checked: true, parentNode: { parentNode: liN }, addEventListener() {} }, { checked: false, parentNode: { parentNode: liX }, addEventListener() {} } ];
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }), querySelectorAll: () => cks };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
console.log('준비물 카운트(자진퇴사 선택):', els['ua-count'].textContent);
assert.ok(outP.join().includes('2027-11-13(토)'));
assert.ok(outP.join().includes('8일분'));
assert.strictEqual(els['ua-count'].textContent, '준비 완료: 1 / 2');
els['ua-reason'].value = 'inv'; eval(src);
assert.strictEqual(els['ua-count'].textContent, '준비 완료: 1 / 1');
console.log('PASS 퇴사 형태에 따라 증빙 항목 표시/숨김');
