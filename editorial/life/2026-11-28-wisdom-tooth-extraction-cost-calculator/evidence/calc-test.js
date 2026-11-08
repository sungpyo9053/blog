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
const calc = window.wtCalc, exam = window.wtExam;
function run(o) {
  const x = Object.assign({ type: 'imp3', n: 1, inst: 'clinic', area: 'dong', age: 25, pano: true, ct: false, second: false, visit: 'first', add: 0 }, o);
  if (x.exam === undefined) x.exam = exam(x.inst, x.visit);
  return calc(x);
}
const cases = [
  ['치과의원 구치1 재진 촬영없음 22,310 -> 6,600', { type: 'post', visit: 're', pano: false }, { total: 22310, oop: 6600 }],
  ['치과의원 완전매복1 초진 파노라마 121,600 -> 36,400', {}, { total: 121600, oop: 36400, payer: 85200 }],
  ['치과의원 완전매복1 +CT 180,510 -> 54,100', { ct: true }, { total: 180510, oop: 54100 }],
  ['치과의원 완전매복2 211,300 -> 63,300', { n: 2 }, { total: 211300, oop: 63300 }],
  ['치과의원 완전매복2 제2의수술 166,450 -> 49,900', { n: 2, second: true }, { total: 166450, oop: 49900 }],
  ['치과병원 동 완전매복1 파노라마+CT 181,790 -> 72,700', { inst: 'dhosp', ct: true }, { total: 181790, oop: 72700 }],
  ['치과병원 읍면 35%', { inst: 'dhosp', area: 'eup', ct: true }, { oop: 63600 }],
  ['종합병원 동 복잡매복1 파노라마 67,650 -> 33,800', { inst: 'ghosp', type: 'imp2' }, { total: 67650, oop: 33800 }],
  ['종합병원 읍면 45% -> 30,400', { inst: 'ghosp', type: 'imp2', area: 'eup' }, { oop: 30400 }],
  ['상급종합 완전매복1 파노라마+CT 160,690 -> 96,400', { inst: 'thosp', ct: true }, { total: 160690, oop: 96400 }],
  ['상급종합 진찰료 10,000 전액 + 나머지 60%', { inst: 'thosp', ct: true, exam: 10000 }, { total: 170690, oop: 10000 + 96400 }],
  ['상급종합 구치는 가산코드 없음 9,230', { inst: 'thosp', type: 'post', pano: false }, { ext: 9230, oop: 5500 }],
  ['상급종합 완전매복2 제2의수술 96,660+67,660', { inst: 'thosp', n: 2, second: true, pano: false }, { ext: 164320 }],
  ['종합병원 완전매복2 제2의수술 74,350+52,050', { inst: 'ghosp', n: 2, second: true, pano: false }, { ext: 126400 }],
  ['개수 상한 4', { n: 9, pano: false, visit: 'none' }, { n: 4, ext: 358800 }],
  ['종별가산 10%', { pano: false, visit: 'none', add: 10 }, { ext: 98670, oop: 29600 }],
  ['65세 치과의원 구치1 재진 22,310 -> 20% 4,400', { type: 'post', visit: 're', pano: false, age: 65 }, { oop: 4400, senior: true }],
  ['65세 치과의원 전치1 재진 17,960 -> 10% 1,700', { type: 'ant', visit: 're', pano: false, age: 65 }, { total: 17960, oop: 1700, senior: true }],
  ['65세 치과의원 구치1 진찰료없음 11,140 -> 1,500', { type: 'post', visit: 'none', pano: false, age: 65 }, { oop: 1500, senior: true }],
  ['65세 매복은 30%', { age: 65 }, { oop: 36400, senior: false }],
  ['65세 치과병원은 감경 없음', { inst: 'dhosp', type: 'post', visit: 'none', pano: false, age: 65 }, { oop: 4400, senior: false }],
];
for (const [name, o, exp] of cases) {
  const r = run(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 상대가치점수 x 환산지수 검산 (10원 단위 반올림)
const pts = { U4412: [67.15, 6790, 5630], U4413: [110.17, 11140, 9230], U4414: [240.73, 24340, 20170], U4415: [363.23, 36720, 30440], U4416: [645.29, 65240, 54080], U4417: [887.27, 89700, 74350] };
for (const [c, [p, d, h]] of Object.entries(pts)) {
  assert.strictEqual(Math.round(p * 101.1 / 10) * 10, d, c + ' 치과');
  assert.strictEqual(Math.round(p * 83.8 / 10) * 10, h, c + ' 병원');
}
console.log('PASS 점수 x 환산지수(치과 101.1, 병원 83.8) = 공단 단가');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'wt-type': 'imp3', 'wt-n': '1', 'wt-inst': 'clinic', 'wt-area': 'dong', 'wt-age': '25', 'wt-visit': 'first', 'wt-exam': '', 'wt-add': '0' };
const outP = [], els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], style: {}, addEventListener() {} });
els['wt-pano'] = { checked: true, addEventListener() {} };
els['wt-ct'] = { checked: false, addEventListener() {} };
els['wt-second'] = { checked: false, addEventListener() {} };
els['wt-out'] = { style: {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('36,400원'));
assert.strictEqual(els['wt-exam'].value, 16840);
console.log('ALL PASS');
