// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산 (도로교통법 제87조·부칙 제2조, 시행령 별표 6, 시행규칙 별표 28)
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if ((src.match(/'(?:[^'\\\n]|\\.)*'/g) || []).some(s => s.includes('<'))) throw new Error('< inside string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD'); JSON.parse(ld);
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const calc = window.licenseRenewCalc;
const f = t => new Date(t).toISOString().slice(0, 10);
const cases = [
  ['2종, 2016 합격 25세: 10년, 새 기간+종전 기간(~2026-12-31), 오늘 기간 안', ['2', '1990-05-20', '2016-03-10', false, '2026-10-29'],
    { cycle: 10, year: 2026, start: '2025-11-20', end: '2026-11-20', effEnd: '2026-12-31', aptitude: false, status: 'in', days: 63 }],
  ['1종, 2026 합격 31세: 2036 생일 ±6개월, 종전 기간 없음', ['1', '1995-03-10', '2026-04-01', false, '2026-10-29'],
    { cycle: 10, year: 2036, start: '2035-09-10', end: '2036-09-10', old: false, aptitude: true, status: 'before' }],
  ['1종, 갱신일 65세: 5년', ['1', '1958-08-15', '2024-03-02', false, '2026-10-29'], { age: 65, cycle: 5, year: 2029, effStart: '2029-01-01', effEnd: '2030-02-15' }],
  ['1종, 갱신일 64세: 10년', ['1', '1959-08-15', '2024-03-02', false, '2026-10-29'], { age: 64, cycle: 10 }],
  ['갱신일 75세(2019 이후): 3년', ['2', '1945-01-01', '2020-06-01', false, '2026-10-29'], { age: 75, cycle: 3, year: 2023, start: '2023-01-01', effEnd: '2023-12-31', oldOnly: true }],
  ['갱신일 75세(2019 이전): 5년', ['2', '1940-01-01', '2016-06-01', false, '2026-10-29'], { age: 76, cycle: 5, year: 2021, end: '2021-12-31' }],
  ['한쪽 눈 1종 보통: 3년', ['1', '1990-01-01', '2026-02-01', true, '2026-10-29'], { cycle: 3, year: 2029 }],
  ['한쪽 눈 체크해도 2종은 10년', ['2', '1990-01-01', '2026-02-01', true, '2026-10-29'], { cycle: 10 }],
  ['2종 70세 이상 갱신: 적성검사·3만원', ['2', '1956-04-01', '2016-04-01', false, '2026-10-29'], { ageAtBirthday: 70, aptitude: true, fine: 30000 }],
  ['2종 69세: 갱신·2만원', ['2', '1957-04-01', '2016-04-01', false, '2026-10-29'], { ageAtBirthday: 69, aptitude: false, fine: 20000, cancel: null }],
  ['1종 경과 30일: 과태료 3만원, 취소 기준일 1년 뒤', ['1', '1990-06-15', '2016-02-01', false, '2027-01-30'], { status: 'over', days: 30, fine: 30000, cancel: '2027-12-31', cancelPassed: false }],
  ['1종 1년 초과: 취소 대상', ['1', '1990-06-15', '2016-02-01', false, '2028-01-01'], { status: 'over', cancelPassed: true }],
  ['2종 경과: 2만원, 취소 없음', ['2', '1990-06-15', '2016-02-01', false, '2028-01-01'], { status: 'over', fine: 20000, cancel: null }],
  ['2월 29일생 평년: 2월 28일 처리', ['1', '1992-02-29', '2017-05-01', false, '2026-10-29'], { year: 2027, start: '2026-08-28', end: '2027-08-28' }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  assert.ok(r.ok, name + ' not ok: ' + r.msg);
  for (const k of Object.keys(exp)) {
    let v = r[k];
    if (['start', 'end', 'effStart', 'effEnd', 'cancel'].includes(k) && v !== null) v = f(v);
    assert.strictEqual(v, exp[k], name + ' ' + k + '=' + v);
  }
  console.log('PASS', name, JSON.stringify({ cycle: r.cycle, year: r.year, start: f(r.start), end: f(r.end), effStart: f(r.effStart), effEnd: f(r.effEnd), status: r.status, days: r.days, fine: r.fine }));
}
for (const [name, args] of [['2011.12.8 이전', ['1', '1970-01-01', '2010-01-01', false, '2026-10-29']], ['생년월일 없음', ['1', '', '2016-01-01', false, '2026-10-29']], ['역순', ['1', '2000-01-01', '1999-01-01', false, '2026-10-29']]]) {
  const r = calc(...args); assert.ok(!r.ok); console.log('PASS', name, '->', r.msg);
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'dl-type': '2', 'dl-birth': '1990-05-20', 'dl-base': '2016-03-10' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['dl-out', 'dl-eye', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('종전 기간도 인정'));
