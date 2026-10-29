// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('< inside string literal');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.healthCheck2026;
const names = r => r.cancers.map(x => x.name + ':' + x.pay).join(',');
const cases = [
  ['1980 여 사무직 10/31', [1980, 'office', 'F', '2026-10-31', {}], { age: 46, generalOk: true, daysLeft: 61, carry: false }, '위암:10,유방암:10,자궁경부암:0'],
  ['1981 남 사무직 -> 대상 아님, 추가등록 안내', [1981, 'office', 'M', '2026-10-31', {}], { age: 45, generalOk: false, carry: true }, ''],
  ['1981 남 비사무직 -> 매년', [1981, 'nonoffice', 'M', '2026-10-31', {}], { generalOk: true, carry: false }, ''],
  ['1976 남 지역세대주 50세 -> 위·대장', [1976, 'head', 'M', '2026-01-01', {}], { age: 50, generalOk: true, daysLeft: 364 }, '위암:10,대장암:0'],
  ['2006 여 피부양자 20세', [2006, 'dependent', 'F', '2026-12-31', {}], { age: 20, generalOk: true, daysLeft: 0 }, '자궁경부암:0'],
  ['2008 피부양자 18세 -> 아님', [2008, 'dependent', 'F', '2026-10-31', {}], { generalOk: false, carry: false }, ''],
  ['2008 지역세대주 18세 -> 대상(세대주는 나이 무관)', [2008, 'head', 'M', '2026-10-31', {}], { generalOk: true }, ''],
  ['1962 의료급여 64세', [1962, 'medicaid', 'F', '2026-10-31', {}], { age: 64, generalOk: true }, '위암:0,대장암:0,유방암:0,자궁경부암:0'],
  ['1961 의료급여 65세(홀수년) -> 일반 아님, 2025 미수검 추가등록 안내', [1961, 'medicaid', 'M', '2026-10-31', {}], { age: 65, generalOk: false, carry: true }, '대장암:0'],
  ['1960 의료급여 66세 -> 생애전환기', [1960, 'medicaid', 'M', '2026-10-31', {}], { age: 66, generalOk: true }, '위암:0,대장암:0'],
  ['1970 남 하위50% 간암 고위험', [1970, 'office', 'M', '2026-10-31', { low: true, liver: true }], { age: 56 }, '위암:0,대장암:0,간암:0'],
  ['1972 남 폐암 고위험 54세', [1972, 'head', 'M', '2026-10-31', { lung: true }], { age: 54 }, '위암:10,대장암:0,폐암:10'],
  ['1952 폐암 고위험 74세', [1952, 'head', 'M', '2026-10-31', { lung: true }], { age: 74 }, '위암:10,대장암:0,폐암:10'],
  ['1950 폐암 고위험 76세 -> 폐암 없음', [1950, 'head', 'M', '2026-10-31', { lung: true }], { age: 76 }, '위암:10,대장암:0'],
  ['1974 폐암 고위험 52세 -> 폐암 없음', [1974, 'head', 'M', '2026-10-31', { lung: true }], { age: 52 }, '위암:10,대장암:0'],
  ['1977 여 홀수년 49세 간암 -> 간암만(6개월 주기)', [1977, 'office', 'F', '2026-10-31', { liver: true }], { generalOk: false }, '간암:10'],
  ['2027 기준 홀수년생 대상', [1981, 'office', 'M', '2027-12-30', {}], { year: 2027, generalOk: true, daysLeft: 1 }, '위암:10'],
];
for (const [name, args, exp, cn] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  assert.strictEqual(names(r), cn, name + ' cancers=' + names(r));
  console.log('PASS', name, '|', r.general, '|', names(r) || '-', '| D-' + r.daysLeft);
}
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'hc-year': '1980', 'hc-sex': 'F', 'hc-type': 'office', 'hc-date': '2026-10-31' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['hc-out', 'hc-low', 'hc-liver', 'hc-lung', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
const RealDate = Date; global.Date = class extends RealDate { constructor(...a) { if (a.length) super(...a); else super('2026-10-31T09:00:00+09:00'); } static UTC(...a) { return RealDate.UTC(...a); } };
eval(src);
console.log('UI 출력:', outP.join(' | '));
assert.ok(outP.join().includes('61일 남음'));
assert.ok(outP.join().includes('본인부담 10%'));
console.log('PASS UI');
