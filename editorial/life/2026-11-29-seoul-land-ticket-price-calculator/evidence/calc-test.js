// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.seoullandCalc;
const C = (a, t, c, k, s) => ({ adult: a, teen: t, child: c, kid: k, senior: s });
const Z = C(0, 0, 0, 0, 0);
const cases = [
  ['종일권 어른2+어린이1', ['day', 'none', C(2, 0, 1, 0, 0), Z, 0], 147000, 0],
  ['야간권 어른2+어린이1', ['night', 'none', C(2, 0, 1, 0, 0), Z, 0], 126000, 0],
  ['종일권 어른2+청소년1+어린이1', ['day', 'none', C(2, 1, 1, 0, 0), Z, 0], 193000, 0],
  ['종일권 경로3', ['day', 'none', C(0, 0, 0, 0, 3), Z, 0], 129000, 0],
  ['60개월 미만 어린이 종일권', ['day', 'none', C(0, 0, 0, 1, 0), Z, 0], 43000, 0],
  ['장애인 청소년+동반 어른 종일권', ['day', 'disabled', Z, C(1, 1, 0, 0, 0), 0], 49000, 0],
  ['장애인 어린이 야간권', ['night', 'disabled', Z, C(0, 0, 1, 0, 0), 0], 18000, 0],
  ['국가유공자 어른1 야간권', ['night', 'merit', Z, C(1, 0, 0, 0, 0), 0], 22500, 0],
  ['60세 특별 경로2+정가 어린이1', ['day', 's60', C(0, 0, 1, 0, 0), C(0, 0, 0, 0, 2), 0], 67000, 0],
  ['60세 특별 야간권(미적용)', ['night', 's60', Z, C(1, 0, 0, 0, 0), 0], 0, 1],
  ['60세 특별 어린이(대상 아님)', ['day', 's60', Z, C(0, 0, 1, 0, 0), 0], 0, 1],
  ['음수·빈값 방어', ['day', 'none', C(-3, '', 'x', 0, 1), Z, -2], 43000, 0],
];
for (const [name, args, total, unknown] of cases) {
  const r = calc(...args);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  assert.strictEqual(r.unknown.length, unknown, name + ' unknown=' + r.unknown.length);
  console.log('PASS', name, r.total.toLocaleString('ko-KR') + '원', r.unknown.join(','));
}
let a = calc('day', 'none', C(2, 0, 1, 1, 0), Z, 5);
assert.strictEqual(a.dayTotal, 950000); assert.strictEqual(a.annualTotal, 765000);
console.log('PASS 연간권 비교 어른2+주니어1+키즈1 5회: 1일권', a.dayTotal, '연간권', a.annualTotal);
a = calc('day', 'none', C(1, 0, 0, 0, 0), Z, 4);
assert.ok(a.annualTotal > a.dayTotal);
a = calc('day', 'none', C(1, 0, 0, 0, 0), Z, 5);
assert.ok(a.dayTotal > a.annualTotal);
console.log('PASS 어른 본전 5회째');
assert.strictEqual(calc('day', 'disabled', Z, C(2, 0, 0, 0, 0), 0).warn.length, 1);
assert.strictEqual(calc('day', 'disabled', Z, C(1, 0, 0, 0, 0), 0).warn.length, 0);
console.log('PASS 장애인 동반 경고');
const vals = { 'sl-base': 'day', 'sl-disc': 'none', 'sl-adult': '2', 'sl-teen': '0', 'sl-child': '1', 'sl-kid': '0', 'sl-senior': '0', 'sl-d-adult': '0', 'sl-d-teen': '0', 'sl-d-child': '0', 'sl-d-senior': '0', 'sl-infant': '1', 'sl-visits': '1' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['sl-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('147,000원'));
