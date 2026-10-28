// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { evaluate, fmt } = window.housingLoanCalc;
const base = { inc: 6000, app: 0, asset: 30000, price: 45000, area: '85', htype: 'apt', region: 'cap', homes: 0, hh: 'married', kids: 0, first: true, newly: false, birth: false, dual: false, term: 30, other: 0 };
const run = (o) => { const [d, n, b, g] = evaluate(Object.assign({}, base, o)); return { d, n, b, g }; };
const pick = r => ({ ok: r.ok, limit: r.limit, cap: r.cap, ltv: r.ltv, base: r.base, rate: r.rate, why: r.why });
const cases = [
  ['기본: 6천만원 생애최초 수도권 4.5억', {}, r => {
    assert.strictEqual(r.d.ok, true); assert.strictEqual(r.d.cap, 24000); assert.strictEqual(r.d.ltv, 70);
    assert.strictEqual(r.d.base, 3.80); assert.strictEqual(r.d.rate, 3.60); assert.strictEqual(r.d.limit, 24000);
    assert.strictEqual(r.n.ok, false); assert.strictEqual(r.b.ok, false);
    assert.strictEqual(r.g.ok, true); assert.strictEqual(r.g.cap, 42000); assert.strictEqual(r.g.ltv, 70); assert.strictEqual(r.g.limit, 31500); assert.strictEqual(r.g.rate, 5.10); }],
  ['디딤돌 소득 6천 초과 비생애최초 -> 불가, 보금자리 가능', { inc: 6500, first: false }, r => {
    assert.strictEqual(r.d.ok, false); assert.strictEqual(r.g.ok, true); assert.strictEqual(r.g.cap, 36000); }],
  ['순자산 5.2억 -> 디딤돌 불가', { asset: 52000 }, r => assert.strictEqual(r.d.ok, false)],
  ['지방 생애최초 LTV 80%, 금리 -0.2', { region: 'local', price: 30000 }, r => {
    assert.strictEqual(r.d.ltv, 80); assert.strictEqual(r.d.base, 3.60); assert.strictEqual(r.d.limit, 24000);
    assert.strictEqual(r.g.ltv, 80); assert.strictEqual(r.g.limit, 24000); }],
  ['신혼+생애최초 8천만원 -> 일반 3.2억, 전용 H 30년 3.85', { inc: 8000, newly: true, price: 55000 }, r => {
    assert.strictEqual(r.d.ok, true); assert.strictEqual(r.d.cap, 32000); assert.strictEqual(r.d.base, 4.15);
    assert.strictEqual(r.n.ok, true); assert.strictEqual(r.n.base, 3.85); assert.strictEqual(r.n.limit, 32000);
    assert.strictEqual(r.g.ok, true); assert.strictEqual(r.g.rate, 5.10); }],
  ['신혼 합산 9천, 신청인 5천 -> 디딤돌 특례 최고금리+0.3', { inc: 9000, app: 5000, newly: true, first: false }, r => {
    assert.strictEqual(r.d.ok, true); assert.strictEqual(r.d.base, 4.45); assert.strictEqual(r.d.rate, 4.25);
    assert.strictEqual(r.g.ok, true); }],
  ['신혼 합산 9천, 신청인 6.5천 -> 디딤돌 불가, 보금자리 특례 가능', { inc: 9000, app: 6500, newly: true }, r => {
    assert.strictEqual(r.d.ok, false); assert.strictEqual(r.g.ok, true); }],
  ['신생아 1.2억 수도권 8억', { inc: 12000, birth: true, price: 80000 }, r => {
    assert.strictEqual(r.b.ok, true); assert.strictEqual(r.b.base, 3.50); assert.strictEqual(r.b.cap, 40000); assert.strictEqual(r.b.limit, 40000);
    assert.strictEqual(r.d.ok, false); assert.strictEqual(r.g.ok, false); }],
  ['신생아 맞벌이 1.8억', { inc: 18000, birth: true, dual: true }, r => { assert.strictEqual(r.b.ok, true); assert.strictEqual(r.b.base, 4.50); }],
  ['신생아 외벌이 1.4억 -> 불가', { inc: 14000, birth: true }, r => assert.strictEqual(r.b.ok, false)],
  ['보금자리 2자녀 1억 소득, 규제지역 비실수요', { inc: 9500, kids: 2, first: false, region: 'capReg', price: 58000 }, r => {
    assert.strictEqual(r.g.ok, true); assert.strictEqual(r.g.cap, 40000); assert.strictEqual(r.g.ltv, 60);
    assert.strictEqual(r.g.base, 5.30); assert.strictEqual(r.g.rate, 4.80); assert.strictEqual(r.g.limit, 34800); }],
  ['보금자리 6억 초과 -> 불가', { price: 61000 }, r => assert.strictEqual(r.g.ok, false)],
  ['보금자리 1주택 가능, 디딤돌 불가', { homes: 1, first: false }, r => { assert.strictEqual(r.g.ok, true); assert.strictEqual(r.d.ok, false); }],
  ['30세 미만 미혼 단독 -> 디딤돌 불가', { hh: 'singleU30', first: false }, r => assert.strictEqual(r.d.ok, false)],
  ['30세 이상 미혼 60㎡ 2.8억 생애최초 -> 2억 한도', { hh: 'single30', area: '60', price: 28000 }, r => {
    assert.strictEqual(r.d.ok, true); assert.strictEqual(r.d.cap, 20000); assert.strictEqual(r.d.limit, 19600); }],
  ['DTI 제한: 소득 2천만원 30년', { inc: 2000, first: false, price: 40000 }, r => {
    // 3.10% 30년 연간 원리금계수 약 0.05124 -> 1200/0.05124 = 23,418만원
    assert.strictEqual(r.d.base, 3.10); assert.ok(r.d.dtiAmt > 23300); assert.ok(r.d.dtiAmt < 23500); assert.strictEqual(r.d.limit, 20000); }],
  ['다른 대출 이자 1,000만원 -> DTI 한도 감소', { inc: 2000, first: false, price: 40000, other: 1000 }, r => {
    assert.ok(r.d.dtiAmt < 4000); assert.strictEqual(r.d.limit, r.d.dtiAmt); }],
];
for (const [name, o, check] of cases) { const r = run(o); check(r); console.log('PASS', name, JSON.stringify({ d: pick(r.d), n: pick(r.n), b: pick(r.b), g: pick(r.g) })); }
assert.strictEqual(fmt(24000), '2억 4,000만원'); assert.strictEqual(fmt(40000), '4억원'); assert.strictEqual(fmt(8500), '8,500만원');
console.log('PASS fmt');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'hl-inc': '6000', 'hl-app': '', 'hl-asset': '30000', 'hl-price': '45000', 'hl-area': '85', 'hl-htype': 'apt', 'hl-region': 'cap', 'hl-homes': '0', 'hl-hh': 'married', 'hl-kids': '0', 'hl-term': '30', 'hl-other': '0' };
const checks = { 'hl-first': true, 'hl-newly': false, 'hl-birth': false, 'hl-dual': false };
const outP = [];
const el = id => ({ value: vals[id], checked: checks[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } });
const els = {}; ['hl-out', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {}, appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:\n' + outP.join('\n'));
assert.ok(outP.join().includes('2억 4,000만원'));
assert.ok(outP.join().includes('3억 1,500만원'));
console.log('PASS UI');
