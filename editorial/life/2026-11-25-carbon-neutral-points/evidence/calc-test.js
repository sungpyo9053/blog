// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
  if (/[&<]/.test(m[1])) throw new Error('& or < in JSON-LD');
  const j = JSON.parse(m[1]); assert.ok(j.mainEntity.length >= 6); console.log('PASS JSON-LD FAQ', j.mainEntity.length);
}
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.carbonPointCalc;
// 단가표: 규정 별표2 제3호
const unit = Object.fromEntries(window.carbonPointItems.map(i => [i[0], i[1]]));
assert.deepStrictEqual(unit, { 'cp-er': 10, 'cp-tb': 300, 'cp-cr': 100, 'cp-rf': 500, 'cp-rc': 500, 'cp-pc': 500, 'cp-ev': 100, 'cp-bk': 100, 'cp-rr': 300, 'cp-gp': 500, 'cp-rm': 100, 'cp-bg': 50, 'cp-zw': 100, 'cp-ph': 1000, 'cp-tr': 3000, 'cp-sl': 10000 });
console.log('PASS 단가 16개 = 규정 별표2');
const cases = [
  ['기본값 전자영수증10·텀블러8·장바구니4', [[10, 10, 'm'], [300, 8, 'm'], [50, 4, 'm']], 0, { month: 2700, yearRaw: 32400, yearCapped: 32400, capMonth: null }],
  ['텀블러 20개/월 -> 72,000 한도 70,000', [[300, 20, 'm']], 0, { month: 6000, yearRaw: 72000, yearCapped: 70000, capMonth: 12 }],
  ['전자영수증 30건/월 -> 300원, 연 3,600', [[10, 30, 'm']], 0, { month: 300, yearRaw: 3600, yearCapped: 3600 }],
  ['이미 65,000 받음 + 월 3,000', [[300, 10, 'm']], 65000, { left: 5000, yearCapped: 5000, capMonth: 2 }],
  ['1년 항목만: 태양광1+나무심기2', [[10000, 1, 'y'], [3000, 2, 'y']], 0, { month: 0, once: 16000, yearRaw: 16000, yearCapped: 16000 }],
  ['재활용 2.5kg 소수', [[300, 2.5, 'm']], 0, { month: 750 }],
  ['이미 한도 초과 입력 -> 남은 0', [[300, 1, 'm']], 80000, { left: 0, yearCapped: 0, capMonth: 0 }],
  ['음수·빈값은 0 처리', [[300, -3, 'm'], [500, NaN, 'm']], NaN, { month: 0, left: 70000 }],
];
for (const [name, rows, used, exp] of cases) {
  const r = calc(rows, used);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'cp-er': '10', 'cp-tb': '8', 'cp-bg': '4', 'cp-used': '0' };
const outP = [];
const el = id => ({ value: vals[id] !== undefined ? vals[id] : '0', style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; window.carbonPointItems.map(i => i[0]).concat(['cp-used', 'cp-out']).forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('2,700원'));
assert.ok(outP.join().includes('32,400원'));
console.log('ALL PASS');
