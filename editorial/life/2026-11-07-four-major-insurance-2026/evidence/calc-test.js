// node evidence/calc-test.js — ko.html의 계산기 <script>를 그대로 추출해 실행
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
assert(!src.includes('&'), 'script must not contain &');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.fourInsuranceCalc;
const cases = [
  // [이름, 월보수, 고용안정 1/10000, 산재(업종‰*10+6), 시기, 기대값]
  ['300만 원, 150명 미만, 도소매', 3000000, 25, 86, 0, {np:142500,h:107850,l:14172,eW:27000,eE:34500,iac:25800,worker:291522,employer:324822}],
  ['700만 원, 국민연금 상한 659만 원', 7000000, 25, 86, 0, {base:6590000,np:313025}],
  ['700만 원, 2026 상반기 상한 637만 원', 7000000, 25, 86, 1, {base:6370000,np:302575}],
  ['30만 원, 국민연금 하한 41만 원', 300000, 25, 86, 0, {base:410000,np:19475,h:10785}],
  ['25만 원, 건강보험 하한(근로자 10,080원)', 250000, 25, 86, 0, {h:10080}],
  ['1억 6천만 원, 건강보험 상한(근로자 4,591,740원)', 160000000, 85, 356, 0, {base:6590000,h:4591740}],
  ['NPS 공단 예시 106만 원 → 50,350원', 1060000, 25, 86, 0, {np:50350}],
];
for (const [name, pay, s, i, half, exp] of cases) {
  const r = calc(pay, s, i, half);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], `${name}: ${k} ${r[k]} != ${exp[k]}`);
  console.log('PASS', name, JSON.stringify(r));
}
