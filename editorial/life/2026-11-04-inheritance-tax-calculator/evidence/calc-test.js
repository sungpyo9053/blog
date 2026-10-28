// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.inheritanceTaxCalc, taxOf = window.inheritanceTaxOf;
const E = 1e8, M = 1e4;
const base = { assets: 0, debts: 0, funeral: 0, enshrine: 0, spouse: false, actual: 0, kids: 2, parents: 0, fin: 0, house: 0, filed: true };
const cases = [
  ['일괄공제만으로 0원: 자녀2, 5억', { assets: 5 * E }, { taxable: 4.95 * E, lump: 5 * E, base: 0, pay: 0 }],
  ['배우자+자녀2, 10억, 장례 1천만 -> 0원', { assets: 10 * E, funeral: 1000 * M, spouse: true }, { taxable: 9.9 * E, spouseDed: 5 * E, base: 0, pay: 0 }],
  ['배우자 5억 최소: 실제 1억', { assets: 20 * E, spouse: true, actual: 1 * E }, { spouseDed: 5 * E }],
  ['배우자 실제 10억, 30억, 자녀2 (예시3)', { assets: 30 * E, funeral: 1000 * M, spouse: true, actual: 10 * E }, { spouseDed: 10 * E, base: 14.9 * E, tax: 436000000, credit: 13080000, pay: 422920000 }],
  ['배우자 법정상속분 한도: 실제 20억, 30억, 자녀2 -> 약 12.857억', { assets: 30 * E, spouse: true, actual: 20 * E }, { spouseDed: Math.round(30 * E * 1.5 / 3.5) }],
  ['배우자 30억 상한: 100억, 자녀1, 실제 50억', { assets: 100 * E, spouse: true, actual: 50 * E, kids: 1 }, { spouseDed: 30 * E }],
  ['자녀2만 10억, 장례 증빙 없음 (예시2)', { assets: 10 * E }, { funeralDed: 500 * M, base: 4.95 * E, tax: 89000000, credit: 2670000, pay: 86330000 }],
  ['장례 상한: 장례 2천만+봉안 800만 -> 1,500만', { assets: 10 * E, funeral: 2000 * M, enshrine: 800 * M }, { funeralDed: 1500 * M }],
  ['배우자 단독: 일괄공제 없이 기초 2억', { assets: 10 * E, spouse: true, actual: 10 * E, kids: 0, parents: 0 }, { sole: true, lump: 2 * E, spouseDed: 10 * E }],
  ['자녀 7명: 인적 5.5억 > 일괄 5억', { assets: 20 * E, kids: 7 }, { lump: 5.5 * E }],
  ['무신고: 일괄 5억, 신고공제 0', { assets: 20 * E, kids: 7, filed: false }, { lump: 5 * E, credit: 0 }],
  ['금융재산 3억 -> 6천만', { assets: 20 * E, fin: 3 * E }, { finDed: 6000 * M }],
  ['금융재산 1,500만 -> 전액', { assets: 20 * E, fin: 1500 * M }, { finDed: 1500 * M }],
  ['금융재산 5천만 -> 2천만(최소)', { assets: 20 * E, fin: 5000 * M }, { finDed: 2000 * M }],
  ['금융재산 20억 -> 2억 한도', { assets: 30 * E, fin: 20 * E }, { finDed: 2 * E }],
  ['동거주택 8억 -> 6억 한도', { assets: 30 * E, house: 8 * E }, { houseDed: 6 * E }],
  ['채무 초과 -> 과세가액 0', { assets: 3 * E, debts: 5 * E }, { taxable: 0, pay: 0 }],
];
for (const [name, inp, exp] of cases) {
  const r = calc({ ...base, ...inp });
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-6 || r[k] === exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 세율 구간 경계 (제26조, 국세청 누진공제)
const bounds = [[49 * M, 0], [50 * M, 50000], [1 * E, 10000000], [1 * E + 1, 10000000], [5 * E, 90000000], [5 * E + 10, 90000003], [10 * E, 240000000], [30 * E, 1040000000], [31 * E, 1090000000]];
for (const [b, t] of bounds) { assert.strictEqual(taxOf(b), t, 'taxOf ' + b); console.log('PASS 경계 과세표준', b.toLocaleString(), '-> 산출세액', taxOf(b).toLocaleString()); }
// 누진공제 방식 = 법조문 누적 방식 일치
for (const b of [0.7 * E, 3 * E, 7 * E, 20 * E, 45 * E]) {
  const law = b <= E ? b * .1 : b <= 5 * E ? 1e7 + (b - E) * .2 : b <= 10 * E ? 9e7 + (b - 5 * E) * .3 : b <= 30 * E ? 2.4e8 + (b - 10 * E) * .4 : 10.4e8 + (b - 30 * E) * .5;
  assert.strictEqual(taxOf(b), Math.round(law));
}
console.log('PASS 누진공제 방식 = 제26조 누적 방식 5건');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'it-assets': '100000', 'it-debts': '0', 'it-funeral': '500', 'it-enshrine': '0', 'it-spouse': '1', 'it-actual': '0', 'it-kids': '2', 'it-parents': '0', 'it-fin': '0', 'it-house': '0', 'it-filed': '1' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['it-out', 'it-spouse-box', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('납부할 세액(추정): 0원'));
