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
const N = window.eeNext, EL = window.eeElig, WR = window.eeWritten, PR = window.eePractical, X = window.eeExempt, R = window.eeRounds, P = window.eeP;
// 1) 일정 배열 = 큐넷 전기기사 페이지(evidence) 원문 순서
const strip = f => fs.readFileSync(path.join(__dirname, f), 'utf8').replace(/<script[\s\S]*?<\/script>/g, '').replace(/<!--[\s\S]*?-->/g, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
for (const f of ['qnet-1150-A0.html', 'qnet-2140-A0.html']) {
  const raw = strip(f);
  for (const r of R) {
    const i = raw.indexOf('2026년 정기 기사 ' + r[0]);
    assert.ok(i >= 0, f + ' ' + r[0] + ' 없음');
    const j = raw.indexOf('2026년 정기 기사', i + 10);
    const seg = raw.slice(i, j > 0 ? j : raw.indexOf('원서접수시간은', i));
    assert.deepStrictEqual(seg.match(/\d{4}\.\d{2}\.\d{2}/g), r.slice(1), f + ' ' + r[0]);
  }
}
console.log('PASS 3회차 14개 날짜 = evidence 원본(전기기사 1150, 전기산업기사 2140)');
// 2) 필답형 시험일 = 시행계획 공고
const plan = fs.readFileSync(path.join(__dirname, 'qnet-2026-plan.txt'), 'utf8');
assert.ok(/필답시험일\s+4\.18\(토\)\s+7\.19\(일\)\s+10\.25\(일\), 11\.7\(토\)/.test(plan));
const s1 = plan.indexOf("10. 25("), s2 = plan.indexOf("11. 7(");
const ee = plan.indexOf('전기기사', s1);
assert.ok(s1 > 0 && ee > s1 && s2 > ee, '전기기사가 10.25 목록에 있음');
assert.deepStrictEqual(P, ['2026.04.18', '2026.07.19', '2026.10.25']);
console.log('PASS 필답형 시험일 4.18 / 7.19 / 10.25(전기기사는 10.25 목록) = 시행계획 PDF');
// 3) 본문 표 = 배열
const rows = [...html.matchAll(/<tr><td>([1-3]회)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><\/tr>/g)];
assert.strictEqual(rows.length, 3);
const md = s => s.slice(5);
rows.forEach((m, k) => { const r = R[k]; assert.deepStrictEqual(m.slice(1), [r[0], md(r[1]) + '~' + md(r[2]), md(r[5]) + '~' + md(r[6]), md(r[7]), md(r[8]) + '~' + md(r[9]), md(P[k]), md(r[14])]); });
console.log('PASS 본문 일정표 3행 = 스크립트 배열');
// 4) 응시 자격
const ec = [
  ['eng', 'univ', 'none', 0, true, '제4호'],
  ['eng', 'none', 'craft', 3, true, '제2호'],
  ['eng', 'none', 'craft', 2.5, false, null],
  ['ind', 'none', 'craft', 2, true, '제1호'],
  ['eng', 'none', 'ind', 1, true, '제1호'],
  ['eng', 'none', 'ind', 0, false, null],
  ['eng', 'none', 'eng', 0, true, '제3호'],
  ['eng', 'col3', 'none', 1, true, '제5호'],
  ['eng', 'col2', 'none', 1, false, null],
  ['eng', 'col2', 'none', 2, true, '제6호'],
  ['eng', 'colpre', 'none', 0, false, null],
  ['ind', 'colpre', 'none', 0, true, '제3호'],
  ['eng', 'none', 'none', 4, true, '제9호'],
  ['ind', 'none', 'none', 2, true, '제6호'],
  ['ind', 'none', 'none', 1.5, false, null],
  ['ind', 'none', 'ind', 0, true, '제2호'],
  ['eng', 'none', 'none', '', false, null],
];
for (const [t, e, q, y, ok, cl] of ec) {
  const r = EL(t, e, q, String(y));
  assert.strictEqual(r.ok, ok, JSON.stringify([t, e, q, y]));
  if (cl) assert.ok(r.clauses.some(c => c.startsWith(cl)), cl);
  console.log('PASS 자격', JSON.stringify([t, e, q, y]), ok, r.clauses.join(' / '));
}
// 5) 필기 과락·평균
const wc = [
  [['45', '70', '65', '55', '80'], { state: 'pass', avg: 63, fails: [] }],
  [['45', '70', '65', '35', '80'], { state: 'fail', avg: 59, fails: [3] }],
  [['90', '90', '90', '90', '35'], { state: 'fail', avg: 79, fails: [4] }],
  [['40', '60', '60', '60', '80'], { state: 'pass', avg: 60, fails: [] }],
  [['50', '50', '50', '50', '50'], { state: 'fail', avg: 50, fails: [] }],
  [['', '', '', '', ''], { state: 'none' }],
  [['60', '', '60', '60', '60'], { state: 'incomplete' }],
  [['60', '101', '60', '60', '60'], { state: 'invalid' }],
  [['39.9', '100', '100', '100', '100'], { state: 'fail', avg: 87.98, fails: [0] }],
];
for (const [a, exp] of wc) { const r = WR(a); for (const k of Object.keys(exp)) assert.deepStrictEqual(r[k], exp[k], a + ' ' + k); console.log('PASS 필기', a.join(','), JSON.stringify(r)); }
assert.strictEqual(PR('60'), 'pass'); assert.strictEqual(PR('59.5'), 'fail'); assert.strictEqual(PR(''), 'none'); assert.strictEqual(PR('-1'), 'invalid');
console.log('PASS 실기 60 pass / 59.5 fail / 빈칸 none / -1 invalid');
// 6) 면제 2년
assert.strictEqual(X('2026-09-09'), '2028.09.09 (토)');
console.log('PASS 면제: 2026-09-09 -> 2028.09.09 (토)');
// 7) 다음 일정
const nc = [
  ['확인일 10-31 접수', 'reg', '2026-10-31', null],
  ['확인일 10-31 전체', 'any', '2026-10-31', { label: '2026년 3회 최종 합격자 발표', state: 'before', left: 48 }],
  ['발행일 11-22 시험', 'exam', '2026-11-22', null],
  ['발행일 11-22 전체', 'any', '2026-11-22', { label: '2026년 3회 최종 합격자 발표', state: 'before', left: 26 }],
  ['12-18 당일', 'any', '2026-12-18', { state: 'open', left: 0 }],
  ['12-19 이후', 'any', '2026-12-19', null],
  ['10-20 시험', 'exam', '2026-10-20', { label: '2026년 3회 실기 필답형 시험', start: '2026.10.25', left: 5 }],
  ['01-01 접수', 'reg', '2026-01-01', { label: '2026년 1회 필기 원서접수', left: 11 }],
  ['02-10 시험 진행 중', 'exam', '2026-02-10', { label: '2026년 1회 필기시험(CBT)', state: 'open', left: 21 }],
  ['04-01 시험', 'exam', '2026-04-01', { label: '2026년 1회 실기 필답형 시험', left: 17 }],
];
for (const [name, t, d, exp] of nc) {
  const r = N(t, d);
  if (exp === null) assert.strictEqual(r, null, name); else for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 8) UI 렌더 (최소 DOM 스텁, 기준일 2026-11-22 고정)
const RealDate = Date;
global.Date = class extends RealDate { constructor(...a) { if (a.length) super(...a); else super(2026, 10, 22, 9, 0); } static UTC(...a) { return RealDate.UTC(...a); } };
const outP = []; const els = {};
const vals = { 'ee-target': 'eng', 'ee-edu': 'none', 'ee-qual': 'craft', 'ee-exp': '3', 'ee-s1': '45', 'ee-s2': '70', 'ee-s3': '65', 'ee-s4': '35', 'ee-s5': '80', 'ee-p': '62', 'ee-pub': '2026-09-09', 'ee-date': '' };
const mk = (id) => ({ value: vals[id] || '', style: {}, addEventListener() {}, set innerHTML(x) { if (id === 'ee-out') outP.length = 0; }, appendChild(p) { if (id === 'ee-out') outP.push(p.textContent); } });
['ee-out', 'ee-today', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
global.Date = RealDate;
console.log('UI 출력(기준일 2026-11-22):\n  ' + outP.join('\n  '));
const all = outP.join('|');
assert.strictEqual(els['ee-date'].value, '2026-11-22');
assert.ok(all.includes('전기기사 응시 자격: 해당(별표 4의2 제2호 기능사 취득 후 실무 3년 이상)'));
assert.ok(all.includes('평균 59점. 불합격(과락(40점 미만) 회로이론(및 제어공학), 평균 60점 미만)'));
assert.ok(all.includes('실기: 60점 이상'));
assert.ok(all.includes('2028.09.09 (토)'));
assert.ok(all.includes('가장 가까운 일정: 2026년 3회 최종 합격자 발표 2026.12.18 (금) · D-26'));
assert.ok(all.includes('다음 접수: 공식 공고된 2026년 일정에는 남은 항목이 없다. 2027년 일정은 큐넷 시행계획 공고 전이라 확인하지 못했다.'));
console.log('ALL PASS');
