// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
assert.ok(faq >= 6, 'FAQ count ' + faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.petInsCalc;
const base = { prem: 35000, cost: 100000, visits: 3, ratio: 70, ded: 30000, dcap: 300000, ycap: 0 };
const cases = [
  ['본문 예1: 10만원 통원 3회, 70%, 3만원', {}, { per: 49000, pay: 147000, prem: 420000, net: -273000, be: 230000, spend: 573000 }],
  ['본문 예2: 300만원 수술, 한도 없음', { cost: 3000000, visits: 1, dcap: 0 }, { per: 2079000, pay: 2079000, net: 1659000 }],
  ['본문 예2: 300만원 수술, 1일 30만원 한도', { cost: 3000000, visits: 1 }, { per: 300000, pay: 300000, net: -120000, dayCut: true }],
  ['금감원 분쟁사례5: 150만원 통원, 1일 15만원, 80%, 1만원', { cost: 1500000, visits: 1, ratio: 80, ded: 10000, dcap: 150000 }, { pay: 150000, dayCut: true }],
  ['50%형 1일 5만원 한도', { ratio: 50, dcap: 50000 }, { per: 35000, pay: 105000 }],
  ['연간 한도 500만원', { cost: 1000000, visits: 12, dcap: 0, ycap: 5000000 }, { per: 679000, pay: 5000000, yearCut: true }],
  ['진료비가 자기부담금 이하 -> 0원', { cost: 20000 }, { per: 0, pay: 0 }],
  ['1회 방문 + 1일 한도로 보험료 회수 불가', { visits: 1 }, { be: -1 }],
  ['방문 0회', { visits: 0 }, { pay: 0, be: null, net: -420000 }],
];
for (const [name, inp, exp] of cases) {
  const r = calc(Object.assign({}, base, inp));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'pi-prem': '35000', 'pi-cost': '100000', 'pi-visits': '3', 'pi-ratio': '70', 'pi-ded': '30000', 'pi-dcap': '300000', 'pi-ycap': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = { 'pi-out': el('pi-out') }; Object.keys(vals).forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('1년 예상 보험금: 147,000원'));
assert.ok(outP.join().includes('230,000원 이상'));
console.log('ALL PASS', cases.length + 1, 'FAQ', faq);
