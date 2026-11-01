// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하고, 내장 표를 KASI 조회 결과(396일)와 전수 대조
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
for (const s of scripts) { if (s.indexOf('&') >= 0) throw new Error('& in script'); if (/\n\s*\n/.test(s)) throw new Error('blank line in script'); if (s.indexOf('<') >= 0) throw new Error('< in script'); }
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD'); JSON.parse(ld);
global.window = {}; global.document = { getElementById: () => null };
eval(scripts[0]);
const C = window.sonCalc;
const rows = fs.readFileSync(path.join(__dirname, 'kasi-solc-2026-12_2027-12.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
let son = 0, wk = 0, hol = 0;
for (const r of rows) {
  const o = C.info(+r.SOLC_YYYY, +r.SOLC_MM, +r.SOLC_DD);
  assert.ok(o, 'null ' + r.SOLC_YYYY + r.SOLC_MM + r.SOLC_DD);
  assert.strictEqual(o.ly, +r.LUNC_YYYY); assert.strictEqual(o.lm, +r.LUNC_MM); assert.strictEqual(o.ld, +r.LUNC_DD);
  assert.strictEqual(o.len, +r.LUNC_EN_DD); assert.strictEqual(o.wd, r.SOLC_WEEK);
  if (o.son) { son++; if (o.weekend) wk++; else if (o.holiday) hol++; }
}
console.log('PASS 396일 음력 연·월·일·달길이·요일 KASI와 전부 일치');
assert.strictEqual(son, 74); assert.strictEqual(wk, 18); assert.strictEqual(hol, 2);
console.log('PASS 손없는날 74일, 주말 18일, 평일 공휴일 2일');
const counts = [[2026,12,6],[2027,1,6],[2027,2,6],[2027,3,5],[2027,4,6],[2027,5,5],[2027,6,6],[2027,7,5],[2027,8,7],[2027,9,5],[2027,10,5],[2027,11,6],[2027,12,6]];
for (const [y,m,n] of counts) assert.strictEqual(C.monthSon(y,m).length, n, y+'-'+m);
console.log('PASS 월별 개수', counts.map(c => c[1]+'월 '+c[2]).join(', '));
assert.strictEqual(C.monthSon(2027,8).map(o=>o.d).join(), '1,10,11,20,21,30,31');
assert.strictEqual(C.info(2026,11,30), null); assert.strictEqual(C.info(2028,1,1), null);
assert.strictEqual(C.info(2027,5,5).holiday, '어린이날'); assert.ok(C.info(2027,5,5).son);
assert.ok(!C.info(2026,12,25).son);
assert.strictEqual(C.near(2027,3,28,1).d, 5); assert.strictEqual(C.near(2027,3,28,-1).d, 27);
assert.strictEqual(C.near(2026,12,1,-1), null);
console.log('PASS 경계·공휴일·앞뒤 손없는날');
const d = C.deposit(1500000);
assert.deepStrictEqual(d, {deposit:150000,custBefore:150000,custDay:300000,bizBefore2:300000,bizBefore1:600000,bizDay:900000,bizNoNotice:1500000,late2h:900000});
console.log('PASS 계약금·위약금(표준약관 제6·9조) 150만원 예', JSON.stringify(d));
// UI 렌더 (최소 DOM 스텁)
function mk(v){ return { value: v, checked: false, style: {}, kids: [], addEventListener(){}, set innerHTML(x){ this.kids = []; }, appendChild(p){ this.kids.push(p.textContent); } }; }
const els = { 'sn-list': mk(), 'sn-month': mk('2027-11'), 'sn-wkonly': mk(), 'sn-date': mk('2027-03-27'), 'sn-day': mk(), 'dp-out': mk(), 'dp-fee': mk('1500000') };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
for (const s of scripts) eval(s);
console.log('UI 달 출력:', els['sn-list'].kids.join(' | '));
console.log('UI 날짜 출력:', els['sn-day'].kids.join(' | '));
console.log('UI 계약금 출력:', els['dp-out'].kids.join(' | '));
assert.ok(els['sn-day'].kids.join().includes('음력 2027년 2월 20일'));
assert.ok(els['dp-out'].kids.join().includes('150,000원'));
console.log('ALL PASS');
