// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.vetFeeCalc, D = window.vetFeeData;
// 공개 시스템 JSON 원본과 대조
const raw = JSON.parse(fs.readFileSync(path.join(__dirname, 'animalclinicfee-searchTotalPrice-2025.json'), 'utf8').split('\n')[1]);
let n = 0;
const K = ['first5','first10','first20','re5','re10','re20','consult','hosp5','hosp10','hosp20','hospcat','dhppl','catvac','rabies','kennel','corona','flu','heart','ext','deworm','cbc','xray5'];
for (const s of Object.keys(D)) K.forEach((k, i) => { if (raw[s][k]) { assert.deepStrictEqual(D[s][i], raw[s][k], s + k); n++; } });
console.log('PASS 공개 시스템 JSON과 일치', n, '값');
// 보도자료(2025.12.22.) 전국 값과 대조
const pr = { first5: 9873, re5: 7931, consult: 10283, hosp5: 51468, hospcat: 56417, dhppl: 26337, catvac: 39478, rabies: 24803, kennel: 22666, corona: 22266, flu: 34931, heart: 16542, ext: 18927, deworm: 3960, cbc: 35973 };
for (const k in pr) assert.strictEqual(D['전국'][K.indexOf(k)][0], pr[k], k);
console.log('PASS 보도자료 전국 평균', Object.keys(pr).length, '항목');
const z = { first: 0, re: 0, hosp: 0, vac: 0, rabies: 0, kennel: 0, corona: 0, flu: 0, heart: 0, ext: 0, deworm: 0, quote: 0 };
const cases = [
  ['서울 개 5kg 평균: 초진1+종합1+광견병1', ['서울특별시', 'dog', 0, 0, { first: 1, vac: 1, rabies: 1 }], { total: 10447 + 28049 + 25912, natTotal: 9873 + 26337 + 24803 }],
  ['세종 개 종합1+광견병1 = 42,950', ['세종특별자치시', 'dog', 0, 0, { vac: 1, rabies: 1 }], { total: 42950 }],
  ['전국 고양이 종합백신 3회', ['전국', 'cat', 0, 0, { vac: 3 }], { total: 39478 * 3, minTotal: 8000 * 3, maxTotal: 75000 * 3 }],
  ['대구 개 20kg 입원 2일 + 초진', ['대구광역시', 'dog', 2, 0, { first: 1, hosp: 2 }], { total: D['대구광역시'][2][0] + D['대구광역시'][9][0] * 2 }],
  ['고양이 입원은 체중 무관 hospcat', ['전국', 'cat', 2, 0, { hosp: 1 }], { total: 56417 }],
  ['중간값 기준 광견병 전국', ['전국', 'dog', 0, 1, { rabies: 1 }], { total: 25000 }],
  ['광범위 구충 전국(보도자료 값) 2회 + 견적 150,000', ['전국', 'dog', 0, 0, { deworm: 2, quote: 150000 }], { total: 7920, grand: 157920 }],
  ['횟수 0', ['서울특별시', 'dog', 0, 0, {}], { total: 0, grand: 0 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(args[0], args[1], args[2], args[3], Object.assign({}, z, args[4]));
  for (const k in exp) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ total: r.total, natTotal: r.natTotal, minTotal: r.minTotal, maxTotal: r.maxTotal, grand: r.grand }));
}
// UI 기본값 렌더 (서울, 개, 5kg, 평균, 초진1·종합1·광견병1)
const vals = { 'vf-sp': 'dog', 'vf-wt': '0', 'vf-basis': '0', 'vf-first': '1', 'vf-re': '0', 'vf-hosp': '0', 'vf-vac': '1', 'vf-rabies': '1', 'vf-kennel': '0', 'vf-corona': '0', 'vf-flu': '0', 'vf-heart': '0', 'vf-ext': '0', 'vf-deworm': '0', 'vf-quote': '0' };
const outP = [], opts = [];
const mk = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { if (id === 'vf-sido') { opts.push(p); if (p.selected) this.value = p.value; } else outP.push(p.textContent); } });
const els = {}; ['vf-out', 'vf-sido', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('시도 옵션', opts.length, '개, 선택:', els['vf-sido'].value);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.strictEqual(opts.length, 18);
assert.ok(outP.join().includes('64,408원'));
console.log('ALL PASS');
