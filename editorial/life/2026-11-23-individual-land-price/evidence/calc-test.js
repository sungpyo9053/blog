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
assert.strictEqual(faq, (html.split('id="faq"')[1].split('<script')[0].match(/<h3>/g) || []).length);
console.log('PASS JSON-LD 파싱, FAQ', faq, '개 본문과 일치');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.landPriceCalc;
const cases = [
  ['본문 예: 330㎡ x 1,250,000', [330, 'sqm', 1250000, 100], { total: 412500000, mine: 412500000, pyeong: 100, perPyeong: 4125000, landTaxBase: 288750000 }],
  ['절반 지분', [330, 'sqm', 1250000, 50], { total: 412500000, mine: 206250000, landTaxBase: 144375000 }],
  ['평 입력 100평 -> 330㎡', [100, 'py', 1250000, 100], { sqm: 330, total: 412500000 }],
  ['지분 미입력(NaN) -> 100%', [10, 'sqm', 1000, NaN], { share: 100, mine: 10000 }],
  ['지분 150 -> 100 상한', [10, 'sqm', 1000, 150], { share: 100, mine: 10000 }],
  ['국토부 2026(안) 최고가 필지 169.3㎡ x 188,400,000', [169.3, 'sqm', 188400000, 100], { total: 31896120000 }],
  ['소수 면적 반올림 12.34㎡ x 777', [12.34, 'sqm', 777, 100], { total: 9588 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-6, name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'lp-area': '330', 'lp-unit': 'sqm', 'lp-price': '1250000', 'lp-share': '100' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['lp-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('412,500,000원'));
assert.ok(!outP.join().includes('지분('));
vals['lp-share'] = '50'; outP.length = 0; eval(src);
assert.ok(outP.join().includes('206,250,000원'));
vals['lp-area'] = ''; outP.length = 0; eval(src);
assert.ok(outP.join().includes('면적을 입력'));
console.log('PASS UI 지분·빈 입력');
