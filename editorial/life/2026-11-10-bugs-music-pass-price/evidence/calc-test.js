// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^'\n]*'/g)) if (s.indexOf('<') >= 0) throw new Error('< in string ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.bugsPassCalc;
const cases = [
  ['무제한 정가 12개월', 'unl', 'auto', 12, 0, { monthly: 8690, total: 104280, save: 0 }],
  ['무제한 30일권 = 자동결제', 'unl', 'd30', 1, 0, { monthly: 8690, total: 8690 }],
  ['무제한 1년 할인 12개월 -> 15,648 절약', 'unl', 'year', 12, 0, { monthly: 7386, total: 88632, save: 15648 }],
  ['모바일 1년 할인 12개월', 'mob', 'year', 12, 0, { total: 77412, save: 13668 }],
  ['1년 할인 18개월: 13개월째부터 정가 가정', 'unl', 'year', 18, 0, { total: 88632 + 8690 * 6, later: 8690 }],
  ['오프라인은 1년 할인 없음 -> 정가', 'off', 'year', 12, 0, { monthly: 11990, total: 143880 }],
  ['크루 멤버 무제한 1개월', 'unl', 'crew', 1, 0, { monthly: 6490 }],
  ['크루 Premium 멤버', 'prem', 'crew', 1, 0, { monthly: 9900 }],
  ['Premium+오프라인 크루 없음 -> 정가', 'premoff', 'crew', 1, 0, { monthly: 17600 }],
  ['무제한 + MP3 10곡 1개월 = 14,740', 'unl', 'auto', 1, 6050, { monthly: 14740, total: 14740 }],
  ['MP3 5곡 자동결제 선택 -> 30일권 3,300', 'mp5', 'auto', 3, 6050, { monthly: 3300, total: 9900 }],
  ['개월 0 -> 오류', 'unl', 'auto', 0, 0, { ok: false }],
];
for (const [name, plan, pay, m, add, exp] of cases) {
  const r = calc(plan, pay, m, add);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ monthly: r.monthly, total: r.total, save: r.save, later: r.later, notes: r.notes }));
}
// 비교값: 12개월 무제한 멜론 104,280 / 지니 110,880 / FLO 104,280
assert.deepStrictEqual(calc('unl', 'auto', 12, 0).cmp.map(c => c[1]), [104280, 110880, 104280]);
console.log('PASS 비교값 12개월 무제한', JSON.stringify(calc('unl', 'auto', 12, 0).cmp));
// 크루 4인 합계 = 리더 정가 + 멤버 3
assert.strictEqual(calc('unl', 'auto', 1, 0).total + 3 * calc('unl', 'crew', 1, 0).total, 28160);
console.log('PASS 크루 4인 28,160');
// UI 기본값 렌더 (무제한, 자동결제, 12개월)
const vals = { 'bg-plan': 'unl', 'bg-pay': 'auto', 'bg-months': '12', 'bg-add': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['bg-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('104,280원'));
