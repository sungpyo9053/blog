// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/'[^'\n]*</.test(src)) throw new Error('< inside JS string');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const T = window.taxCalc33;
const W = [
  ['국세청 예: 보험모집인 500만 원 -> 소득세 150,000', 5000000, 'biz', { tax: 150000, local: 15000, net: 4835000 }],
  ['100만 원 3.3% -> 967,000', 1000000, 'biz', { tax: 30000, local: 3000, total: 33000, net: 967000 }],
  ['절사: 125,000원 -> 지방세 375->370', 125000, 'biz', { tax: 3750, local: 370, total: 4120, net: 120880 }],
  ['절사: 333,333원 -> 9,990 + 990', 333333, 'biz', { tax: 9990, local: 990, net: 322353 }],
  ['절사: 333원 -> 소득세 9.99원 -> 0', 333, 'biz', { tax: 0, local: 0, net: 333 }],
  ['국세청 예: 기타소득 125,000원 -> 0원(과세최저한)', 125000, 'oth', { income: 0, tax: 0, net: 125000 }],
  ['기타소득 125,010원 -> 8.8%', 125010, 'oth', { income: 50004, tax: 10000, local: 1000, net: 114010 }],
  ['기타소득 100만 원 -> 88,000', 1000000, 'oth', { income: 400000, tax: 80000, local: 8000, net: 912000 }],
];
for (const [name, g, k, exp] of W) {
  const r = T.withhold(g, k);
  for (const key of Object.keys(exp)) assert.strictEqual(r[key], exp[key], name + ' ' + key + '=' + r[key]);
  console.log('PASS', name, JSON.stringify(r));
}
// 역산: 정확히 맞는 지급액이 다시 같은 실수령액을 내는지
for (const [n, k, first] of [[1000000, 'biz', 1034120], [3000000, 'biz', 3102370], [500000, 'biz', 517060], [967000, 'biz', 999980], [912000, 'oth', null], [100000, 'oth', 100000]]) {
  const s = T.grossFromNet(n, k);
  assert.ok(s.exact.length > 0, 'no exact for ' + n);
  s.exact.forEach(g => assert.strictEqual(T.withhold(g, k).net, n));
  if (first) assert.strictEqual(s.exact[0], first);
  console.log('PASS 역산', k, n, '->', s.exact.join(' / '));
}
assert.ok(T.grossFromNet(967000, 'biz').exact.includes(1000000));
// 정확히 맞는 지급액이 없는 실수령액 찾기 -> nearest 제공 확인
let miss = 0;
for (let n = 1000000; n < 1000200; n++) { const s = T.grossFromNet(n, 'biz'); if (!s.exact.length) { miss++; assert.ok(T.withhold(s.nearest, 'biz').net >= n); } }
console.log('PASS 역산 근사값 처리(정확값 없는 실수령액', miss, '건)');
// 세율표(국세청 2023~2025 귀속): 과세표준 3천만 원 -> 3,240,000원
assert.strictEqual(T.rateTax(30000000), 3240000);
assert.strictEqual(T.rateTax(14000000), 840000);
assert.strictEqual(T.rateTax(50000000), 6240000);
console.log('PASS 기본세율(국세청 예: 과표 3천만 원 -> 3,240,000원)');
// 국세청 환급 사례 구조 검산: 수입 1,000만 원, 33만 원 원천징수, 실제 세금 22만 원 -> 11만 원 환급
// (국세청은 경비율을 밝히지 않음. 경비율 40%를 넣으면 결정세액 20만 원이 되어 사례 금액과 같아짐)
const st = T.settle(10000000, 40, 1);
assert.strictEqual(st.decided, 200000); assert.strictEqual(st.paid, 300000); assert.strictEqual(st.diff, -110000);
console.log('PASS 정산 구조(국세청 환급 사례 11만 원 재현)', JSON.stringify(st));
// 표 값 검산
const rows = [[100000, 3300, 0], [125000, 4120, 0], [300000, 9900, 26400], [500000, 16500, 44000], [1000000, 33000, 88000], [2000000, 66000, 176000], [3000000, 99000, 264000], [5000000, 165000, 440000]];
for (const [g, b, o] of rows) {
  assert.strictEqual(T.withhold(g, 'biz').total, b); assert.strictEqual(T.withhold(g, 'oth').total, o);
  const fmt = n => n.toLocaleString('en-US') + '원';
  assert.ok(html.includes('<td>' + fmt(g) + '</td><td>' + fmt(b) + '</td><td>' + fmt(g - b) + '</td><td>' + fmt(o) + '</td><td>' + fmt(g - o) + '</td>'), 'table row ' + g);
}
console.log('PASS 공제표', rows.length, '행');
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'tx-dir': 'g2n', 'tx-kind': 'biz', 'tx-amt': '1000000', 'st-gross': '10000000', 'st-rate': '40', 'st-ppl': '1' };
const outs = { 'tx-out': [], 'st-out': [] };
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['tx-label'] = { textContent: '' };
Object.keys(outs).forEach(id => els[id] = { set innerHTML(v) { outs[id].length = 0; }, appendChild(p) { outs[id].push(p.textContent); } });
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 지급액->실수령:', outs['tx-out'].join(' | '));
console.log('UI 5월 정산:', outs['st-out'].join(' | '));
assert.ok(outs['tx-out'].join().includes('967,000원'));
assert.ok(outs['st-out'].join().includes('예상 환급: 약 110,000원'));
