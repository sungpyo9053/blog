// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('< in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
assert.ok(!/[&<]/.test(ld)); const faq = JSON.parse(ld);
assert.strictEqual(faq.mainEntity.length, (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length);
console.log('PASS JSON-LD 파싱, FAQ', faq.mainEntity.length, '개 = 본문 h3 수');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const J = window.reJudge, N = window.reNext, E = window.reEvents;
// 1) 일정 배열이 큐넷 메인/공고문 원문에 있는지
const main = fs.readFileSync(path.join(__dirname, 'qnet-junggae-main.html'), 'utf8').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
for (const s of ['접수기간 2026.08.03 ~ 2026.08.07', '빈자리 추가접수 기간 2026.10.01 ~ 2026.10.02', '시험일정 2026.10.31 ~ 2026.10.31', '가답안발표기간 2026.10.31 ~ 2026.11.06', '합격자발표기간 2026.12.02 ~ 2027.01.31']) assert.ok(main.includes(s), s);
const plan = fs.readFileSync(path.join(__dirname, 'qnet-plan37.txt'), 'utf8');
for (const s of ["’27. 8. 2. ~ 8. 6. 예정", "’27. 10. 30. 예정", '13,700원', '14,300원', '28,000원', '매 과목 40점 이상, 전 과목 평균 60점']) assert.ok(plan.includes(s), s);
console.log('PASS 일정·수수료·기준 문자열 = evidence 원문');
// 2) 합격 판정
const jc = [
  ['1차 55·70 합격', ['55', '70'], ['', '', ''], false, { first: 'pass', second: 'none', final: 'none' }],
  ['1차 39·90 과락', ['39', '90'], ['', '', ''], false, { first: 'fail', second: 'none', final: 'fail' }],
  ['1차 50·60 평균55', ['50', '60'], ['', '', ''], false, { first: 'fail', second: 'none', final: 'fail' }],
  ['경계 40·80 평균60', ['40', '80'], ['', '', ''], false, { first: 'pass' }],
  ['2차 80·38·70 과락', ['60', '60'], ['80', '38', '70'], false, { first: 'pass', second: 'fail', final: 'fail' }],
  ['최종 합격', ['60', '60'], ['60', '60', '60'], false, { first: 'pass', second: 'pass', final: 'pass' }],
  ['1차 불합격+2차 기준 충족 -> 무효', ['30', '90'], ['70', '70', '70'], false, { first: 'fail', second: 'pass', final: 'void' }],
  ['1차 면제+2차 합격', ['', ''], ['50', '70', '60'], true, { first: 'exempt', second: 'pass', final: 'pass' }],
  ['범위 밖', ['101', '50'], ['', '', ''], false, { first: 'invalid' }],
  ['문자', ['abc', '50'], ['', '', ''], false, { first: 'invalid' }],
];
for (const [name, a, b, ex, exp] of jc) {
  const r = J(a, b, ex);
  if (exp.first) assert.strictEqual(r.first.state, exp.first, name + ' first');
  if (exp.second) assert.strictEqual(r.second.state, exp.second, name + ' second');
  if (exp.final) assert.strictEqual(r.final, exp.final, name + ' final');
  console.log('PASS', name, JSON.stringify(r));
}
assert.strictEqual(J(['50', '60'], ['', '', ''], false).first.need, 10);
assert.strictEqual(J(['60', '60'], ['80', '38', '70'], false).second.avg, 62.67);
console.log('PASS 부족 점수 10점, 2차 평균 62.67');
// 3) 다음 일정
const nc = [
  ['10-30 접수', 'reg', '2026-10-30', { label: '제38회 원서접수(예정)', left: 276 }],
  ['10-30 시험', 'exam', '2026-10-30', { label: '제37회 1·2차 시험', state: 'before', left: 1 }],
  ['11-17 전체 -> 발표', 'any', '2026-11-17', { label: '제37회 합격자 발표', state: 'before', left: 15 }],
  ['11-17 시험', 'exam', '2026-11-17', { label: '제38회 1·2차 시험(예정)', left: 347 }],
  ['11-03 가답안 진행 중', 'any', '2026-11-03', { label: '제37회 가답안 공개·의견제시', state: 'open', left: 3 }],
  ['2027-08-04 접수 진행', 'reg', '2027-08-04', { state: 'open', left: 2 }],
  ['2027-10-31 이후 없음', 'any', '2027-10-31', null],
];
for (const [name, t, d, exp] of nc) {
  const r = N(t, d);
  if (exp === null) assert.strictEqual(r, null, name); else for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 4) UI 렌더 (기준일 2026-11-17 고정, 본문 예시 점수)
const RealDate = Date;
global.Date = class extends RealDate { constructor(...a) { if (a.length) super(...a); else super(2026, 10, 17, 9, 0); } static UTC(...a) { return RealDate.UTC(...a); } };
const outP = []; const els = {};
const vals = { 're-a1': '55', 're-a2': '70', 're-b1': '80', 're-b2': '38', 're-b3': '70', 're-date': '' };
const mk = (id) => ({ value: vals[id] || '', checked: false, disabled: false, style: {}, addEventListener() {}, set innerHTML(x) { if (id === 're-out') outP.length = 0; }, appendChild(p) { if (id === 're-out') outP.push(p.textContent); } });
['re-out', 're-ex', 're-today', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
global.Date = RealDate;
console.log('UI 출력(기준일 2026-11-17):\n  ' + outP.join('\n  '));
const all = outP.join('|');
assert.ok(all.includes('1차: 평균 62.5점, 모든 과목 40점 이상이라 합격 기준 충족'));
assert.ok(all.includes('부동산공법 40점 미만(과락)'));
assert.ok(all.includes('제37회 합격자 발표 2026.12.02 (수) · D-15'));
console.log('ALL PASS');
