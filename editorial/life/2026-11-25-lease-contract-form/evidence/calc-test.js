// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length, h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ JSON-LD', faq, '= FAQ h3', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.leaseContractCheck, add = window.leaseAddDays;
assert.strictEqual(add('2026-12-01', 30), '2026-12-31');
assert.strictEqual(add('2026-12-15', 30), '2027-01-14');
assert.strictEqual(add('2027-01-15', 14), '2027-01-29');
assert.strictEqual(add('2028-02-20', 14), '2028-03-05');
console.log('PASS 날짜 계산 4개(초일 불산입, 연·윤년 넘김)');
const cases = [
  ['전세 2억 시 지역 -> 신고 대상', ['day', 20000, 0, 'yes', false, '2026-12-01', '2027-01-15'], { report: true, taxNoConsent: true, reportDue: '2026-12-31' }],
  ['보증금 6천 정확히, 월세 0 -> 비대상(초과 아님)', ['day', 6000, 0, 'yes', false, '2026-12-01', ''], { report: false }],
  ['보증금 6001 -> 대상', ['day', 6001, 0, 'yes', false, '2026-12-01', ''], { report: true }],
  ['보증금 5천 + 월세 35 -> 대상(FAQ)', ['day', 5000, 35, 'yes', false, '2026-12-01', ''], { report: true }],
  ['보증금 1천 + 월세 30 -> 비대상, 동의없는 열람 불가', ['day', 1000, 30, 'yes', false, '2026-12-01', ''], { report: false, taxNoConsent: false }],
  ['보증금 1001 -> 동의없는 열람 가능', ['day', 1001, 30, 'yes', false, '2026-12-01', ''], { taxNoConsent: true }],
  ['도의 군 -> 비대상', ['day', 20000, 0, 'no', false, '2026-12-01', ''], { report: false }],
  ['금액 변동 없는 갱신 -> 비대상', ['day', 20000, 0, 'yes', true, '2026-12-01', ''], { report: false }],
  ['잔금일 -> 전입 14일', ['balance', 20000, 0, 'yes', false, '2026-12-01', '2027-01-15'], { moveDue: '2027-01-29' }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ report: r.report, taxNoConsent: r.taxNoConsent, reportDue: r.reportDue, moveDue: r.moveDue }));
}
const j = (st, ...a) => { const r = c(st, ...a); return r.todo.concat(r.docs, r.deadlines).join(' / '); };
assert.ok(j('before', 20000, 0, 'yes', false, '', '').includes('등기사항증명서'));
assert.ok(j('before', 20000, 0, 'yes', false, '', '').includes('납세증명서'));
assert.ok(j('day', 20000, 0, 'yes', false, '2026-12-01', '2027-01-15').includes('2026년 12월 31일(목)까지'));
assert.ok(j('day', 20000, 0, 'yes', false, '2026-12-01', '2027-01-15').includes('2027년 1월 15일(금)(임대차 시작일)'));
assert.ok(j('balance', 20000, 0, 'yes', false, '2026-12-01', '2027-01-15').includes('2027년 1월 29일(금)까지'));
assert.ok(j('balance', 20000, 0, 'yes', false, '2026-12-01', '2027-01-15').includes('600원'));
assert.ok(j('after', 20000, 0, 'yes', false, '2026-12-01', '2027-01-15').includes('증액분 확정일자'));
assert.ok(!j('after', 20000, 0, 'yes', false, '2026-12-01', '2027-01-15').includes('임대인 동의 없이도'));
assert.ok(j('day', 3000, 20, 'yes', false, '2026-12-01', '').includes('신고 대상이 아니다'));
console.log('PASS 단계별 안내 9개');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'lc-stage': 'before', 'lc-dep': '20000', 'lc-rent': '0', 'lc-region': 'yes', 'lc-cdate': '2026-12-01', 'lc-mdate': '2027-01-15' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['lc-out', 'lc-same', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('표준계약서'));
