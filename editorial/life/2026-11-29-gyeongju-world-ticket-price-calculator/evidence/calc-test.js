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
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq.length, h3faq); console.log('PASS FAQ JSON-LD', faq.length, '= h3', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.gyeongjuWorldCalc;
const C = (a, t, c) => ({ adult: a, teen: t, child: c });
const Z = C(0, 0, 0);
const cases = [
  ['종일권 어른2+어린이1', ['day', 'none', C(2, 0, 1), Z, 0], 147000, 0],
  ['오후권 어른2+어린이1', ['pm', 'none', C(2, 0, 1), Z, 0], 107000, 0],
  ['종일권 어른2+청소년1+어린이1', ['day', 'none', C(2, 1, 1), Z, 0], 194000, 0],
  ['투숙객 어른2+청소년1+어린이1', ['day', 'stay', Z, C(2, 1, 1), 0], 136000, 0],
  ['꽃보다60 2명+정가 어린이1', ['day', 's60', C(0, 0, 1), C(2, 0, 0), 0], 59000, 0],
  ['장애인 청소년+보호자 어른', ['day', 'dis', Z, C(1, 1, 0), 0], 51000, 0],
  ['국가유공자 어린이1', ['day', 'merit', Z, C(0, 0, 1), 0], 19000, 0],
  ['문화누리 어른2+어린이2', ['day', 'nuri', Z, C(2, 0, 2), 0], 110000, 0],
  ['제휴카드 어른1+정가 어린이1', ['day', 'card', C(0, 0, 1), C(1, 0, 0), 0], 66000, 0],
  ['제휴카드 어린이(대상 아님)', ['day', 'card', Z, C(0, 0, 1), 0], 0, 1],
  ['오후권+장애인(우대 미적용)', ['pm', 'dis', Z, C(1, 0, 0), 0], 0, 1],
  ['수험생1+부모2', ['day', 'exam', Z, C(2, 1, 0), 0], 78000, 0],
  ['인스타 청소년1', ['day', 'insta', Z, C(0, 1, 0), 0], 34000, 0],
  ['임신부 어린이칸(대상 아님)', ['day', 'preg', Z, C(0, 0, 1), 0], 0, 1],
  ['음수·빈값 방어', ['day', 'none', C(-3, '', 'x'), Z, -2], 0, 0],
];
for (const [name, args, total, unknown] of cases) {
  const r = calc(...args);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  assert.strictEqual(r.unknown.length, unknown, name + ' unknown=' + r.unknown.length);
  console.log('PASS', name, r.total.toLocaleString('ko-KR') + '원', r.unknown.join(','));
}
let a = calc('day', 'none', C(2, 0, 1), Z, 4);
assert.strictEqual(a.dayTotal, 588000); assert.strictEqual(a.annualTotal, 550000);
console.log('PASS 연간권 비교 어른2+어린이1 4회: 1일권', a.dayTotal, '연간권', a.annualTotal);
assert.ok(calc('day', 'none', C(1, 0, 0), Z, 3).annualTotal > calc('day', 'none', C(1, 0, 0), Z, 3).dayTotal);
assert.ok(calc('day', 'none', C(1, 0, 0), Z, 4).dayTotal > calc('day', 'none', C(1, 0, 0), Z, 4).annualTotal);
assert.ok(calc('day', 'none', C(0, 0, 1), Z, 4).dayTotal > calc('day', 'none', C(0, 0, 1), Z, 4).annualTotal);
console.log('PASS 어른·어린이 본전 4회째');
assert.strictEqual(calc('day', 'dis', Z, C(3, 0, 0), 0).warn.length, 1);
assert.strictEqual(calc('day', 'dis', Z, C(2, 0, 0), 0).warn.length, 0);
assert.strictEqual(calc('day', 'nuri', Z, C(3, 0, 2), 0).warn.length, 1);
console.log('PASS 동반 인원 경고');
const vals = { 'gw-base': 'day', 'gw-disc': 'none', 'gw-adult': '2', 'gw-teen': '1', 'gw-child': '1', 'gw-d-adult': '0', 'gw-d-teen': '0', 'gw-d-child': '0', 'gw-infant': '1', 'gw-visits': '1' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['gw-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 출력(어른2·청소년1·어린이1·영아1):', outP.join(' | '));
assert.ok(outP[0].includes('194,000원'));
