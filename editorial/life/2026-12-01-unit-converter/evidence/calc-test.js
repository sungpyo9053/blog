// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); console.log('JSON-LD OK, Q', faq.mainEntity.length);
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(h3faq, faq.mainEntity.length); console.log('FAQ h3 == JSON-LD Q:', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { conv, ftin } = window.unitConv;
// 기대값은 인용한 정의에서 직접 계산: in=25.4mm, ft=0.3048m, yd=0.9144m, mi=1.609344km(국표원),
// 평=400/121㎡·근=600g·돈=3.75g(KRISS), lb=0.45359237kg·℉=℃×9/5+32(석유관리원), ha=1e4㎡·h=3600s·k=1e3(KRISS SI),
// 에이커≒4046㎡·온스=28.349g·갤런=3.785412L(국표원)
const cases = [
  ['1in → mm', 'len', 1, 'in', 'mm', false, 25.4],
  ['1ft → m', 'len', 1, 'ft', 'm', false, 0.3048],
  ['1yd → m', 'len', 1, 'yd', 'm', false, 0.9144],
  ['1mi → km', 'len', 1, 'mi', 'km', false, 1.609344],
  ['1ft → in', 'len', 1, 'ft', 'in', false, 12],
  ['165cm → in', 'len', 165, 'cm', 'in', false, 165 / 2.54],
  ['6ft → cm', 'len', 6, 'ft', 'cm', false, 182.88],
  ['65in → cm', 'len', 65, 'in', 'cm', false, 165.1],
  ['150yd → m', 'len', 150, 'yd', 'm', false, 137.16],
  ['30평 → ㎡', 'area', 30, 'py', 'm2', false, 12000 / 121],
  ['84㎡ → 평', 'area', 84, 'm2', 'py', false, 84 * 121 / 400],
  ['100㎡ → 평', 'area', 100, 'm2', 'py', false, 30.25],
  ['1ha → 평', 'area', 1, 'ha', 'py', false, 3025],
  ['1ft² → ㎡', 'area', 1, 'ft2', 'm2', false, 0.09290304],
  ['1에이커 → ㎡(근삿값)', 'area', 1, 'ac', 'm2', false, 4046],
  ['1근 → g', 'mass', 1, 'geun', 'g', false, 600],
  ['1근 → 돈', 'mass', 1, 'geun', 'don', false, 160],
  ['10돈 → g', 'mass', 10, 'don', 'g', false, 37.5],
  ['1lb → kg', 'mass', 1, 'lb', 'kg', false, 0.45359237],
  ['1kg → lb', 'mass', 1, 'kg', 'lb', false, 1 / 0.45359237],
  ['1oz → g', 'mass', 1, 'oz', 'g', false, 28.349],
  ['1gal → L', 'vol', 1, 'gal', 'l', false, 3.785412],
  ['2L → mL', 'vol', 2, 'l', 'ml', false, 2000],
  ['36.5℃ → ℉', 'temp', 36.5, 'c', 'f', false, 97.7],
  ['0℃ → ℉', 'temp', 0, 'c', 'f', false, 32],
  ['100℉ → ℃', 'temp', 100, 'f', 'c', false, 340 / 9],
  ['-40℉ → ℃', 'temp', -40, 'f', 'c', false, -40],
  ['100km/h → mph', 'speed', 100, 'kmh', 'mph', false, 100000 / 1609.344],
  ['60mph → km/h', 'speed', 60, 'mph', 'kmh', false, 60 * 1.609344],
  ['1mph → m/s', 'speed', 1, 'mph', 'ms', false, 0.44704],
  ['10m/s → km/h', 'speed', 10, 'ms', 'kmh', false, 36],
  ['1GB → MB (1000)', 'data', 1, 'GB', 'MB', false, 1000],
  ['1GB → MB (1024)', 'data', 1, 'GB', 'MB', true, 1024],
  ['1GB → B (1024)', 'data', 1, 'GB', 'B', true, 1073741824],
  ['1KB → B (1000)', 'data', 1, 'KB', 'B', false, 1000],
  ['1TB → GB (1000바이트를 1024로 다시 나눔)', 'data', conv('data', 1, 'TB', 'B', false), 'B', 'GB', true, 1e12 / Math.pow(1024, 3)],
];
for (const [name, c, v, f, t, bin, exp] of cases) {
  const r = conv(c, v, f, t, bin);
  assert.ok(Math.abs(r - exp) <= 1e-9 * Math.max(1, Math.abs(exp)), name + ' got ' + r + ' expected ' + exp);
  console.log('PASS', name, '=', +r.toPrecision(10));
}
console.log('변환 케이스', cases.length, '개 통과');
// 피트·인치 조합과 표 반올림 값
const fi = ftin(165); assert.strictEqual(fi[0], 5); assert.strictEqual(Math.round(fi[1] * 100) / 100, 4.96);
const fi2 = ftin(175); assert.strictEqual(fi2[0], 5); assert.strictEqual(Math.round(fi2[1] * 100) / 100, 8.9);
const r2 = (x) => Math.round(x * 100) / 100;
assert.strictEqual(r2(conv('area', 30, 'py', 'm2')), 99.17);
assert.strictEqual(r2(conv('area', 84, 'm2', 'py')), 25.41);
assert.strictEqual(r2(conv('speed', 100, 'kmh', 'mph')), 62.14);
assert.strictEqual(r2(conv('speed', 60, 'mph', 'kmh')), 96.56);
assert.strictEqual(r2(conv('speed', 70, 'mph', 'kmh')), 112.65);
assert.strictEqual(r2(conv('temp', 350, 'f', 'c')), 176.67);
assert.strictEqual(r2(conv('area', 500, 'ft2', 'm2')), 46.45);
assert.strictEqual(r2(conv('area', 500, 'ft2', 'py')), 14.05);
assert.strictEqual(r2(conv('area', 1, 'ac', 'py')), 1223.92);
assert.strictEqual(r2(1e12 / Math.pow(1024, 3)), 931.32);
console.log('PASS 피트·인치 조합 2개, 본문·표 반올림 값 10개');
// UI 렌더 확인 — 최소 DOM 스텁
const outP = [];
function mk(id) { return { id, value: '', style: {}, children: [], appendChild(o) { this.children.push(o); if (id === 'uc-out') outP.push(o.textContent); }, addEventListener(e, fn) { this['on' + e] = fn; }, set innerHTML(v) { this.children = []; if (id === 'uc-out') outP.length = 0; } }; }
const els = { 'uc-out': mk('uc-out'), 'uc-cat': mk('uc-cat'), 'uc-val': mk('uc-val'), 'uc-from': mk('uc-from') };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값(165cm):', outP.join(' | '));
assert.ok(outP.join().includes('5피트 4.96인치'));
els['uc-cat'].value = 'data'; els['uc-cat'].onchange();
console.log('UI 데이터(1GB):', outP.join(' | '));
assert.ok(outP.join().includes('1,024 (1024 기준)'));
els['uc-cat'].value = 'temp'; els['uc-cat'].onchange();
console.log('UI 온도(36.5℃):', outP.join(' | '));
assert.ok(outP.join().includes('97.7'));
els['uc-val'].value = 'abc'; els['uc-val'].oninput();
assert.ok(outP.join().includes('숫자를 입력'));
console.log('ALL PASS');
