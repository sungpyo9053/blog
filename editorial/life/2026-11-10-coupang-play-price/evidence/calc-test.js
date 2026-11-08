// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/^\s*$/m.test(src.trim())) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g)) if (lit.indexOf('<') >= 0) throw new Error('< in string literal ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.coupangPlayCalc, cmp = window.coupangPlayCompare;
const base = { wowFee: 7890, wowPaid: false, sports: false, sportsPrice: 0, para: false, paraPrice: 0, other: 0, months: 12, people: 1 };
const cases = [
  ['일반회원 패스 없음 = 0원', { member: 'general' }, { monthly: 0, total: 0, streams: 1 }],
  ['와우만 12개월 = 94,680원', { member: 'wow' }, { monthly: 7890, total: 94680, yearly: 94680, streams: 2 }],
  ['와우 + 스포츠 9,900 = 월 17,790, 연 213,480', { member: 'wow', sports: true, sportsPrice: 9900 }, { monthly: 17790, total: 213480 }],
  ['와우 이미 결제 + 스포츠 = 연 118,800', { member: 'wow', wowPaid: true, sports: true, sportsPrice: 9900 }, { base: 0, monthly: 9900, total: 118800 }],
  ['일반 + 스포츠 16,600 12개월 = 199,200', { member: 'general', sports: true, sportsPrice: 16600 }, { monthly: 16600, total: 199200 }],
  ['파라마운트+ 일반 4,900 12개월 = 58,800', { member: 'general', para: true, paraPrice: 4900 }, { total: 58800 }],
  ['파라마운트+ 와우가 3,300 12개월(와우 기결제) = 39,600', { member: 'wow', wowPaid: true, para: true, paraPrice: 3300 }, { total: 39600 }],
  ['와우 2명 1인당 3,945', { member: 'wow', people: 2 }, { perPerson: 3945, overStreams: false }],
  ['와우+스포츠 2명 1인당 8,895', { member: 'wow', sports: true, sportsPrice: 9900, people: 2 }, { perPerson: 8895 }],
  ['일반 2명 -> 동시 시청 초과', { member: 'general', people: 2 }, { overStreams: true }],
  ['와우 3명 -> 동시 시청 초과', { member: 'wow', people: 3 }, { overStreams: true }],
  ['와우 + 스포츠 + 기타 3개월', { member: 'wow', sports: true, sportsPrice: 9900, other: 5000, months: 3 }, { monthly: 22790, total: 68370 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(Object.assign({}, base, o));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
const c2 = cmp(2);
assert.deepStrictEqual(c2.map(x => x.perPerson), [3500, 6750, 8500, 2750, 6750, 8500]);
assert.deepStrictEqual(cmp(3).map(x => x.over), [true, true, false, true, true, false]);
console.log('PASS 비교표 2명 1인당', c2.map(x => x.name + ' ' + x.perPerson).join(', '));
assert.strictEqual(window.coupangPlayPrice.general.sports, 16600);
assert.strictEqual(window.coupangPlayPrice.wow.sports, 9900);
// UI 기본값 렌더 + 회원 변경 시 프리셋 전환 — 최소 DOM 스텁
const vals = { 'cp-member': 'general', 'cp-wowfee': '7890', 'cp-sportsprice': '16600', 'cp-paraprice': '4900', 'cp-other': '0', 'cp-months': '12', 'cp-people': '1' };
const checks = { 'cp-wowpaid': false, 'cp-sports': true, 'cp-para': false };
const boxes = { 'cp-out': [], 'cp-cmp': [] }, handlers = {};
const els = {};
Object.keys(vals).concat(Object.keys(checks)).forEach(id => {
  els[id] = { get value() { return vals[id]; }, set value(v) { vals[id] = String(v); }, get checked() { return checks[id]; }, addEventListener(t, f) { (handlers[id] = handlers[id] || []).push(f); } };
});
Object.keys(boxes).forEach(id => { els[id] = { style: {}, set innerHTML(v) { boxes[id].length = 0; }, appendChild(p) { boxes[id].push(p.textContent); } }; });
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값(일반+스포츠):', boxes['cp-out'].join(' | '));
assert.ok(boxes['cp-out'][0].includes('16,600원'));
assert.ok(boxes['cp-out'][1].includes('199,200원'));
vals['cp-member'] = 'wow'; handlers['cp-member'].forEach(f => f());
console.log('와우로 변경:', boxes['cp-out'].join(' | '));
assert.strictEqual(vals['cp-sportsprice'], '9900');
assert.ok(boxes['cp-out'][0].includes('17,790원'));
console.log('비교:', boxes['cp-cmp'].join(' | '));
console.log('ALL PASS');
