// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('raw < in string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.disneyPlusCalc;
const cases = [
  ['스탠다드 연간 12개월', 9900, 99000, 12, true, 0, { total: 99000, monthlyTotal: 118800, saving: 19800, perMonth: 8250, payments: 1 }],
  ['프리미엄 연간 12개월', 13900, 139000, 12, true, 0, { total: 139000, monthlyTotal: 166800, saving: 27800, perMonth: 11583 }],
  ['스탠다드 10개월 손익분기', 9900, 99000, 10, true, 0, { total: 99000, saving: 0 }],
  ['스탠다드 13개월 연간 2회', 9900, 99000, 13, true, 0, { payments: 2, total: 198000, saving: -69300 }],
  ['스탠다드 월간 + 추가회원 12개월 = 프리미엄 월간 12개월', 9900, 99000, 12, false, 4000, { total: 166800, extraTotal: 48000 }],
  ['스탠다드 연간 + 추가회원(매월) 12개월', 9900, 99000, 12, true, 4000, { total: 147000 }],
  ['광고형 12개월(연간 없음 -> 월간)', 7000, 0, 12, true, 0, { yearlyUsed: false, total: 84000 }],
  ['3종 번들 6개월', 21500, 0, 6, false, 0, { total: 129000, perMonth: 21500 }],
];
for (const [name, m, y, n, yr, ex, exp] of cases) {
  const r = calc(m, y, n, yr, ex);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.strictEqual(24900 - 21500, 3400); assert.strictEqual(Math.round(3400 / 24900 * 10000) / 100, 13.65);
console.log('PASS 번들 13.65% 검산');
// UI 기본값(스탠다드, 연간, 12개월) 렌더 + 가격 수정·번들 추가회원 제외 확인 — 최소 DOM 스텁
const vals = { 'dp-plan': 'std', 'dp-cycle': 'y', 'dp-months': '12', 'dp-extra-price': '4000', 'dp-mprice': '', 'dp-yprice': '' };
const handlers = {}, boxes = { 'dp-out': [], 'dp-cmp': [] };
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = String(v); }, checked: false, disabled: false, style: {},
  addEventListener(ev, f) { (handlers[id + ev] = handlers[id + ev] || []).push(f); },
  set innerHTML(v) { if (boxes[id]) boxes[id].length = 0; }, appendChild(p) { boxes[id].push(p.textContent); } });
const els = {}; ['dp-out', 'dp-cmp', 'dp-reset', 'dp-extra', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값:', boxes['dp-out'].join(' | '));
assert.ok(boxes['dp-out'][0].includes('99,000원'));
assert.ok(boxes['dp-out'].join().includes('19,800원 아낍니다'));
console.log('UI 비교:', boxes['dp-cmp'].join(' | '));
// 가격 수정(가상 인상가 입력 테스트용 임의값) 반영
vals['dp-mprice'] = '11000'; vals['dp-yprice'] = '110000'; handlers['dp-mpriceinput'][0]();
console.log('UI 가격 수정 11,000/110,000:', boxes['dp-out'].join(' | '));
assert.ok(boxes['dp-out'].join().includes('22,000원 아낍니다'));
assert.ok(boxes['dp-cmp'].join().includes('스탠다드: 월간 132,000원'));
// 번들 + 추가회원 -> 제외 문구
vals['dp-plan'] = 'b3'; els['dp-extra'].checked = true; handlers['dp-planchange'][0]();
console.log('UI 번들+추가회원:', boxes['dp-out'].join(' | '));
assert.ok(boxes['dp-out'].join().includes('추가 회원을 붙일 수 없어'));
assert.ok(boxes['dp-out'][0].includes('258,000원'));
// 되돌리기
handlers['dp-resetclick'][0](); vals['dp-plan'] = 'std'; handlers['dp-planchange'][0]();
assert.strictEqual(vals['dp-mprice'], '9900');
console.log('PASS UI');
