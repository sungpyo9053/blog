// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const chk = window.happyHousingCheck;
const o = (x) => Object.assign({ group: 'youth', age: 29, size: 1, member: false, dual: false, kids: 0, income: 0, asset: 0, car: 0 }, x);
// 1) 공고문(2026.10.19. LH 인천부평) 가산 소득표 26개 값 재현
const table = {
  1: { 120: 4576036 },
  2: { 110: 6452897, 120: 7039524, 130: 7626151, 140: 8212778 },
  3: { 100: 8168429, 110: 8985272, 120: 9802115, 130: 10618958, 140: 11435801 },
  4: { 100: 8802202, 110: 9682422, 120: 10562642, 130: 11442863, 140: 12323083 },
  5: { 100: 9326985, 110: 10259684, 120: 11192382, 130: 12125081, 140: 13057779 },
  6: { 100: 9906263, 110: 10896889, 120: 11887516, 130: 12878142, 140: 13868768 },
};
let n = 0;
for (const size of Object.keys(table)) for (const ratio of Object.keys(table[size])) {
  // 신혼부부 경로로 비율을 맞춰 한도를 뽑는다
  const s = +size, rt = +ratio;
  let input;
  if (s === 1) input = o({ group: 'youth', size: 1 });
  else {
    const baseR = s === 2 ? 110 : 100, extra = rt - baseR;
    const dual = extra >= 20, kids = (extra - (dual ? 20 : 0)) / 10;
    input = o({ group: 'newlywed', size: s, dual, kids });
  }
  const r = chk(input);
  assert.strictEqual(r.ratio, rt, 'ratio ' + size + '/' + ratio);
  assert.strictEqual(r.incomeLimit, table[size][ratio], 'limit ' + size + '/' + ratio + '=' + r.incomeLimit);
  n++;
}
console.log('PASS 공고 소득표 ' + n + '개 값 일치');
// 2) 계층별 사례
const cases = [
  ['청년 1인 세대주, 월 350만, 자산 1.2억, 차 0', o({ income: 3500000, asset: 120000000 }), { ratio: 120, incomeLimit: 4576036, eligible: true, period: '10년' }],
  ['청년 세대원(부모와 4인 세대) -> 본인 1인 120%', o({ size: 4, member: true, income: 4576036 }), { ratio: 120, incomeLimit: 4576036, eligible: true }],
  ['청년 1인 소득 1원 초과', o({ income: 4576037 }), { incomeOk: false, eligible: false }],
  ['청년 자동차 4,542만 경계 충족', o({ car: 45420000, asset: 45420000 }), { carOk: true, eligible: true }],
  ['청년 자동차 4,543만 초과', o({ car: 45430000 }), { carOk: false, eligible: false }],
  ['청년 자산 2억 5,100만 경계', o({ asset: 251000000 }), { assetOk: true }],
  ['대학생 차 보유 -> 불가', o({ group: 'student', size: 3, car: 5000000 }), { carOk: false, eligible: false, assetLimit: 108000000 }],
  ['대학생 3인(본인+부모) 월 800만', o({ group: 'student', size: 3, income: 8000000 }), { ratio: 100, incomeLimit: 8168429, eligible: true }],
  ['신혼 맞벌이 2인 월 760만', o({ group: 'newlywed', size: 2, dual: true, income: 7600000, asset: 300000000, car: 30000000 }), { ratio: 130, incomeLimit: 7626151, eligible: true, assetLimit: 345000000 }],
  ['신혼 외벌이 3인 출산1 -> 110%, 자산 3.79억', o({ group: 'newlywed', size: 3, kids: 1 }), { ratio: 110, incomeLimit: 8985272, assetLimit: 379000000, carLimit: 49960000 }],
  ['신혼 맞벌이 4인 출산2 -> 140%', o({ group: 'newlywed', size: 4, dual: true, kids: 2 }), { ratio: 140, incomeLimit: 12323083, assetLimit: 413000000, carLimit: 54510000 }],
  ['한부모 2인 110%', o({ group: 'single', size: 2, income: 6452897 }), { ratio: 110, eligible: true }],
  ['고령자 64세 -> 나이 불충족', o({ group: 'elderly', age: 64, size: 2 }), { ageOk: false, eligible: false }],
  ['고령자 70세 1인 월 450만, 자산 3억', o({ group: 'elderly', age: 70, income: 4500000, asset: 300000000 }), { eligible: true, period: '20년', coef: '0.76' }],
  ['7인 가구 100% = 6인 + 579,278', o({ group: 'elderly', age: 70, size: 7 }), { incomeLimit: 9906263 + 579278 }],
  ['주거급여수급자: 소득·자산 요건 없음', o({ group: 'housing', income: 99999999, asset: 999999999 }), { eligible: true, period: '20년', coef: '0.60' }],
];
for (const [name, input, exp] of cases) {
  const r = chk(input);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ratio: r.ratio, incomeLimit: r.incomeLimit, eligible: r.eligible }));
}
// 3) UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'hh-group': 'youth', 'hh-age': '29', 'hh-size': '1', 'hh-kids': '0', 'hh-income': '3500000', 'hh-asset': '12000', 'hh-car': '0' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['hh-out', 'hh-member', 'hh-dual', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
assert.ok(outP.join().includes('4,576,036원'));
assert.ok(outP[0].includes('충족'));
