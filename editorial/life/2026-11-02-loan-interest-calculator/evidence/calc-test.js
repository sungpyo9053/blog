// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하고 금융감독원 계산기 결과(fss-calc-api-*.json)와 대조
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('< inside string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { sched, dayInterest } = window.loanCalc;
const R = Math.round, num = s => parseInt(s.replace(/,/g, ''), 10);
// 1) 금감원 주택담보대출 계산기(calculate.ujson) 결과와 대조
const TYPES = { 1: 'equal', 2: 'prin', 3: 'bullet' };
for (const [P, pct, n] of [[100000000, 4, 360], [30000000, 5, 60]]) for (const t of [1, 2, 3]) {
  const j = JSON.parse(fs.readFileSync(path.join(__dirname, `fss-calc-api-${P}-${pct}-${n}-type${t}.json`), 'utf8')).result;
  const rows = [...j.resultList.matchAll(/<tr>(.*?)<\/tr>/g)].map(m => [...m[1].matchAll(/<td[^>]*>(.*?)<\/td>/g)].map(x => x[1]));
  const s = sched(P, pct, n, 0, TYPES[t]);
  assert.strictEqual(rows.length, n);
  let maxDiff = 0;
  rows.forEach((r, i) => { // 금감원 열: 회차, 상환금, 납입원금, 이자, 납입원금합계, 잔금
    for (const [col, v] of [[1, s.rows[i].pay], [2, s.rows[i].prin], [3, s.rows[i].int]]) maxDiff = Math.max(maxDiff, Math.abs(num(r[col]) - v));
  });
  assert.ok(maxDiff <= 1, 'row diff ' + maxDiff);
  const fssTot = num(j.result.totRateAmout);
  assert.ok(Math.abs(fssTot - s.interest) <= 2, `total ${fssTot} vs ${s.interest}`);
  console.log(`PASS 금감원 대조 ${P}/${pct}%/${n}개월 ${TYPES[t]}: 첫 회 ${R(s.first)} 마지막 ${R(s.last)} 총이자 ${R(s.interest)} (금감원 ${fssTot}, 회차별 최대 차이 ${maxDiff.toFixed(2)}원)`);
}
// 2) 원리금균등 공식 직접 대조: P r / (1-(1+r)^-n)
{ const P = 1e8, r = 0.04 / 12, n = 360; const pmt = P * r / (1 - Math.pow(1 + r, -n));
  assert.strictEqual(R(sched(P, 4, n, 0, 'equal').rows[100].pay), R(pmt)); assert.strictEqual(R(pmt), 477415);
  assert.strictEqual(R(sched(P, 4, n, 0, 'prin').interest), R(P * r * (n + 1) / 2));
  console.log('PASS 원리금균등 공식 477,415원 · 원금균등 총이자 = P·r·(n+1)/2'); }
// 3) 0% 금리
for (const t of ['equal', 'prin']) { const s = sched(30000000, 0, 60, 0, t); assert.strictEqual(s.interest, 0); s.rows.forEach(r => assert.ok(Math.abs(r.pay - 500000) < 1e-6)); assert.strictEqual(s.rows[59].bal, 0); }
{ const s = sched(30000000, 0, 60, 0, 'bullet'); assert.strictEqual(s.interest, 0); assert.strictEqual(s.last, 30000000); }
console.log('PASS 0%: 매달 500,000원, 총이자 0원');
// 4) 거치기간
{ const e = sched(1e8, 4, 360, 12, 'equal'), p = sched(1e8, 4, 360, 12, 'prin');
  assert.strictEqual(R(e.first), 333333); assert.strictEqual(R(e.firstAfter), 485973); assert.strictEqual(R(e.interest), 73118766);
  assert.strictEqual(R(p.firstAfter), 620690); assert.strictEqual(R(p.interest), 62166667);
  e.rows.slice(0, 12).forEach(r => assert.strictEqual(r.prin, 0)); assert.strictEqual(e.rows[359].bal, 0);
  console.log('PASS 거치 12개월: 원리금 333,333 → 485,973원, 총이자 73,118,766원 · 원금균등 620,690원, 62,166,667원'); }
// 5) 본문 표 값
const expect = [[1e8, 4, 360, 'equal', 477415, 477415, 71869506], [1e8, 4, 360, 'prin', 611111, 278704, 60166667], [1e8, 4, 360, 'bullet', 333333, 100333333, 120000000],
  [3e7, 5, 60, 'equal', 566137, 566137, 3968221], [3e7, 5, 60, 'prin', 625000, 502083, 3812500], [3e7, 5, 60, 'bullet', 125000, 30125000, 7500000]];
for (const [P, pct, n, t, f, l, it] of expect) { const s = sched(P, pct, n, 0, t); assert.deepStrictEqual([R(s.first), R(s.last), R(s.interest)], [f, l, it]); assert.ok(html.includes(f.toLocaleString('en-US') + '원')); assert.ok(html.includes(it.toLocaleString('en-US') + '원')); }
console.log('PASS 본문 비교표 6행');
// 6) 일할 이자
assert.strictEqual(dayInterest(1e8, 4, 30, false), 328767); assert.strictEqual(dayInterest(1e8, 4, 31, false), 339726); assert.strictEqual(dayInterest(1e8, 4, 30, true), 327868);
assert.strictEqual(Math.floor(566137 * 0.08 * 30 / 365), 3722);
console.log('PASS 일할: 30일 328,767원 · 31일 339,726원 · 윤년 30일 327,868원 · 연체 예시 3,722원');
// 7) UI 렌더(최소 DOM 스텁)
const vals = { 'lc-amt': '100000000', 'lc-rate': '4', 'lc-years': '30', 'lc-grace': '0', 'lc-type': 'equal', 'lc-dp': '100000000', 'lc-dr': '4', 'lc-dd': '30' };
const texts = [];
function node(tag) { const n = { tag, style: {}, children: [], textContent: '', appendChild(c) { this.children.push(c); return c; }, set innerHTML(v) { this.children = []; } }; return n; }
function collect(n, acc) { if (n.textContent) acc.push(n.textContent); n.children.forEach(c => collect(c, acc)); return acc; }
const els = {}; Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['lc-leap'] = { checked: false, addEventListener() {} };
['lc-out', 'lc-table', 'lc-dout'].forEach(id => els[id] = node('div'));
global.document = { getElementById: id => els[id], createElement: node };
eval(src);
const outText = collect(els['lc-out'], []).join(' | ');
console.log('UI 기본값 출력:', outText);
console.log('UI 회차표 행 수:', els['lc-table'].children[1].children[1].children.length);
console.log('UI 일할:', els['lc-dout'].textContent);
assert.ok(outText.includes('477,415원')); assert.ok(outText.includes('71,869,506원')); assert.strictEqual(els['lc-table'].children[1].children[1].children.length, 360);
// 거치·0%·잘못된 입력
els['lc-grace'].value = '12'; eval(src); assert.ok(collect(els['lc-out'], []).join().includes('해당 없음'));
els['lc-grace'].value = '400'; eval(src); assert.ok(collect(els['lc-out'], []).join().includes('거치기간은 대출기간보다 짧아야'));
els['lc-grace'].value = '0'; els['lc-rate'].value = '0'; eval(src); assert.ok(collect(els['lc-out'], []).join().includes('277,778원'));
console.log('PASS UI: 거치 열, 잘못된 거치 경고, 0% 렌더');
