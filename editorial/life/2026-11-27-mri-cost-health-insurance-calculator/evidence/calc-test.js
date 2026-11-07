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
const calc = window.mriCalc;
function run(o) {
  const b = { part: 'lspine', cov: 'cov', inst: 'clinic', area: 'dong', adm: 'out', tesla: 't15', read: 'rad', pt: 'gen', ncp: 0 };
  return calc(Object.assign({}, b, o));
}
const cases = [
  ['허리 의원 222,110+115,380=337,490 x30% -> 101,200', {}, { total: 337490, rate: 30, oop: 101200 }],
  ['허리 병원 동 295,840 x40% -> 118,300', { inst: 'hosp' }, { total: 295840, oop: 118300 }],
  ['허리 병원 읍면 35% -> 103,500', { inst: 'hosp', area: 'eup' }, { rate: 35, oop: 103500 }],
  ['허리 종합 50% -> 147,900', { inst: 'ghosp' }, { oop: 147900 }],
  ['허리 종합 읍면 45% -> 133,100', { inst: 'ghosp', area: 'eup' }, { oop: 133100 }],
  ['허리 상급 60% -> 177,500', { inst: 'tert' }, { rate: 60, oop: 177500 }],
  ['목 = 허리 단가', { part: 'cspine', inst: 'ghosp' }, { total: 295840, oop: 147900 }],
  ['허리 의원 3T 242,310+115,380', { tesla: 't3' }, { total: 357690, oop: 107300 }],
  ['허리 의원 0.5T 미만 181,730+115,380', { tesla: 'tl' }, { total: 297110 }],
  ['허리 의원 일반판독 222,110+86,540', { read: 'gen' }, { total: 308650, oop: 92500 }],
  ['뇌 의원 215,960+112,190=328,150 -> 98,400', { part: 'brain' }, { total: 328150, oop: 98400 }],
  ['뇌 병원 287,650 -> 115,000', { part: 'brain', inst: 'hosp' }, { total: 287650, oop: 115000 }],
  ['뇌 종합 -> 143,800', { part: 'brain', inst: 'ghosp' }, { oop: 143800 }],
  ['뇌 상급 -> 172,500', { part: 'brain', inst: 'tert' }, { oop: 172500 }],
  ['뇌 상급 3T 206,520+98,340=304,860 -> 182,900', { part: 'brain', inst: 'tert', tesla: 't3' }, { total: 304860, oop: 182900 }],
  ['무릎 의원 303,960 -> 91,100', { part: 'knee' }, { total: 303960, oop: 91100 }],
  ['무릎 병원 266,440 -> 106,500', { part: 'knee', inst: 'hosp' }, { oop: 106500 }],
  ['무릎 종합 -> 133,200', { part: 'knee', inst: 'ghosp' }, { oop: 133200 }],
  ['무릎 상급 -> 159,800', { part: 'knee', inst: 'tert' }, { oop: 159800 }],
  ['무릎 테슬라 무시', { part: 'knee', tesla: 't3' }, { total: 303960 }],
  ['어깨 일반판독 276,330', { part: 'shoulder', read: 'gen' }, { total: 276330, oop: 82800 }],
  ['허리 종합 80% -> 236,600', { inst: 'ghosp', cov: 'sel' }, { rate: 80, oop: 236600 }],
  ['허리 종합 입원 50%, 100원 미만 부담 147,920', { inst: 'ghosp', adm: 'in' }, { rate: 50, oop: 147920 }],
  ['허리 의원 입원 30% 101,247', { adm: 'in' }, { oop: 101247 }],
  ['산정특례 중증 5% 종합 -> 14,700', { inst: 'ghosp', pt: 'sev' }, { rate: 5, oop: 14700 }],
  ['산정특례 희귀 10% 상급 -> 29,500', { inst: 'tert', pt: 'rare' }, { rate: 10, oop: 29500 }],
  ['비급여 600,000', { cov: 'nc', ncp: 600000 }, { status: 'nc', pay: 600000, oop: 0 }],
  ['비급여 금액 미입력', { cov: 'nc' }, { status: 'nc', pay: 0 }],
];
for (const [name, o, exp] of cases) {
  const r = run(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'mr-part': 'lspine', 'mr-cov': 'cov', 'mr-inst': 'clinic', 'mr-area': 'dong', 'mr-adm': 'out', 'mr-tesla': 't15', 'mr-read': 'rad', 'mr-pt': 'gen', 'mr-ncp': '' };
const outP = [], els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['mr-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('101,200원'));
els['mr-cov'].value = 'nc'; els['mr-ncp'].value = '550000';
eval(src);
console.log('UI 비급여 출력:', outP.join(' | '));
assert.ok(outP.join().includes('550,000원'));
els['mr-cov'].value = 'cov'; els['mr-inst'].value = 'tert'; els['mr-part'].value = 'knee'; els['mr-adm'].value = 'in';
eval(src);
console.log('UI 상급 무릎 입원 출력:', outP.join(' | '));
assert.ok(outP.join().includes('159,864원'));
console.log('ALL PASS');
