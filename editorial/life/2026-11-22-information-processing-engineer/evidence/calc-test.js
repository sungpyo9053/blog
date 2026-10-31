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
const N = window.ipNext, G = window.ipElig, WR = window.ipWritten, PR = window.ipPractical, X = window.ipExempt, D = window.ipDday, R = window.ipRounds, P = window.ipPractDays;
// 1) 일정 배열 = 큐넷 정보처리기사 페이지(evidence) 원문 날짜 순서
const raw = fs.readFileSync(path.join(__dirname, 'qnet-1320-B0.html'), 'utf8')
  .replace(/<script[\s\S]*?<\/script>/g, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
for (const r of R) {
  const i = raw.indexOf('2026년 정기 기사 ' + r[0]);
  assert.ok(i >= 0, r[0] + ' 원본에 없음');
  const j = raw.indexOf('2026년 정기 기사', i + 10);
  const seg = raw.slice(i, j > 0 ? j : raw.indexOf('※ 2022년도', i));
  assert.deepStrictEqual(seg.match(/\d{4}\.\d{2}\.\d{2}/g), r.slice(1), r[0] + ' 불일치');
}
console.log('PASS 3회차 14개 날짜 = evidence qnet-1320-B0 원본 순서');
// 수수료 원문
assert.ok(raw.includes('필기 실기 19,400원 22,600원')); assert.ok(html.includes('필기 19,400원, 실기 22,600원'));
console.log('PASS 수수료 19,400 / 22,600 = 원문');
// 필답형 시험일 = 시행계획 원문
const plan = fs.readFileSync(path.join(__dirname, 'qnet-2026-plan.txt'), 'utf8');
assert.ok(/필답시험일\s+4\.18\(토\)\s+7\.19\(일\)\s+10\.25\(일\), 11\.7\(토\)/.test(plan));
const s25 = plan.indexOf("10. 25("), s7 = plan.indexOf("11. 7(");
assert.ok(plan.slice(s25, s7).includes('정보처리기사') && !plan.slice(s7, s7 + 4000).includes('정보처리기사'));
assert.deepStrictEqual(P, ['2026.04.18', '2026.07.19', '2026.10.25']);
console.log('PASS 필답형 4.18·7.19·10.25, 정보처리기사는 10.25 시행 목록');
// 2) 본문 표 = 배열
const rows = [...html.matchAll(/<tr><td>([1-3]회)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><\/tr>/g)];
assert.strictEqual(rows.length, 3);
const md = s => s.slice(5);
rows.forEach((m, k) => { const r = R[k]; assert.deepStrictEqual(m.slice(1), [r[0], md(r[1]) + '~' + md(r[2]), md(r[5]) + '~' + md(r[6]), md(r[7]), md(r[8]) + '~' + md(r[9]), md(r[12]) + '~' + md(r[13]), md(r[14])]); });
console.log('PASS 본문 일정표 3행 = 스크립트 배열');
// 3) 응시자격 (별표 4의2)
const gc = [
  ['eng', 'ue', 'none', '', true, '4호'],
  ['eng', 'u', 'none', '0', true, '4호'],
  ['eng', 'c2', 'none', '1', false, null, 2],
  ['eng', 'c2', 'none', '2', true, '6호'],
  ['eng', 'uh', 'none', '2', true, '6호'],
  ['eng', 'c3', 'none', '1', true, '5호'],
  ['eng', 'c3e', 'none', '0', false, null, 4],
  ['eng', 'none', 'none', '3.5', false, null, 4],
  ['eng', 'none', 'none', '4', true, '9호'],
  ['eng', 'none', 'craft', '3', true, '2호'],
  ['eng', 'none', 'craft', '2', false, null, 3],
  ['eng', 'c2', 'craft', '1', false, null, 2],
  ['eng', 'none', 'ind', '1', true, '1호'],
  ['eng', 'none', 'ind', '0', false, null, 1],
  ['eng', 'none', 'eng', '0', true, '3호'],
  ['ind', 'c2e', 'none', '', true, '3호'],
  ['ind', 'uh', 'none', '', true, '3호'],
  ['ind', 'ue', 'none', '', true, '4호'],
  ['ind', 'none', 'craft', '1', true, '1호'],
  ['ind', 'none', 'craft', '0', false, null, 1],
  ['ind', 'none', 'none', '2', true, '6호'],
  ['ind', 'none', 'none', '1', false, null, 2],
  ['ind', 'none', 'ind', '0', true, '2호'],
  ['craft', 'none', 'none', '', true, '제한이 없다'],
];
for (const [g, e, c, x, ok, key, need] of gc) {
  const r = G(g, e, c, x); assert.strictEqual(r.ok, ok, JSON.stringify([g, e, c, x, r]));
  if (key) assert.ok(r.rule.includes(key), r.rule); if (need) assert.strictEqual(r.need, need, r.rule);
  console.log('PASS 자격', JSON.stringify([g, e, c, x]), ok ? '가능' : '불가', '|', r.rule);
}
assert.strictEqual(G('eng', 'u', 'none', '-1').ok, null); assert.strictEqual(G('eng', 'u', 'none', 'abc').ok, null);
console.log('PASS 자격 음수·문자 경력 -> 입력 오류');
// 4) 필기 판정
const wc = [
  ['e26', [80, 75, 35, 90, 85], { status: 'fail-sub', avg: 73, failed: ['데이터베이스구축'] }],
  ['e26', [60, 60, 60, 60, 60], { status: 'pass', avg: 60, failed: [] }],
  ['e26', [40, 40, 40, 100, 100], { status: 'pass', avg: 64, failed: [] }],
  ['e26', [55, 55, 60, 60, 65], { status: 'fail-avg', avg: 59, failed: [] }],
  ['e26', [39, 100, 100, 100, 100], { status: 'fail-sub', avg: 87.8, failed: ['소프트웨어설계'] }],
  ['e27', [70, 50, 65, 60, ''], { status: 'pass', avg: 61.25, failed: [] }],
  ['ind', [45, 70, 64], { status: 'pass', avg: 59.67 }],
  ['ind', [100, 100, 30], { status: 'fail-sub', avg: 76.67, failed: ['데이터베이스 활용'] }],
  ['craft', [60], { status: 'pass', avg: 60 }],
  ['craft', [59], { status: 'fail-avg', avg: 59 }],
  ['e26', ['', '', '', '', ''], { status: 'none' }],
  ['e26', [70, '', 70, 70, 70], { status: 'incomplete' }],
  ['e26', [70, 101, 70, 70, 70], { status: 'invalid' }],
];
wc[6][2].status = 'fail-avg'; wc[6][2].failed = [];
for (const [m, a, exp] of wc) { const r = WR(m, a); for (const k of Object.keys(exp)) assert.deepStrictEqual(r[k], exp[k], m + ' ' + a + ' ' + k + '=' + JSON.stringify(r[k])); console.log('PASS 필기', m, JSON.stringify(a), JSON.stringify(r)); }
assert.strictEqual(PR('60'), 'pass'); assert.strictEqual(PR(59.5), 'fail'); assert.strictEqual(PR(''), 'none'); assert.strictEqual(PR(-3), 'invalid');
console.log('PASS 실기 60점 기준');
// 5) 면제·D-day
assert.strictEqual(X('2026-09-09'), '2028.09.09 (토)');
assert.strictEqual(D('2026-12-18', '2026-11-22'), 'D-26'); assert.strictEqual(D('2026-11-22', '2026-11-22'), 'D-day'); assert.strictEqual(D('2026-10-25', '2026-11-22'), '시험일이 28일 지났다');
console.log('PASS 면제 2026-09-09 -> 2028.09.09 (토), D-day 3건');
// 6) 다음 일정
const nc = [
  ['확인일 10-31 접수', 'reg', '2026-10-31', null],
  ['확인일 10-31 시험', 'exam', '2026-10-31', null],
  ['확인일 10-31 전체', 'any', '2026-10-31', { label: '2026년 3회 최종 합격자 발표', state: 'before', left: 48 }],
  ['발행일 11-22 전체', 'any', '2026-11-22', { label: '2026년 3회 최종 합격자 발표', state: 'before', left: 26 }],
  ['12-18 당일', 'any', '2026-12-18', { label: '2026년 3회 최종 합격자 발표', state: 'open', left: 0 }],
  ['12-19 이후 없음', 'any', '2026-12-19', null],
  ['10-20 시험 -> 3회 필답형', 'exam', '2026-10-20', { label: '2026년 3회 실기(필답형) 시험', state: 'before', left: 5 }],
  ['10-19 접수 -> 실기 빈자리 마지막 날', 'reg', '2026-10-19', { label: '2026년 3회 실기 빈자리 접수', state: 'open', left: 0 }],
  ['01-01 접수', 'reg', '2026-01-01', { label: '2026년 1회 필기 원서접수', state: 'before', left: 11 }],
  ['02-10 시험 -> 1회 필기 진행 중', 'exam', '2026-02-10', { label: '2026년 1회 필기시험', state: 'open', left: 21 }],
];
for (const [name, t, d, exp] of nc) {
  const r = N(t, d);
  if (exp === null) assert.strictEqual(r, null, name); else for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 7) UI 렌더 (최소 DOM 스텁, 기준일 2026-11-22 고정)
const RealDate = Date;
global.Date = class extends RealDate { constructor(...a) { if (a.length) super(...a); else super(2026, 10, 22, 9, 0); } static UTC(...a) { return RealDate.UTC(...a); } };
const outP = []; const els = {};
const vals = { 'ip-grade': 'eng', 'ip-edu': 'c2', 'ip-cert': 'none', 'ip-exp': '1', 'ip-mode': 'e26', 'ip-s1': '80', 'ip-s2': '75', 'ip-s3': '35', 'ip-s4': '90', 'ip-s5': '85', 'ip-p': '', 'ip-pub': '2026-09-09', 'ip-my': '2026-12-18', 'ip-date': '' };
const mk = (id) => ({ value: vals[id] || '', style: {}, textContent: '', addEventListener() {}, set innerHTML(x) { if (id === 'ip-out') outP.length = 0; }, appendChild(p) { if (id === 'ip-out') outP.push(p.textContent); } });
Object.keys(vals).concat(['ip-out', 'ip-today', 'ip-r1', 'ip-r2', 'ip-r3', 'ip-r4', 'ip-r5', 'ip-l1', 'ip-l2', 'ip-l3', 'ip-l4', 'ip-l5']).forEach(id => els[id] = mk(id));
global.document = { getElementById: id => { if (!els[id]) throw new Error('no element ' + id); return els[id]; }, createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(기준일 2026-11-22, 2년제 졸업·경력 1년, 80/75/35/90/85):\n  ' + outP.join('\n  '));
assert.strictEqual(els['ip-date'].value, '2026-11-22');
assert.strictEqual(els['ip-l3'].textContent, '데이터베이스구축(과목 100점 만점)'); assert.strictEqual(els['ip-r5'].style.display, '');
const all = outP.join('|');
assert.ok(all.includes('기사 응시자격이 없다. 지금 조건에서는 실무 경력이 2년 이상'));
assert.ok(all.includes('필기: 과락 - 데이터베이스구축 과목이 40점 미만이다(평균 73점)'));
assert.ok(all.includes('2028.09.09 (토)'));
assert.ok(all.includes('내 시험일 2026.12.18 (금): D-26'));
assert.ok(all.includes('다음 접수: 공식 공고된 2026년 일정이 모두 끝났다'));
assert.ok(all.includes('가장 가까운 일정: 2026년 3회 최종 합격자 발표 2026.12.18 (금) · D-26'));
// 모드 전환: 산업기사 3과목이면 4·5행 숨김
vals['ip-mode'] = 'ind'; vals['ip-grade'] = 'ind'; Object.keys(vals).forEach(k => els[k].value = vals[k]);
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
global.Date = RealDate;
assert.strictEqual(els['ip-r4'].style.display, 'none'); assert.strictEqual(els['ip-r5'].style.display, 'none');
assert.ok(outP.join('|').includes('응시자격: 가능 - 2년제·3년제 전문대 졸업자등 또는 졸업예정자(3호)'));
assert.ok(outP.join('|').includes('필기: 과락 - 데이터베이스 활용 과목이 40점 미만이다(평균 63.33점)'));
console.log('UI 출력(산업기사 모드):\n  ' + outP.join('\n  '));
console.log('ALL PASS');
