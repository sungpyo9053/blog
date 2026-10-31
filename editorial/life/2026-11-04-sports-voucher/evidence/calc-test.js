// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
assert.strictEqual(JSON.parse(ld).mainEntity.length, (html.split('<h2 id="faq">')[1].match(/<h3>/g) || []).length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.sportsVoucherCheck;
const cases = [
  ['2027 경계: 2009년생 수급 -> 18세 가능', [2027, 2009, false, 'basic', false], { eligible: true, rank: '1순위', monthly: 105000, annual: 1260000 }],
  ['2027 경계: 2022년생 차상위 -> 5세 가능', [2027, 2022, false, 'near', false], { eligible: true, rank: '2순위', age: 5 }],
  ['2027 경계: 2008년생 -> 19세 불가', [2027, 2008, false, 'basic', false], { eligible: false }],
  ['2027 경계: 2023년생 -> 4세 불가', [2027, 2023, false, 'basic', false], { eligible: false }],
  ['2026 경계: 2008년생 수급 -> 가능', [2026, 2008, false, 'basic', false], { eligible: true }],
  ['2026 경계: 2021년생 가능 / 2022년생 불가', [2026, 2022, false, 'basic', false], { eligible: false }],
  ['수급 30개월 이상 -> 3순위', [2027, 2015, false, 'basic', true], { rank: '3순위' }],
  ['한부모 30개월 이상 -> 4순위', [2027, 2015, false, 'single', true], { rank: '4순위' }],
  ['범죄피해 -> 우선선정', [2027, 2015, false, 'police', true], { rank: '우선선정' }],
  ['일반가정 비장애 -> 불가', [2027, 2015, false, 'none', false], { eligible: false }],
  ['장애 5~18 저소득 -> 1순위 11만', [2027, 2015, true, 'near', false], { eligible: true, rank: '1순위', monthly: 110000, annual: 1320000 }],
  ['장애 19+ 수급 -> 2순위', [2027, 1990, true, 'basic', false], { rank: '2순위' }],
  ['장애 19+ 한부모 -> 3순위', [2027, 1990, true, 'single', false], { rank: '3순위' }],
  ['장애 5~18 비저소득 -> 4순위', [2027, 2015, true, 'none', false], { rank: '4순위' }],
  ['장애 19+ 비저소득 -> 5순위', [2027, 1980, true, 'none', false], { rank: '5순위' }],
  ['장애 2027 경계 1958년생 69세 가능', [2027, 1958, true, 'none', false], { eligible: true, age: 69 }],
  ['장애 2027 경계 1957년생 70세 불가', [2027, 1957, true, 'none', false], { eligible: false }],
  ['장애 2026 경계 1957년생 가능', [2026, 1957, true, 'none', false], { eligible: true }],
];
assert.strictEqual(c(2026, 2021, false, 'basic', false).eligible, true);
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.ok(window.sportsVoucherYears[2027].apply.includes('11월 9일'));
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'sv-year': '2027', 'sv-birth': '2015', 'sv-dis': 'no', 'sv-inc': 'basic', 'sv-long': 'no' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['sv-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('105,000원'));
