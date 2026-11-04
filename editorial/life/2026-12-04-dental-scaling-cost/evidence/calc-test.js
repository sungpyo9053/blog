// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'[^'\n]*'/g)) if (m[0].includes('<')) throw new Error('< in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); console.log('JSON-LD OK, Q', faq.mainEntity.length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.scalingCalc, def = window.scalingDefaults;
function run(o) {
  const b = { inst: 'clinic', area: 'dong', age: 30, used: false, purpose: 'annual', sext: 6, visit: 'first', night: false, add: 0, nc: 0 };
  const x = Object.assign({}, b, o);
  const d = def(x.inst, x.purpose, x.night, x.visit);
  if (x.scale === undefined) x.scale = d.scale;
  if (x.exam === undefined) x.exam = d.exam;
  return calc(x);
}
const cases = [
  ['치과의원 초진 60,790 -> 18,200', {}, { status: 'cov', total: 60790, oop: 18200, payer: 42590 }],
  ['치과의원 재진 55,120 -> 16,500', { visit: 're' }, { total: 55120, oop: 16500 }],
  ['치과병원 초진 동 62,070 -> 24,800', { inst: 'dhosp' }, { total: 62070, oop: 24800 }],
  ['치과병원 재진 동 56,390 -> 22,500', { inst: 'dhosp', visit: 're' }, { total: 56390, oop: 22500 }],
  ['치과병원 초진 읍면 35% -> 21,700', { inst: 'dhosp', area: 'eup' }, { oop: 21700 }],
  ['치과의원 읍면도 30%', { area: 'eup' }, { oop: 18200 }],
  ['종합병원 진찰료 0, 36,430 x 50% -> 18,200', { inst: 'ghosp' }, { total: 36430, oop: 18200 }],
  ['종합병원 읍면 45% -> 16,300', { inst: 'ghosp', area: 'eup' }, { oop: 16300 }],
  ['야간 치과의원 초진 82,760 -> 24,800', { night: true }, { total: 82760, oop: 24800 }],
  ['진찰료 없음 43,950 -> 13,100', { visit: 'none' }, { total: 43950, oop: 13100 }],
  ['종별가산 10% 입력 -> 48,345+16,840', { add: 10 }, { total: 48345 + 16840, oop: 19500 }],
  ['18세 -> 대상 아님', { age: 18 }, { status: 'under19' }],
  ['19세 경계 -> 급여', { age: 19 }, { status: 'cov' }],
  ['이미 사용 -> 비급여, 입력가 그대로', { used: true, nc: 50000 }, { status: 'used', nc: 50000 }],
  ['미용 목적 -> 비급여', { purpose: 'cosmetic' }, { status: 'noncov', nc: 0 }],
  ['잇몸치료 6부위 진찰료 없음 59,220 -> 17,700', { purpose: 'perio', visit: 'none' }, { total: 59220, oop: 17700 }],
  ['잇몸치료는 이미 사용해도 급여', { purpose: 'perio', used: true, visit: 'none' }, { status: 'cov' }],
  ['잇몸치료는 18세도 급여(나이 조건 없음)', { purpose: 'perio', age: 18, visit: 'none' }, { status: 'cov' }],
  ['65세 치과의원 전악 -> 30%', { age: 65 }, { oop: 18200, senior: false }],
  ['65세 1부위 9,870 -> 1,500원', { age: 65, purpose: 'perio', sext: 1, visit: 'none' }, { total: 9870, oop: 1500, senior: true }],
  ['65세 1부위+재진 21,040 -> 20% 4,200', { age: 65, purpose: 'perio', sext: 1, visit: 're' }, { total: 21040, oop: 4200, senior: true }],
  ['65세 1부위 야간 14,810 -> 1,500', { age: 65, purpose: 'perio', sext: 1, visit: 'none', night: true }, { total: 14810, oop: 1500 }],
  ['65세 치과병원은 감경 없음', { age: 65, inst: 'dhosp', purpose: 'perio', sext: 1, visit: 'none' }, { oop: 3900, senior: false }],
];
for (const [name, o, exp] of cases) {
  const r = run(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'sc-inst': 'clinic', 'sc-area': 'dong', 'sc-age': '30', 'sc-used': '0', 'sc-purpose': 'annual', 'sc-sext': '6', 'sc-visit': 'first', 'sc-scale': '', 'sc-exam': '', 'sc-add': '0', 'sc-nc': '' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], style: {}, addEventListener() {} });
els['sc-night'] = { checked: false, addEventListener() {} };
els['sc-out'] = { style: {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('18,200원'));
assert.strictEqual(els['sc-scale'].value, 43950);
console.log('ALL PASS');
