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
const bodyQ = (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length;
assert.strictEqual(bodyQ, faq.mainEntity.length, 'FAQ count mismatch');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.colonCalc;
function run(o) {
  const b = { mode: 'med', birth: 1974, fobt: 'pos', inst: 'clinic', area: 'dong', visit: 'first', tissue: 'none', polyps: 1, path: 1, sed: 'none', sednc: 0, chk: 0, add: 0 };
  return calc(Object.assign({}, b, o));
}
const cases = [
  ['진료 의원 초진 142,400 -> 42,700', {}, { cov: 142400, oop: 42700, pay: 42700 }],
  ['진료 의원 재진 136,930 -> 41,000', { visit: 're' }, { cov: 136930, oop: 41000 }],
  ['진료 의원 진찰료 없음 123,560 -> 37,000', { visit: 'none' }, { cov: 123560, oop: 37000 }],
  ['진료 의원 용종1+병리1 301,060 -> 90,300', { tissue: 'polyp' }, { cov: 301060, oop: 90300 }],
  ['진료 의원 용종3+병리1 = +2x46,170', { tissue: 'polyp', polyps: 3 }, { cov: 301060 + 92340, oop: 118000 }],
  ['진료 종합 초진 조직검사+병리1 182,210 -> 91,100', { inst: 'ghosp', tissue: 'biopsy' }, { cov: 182210, oop: 91100 }],
  ['진료 종합 읍면 45%', { inst: 'ghosp', area: 'eup', tissue: 'biopsy' }, { oop: 81900 }],
  ['진료 병원 동 40%: 94,490+13,810+17,500=125,800 -> 50,300', { inst: 'hosp' }, { cov: 125800, oop: 50300 }],
  ['진료 병원 읍면 35% -> 44,000', { inst: 'hosp', area: 'eup' }, { oop: 44000 }],
  ['진료 상급 초진: 21,440 + (108,300 x 60%) -> 21,440+64,900', { inst: 'tert' }, { cov: 129740, oop: 21440 + 64900 }],
  ['진료 의원 수면 급여 I: +49,350', { sed: 'EA001' }, { cov: 191750, oop: 57500 }],
  ['진료 의원 수면 비급여 80,000', { sed: 'nc', sednc: 80000 }, { oop: 42700, nc: 80000, pay: 122700 }],
  ['진료 종별가산 10%', { add: 10 }, { cov: Math.round(123560 * 1.1) + 18840 }],
  ['국가검진 용종 없음 0원', { mode: 'nat' }, { status: 'ok', cov: 0, oop: 0, pay: 0 }],
  ['국가검진 조직검사만 0원', { mode: 'nat', tissue: 'biopsy' }, { cov: 0, pay: 0 }],
  ['국가검진 의원 용종1 118,120 -> 35,400', { mode: 'nat', tissue: 'polyp' }, { cov: 118120, oop: 35400 }],
  ['국가검진 종합 용종2 144,010 -> 72,000', { mode: 'nat', inst: 'ghosp', tissue: 'polyp', polyps: 2 }, { cov: 144010, oop: 72000 }],
  ['국가검진 진찰료 선택해도 미포함', { mode: 'nat', tissue: 'polyp', visit: 'first' }, { cov: 118120 }],
  ['국가검진 수면 비급여 60,000', { mode: 'nat', sed: 'nc', sednc: 60000 }, { pay: 60000 }],
  ['국가검진 49세(1977년생) -> 대상 아님', { mode: 'nat', birth: 1977 }, { status: 'age' }],
  ['국가검진 50세(1976년생) 경계 -> 대상', { mode: 'nat', birth: 1976 }, { status: 'ok' }],
  ['국가검진 분변잠혈 안 받음 -> 검진옵션 전환', { mode: 'nat', fobt: 'none', chk: 150000 }, { status: 'nofobt', mode: 'chk', nc: 150000, pay: 150000 }],
  ['검진옵션 150,000 + 용종1 의원', { mode: 'chk', chk: 150000, tissue: 'polyp' }, { nc: 150000, oop: 35400, pay: 185400 }],
  ['검진옵션 나이 무관(30세)', { mode: 'chk', birth: 1996, chk: 100000 }, { status: 'ok', pay: 100000 }],
];
for (const [name, o, exp] of cases) {
  const r = run(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'cs-case': 'nat', 'cs-birth': '1974', 'cs-fobt': 'pos', 'cs-inst': 'clinic', 'cs-area': 'dong', 'cs-visit': 'first', 'cs-tissue': 'none', 'cs-polyps': '1', 'cs-path': '1', 'cs-sed': 'none', 'cs-sednc': '', 'cs-chk': '', 'cs-add': '0' };
const outP = [], els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['cs-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('0원(공단 전액 부담)'));
els['cs-case'].value = 'med';
eval(src);
console.log('UI 진료 출력:', outP.join(' | '));
assert.ok(outP.join().includes('42,700원'));
console.log('ALL PASS');
