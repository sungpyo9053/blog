// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const W = window.cl2Written, P = window.cl2Practical, E = window.cl2Expiry, C = window.cl2Check;
const wc = [
  ['50·70 평균 60 -> 합격', 50, 70, { pass: true, avg: 60 }],
  ['35·90 평균 62.5 과락 -> 불합격', 35, 90, { pass: false, avg: 62.5 }],
  ['40·80 경계 40점 -> 합격', 40, 80, { pass: true, avg: 60 }],
  ['39·100 -> 과락', 39, 100, { pass: false }],
  ['55·60 평균 57.5 -> 불합격', 55, 60, { pass: false, avg: 57.5 }],
  ['101 입력 -> 오류', 101, 50, { ok: false }],
];
for (const [n, a, b, exp] of wc) { const r = W(a, b); for (const k in exp) assert.strictEqual(r[k], exp[k], n + ' ' + k); console.log('PASS', n, JSON.stringify(r)); }
assert.deepStrictEqual(W(35, 30).fail, ['컴퓨터 일반', '스프레드시트 일반']);
for (const [p, pass, need] of [[70, true, 0], [69, false, 1], [100, true, 0], [0, false, 70]]) { const r = P(p); assert.strictEqual(r.pass, pass); assert.strictEqual(r.need, need); console.log('PASS 실기', p, JSON.stringify(r)); }
assert.strictEqual(P(-1).ok, false);
for (const [d, e] of [['2026-11-17', '2028-11-17'], ['2028-02-29', '2030-02-28'], ['2026-12-31', '2028-12-31'], ['2026-02-30', null]]) { assert.strictEqual(E(d), e); console.log('PASS 만료일', d, '->', e); }
let r = C('2026-11-17', '2028-11-17'); assert.strictEqual(r.state, 'valid'); assert.strictEqual(r.left, 0); console.log('PASS 만료 당일 응시 가능', JSON.stringify(r));
r = C('2026-11-17', '2028-11-18'); assert.strictEqual(r.state, 'expired'); assert.strictEqual(r.left, -1); console.log('PASS 만료 다음 날', JSON.stringify(r));
r = C('2026-11-17', '2026-12-01'); assert.strictEqual(r.state, 'valid'); assert.strictEqual(r.left, 717); console.log('PASS 2주 뒤 응시', JSON.stringify(r));
r = C('2026-11-17', '2026-11-10'); assert.strictEqual(r.state, 'before'); console.log('PASS 합격일 이전 날짜', JSON.stringify(r));
// 본문 응시료 합계 검산
assert.strictEqual(20500 + 1200 + 25000 + 1200, 47900); assert.strictEqual(3100 + 3300, 6400); console.log('PASS 응시료 47,900원 / 발급 6,400원');
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'cl-a': '55', 'cl-b': '70', 'cl-p': '72', 'cl-pass': '2026-11-17', 'cl-exam': '2027-03-02' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['cl-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력:', outP.join(' | '));
assert.ok(outP[0].includes('평균 62.5점'));
assert.ok(outP.join().includes('2028년 11월 17일(금)'));
assert.ok(outP.join().includes('유효기간 안'));
console.log('ALL PASS');
