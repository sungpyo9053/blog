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
const C = window.toeicCheck, P = window.toeicPick, R = window.toeicRounds;
// 1) 스크립트 일정 문자열이 공식 일정 원본(evidence)에 그대로 있는지
const raw = fs.readFileSync(path.join(__dirname, 'exam.toeic.co.kr_receipt_examSchList.php.html'), 'utf8')
  .replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
for (const x of R) {
  const i = raw.indexOf(x[0] + ' ');
  assert.ok(i >= 0, x[0] + ' 원본에 없음');
  const seg = raw.slice(i, i + 400);
  const want = `${x[0]} ${x[1]} ${x[2]} ${x[3]} ${x[4]} 정기접수 : ${x[5]} ${x[6]}~${x[7]} ${x[8]} 특별추가 : ${x[9]} ${x[10]}~${x[11]} ${x[12]}`;
  assert.ok(seg.startsWith(want), x[0] + ' 불일치\n' + seg.slice(0, want.length) + '\n' + want);
}
console.log('PASS 6회차 13개 필드 = evidence 원본 문자열');
// 2) 본문 일정표 시험일·성적발표가 배열과 같은지
const rows = [...html.matchAll(/<tr><td>(제58\d회)<\/td><td>([^<]+)<\/td><td>[^<]+<\/td><td>[^<]+<\/td><td>([^<]+)<\/td><\/tr>/g)];
assert.strictEqual(rows.length, 6);
rows.forEach((m, k) => { assert.strictEqual(m[1], R[k][0]); assert.strictEqual(m[2], R[k][1]); assert.strictEqual(m[3], R[k][3] + ' ' + R[k][4]); });
console.log('PASS 본문 표 6행 = 스크립트 배열');
// 3) 계산 결과
const cases = [
  ['발행일 11-12, 583회: 특별추가 오늘 마감', 2, '2026-11-12', { examLeft: 3, scoreLeft: 12, expire: '2028.11.15 (수)', reg: { state: 'closed' }, add: { state: 'open', left: 0 } }],
  ['발행일 11-12, 584회: 정기 마감까지 4일, 발표 26일', 3, '2026-11-12', { examLeft: 17, scoreLeft: 26, reg: { state: 'open', left: 4 }, add: { state: 'before', left: 6 } }],
  ['발행일 11-12, 586회: 정기 접수 진행 중', 5, '2026-11-12', { reg: { state: 'open', left: 32 }, scoreLeft: 55, expire: '2028.12.27 (수)' }],
  ['확인일 10-29, 586회: 정기 접수 11일 뒤 시작', 5, '2026-10-29', { reg: { state: 'before', left: 11 } }],
  ['581회 토요일, 발표 후', 0, '2026-11-12', { examLeft: -12, scoreLeft: -2, expire: '2028.10.31 (화)', reg: { state: 'closed' }, add: { state: 'closed' } }],
  ['583회 시험 당일', 2, '2026-11-15', { examLeft: 0, add: { state: 'closed' } }],
  ['585회 정기 마감 당일', 4, '2026-11-30', { reg: { state: 'open', left: 0 } }],
  ['585회 특별추가 시작 당일', 4, '2026-12-02', { reg: { state: 'closed' }, add: { state: 'open', left: 8 } }],
  ['586회 성적 발표 당일(2027)', 5, '2027-01-06', { scoreLeft: 0, expireLeft: 721 }],
];
for (const [name, i, d, exp] of cases) {
  const r = C(i, d);
  for (const k of Object.keys(exp)) {
    if (typeof exp[k] === 'object') for (const kk of Object.keys(exp[k])) assert.strictEqual(r[k][kk], exp[k][kk], name + ' ' + k + '.' + kk + '=' + r[k][kk]);
    else assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  }
  console.log('PASS', name, JSON.stringify({ examLeft: r.examLeft, reg: r.reg.state + '/' + r.reg.left, add: r.add.state + '/' + r.add.left, scoreLeft: r.scoreLeft, expire: r.expire }));
}
assert.strictEqual(P('2026-11-12'), 2); assert.strictEqual(P('2026-11-15'), 2); assert.strictEqual(P('2026-11-16'), 3);
assert.strictEqual(P('2026-10-29'), 0); assert.strictEqual(P('2027-02-01'), 5);
console.log('PASS 기본 회차 선택(기준일 이후 첫 시험, 끝나면 마지막 회차)');
// 4) UI 렌더 (최소 DOM 스텁, 기준일 2026-11-12 고정)
const RealDate = Date;
global.Date = class extends RealDate { constructor(...a) { if (a.length) super(...a); else super(2026, 10, 12, 9, 0); } static UTC(...a) { return RealDate.UTC(...a); } };
const outP = []; const els = {};
const mk = (id, v) => ({ value: v, style: {}, addEventListener() {}, set innerHTML(x) { if (id === 'tc-out') outP.length = 0; }, appendChild(p) { if (id === 'tc-out') outP.push(p.textContent); } });
['tc-out', 'tc-round', 'tc-date', 'tc-today'].forEach(id => els[id] = mk(id, ''));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
global.Date = RealDate;
console.log('UI 기본값(2026-11-12) 출력:\n  ' + outP.join('\n  '));
assert.strictEqual(els['tc-round'].value, 2);
assert.ok(outP.join().includes('특별추가 접수 마감: 2026.11.12 (목) 13:00 · 오늘 13:00 마감'));
console.log('ALL PASS');
