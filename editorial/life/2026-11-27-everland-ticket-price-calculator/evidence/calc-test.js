// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('raw < in string literal');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.everlandCalc;
const C = (a, t, c, s) => ({ adult: a, teen: t, child: c, senior: s });
const Z = C(0, 0, 0, 0);
const cases = [
  ['11월 대인2+소인1', ['nov', 'regular', 'none', C(2, 0, 1, 0), Z, 0, 0], 185000, 0],
  ['12월 대인2+소인1', ['dec', 'regular', 'none', C(2, 0, 1, 0), Z, 0, 0], 155000, 0],
  ['11월 대인2+청소년1+소인1', ['nov', 'regular', 'none', C(2, 1, 1, 0), Z, 0, 0], 250000, 0],
  ['12월 대인2+청소년1+소인1', ['dec', 'regular', 'none', C(2, 1, 1, 0), Z, 0, 0], 210000, 0],
  ['11월 3자녀 우대 대인2+청소년1+소인2', ['nov', 'regular', 'multi', Z, C(2, 1, 2, 0), 0, 0], 244000, 0],
  ['12월 3자녀 우대', ['dec', 'regular', 'multi', Z, C(2, 1, 2, 0), 0, 0], 204000, 0],
  ['11월 장애인 본인 청소년+동반 대인', ['nov', 'regular', 'disabled', Z, C(1, 1, 0, 0), 0, 0], 39000 + 33000, 0],
  ['12월 국가유공자 대인1+소인1, 정가 소인1', ['dec', 'regular', 'merit', C(0, 0, 1, 0), C(1, 0, 1, 0), 0, 0], 45000 + 27500 + 22500, 0],
  ['11월 오후권 대인2 + 소인1(미확인)', ['nov', 'pm', 'none', C(2, 0, 1, 0), Z, 0, 0], 68000, 1],
  ['12월 오후권 대인1(미확인)', ['dec', 'pm', 'none', C(1, 0, 0, 0), Z, 0, 0], 0, 1],
  ['11월 특별우대 대인2+소인1', ['nov', 'special', 'none', C(2, 0, 1, 0), Z, 0, 0], 125000, 0],
  ['임산부 11월 + 유아이용권 2매 + 추가 22,000', ['nov', 'regular', 'pregnant', C(1, 0, 0, 0), C(1, 0, 0, 0), 2, 22000], 65000 + 55000 + 12000 + 22000, 0],
  ['경로 11월 정가', ['nov', 'regular', 'none', C(0, 0, 0, 2), Z, 0, 0], 110000, 0],
  ['음수·빈값 방어', ['nov', 'regular', 'none', C(-3, '', 'x', 1), Z, -1, -5], 55000, 0],
];
for (const [name, args, total, unknown] of cases) {
  const r = calc(...args);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  assert.strictEqual(r.unknown.length, unknown, name + ' unknown=' + r.unknown.length);
  console.log('PASS', name, r.total.toLocaleString('ko-KR') + '원', r.unknown.join(','));
}
assert.strictEqual(calc('nov', 'regular', 'merit', Z, C(3, 0, 0, 0), 0, 0).warn.length, 1);
assert.strictEqual(calc('nov', 'regular', 'pregnant', Z, C(1, 0, 0, 0), 0, 0).warn.length, 0);
console.log('PASS 우대 인원 상한 경고');
// UI 기본값 렌더 확인 - 최소 DOM 스텁
const vals = { 'ev-month': 'nov', 'ev-base': 'regular', 'ev-disc': 'none', 'ev-adult': '2', 'ev-teen': '0', 'ev-child': '1', 'ev-senior': '0', 'ev-d-adult': '0', 'ev-d-teen': '0', 'ev-d-child': '0', 'ev-d-senior': '0', 'ev-infant': '1', 'ev-infant-pass': '0', 'ev-extra': '0' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['ev-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('185,000원'));
