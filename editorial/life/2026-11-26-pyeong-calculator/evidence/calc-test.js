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
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.pyeongCalc;
const cases = [
  ['84㎡ -> 25.41평', 'sqm', 84, 0, 0, { py: 25.41, approx: 25.45 }],
  ['59㎡ -> 17.85평', 'sqm', 59, 0, 0, { py: 17.85, approx: 17.88 }],
  ['114㎡ -> 34.48평', 'sqm', 114, 0, 0, { py: 34.48, approx: 34.55 }],
  ['85㎡ -> 25.71평', 'sqm', 85, 0, 0, { py: 25.71 }],
  ['100㎡ -> 30.25평', 'sqm', 100, 0, 0, { py: 30.25 }],
  ['1평 -> 3.31㎡', 'py', 1, 0, 0, { sqm: 3.31, approx: 3.3 }],
  ['100평 -> 330.58㎡', 'py', 100, 0, 0, { sqm: 330.58 }],
  ['가정: 전용84+주거공용28+기타12', 'sqm', 84, 28, 12, { supply: 112, supplyPy: 33.88, contract: 124, contractPy: 37.51, ratio: 75 }],
  ['주거공용 없이 기타만 -> 공급·계약 0', 'sqm', 84, 0, 12, { supply: 0, contract: 0 }],
];
for (const [name, dir, v, pub, etc, exp] of cases) {
  const r = calc(dir, v, pub, etc);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 400/121 로 계산해도 84㎡ 값이 같은지
assert.strictEqual(Math.round(84 * 121 / 400 * 100) / 100, 25.41);
// 본문 표 값 검산 (㎡ -> 평)
const t1 = [[39, '11.80'], [49, '14.82'], [59, '17.85'], [74, '22.38'], [84, '25.41'], [85, '25.71'], [101, '30.55'], [114, '34.48'], [135, '40.84']];
for (const [m, p] of t1) { assert.strictEqual(calc('sqm', m, 0, 0).py.toFixed(2), p, m + '㎡'); assert.ok(html.includes('<td>' + m + '㎡</td><td>' + p + '평</td>'), 'table ' + m); }
const t2 = [[1, '3.31'], [10, '33.06'], [20, '66.12'], [30, '99.17'], [40, '132.23'], [50, '165.29'], [100, '330.58']];
for (const [p, m] of t2) { assert.strictEqual(calc('py', p, 0, 0).sqm.toFixed(2), m, p + '평'); assert.ok(html.includes('<td>' + p + '평</td><td>' + m + '㎡</td>'), 'table ' + p); }
console.log('PASS 본문 표 값 16개');
// 평당 가격 환산
assert.strictEqual(Math.floor(10000000 / 3.3058 / 10000), 302);
assert.strictEqual(Math.floor(30000000 / 3.3058 / 10000), 907);
console.log('PASS 평당 1,000만원 -> ㎡당 302만원, 3,000만원 -> 907만원');
// UI 렌더 — 최소 DOM 스텁
function ui(vals) {
  const outP = [];
  const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
  const els = {}; ['py-out', 'py-b59', 'py-b84', 'py-b114', ...Object.keys(vals)].forEach(id => els[id] = el(id));
  global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
  eval(src);
  return outP.join(' | ');
}
const base = { 'py-dir': 'sqm', 'py-val': '84', 'py-type': 'ex', 'py-pub': '', 'py-etc': '' };
let o = ui(base); console.log('UI 기본값:', o); assert.ok(o.includes('25.41평'));
o = ui({ ...base, 'py-pub': '28', 'py-etc': '12' }); console.log('UI 공용면적 입력:', o); assert.ok(o.includes('33.88평') && o.includes('37.51평') && o.includes('75%'));
o = ui({ ...base, 'py-dir': 'py', 'py-val': '34', 'py-type': 'sup' }); console.log('UI 평->㎡ 공급:', o); assert.ok(o.includes('112.4㎡'));
o = ui({ ...base, 'py-type': 'con', 'py-pub': '28' }); console.log('UI 계약+공용:', o); assert.ok(o.includes('전용면적으로 골랐을 때만'));
o = ui({ ...base, 'py-val': '' }); console.log('UI 빈 값:', o); assert.ok(o.includes('입력해'));
console.log('ALL PASS');
