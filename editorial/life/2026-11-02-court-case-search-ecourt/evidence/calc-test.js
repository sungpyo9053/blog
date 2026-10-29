// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const stamp = window.courtStamp, fee = window.courtFee, caseNo = window.courtCaseNo;
// 인지액: [이름, 소가, 서류, 종이, 전자]
const sc = [
  ['전자소송포털 API 특허1심(소가 1억) orgInjiAmt 455,000 / injiAmt 409,500', 100000000, 'first', 455000, 409500],
  ['전자소송포털 API 특허상고(소가 1억) 910,000 / 819,000', 100000000, 'supreme', 910000, 819000],
  ['최저: 소가 15만원 -> 1,000원, 전자 900원(화면 유의사항)', 150000, 'first', 1000, 900],
  ['100원 미만 버림: 소가 1,234,567 -> 6,172.8 -> 6,100 / 5,490 -> 5,400', 1234567, 'first', 6100, 5400],
  ['소가 2,000만원 1심', 20000000, 'first', 95000, 85500],
  ['소가 3,000만원 1심(소액 상한)', 30000000, 'first', 140000, 126000],
  ['경계: 소가 999만9,999원 -> 1만분의 50', 9999999, 'first', 49900, 44900],
  ['경계: 소가 1,000만원 -> 0.45%+5,000', 10000000, 'first', 50000, 45000],
  ['소가 10억원 -> 0.35%+555,000', 1000000000, 'first', 4055000, 3649500],
  ['항소장 소가 2,000만원: 95,000 x 1.5', 20000000, 'appeal', 142500, 128200],
  ['지급명령 소가 2,000만원: 95,000 / 10', 20000000, 'order', 9500, 8500],
  ['지급명령 최저: 소가 100만원 -> 500 -> 1,000', 1000000, 'order', 1000, 900],
];
for (const [name, v, k, p, e] of sc) {
  const r = stamp(v, k);
  assert.strictEqual(r.paper, p, name + ' paper=' + r.paper);
  assert.strictEqual(r.e, e, name + ' e=' + r.e);
  console.log('PASS 인지액', name, JSON.stringify(r));
}
// 송달료: [이름, 종류, 원고, 피고, 1회분, 종이, 전자]
const fc = [
  ['단독 1:1, 5,640원', 'single', 1, 1, 5640, 169200, 84600],
  ['소액 1:1', 'small', 1, 1, 5640, 112800, 56400],
  ['항소 1:2', 'appeal', 1, 2, 5640, 203040, 135360],
  ['지급명령 1:1(6회분 이하라 전자도 전체)', 'order', 1, 1, 5640, 67680, 67680],
  ['조정 1:1', 'mediation', 1, 1, 5640, 56400, 56400],
];
for (const [name, t, pl, df, u, p, e] of fc) {
  const r = fee(t, pl, df, u);
  assert.strictEqual(r.paper, p, name + ' paper=' + r.paper);
  assert.strictEqual(r.e, e, name + ' e=' + r.e);
  console.log('PASS 송달료', name, JSON.stringify(r));
}
// API strDlvrChrgForWPT 33,840원(6회분) = 6 x strDlvrChrg 5,640원
assert.strictEqual(6 * 5640, 33840); console.log('PASS 1회분 5,640원 x 6 = 33,840원(API 값과 일치)');
// 사건번호
let r = caseNo('2026가단12345'); assert.strictEqual(r.year, '2026'); assert.strictEqual(r.code, '가단'); assert.strictEqual(r.num, '12345'); assert.strictEqual(r.name, '민사 1심 단독사건');
r = caseNo('17가단10'); assert.strictEqual(r.year, '2017'); assert.strictEqual(r.num, '10');
r = caseNo('2025 재가합 77'); assert.ok(r.retrial); assert.strictEqual(r.name, '민사 1심 합의사건의 재심');
assert.strictEqual(caseNo('가단123'), null);
console.log('PASS 사건번호 4건', JSON.stringify(caseNo('2026가소987')));
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'cc-no': '2026가단12345', 'cc-v': '20000000', 'cc-kind': 'first', 'cc-type': 'single', 'cc-pl': '1', 'cc-df': '1', 'cc-unit': '5640' };
const outs = { 'cc-no-out': [], 'cc-v-out': [], 'cc-f-out': [] };
const els = { 'cc-calc': {} };
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
Object.keys(outs).forEach(id => els[id] = { set innerHTML(v) { outs[id].length = 0; }, appendChild(p) { outs[id].push(p.textContent); } });
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
for (const id of Object.keys(outs)) console.log('UI', id, ':', outs[id].join(' | '));
assert.ok(outs['cc-v-out'].join().includes('85,500원'));
assert.ok(outs['cc-f-out'].join().includes('84,600원'));
assert.ok(outs['cc-no-out'].join().includes('민사 1심 단독사건'));
console.log('ALL PASS');
