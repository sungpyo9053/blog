// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
console.log('JSON-LD FAQ', faq); assert.ok(faq >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.keroCalc, cont = window.keroContainers;
const cases = [
  ['예시: 1.0L/h x 8h x 30일 @1570.26', [1570.26, 1, 8, 30, 0], { liters: 240, cost: 376862, drums: 1.2, cans20: 12, daysPerDrum: 25 }],
  ['예시: 1.0L/h x 5h x 30일', [1570.26, 1, 5, 30, 0], { liters: 150, cost: 235539 }],
  ['지원금 차감 100,000', [1570.26, 1, 8, 30, 100000], { net: 276862 }],
  ['지원금이 더 크면 0', [1570.26, 1, 1, 1, 999999], { net: 0 }],
  ['가동 0시간 -> 0, 드럼 일수 없음', [1570.26, 1, 0, 30, 0], { liters: 0, cost: 0, daysPerDrum: null }],
  ['24시간 상한', [1000, 1, 30, 1, 0], { liters: 24 }],
  ['빈 입력', ['', '', '', '', ''], { liters: 0, cost: 0, net: 0 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표 값 검산 (드럼 200L 환산)
const table = { 1570.26: [314052, 31405, 28265], 1703.61: [340722], 1541.82: [308364], 1558.19: [311638], 1621.63: [324326] };
for (const p of Object.keys(table)) { const c = cont(+p); table[p].forEach((v, i) => assert.strictEqual([c.drum200, c.can20, c.can18][i], v, p)); }
assert.strictEqual(Math.round((1703.61 - 1541.82) * 200), 32358);
assert.strictEqual(Math.round((1703.61 - 1541.82) * 200 * 3), 97074);
assert.strictEqual(Math.round((1572.12 - 1295.18) * 200), 55388);
console.log('PASS 본문 용기·차이 값');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'kh-price': '1570.26', 'kh-lph': '1.0', 'kh-hours': '8', 'kh-days': '30', 'kh-voucher': '0' };
const outP = []; let opts = 0;
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { if (id === 'kh-region') opts++; else outP.push(p.textContent); } });
const els = {}; ['kh-out', 'kh-region', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('지역 옵션', opts); assert.strictEqual(opts, 17);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('376,862원'));
