// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
assert.ok(faq >= 6); console.log('PASS JSON-LD FAQ', faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const Q = window.qooqooCalc, S = Q.stores;
const idx = name => { const i = S.findIndex(s => s[1] === name); assert.ok(i >= 0, name); return i; };
assert.strictEqual(S.length, 84); assert.strictEqual(S.filter(s => s[2] === 1).length, 17);
const cases = [
  ['송파점 주말 성인2+초등1+미취학1', ['송파점', 'weekend', 2, 1, 1], 102600, 0],
  ['산본점 주말 성인2+초등1+미취학1', ['산본점', 'weekend', 2, 1, 1], 78700, 0],
  ['골드 안산점 주말 성인2+초등1+미취학1', ['안산점', 'weekend', 2, 1, 1], 105600, 0],
  ['대구북구점 평일점심 2+1+1', ['대구북구점', 'lunch', 2, 1, 1], 78700, 0],
  ['대구북구점 주말 2+1+1', ['대구북구점', 'weekend', 2, 1, 1], 98700, 0],
  ['골드 분당점 평일저녁 성인4', ['분당점', 'dinner', 4, 0, 0], 131600, 0],
  ['골드 분당점 주말 성인4', ['분당점', 'weekend', 4, 0, 0], 151600, 0],
  ['산본점 평일점심 2+2', ['산본점', 'lunch', 2, 2, 0], 71600, 0],
  ['일산호수공원점 평일점심 2+2', ['일산호수공원점', 'lunch', 2, 2, 0], 95600, 0],
  ['대전점 평일저녁 초등(런치/디너 동일 15,900)', ['대전점', 'dinner', 0, 1, 0], 15900, 0],
  ['포항점 평일저녁 초등(디너=주말 17,900)', ['포항점', 'dinner', 0, 1, 0], 17900, 0],
  ['광복점 초등 확인 불가', ['광복점', 'weekend', 1, 1, 0], 29900, 1],
  ['파주운정점 평일저녁 초등 확인 불가', ['파주운정점', 'dinner', 1, 1, 0], 33900, 1],
  ['광주수완점 가격 비어 있음', ['광주수완점', 'lunch', 2, 0, 1], 0, 2],
  ['음수·빈값 방어', ['송파점', 'lunch', -3, '', 'x'], 0, 0],
];
for (const [name, [st, t, a, k, p], total, unknown] of cases) {
  const r = Q.calc(idx(st), t, a, k, p);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  assert.strictEqual(r.unknown.length, unknown, name + ' unknown=' + r.unknown.length);
  console.log('PASS', name, r.total.toLocaleString('ko-KR') + '원', r.unknown.join(','));
}
let g = Q.range('all', 'weekend', 2, 1, 1);
assert.strictEqual(g.lo.total, 78700); assert.strictEqual(g.hi.total, 105600);
console.log('PASS 전체 주말 2+1+1 최저', g.lo.name, g.lo.total, '최고', g.hi.name, g.hi.total);
g = Q.range('gold', 'lunch', 1, 0, 0);
assert.strictEqual(g.lo.total, 27900); assert.strictEqual(g.hi.total, 29900);
console.log('PASS 골드 평일점심 성인1 범위', g.lo.total, g.hi.total);
g = Q.range('normal', 'lunch', 1, 0, 0);
assert.strictEqual(g.lo.total, 21900); assert.strictEqual(g.hi.total, 29900);
console.log('PASS 일반 평일점심 성인1 범위', g.lo.total, g.hi.total);
// UI 렌더 검산 (가짜 DOM)
function mk(v) { return { value: v, children: [], addEventListener() {}, set innerHTML(x) { this.children = []; }, appendChild(c) { this.children.push(c); } }; }
const els = { 'qq-type': mk('all'), 'qq-store': mk(''), 'qq-time': mk('weekend'), 'qq-adult': mk('2'), 'qq-kid': mk('1'), 'qq-pre': mk('1'), 'qq-out': mk('') };
const txt = c => c.textContent || (c.children[0] ? c.children[0].textContent : '');
global.document = { getElementById: id => els[id], createElement: () => mk('') };
eval(src);
assert.strictEqual(els['qq-store'].children.length, 84);
const outT = els['qq-out'].children.map(txt);
console.log('UI 기본값 출력:', outT.join(' | '));
assert.ok(outT[0].includes('송파점') && outT[0].includes('102,600원'));
