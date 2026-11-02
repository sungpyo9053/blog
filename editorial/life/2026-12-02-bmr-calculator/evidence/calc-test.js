// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g)) if (lit.indexOf('<') >= 0) throw new Error('< in string literal ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.bmrCalc, eer = window.bmrEer;
// 2025 KDRI 1권 표 12·13 산출값 재현 (저활동적 lv=1)
const kdri = [
  ['m', 24, 174.8, 69.1, 2701], ['m', 39.5, 173.4, 68.0, 2525], ['m', 57, 169.2, 64.7, 2275],
  ['f', 24, 161.5, 55.9, 2087], ['f', 39.5, 160.0, 54.8, 1957], ['f', 57, 156.7, 52.5, 1785],
  ['m', 69.5, 166.5, 62.7, 2104], ['m', 75, 163.5, 60.4, 1993], ['f', 69.5, 153.0, 50.1, 1643], ['f', 75, 146.9, 46.2, 1515],
];
for (const [s, a, h, w, exp] of kdri) { assert.strictEqual(eer(s, a, h, w, 1), exp, `KDRI ${s} ${a}세`); }
console.log('PASS KDRI 표 12·13 산출값 10개');
const cases = [
  ['남 30세 175cm 70kg 체지방 20% 저활동(1.5)', ['m', 30, 175, 70, 20, 1.5], { mifflin: 1649, bee: 1691, ffm: 56, ffmRee: 1516, lv: 1, pa: 1.11, tdeeMifflin: 2473, eer: 2660, kdriSet: 2500 }],
  ['여 30세 160cm 55kg 체지방 없음 저활동(1.5)', ['f', 30, 160, 55, NaN, 1.5], { mifflin: 1239, bee: 1280, ffm: null, ffmRee: null, lv: 1, pa: 1.12, eer: 2024, kdriSet: 1900 }],
  ['남 24세 비활동(1.2) -> PA 1.0', ['m', 24, 174.8, 69.1, NaN, 1.2], { lv: 0, pa: 1, kdriSet: 2600 }],
  ['여 80세 매우활동(1.9) -> PA 1.45, 75+ 설정값', ['f', 80, 150, 45, NaN, 1.9], { lv: 3, pa: 1.45, kdriSet: 1500 }],
  ['남 64/65세 경계', ['m', 65, 170, 65, NaN, 1.75], { lv: 2, pa: 1.25, kdriSet: 2000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.ok(r[k] === exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 예시값: 미플린 원식 vs 단순식 차이 확인(참고 출력)
console.log('참고: 미플린 원 회귀식 남30/175/70 =', (9.99 * 70 + 6.25 * 175 - 4.92 * 30 + 166 - 161).toFixed(1));
// UI 렌더 확인 — 최소 DOM 스텁
function render(vals) {
  const outP = [];
  const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
  const els = { 'bmr-out': el('bmr-out') }; Object.keys(vals).forEach(id => els[id] = el(id));
  global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
  eval(src);
  return outP;
}
let o = render({ 'bmr-sex': 'm', 'bmr-age': '30', 'bmr-h': '175', 'bmr-w': '70', 'bmr-bf': '', 'bmr-pal': '1.5' });
console.log('UI 기본값 출력:', o.join(' | '));
assert.ok(o.join().includes('1,649kcal') && o.join().includes('1,691kcal') && o.join().includes('2,660kcal'));
o = render({ 'bmr-sex': 'f', 'bmr-age': '30', 'bmr-h': '160', 'bmr-w': '55', 'bmr-bf': '28', 'bmr-pal': '1.2' });
console.log('UI 여자+체지방:', o.join(' | '));
o = render({ 'bmr-sex': 'm', 'bmr-age': '17', 'bmr-h': '170', 'bmr-w': '60', 'bmr-bf': '', 'bmr-pal': '1.5' });
console.log('UI 17세:', o.join(' | '));
assert.ok(o[0].includes('19세 이상'));
console.log('ALL PASS');
