// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'[^'\n]*'/g)) if (m[0].includes('<')) throw new Error('raw < in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length, h3faq = html.split('<h2 id="faq">')[1].split('<script type')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ JSON-LD', faq, '= 본문 FAQ h3', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.iacCalc;
const cases = [
  // [이름, 평균임금, 일수, 기대값]
  ['일반: 100,000원 30일 -> 70% 70,000', 100000, 30, { daily: 70000, rule: '70', total: 2100000, band: false }],
  ['일반: 150,000원 -> 105,000', 150000, 30, { daily: 105000, total: 3150000 }],
  ['상한: 300,000원 -> 268,299 x 0.7 = 187,809', 300000, 30, { capped: true, avgUsed: 268299, daily: 187809, total: 5634270 }],
  ['상한 경계: 268,299원 그대로', 268299, 10, { capped: false, daily: 187809 }],
  ['저소득: 60,000원 -> 90% 54,000 < 최저임금액 -> 82,560', 60000, 30, { daily: 82560, rule: 'minwage', total: 2476800 }],
  ['저소득 경계: 73,386원(90%=66,047.4) -> 82,560', 73386, 30, { daily: 82560, rule: 'minwage', band: false }],
  ['확인 필요 구간 시작: 73,387원 -> 66,048 (band)', 73387, 30, { daily: 66048, rule: 'cap80', band: true, alt: 82560 }],
  ['확인 필요 구간: 80,000원 -> 66,048 (band)', 80000, 30, { daily: 66048, band: true, total: 1981440 }],
  ['확인 필요 구간 끝: 91,733원(90%=82,559.7)', 91733, 30, { daily: 66048, band: true }],
  ['91,734원(90%=82,560.6) -> 66,048, band 아님', 91734, 30, { daily: 66048, rule: 'cap80', band: false }],
  ['70% 경계: 94,354원(70%=66,047.8) -> 66,048', 94354, 30, { daily: 66048, rule: 'cap80' }],
  ['70% 경계: 94,355원(70%=66,048.5) -> 70% 66,048', 94355, 30, { daily: 66048, rule: '70' }],
  ['3일 이내 -> 0원', 100000, 3, { paid: false, total: 0 }],
  ['4일 -> 전체 일수', 100000, 4, { paid: true, total: 280000 }],
];
for (const [name, avg, off, exp] of cases) {
  const r = calc(avg, off);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값(평균임금 100,000원, 30일) 렌더 — 최소 DOM 스텁
function ui(vals) {
  const outP = [];
  const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
  const els = { 'iac-out': el('iac-out') }; Object.keys(vals).forEach(id => els[id] = el(id));
  global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
  eval(src);
  return outP.join(' | ');
}
let o = ui({ 'iac-avg': '100000', 'iac-sum': '', 'iac-days3': '92', 'iac-off': '30' });
console.log('UI 기본값 출력:', o); assert.ok(o.includes('70,000원') && o.includes('2,100,000원'));
o = ui({ 'iac-avg': '', 'iac-sum': '9000000', 'iac-days3': '92', 'iac-off': '20' });
console.log('UI 3개월 임금 900만원/92일 출력:', o); assert.ok(o.includes('97,826.08') || o.includes('97,826'));
o = ui({ 'iac-avg': '80000', 'iac-sum': '', 'iac-days3': '92', 'iac-off': '30' });
console.log('UI 확인 필요 구간 출력:', o); assert.ok(o.includes('확인하지 못했습니다') && o.includes('2,476,800원'));
console.log('ALL PASS');
