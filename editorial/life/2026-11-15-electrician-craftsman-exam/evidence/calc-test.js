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
const N = window.ecNext, J = window.ecJudge, X = window.ecExempt, R = window.ecRounds;
// 1) 스크립트 일정이 큐넷 전기기능사 페이지(evidence) 원문 순서와 같은지
const raw = fs.readFileSync(path.join(__dirname, 'qnet-7780-A0.html'), 'utf8')
  .replace(/<script[\s\S]*?<\/script>/g, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
for (const r of R) {
  const i = raw.indexOf('2026년 정기 기능사 ' + r[0]);
  assert.ok(i >= 0, r[0] + ' 원본에 없음');
  const seg = raw.slice(i, raw.indexOf('2026년 정기 기능사', i + 10) > 0 ? raw.indexOf('2026년 정기 기능사', i + 10) : i + 600);
  const dates = seg.match(/\d{4}\.\d{2}\.\d{2}/g).filter((d, k, a) => !(k > 0 && d === a[k - 1] && false));
  assert.deepStrictEqual(dates, r.slice(1), r[0] + ' 불일치 ' + dates.join(','));
}
console.log('PASS 4회차 14개 날짜 = evidence 원본 순서');
// 2) 본문 일정표가 배열과 같은지
const rows = [...html.matchAll(/<tr><td>([1-4]회)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><td>([^<]+)<\/td><\/tr>/g)];
assert.strictEqual(rows.length, 4);
const md = s => s.slice(5);
rows.forEach((m, k) => { const r = R[k]; assert.deepStrictEqual(m.slice(1), [r[0], md(r[1]) + '~' + md(r[2]), md(r[5]) + '~' + md(r[6]), md(r[7]), md(r[8]) + '~' + md(r[9]), md(r[12]) + '~' + md(r[13]), md(r[14])]); });
console.log('PASS 본문 표 4행 = 스크립트 배열');
// 3) 합격 판정
const jc = [
  [72, 58, { written: 'pass', practical: 'fail', final: 'none' }],
  [60, 60, { written: 'pass', practical: 'pass', final: 'pass' }],
  [59.99, 90, { written: 'fail', practical: 'pass', final: 'none' }],
  ['', '', { written: 'none', practical: 'none', final: 'none' }],
  ['100', '', { written: 'pass', practical: 'none', final: 'none' }],
  [101, -1, { written: 'invalid', practical: 'invalid', final: 'none' }],
  ['abc', 0, { written: 'invalid', practical: 'fail', final: 'none' }],
];
for (const [w, p, exp] of jc) { assert.deepStrictEqual(J(w, p), exp); console.log('PASS 판정', JSON.stringify([w, p]), JSON.stringify(exp)); }
// 4) 면제 2년
assert.strictEqual(X('2026-10-07'), '2028.10.07 (토)');
assert.strictEqual(X('2026.01.30'), '2028.01.30 (일)');
console.log('PASS 면제 2년: 2026-10-07 -> 2028.10.07 (토)');
// 5) 다음 접수/시험
const nc = [
  ['확인일 10-29 접수', 'reg', '2026-10-29', { label: '2026년 4회 실기 빈자리 접수', state: 'before', left: 10 }],
  ['확인일 10-29 시험', 'exam', '2026-10-29', { label: '2026년 4회 실기시험', state: 'before', left: 16 }],
  ['발행일 11-15 시험', 'exam', '2026-11-15', { label: '2026년 4회 실기시험', state: 'open', left: 17 }],
  ['발행일 11-15 접수', 'reg', '2026-11-15', null],
  ['발행일 11-15 전체', 'any', '2026-11-15', { label: '2026년 4회 실기시험', state: 'open', left: 17 }],
  ['12-03 전체 -> 발표', 'any', '2026-12-03', { label: '2026년 4회 최종 합격자 발표', state: 'before', left: 8 }],
  ['12-11 발표 당일', 'any', '2026-12-11', { label: '2026년 4회 최종 합격자 발표', state: 'open', left: 0 }],
  ['12-12 이후 없음', 'any', '2026-12-12', null],
  ['01-01 접수', 'reg', '2026-01-01', { label: '2026년 1회 필기 원서접수', state: 'before', left: 5 }],
  ['03-17 겹침: 2회 필기 접수 진행 중', 'reg', '2026-03-17', { label: '2026년 2회 필기 원서접수', state: 'open', left: 3 }],
  ['03-17 시험: 1회 실기 진행 중', 'exam', '2026-03-17', { label: '2026년 1회 실기시험', state: 'open', left: 19 }],
];
for (const [name, t, d, exp] of nc) {
  const r = N(t, d);
  if (exp === null) assert.strictEqual(r, null, name); else for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 6) UI 렌더 (최소 DOM 스텁, 기준일 2026-10-29 고정, 필기 72·실기 58·발표 2026-10-07)
const RealDate = Date;
global.Date = class extends RealDate { constructor(...a) { if (a.length) super(...a); else super(2026, 9, 29, 9, 0); } static UTC(...a) { return RealDate.UTC(...a); } };
const outP = []; const els = {};
const vals = { 'ec-w': '72', 'ec-p': '58', 'ec-pub': '2026-10-07', 'ec-date': '' };
const mk = (id) => ({ value: vals[id] || '', style: {}, addEventListener() {}, set innerHTML(x) { if (id === 'ec-out') outP.length = 0; }, appendChild(p) { if (id === 'ec-out') outP.push(p.textContent); } });
['ec-out', 'ec-w', 'ec-p', 'ec-pub', 'ec-date', 'ec-today'].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
global.Date = RealDate;
console.log('UI 출력(기준일 2026-10-29):\n  ' + outP.join('\n  '));
assert.strictEqual(els['ec-date'].value, '2026-10-29');
const all = outP.join('|');
assert.ok(all.includes('필기: 합격 기준(60점 이상) 충족'));
assert.ok(all.includes('실기: 60점 미만, 불합격'));
assert.ok(all.includes('2028.10.07 (토)'));
assert.ok(all.includes('다음 접수: 2026년 4회 실기 빈자리 접수 2026.11.08 (일) ~ 2026.11.09 (월) · D-10'));
assert.ok(all.includes('다음 시험: 2026년 4회 실기시험 2026.11.14 (토) ~ 2026.12.02 (수) · D-16'));
console.log('ALL PASS');
