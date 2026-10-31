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
assert.ok(faq >= 6); console.log('PASS JSON-LD FAQ', faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.activitySupportCalc;
// 시행규칙 별표 3 + 2026 사업안내 p.177·p.179
const course = [
  ['자격 없음', 'none', 24, 16, 10, 50, 150000],
  ['요양보호사', 'care', 20, 12, 10, 42, 120000],
  ['사회복지사', 'social', 20, 12, 10, 42, 120000],
  ['간호사', 'nurse', 20, 12, 10, 42, 120000],
  ['간호조무사', 'aide', 20, 12, 10, 42, 120000],
  ['유사 경력자', 'similar', 20, 12, 10, 42, 120000],
];
for (const [name, lic, t, s, p, tot, fee] of course) {
  const r = calc(lic, 40, 10320);
  assert.deepStrictEqual([r.theory, r.skill, r.practice, r.total, r.feeCap], [t, s, p, tot, fee], name);
  console.log('PASS', name, tot + 'h', '상한', fee);
}
// 급여: 주 40시간 최저시급 → 209시간 2,156,880원(노동포털)
let r = calc('none', 40, 10320);
assert.strictEqual(r.monthHours, 209); assert.strictEqual(r.gross, 2156880);
// 공제: 국민연금 4.75%, 건강 3.595%, 장기요양 건강보험료×9448/71900, 고용 0.9%
assert.strictEqual(r.pension, Math.floor(2156880 * 0.0475));
assert.strictEqual(r.health, Math.floor(Math.floor(2156880 * 0.0719) / 2));
assert.strictEqual(r.emp, Math.floor(2156880 * 0.009));
console.log('PASS 주40h 10,320원', r.monthHours + 'h', r.gross, '공제', r.deduct, '(국민연금', r.pension, '건강', r.health, '장기요양', r.ltc, '고용', r.emp + ')', '공제후', r.net);
assert.ok(Math.abs(r.deduct / r.gross - 0.0972) < 0.0005);
// 주 20시간: 주휴 4시간 → (24×365/7/12)=104.29 → 104시간
r = calc('care', 20, 10320); assert.strictEqual(r.holHours, 4); assert.strictEqual(r.monthHours, 104); assert.strictEqual(r.gross, 1073280);
console.log('PASS 주20h', r.monthHours + 'h', r.gross);
// 주 14시간: 주휴 없음 → 14×365/7/12=60.83 → 61시간
r = calc('none', 14, 12000); assert.strictEqual(r.holHours, 0); assert.strictEqual(r.monthHours, 61); assert.strictEqual(r.gross, 732000);
console.log('PASS 주14h 주휴없음', r.monthHours + 'h', r.gross);
// 주 52시간: 40시간으로 자르고 주휴 8시간 → 209시간, over 표시
r = calc('none', 52, 10320); assert.strictEqual(r.over, true); assert.strictEqual(r.monthHours, 209);
console.log('PASS 주52h → 40h 상한, over');
// 알 수 없는 자격값 → 일반 과정
assert.strictEqual(calc('xx', 0, 0).total, 50); console.log('PASS 미지정 자격 → 50h');
// UI 렌더(최소 DOM 스텁)
const vals = { 'as-lic': 'social', 'as-wage': '10000', 'as-week': '30' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['as-out', 'as-min', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력:', outP.join(' | '));
const o = outP.join();
assert.ok(o.includes('총 42시간')); assert.ok(o.includes('120,000원'));
assert.ok(o.includes('주 6시간')); assert.ok(o.includes('156시간')); assert.ok(o.includes('1,560,000원'));
assert.ok(o.includes('최저시급 10,320원보다 낮습니다'));
console.log('ALL PASS');
