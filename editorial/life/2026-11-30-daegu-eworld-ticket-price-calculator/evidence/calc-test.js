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
const calc = window.eworldCalc;
const C = (a, t, c, s) => ({ adult: a, teen: t, child: c, senior: s || 0 });
const o = (time, cnt, disc, extra) => Object.assign({ time, cnt, disc: disc || 'none', k: 1, cprice: 0, cn: 0, tower: false, cars: 0, visits: 0 }, extra || {});
const cases = [
  // name, input, tickets, total, discounted, notes
  ['종일 정상 어른2+어린이1', o('day', C(2, 0, 1)), 137000, 137000, 0, 0],
  ['야간 정상 어른2+청소년1', o('night', C(2, 1, 0)), 103000, 103000, 0, 0],
  ['야간 정상 어른2+청소년1+어린이1', o('night', C(2, 1, 1)), 136000, 136000, 0, 0],
  ['네이버페이 종일 어른2+어린이1', o('day', C(2, 0, 1), 'naver'), 73500, 73500, 3, 0],
  ['네이버페이 야간 어른1+어린이1', o('night', C(1, 0, 1), 'naver'), 35000, 35000, 2, 0],
  ['임신부 본인1+동반1 (어른2+어린이1)', o('day', C(2, 0, 1), 'senior'), 89000, 89000, 2, 0],
  ['경로 2명 우대본인2', o('day', C(0, 0, 0, 2), 'senior', { k: 2 }), 50000, 50000, 2, 0],
  ['장애인 본인+동반 어른1+어린이1', o('day', C(1, 0, 1), 'disabled'), 44000, 44000, 2, 0],
  ['장애인 50% 이미지값 어른·청소년·어린이 각1, 우대본인2', o('day', C(1, 1, 1), 'disabled', { k: 2 }), 66000, 66000, 3, 0],
  ['장애인 야간이면 정상가', o('night', C(1, 0, 1), 'disabled'), 68000, 68000, 0, 1],
  ['다둥이 어른2+어린이3', o('day', C(2, 0, 3), 'multi'), 107500, 107500, 5, 0],
  ['다둥이 2명이면 미적용', o('day', C(1, 0, 1), 'multi'), 88000, 88000, 0, 1],
  ['문화누리 본인+동반3 어른2+어린이2', o('day', C(2, 0, 2), 'nuri'), 105600, 105600, 4, 0],
  ['문화누리 5명이면 1명 정상가', o('day', C(2, 0, 3), 'nuri'), 144600, 144600, 4, 0],
  ['생일 야간 어른1+청소년1', o('night', C(1, 1, 0), 'birthday'), 35000, 35000, 2, 0],
  ['생일 종일 3명 중 2명', o('day', C(3, 0, 0), 'birthday'), 98000, 98000, 2, 0],
  ['행사가 30,900원 2명', o('day', C(2, 0, 1), 'custom', { cprice: 30900, cn: 2 }), 100800, 100800, 2, 0],
  ['임신부+남편 종일+전망대', o('day', C(2, 0, 0), 'senior', { tower: true }), 50000, 68000, 2, 0],
  ['종일 어른2+어린이1 전망대+주차1', o('day', C(2, 0, 1), 'none', { tower: true, cars: 1 }), 137000, 167000, 0, 0],
  ['야간 전망대 정가 어른1+청소년1+어린이1+경로1', o('night', C(1, 1, 1, 1), 'none', { tower: true }), 136000, 200000, 0, 0],
  ['음수·빈값 방어', o('day', C(-3, '', 'x', 1), 'senior', { k: -1, cars: -2 }), 49000, 49000, 0, 0],
];
for (const [name, input, tickets, total, discounted, notes] of cases) {
  const r = calc(input);
  assert.strictEqual(r.tickets, tickets, name + ' tickets=' + r.tickets);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  assert.strictEqual(r.discounted, discounted, name + ' discounted=' + r.discounted);
  assert.strictEqual(r.notes.length, notes, name + ' notes=' + r.notes.length);
  console.log('PASS', name, '자유이용권', r.tickets, '총액', r.total, '할인인원', r.discounted, r.notes.join(' '));
}
const an = (cnt, v) => calc(o('day', cnt, 'none', { visits: v })).annual[0];
let a = an(C(1, 0, 0), 4); assert.ok(a.annual > a.day);
a = an(C(1, 0, 0), 5); assert.ok(a.day > a.annual); console.log('PASS 어른 연간회원 본전 5회째', a.day, '>', a.annual);
a = an(C(0, 1, 0), 4); assert.ok(a.annual > a.day); a = an(C(0, 1, 0), 5); assert.ok(a.day > a.annual); console.log('PASS 청소년 5회째', a.day);
a = an(C(0, 0, 1), 4); assert.ok(a.annual > a.day); a = an(C(0, 0, 1), 5); assert.ok(a.day > a.annual); console.log('PASS 어린이 5회째', a.day);
const vals = { 'ew-time': 'day', 'ew-adult': '2', 'ew-teen': '0', 'ew-child': '1', 'ew-senior': '0', 'ew-infant': '1', 'ew-disc': 'none', 'ew-k': '1', 'ew-cprice': '0', 'ew-cn': '0', 'ew-tower': '0', 'ew-cars': '0', 'ew-visits': '1' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['ew-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('총 137,000원'));
assert.ok(outP.some(s => s.includes('35개월 이하 1명')));
console.log('PASS UI');
