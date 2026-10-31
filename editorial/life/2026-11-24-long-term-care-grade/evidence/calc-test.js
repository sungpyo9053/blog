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
const calc = window.longTermCareCalc;
// 1) 재가 월 한도액 — 보건복지부고시 제2025-247호 제13조제1항 표
const LIM = { '1': 2512900, '2': 2331200, '3': 1528200, '4': 1409700, '5': 1208900, c: 676320 };
for (const g of Object.keys(LIM)) assert.strictEqual(calc(g, 'home', 'none', 0, 0).limit, LIM[g], 'limit ' + g);
console.log('PASS 2026 월 한도액 6개');
// 2) 시설 1일 수가 본인부담 — 보도자료 붙임2(노인요양시설·공동생활가정 ’26년 본인부담)
const fac = [['nh', '1', 18614], ['nh', '2', 17268], ['nh', '3', 16308], ['nh', '5', 16308], ['gh', '1', 14918], ['gh', '2', 13842], ['gh', '4', 12760]];
for (const [t, g, per] of fac) assert.strictEqual(calc(g, t, 'none', 0, 1).copay, per, t + g);
console.log('PASS 시설 1일 본인부담 7개(보도자료 표와 일치)');
// 3) 사례
const cases = [
  ['재가 1등급 한도 전액, 일반 15%', ['1', 'home', 'none', 2512900, 0], { copay: 376935, over: 0, total: 376935, nhis: 2135965 }],
  ['재가 3등급 170만 원 이용 → 초과 171,800', ['3', 'home', 'none', 1700000, 0], { covered: 1528200, over: 171800, copay: 229230, total: 401030 }],
  ['재가 2등급 60% 감경 100만 원 → 6%', ['2', 'home', 'r60', 1000000, 0], { pm: 60, copay: 60000, total: 60000 }],
  ['재가 인지지원 40% 감경 한도 전액 → 9%', ['c', 'home', 'r40', 676320, 0], { pm: 90, copay: 60869 }],
  ['재가 5등급 의료급여(기초) 면제, 한도 초과 10만', ['5', 'home', 'free', 1308900, 0], { copay: 0, over: 100000, total: 100000 }],
  ['시설 노인요양시설 1등급 30일', ['1', 'nh', 'none', 0, 30], { limit: 2792100, copay: 558420, needApproval: false }],
  ['시설 공동생활가정 4등급 31일 → 승인 필요', ['4', 'gh', 'none', 0, 31], { limit: 1977800, copay: 395560, needApproval: true }],
  ['시설 노인요양시설 2등급 40% 감경 30일 → 12%', ['2', 'nh', 'r40', 0, 30], { pm: 120, copay: 310830 }],
  ['시설 1등급 60% 감경 30일 → 8%', ['1', 'nh', 'r60', 0, 30], { pm: 80, copay: 223380 }],
  ['시설 일수 40 입력 → 31일로 제한', ['1', 'nh', 'none', 0, 40], { days: 31, limit: 2885170 }],
  ['인지지원 시설 → 불가', ['c', 'nh', 'none', 0, 30], { ok: false }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 4) 방문요양 수가표 반올림 방식 확인: 17,450 × 15% = 2,617.5 → 2,618, 63,530 → 9,530
assert.strictEqual(calc('1', 'home', 'none', 17450, 0).copay, 2618);
assert.strictEqual(calc('1', 'home', 'none', 63530, 0).copay, 9530);
console.log('PASS 방문요양 30분·210분 본인부담 반올림(보도자료 2,618·9,530)');
// 5) UI 렌더(최소 DOM 스텁): 재가 3등급 170만 원, 그다음 시설 4등급
function render(vals) {
  const outP = [];
  const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
  const els = {}; ['ltc-out', 'ltc-use-row', 'ltc-days-row', ...Object.keys(vals)].forEach(id => els[id] = el(id));
  global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
  eval(src);
  return { text: outP.join(' | '), els };
}
let u = render({ 'ltc-grade': '3', 'ltc-type': 'home', 'ltc-red': 'none', 'ltc-use': '1700000', 'ltc-days': '30' });
console.log('UI 재가:', u.text);
assert.ok(u.text.includes('1,528,200원')); assert.ok(u.text.includes('229,230원')); assert.ok(u.text.includes('171,800원')); assert.ok(u.text.includes('401,030원'));
assert.strictEqual(u.els['ltc-days-row'].style.display, 'none');
u = render({ 'ltc-grade': '4', 'ltc-type': 'nh', 'ltc-red': 'r40', 'ltc-use': '0', 'ltc-days': '30' });
console.log('UI 시설:', u.text);
assert.ok(u.text.includes('81,540원')); assert.ok(u.text.includes('12%')); assert.ok(u.text.includes('등급판정위원회'));
assert.strictEqual(u.els['ltc-use-row'].style.display, 'none');
u = render({ 'ltc-grade': 'c', 'ltc-type': 'gh', 'ltc-red': 'none', 'ltc-use': '0', 'ltc-days': '30' });
console.log('UI 인지지원 시설:', u.text);
assert.ok(u.text.includes('이용할 수 없습니다'));
console.log('ALL PASS');
