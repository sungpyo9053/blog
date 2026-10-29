// ko.html의 점검기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const ev = window.employmentContractCheck;
const ALL = ['wage1','wage2','wage3','hours','rest','holiday','leave','place','term','days','family','consent','give'];
const without = (...ids) => ALL.filter(x => !ids.includes(x));
const cases = [
  ['정규직 전부 있음', 'regular', false, ALL, { missing: 0, criminal: false, fine1: 0 }],
  ['정규직 연차 누락 -> 벌금 대상, 과태료 없음', 'regular', false, without('leave'), { missing: 1, criminal: true, fine1: 0 }],
  ['정규직 필수 항목 수 9', 'regular', false, [], { required: 9 }],
  ['알바 계약기간+요일별 누락 -> 1호50+6호50=100', 'part', false, without('term','days'), { missing: 2, criminal: false, fine1: 100, fine2: 200, fine3: 400, capped: false }],
  ['알바 휴게+근로시간 누락 -> 같은 2호 1번만 30', 'part', false, without('rest','hours'), { fine1: 30, criminal: true }],
  ['알바 4인 이하: 요일별·근로시간·연차 누락 -> 0', 'part', true, without('days','hours','leave'), { fine1: 0, criminal: true }],
  ['알바 4인 이하: 휴게 누락 -> 2호 30', 'part', true, without('rest'), { fine1: 30 }],
  ['기간제 전부 누락 -> 1+2+3+4+5호 = 50+30+50+30+30 = 190', 'fixed', false, [], { fine1: 190, fine2: 380, fine3: 500, capped: true }],
  ['단시간 전부 누락 -> 190+50 = 240', 'part', false, [], { fine1: 240, fine2: 480, fine3: 500 }],
  ['연소 동의서 누락 -> 과태료 플래그, 벌금 아님', 'minor', false, without('consent'), { missing: 1, family: true, criminal: false, fine1: 0 }],
  ['연소 교부 누락 -> 벌금 대상', 'minor', false, without('give'), { criminal: true }],
  ['건설일용 계약기간 누락 -> 50', 'daily', false, without('term'), { fine1: 50, criminal: false }],
];
for (const [name, type, small, have, exp] of cases) {
  const r = ev(type, small, have);
  const got = { ...r, missing: r.missing.length, required: r.required.length };
  for (const k of Object.keys(exp)) assert.strictEqual(got[k], exp[k], name + ' ' + k + '=' + got[k]);
  console.log('PASS', name, JSON.stringify({ form: r.form, missing: r.missing, hos: r.hos, fine1: r.fine1, criminal: r.criminal, family: r.family }));
}
// UI 렌더 확인 — 최소 DOM 스텁 (기본값: 단시간, 아무것도 체크 안 함)
const outP = []; let boxKids = [];
const mk = (id, v) => ({ id, value: v, checked: false, style: {}, addEventListener() {}, set innerHTML(x) { if (id === 'ec-out') outP.length = 0; if (id === 'ec-items') boxKids = []; }, appendChild(p) { if (id === 'ec-out') outP.push(p.textContent); else boxKids.push(p); } });
const els = { 'ec-type': mk('ec-type', 'part'), 'ec-small': mk('ec-small'), 'ec-items': mk('ec-items'), 'ec-out': mk('ec-out') };
global.document = {
  getElementById: id => els[id],
  createElement: () => ({ style: {}, appendChild() {}, addEventListener() {} }),
  createTextNode: t => t,
  querySelectorAll: () => [],
};
eval(src);
console.log('UI 기본 출력:', outP.join(' | '));
assert.ok(outP[0].includes('단시간근로자 표준근로계약서'));
assert.ok(outP.join().includes('1차 240만원, 2차 480만원, 3차 이상 500만원'));
assert.strictEqual(boxKids.length, 11);
console.log('PASS UI 체크박스 11개, 기본 경고 렌더');
