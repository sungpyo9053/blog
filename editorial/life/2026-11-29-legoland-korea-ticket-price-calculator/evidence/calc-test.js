// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faqN = JSON.parse(ld).mainEntity.length;
assert.ok(faqN >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.legolandCalc;
const O = (o) => Object.assign({ date: '2026-11-29', buy: 'online', adult: 2, child: 1, disc: 'none', dcount: 0, parkH: 0, visits: 1 }, o);
const cases = [
  ['11/29 온라인 대인2+소인1', O({}), 'ok', 96000],
  ['11/29 당일 대인2+소인1', O({ buy: 'onsite' }), 'ok', 120000],
  ['12/25 온라인 대인2+소인2', O({ date: '2026-12-25', child: 2 }), 'ok', 128000],
  ['강원도민 4명', O({ adult: 0, child: 0, disc: 'gangwon', dcount: 4 }), 'ok', 108000],
  ['나라사랑 5명(4명 한도)', O({ adult: 0, child: 0, disc: 'hero', dcount: 5 }), 'ok', 27000 * 4 + 32000],
  ['장애인 1 + 보호자 무료 + 부모 1 온라인', O({ adult: 1, child: 0, disc: 'disabled', dcount: 1 }), 'ok', 72000],
  ['수능 본인+동반2 12/5 현장', O({ date: '2026-12-05', buy: 'onsite', adult: 0, child: 0, disc: 'suneung', dcount: 3 }), 'ok', 80000],
  ['수능 12/19 이후 일반요금', O({ date: '2026-12-19', buy: 'onsite', adult: 0, child: 0, disc: 'suneung', dcount: 2 }), 'ok', 80000],
  ['휴장일 12/1(화)', O({ date: '2026-12-01' }), 'closed', 0],
  ['휴장 11/18', O({ date: '2026-11-18' }), 'before', 0],
  ['3/14 마지막 겨울가', O({ date: '2027-03-14' }), 'ok', 96000],
  ['3/20 운영일 가격 미확인', O({ date: '2027-03-20' }), 'noprice', 0],
  ['3/28 이후 미확인', O({ date: '2027-04-03' }), 'unknown', 0],
  ['음수·빈값 방어', O({ adult: -3, child: 'x' }), 'ok', 0],
];
for (const [name, o, st, total] of cases) {
  const r = calc(o);
  assert.strictEqual(r.status, st, name + ' status=' + r.status);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  console.log('PASS', name, r.status, r.total.toLocaleString('ko-KR') + '원', r.warn.join(' / '));
}
assert.strictEqual(calc(O({ parkH: 8 })).parking, 12000);
assert.strictEqual(calc(O({ parkH: 3 })).parking, 6000);
assert.strictEqual(calc(O({ parkH: 1 })).parking, 0);
console.log('PASS 주차 1h 0원 / 3h 6,000원 / 8h 12,000원');
let a = calc(O({ adult: 1, child: 0, visits: 3 }));
assert.ok(a.annualPass > a.annualDay);
a = calc(O({ adult: 1, child: 0, visits: 4 }));
assert.ok(a.annualDay > a.annualPass);
console.log('PASS 싱글 패스 본전 겨울 온라인 4회째', a.annualDay, a.annualPass);
a = calc(O({ adult: 1, child: 0, disc: 'disabled', dcount: 1 }));
assert.strictEqual(a.people, 3);
assert.strictEqual(a.warn.length, 1);
console.log('PASS 장애인 우대 인원·온라인 경고');
const vals = { 'll-date': '2026-11-29', 'll-buy': 'online', 'll-adult': '2', 'll-child': '1', 'll-infant': '1', 'll-disc': 'none', 'll-dcount': '0', 'll-park': '6', 'll-visits': '1' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['ll-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('96,000원'));
console.log('FAQ JSON-LD 항목', faqN);
