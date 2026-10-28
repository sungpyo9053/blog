// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^']*'/g)) if (m.includes('<')) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.basicLivelihoodCalc;
// 2026 공식 표(보건복지부 수급자선정기준) — 중위소득 × 비율 검산 포함
const med26 = [2564238, 4199292, 5359036, 6494738, 7556719, 8555952];
const med27 = [2736042, 4480645, 5718091, 6929885, 8063019, 9129201];
for (const [y, med] of [['2026', med26], ['2027', med27]]) for (let s = 1; s <= 6; s++) {
  const r = calc(y, s, 0);
  assert.strictEqual(r.median, med[s - 1]);
  for (const [k, pct] of [['living', 0.32], ['medical', 0.40], ['housing', 0.48], ['edu', 0.50]])
    assert.ok(Math.abs(r[k] - med[s - 1] * pct) < 1, y + ' ' + s + '인 ' + k + ' ' + r[k] + ' vs ' + med[s - 1] * pct);
  assert.strictEqual(r.livingPay, r.living);
}
console.log('PASS 2026·2027 표 48개 값이 중위소득 × 32/40/48/50%와 1원 이내 일치');
const cases = [
  ['1인 2026 소득인정액 30만', '2026', 1, 300000, { okLiving: true, livingPay: 520556 }],
  ['복지부 예시 B씨 30세 1인 소득인정액 28만 -> 약 54만', '2026', 1, 280000, { livingPay: 540556 }],
  ['복지부 예시 C씨 4인 소득인정액 169만 -> 약 39만', '2026', 4, 1690000, { okLiving: true, livingPay: 388316 }],
  ['경계: 1인 820,556 -> 충족 0원', '2026', 1, 820556, { okLiving: true, livingPay: 0 }],
  ['경계: 1인 820,557 -> 생계 초과, 의료 충족', '2026', 1, 820557, { okLiving: false, okMedical: true, livingPay: 0 }],
  ['1인 120만 -> 주거·교육만', '2026', 1, 1200000, { okLiving: false, okMedical: false, okHousing: true, okEdu: true }],
  ['1인 130만 -> 전부 초과', '2026', 1, 1300000, { okHousing: false, okEdu: false }],
  ['2027 1인 0원 -> 875,533', '2027', 1, 0, { livingPay: 875533 }],
  ['2027 4인 0원 -> 2,217,563', '2027', 4, 0, { livingPay: 2217563 }],
];
for (const [name, y, s, inc, exp] of cases) {
  const r = calc(y, s, inc);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값(2026, 1인, 30만원) 렌더 확인 — 최소 DOM 스텁
const vals = { 'bl-year': '2026', 'bl-size': '1', 'bl-inc': '300000' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['bl-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('520,556원'));
