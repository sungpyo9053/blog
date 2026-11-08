// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity;
const h3s = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>[^<]*<\/h3>/g).length;
assert.strictEqual(faq.length, h3s); console.log('PASS FAQ JSON-LD', faq.length, '= 본문 h3', h3s);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.oworldCalc;
const C = (a, t, c, s) => ({ adult: a, teen: t, child: c, senior: s });
const W = (a, t, c) => ({ adult: a, teen: t, child: c });
const o = (time, fare, cnt, w, comp, safari, rides, visits) => ({ time, fare, cnt, w: w || W(0, 0, 0), comp: comp || 0, safari: safari === undefined ? 7000 : safari, rides: rides === undefined ? 3 : rides, visits: visits || 0 });
const cases = [
  // name, input, entry, plus, free, unknown
  ['주간 기본 성인2+어린이1 사파리+3회', o('day', 'basic', C(2, 0, 1, 0)), 44000, 110000, 93000, 0],
  ['주간 대전시민 성인2+어린이1', o('day', 'citizen', C(2, 0, 1, 0), null, 0, 0, 0), 35000, 35000, 74000, 0],
  ['야간 기본 성인2+청소년1', o('night', 'basic', C(2, 1, 0, 0), null, 0, 0, 0), 36000, 36000, 73000, 0],
  ['야간 대전시민 성인1+어린이1', o('night', 'citizen', C(1, 0, 1, 0), null, 0, 0, 0), 17000, 17000, 37000, 0],
  ['경로2+청소년1 주간', o('day', 'basic', C(0, 1, 0, 2), null, 0, 0, 0), 33000, 33000, 78000, 0],
  ['성인 사파리+2회 = 자유이용권 차이', o('day', 'basic', C(1, 0, 0, 0), null, 0, 7000, 2), 17000, 34000, 34000, 0],
  ['성인2+5세 사파리만(2세는 무료라 제외)', o('day', 'basic', C(2, 0, 1, 0), null, 0, 7000, 0), 44000, 65000, 93000, 0],
  ['동절기 사파리 5,000원', o('day', 'basic', C(1, 0, 0, 0), null, 0, 5000, 0), 17000, 22000, 34000, 0],
  ['우대 어린이+동반자 주간', o('day', 'basic', C(0, 0, 0, 0), W(0, 0, 1), 1, 0, 0), 0, 0, 15000, 1],
  ['우대 성인 주간', o('day', 'basic', C(0, 0, 0, 0), W(1, 0, 0), 0, 0, 0), 0, 0, 17000, 0],
  ['우대 성인 야간(가격 미확인)', o('night', 'basic', C(0, 0, 0, 0), W(1, 0, 0), 0, 0, 0), 0, 0, 0, 1],
  ['음수·빈값·잘못된 사파리값 방어', o('day', 'basic', C(-3, '', 'x', 1), null, -1, 1234, -2), 10000, 10000, 25000, 0],
];
for (const [name, input, entry, plus, free, unknown] of cases) {
  const r = calc(input);
  assert.strictEqual(r.entry, entry, name + ' entry=' + r.entry);
  assert.strictEqual(r.plus, plus, name + ' plus=' + r.plus);
  assert.strictEqual(r.free, free, name + ' free=' + r.free);
  assert.strictEqual(r.unknown.length, unknown, name + ' unknown=' + r.unknown.length);
  console.log('PASS', name, '입장권', r.entry, '입장권+원내', r.plus, '자유이용권', r.free, r.unknown.join(','));
}
const an = (fare, cnt, v) => calc(o('day', fare, cnt, null, 0, 0, 0, v));
let a = an('basic', C(1, 0, 0, 0), 3); assert.ok(a.annualTotal > a.dayFree);
a = an('basic', C(1, 0, 0, 0), 4); assert.ok(a.dayFree > a.annualTotal); console.log('PASS 성인 본전 4회째', a.dayFree, '>', a.annualTotal);
a = an('basic', C(0, 0, 1, 0), 4); assert.ok(a.annualTotal > a.dayFree);
a = an('basic', C(0, 0, 0, 1), 5); assert.ok(a.dayFree > a.annualTotal); console.log('PASS 어린이·경로 본전 5회째', a.dayFree);
a = an('citizen', C(1, 0, 0, 0), 4); assert.ok(a.annualTotal > a.dayFree);
a = an('citizen', C(1, 0, 0, 0), 5); assert.ok(a.dayFree > a.annualTotal); console.log('PASS 대전시민 성인 본전 5회째', a.dayFree);
const vals = { 'ow-time': 'day', 'ow-fare': 'basic', 'ow-adult': '2', 'ow-teen': '0', 'ow-child': '1', 'ow-senior': '0', 'ow-infant': '1', 'ow-w-adult': '0', 'ow-w-teen': '0', 'ow-w-child': '0', 'ow-w-comp': '0', 'ow-safari': '7000', 'ow-rides': '3', 'ow-visits': '1' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['ow-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('44,000원')); assert.ok(outP[0].includes('110,000원')); assert.ok(outP[0].includes('93,000원'));
assert.ok(outP.some(s => s.includes('자유이용권이 17,000원 싸다')));
console.log('PASS UI');
