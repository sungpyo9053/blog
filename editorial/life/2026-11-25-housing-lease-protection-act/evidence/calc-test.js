// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const H = window.hlLease, f = a => H.fmt(a);
// 1. 갱신 기간
let r = H.renew(H.parse('2027-08-31'));
assert.strictEqual(f(r.start), '2027년 2월 28일'); assert.strictEqual(f(r.last), '2027년 6월 30일');
assert.strictEqual(f(r.newStart), '2027년 9월 1일'); assert.strictEqual(f(r.newEnd), '2029년 8월 31일');
console.log('PASS 만료 2027-08-31 ->', f(r.start), '~', f(r.last), '/ 새 기간', f(r.newStart), '~', f(r.newEnd));
r = H.renew(H.parse('2027-01-15'));
assert.strictEqual(f(r.start), '2026년 7월 15일'); assert.strictEqual(f(r.last), '2026년 11월 15일');
console.log('PASS 만료 2027-01-15 (연도 넘김) ->', f(r.start), '~', f(r.last));
assert.strictEqual(f(H.cancelEff(H.parse('2026-11-30'))), '2027년 2월 28일');
console.log('PASS 해지 통지 2026-11-30 -> 효력 2027년 2월 28일');
// 2. 5% 상한·전환율
let c = H.rentCap(300000000, 0, 3.00);
assert.strictEqual(c.rate, 5); assert.strictEqual(c.depInc, 15000000);
console.log('PASS 보증금 3억, 기준금리 3.00% -> 전환율 5%, 상한 +15,000,000');
assert.strictEqual(H.rentCap(50000000, 0, 3).depInc, 2500000);
console.log('PASS 생활법령 예: 보증금 5천만 -> 250만');
assert.strictEqual(H.convMonthly(100000000, 3.00), 416667);
console.log('PASS 1억 월세 전환(5%) -> 416,667');
assert.strictEqual(Math.round(H.convMonthly(200000000, 2.00) / 10000), 67);
console.log('PASS 국토부 2020 예(전환율 4%): 2억 -> 월 약 67만');
assert.strictEqual(H.convMonthly(300000000, 0.5 + 1.5 + 6), 2500000); // min(10, 10) 상한
assert.strictEqual(H.rentCap(0, 0, 9).rate, 10);
console.log('PASS 기준금리 9% -> 전환율 상한 10%');
c = H.rentCap(10000000, 500000, 3.00);
assert.strictEqual(c.rentInc, 25000); assert.strictEqual(c.conv, 130000000); assert.strictEqual(c.convInc, 6500000); assert.strictEqual(c.convAsRent, 27083);
console.log('PASS 보증금 1천만·월세 50만 -> 월세 +25,000, 환산 1.3억, 5% 650만(월 27,083)');
// 3. 최우선변제
const s = (g, d, p) => H.small(g, d, p || 0);
assert.deepStrictEqual([s(0, 165000000).eligible, s(0, 165000000).amount], [true, 55000000]);
assert.strictEqual(s(0, 165000001).eligible, false);
assert.strictEqual(s(1, 145000000).amount, 48000000);
assert.strictEqual(s(2, 85000000).amount, 28000000);
assert.strictEqual(s(3, 75000000).amount, 25000000);
assert.strictEqual(s(3, 75000001).eligible, false);
assert.strictEqual(s(3, 20000000).amount, 20000000);
const h = s(0, 100000000, 80000000); assert.strictEqual(h.amount, 40000000); assert.ok(h.halfCap);
console.log('PASS 지역 4구간 경계·보증금 미만·주택가액 1/2 제한');
// UI 기본값 렌더
const vals = { 'hl-end': '2027-08-31', 'hl-notice': '', 'hl-dep': '300000000', 'hl-rent': '0', 'hl-base': '3.00', 'hl-convert': '', 'hl-region': '0', 'hl-sdep': '150000000', 'hl-price': '' };
const outs = {};
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outs[id] = []; }, appendChild(p) { outs[id].push(p.textContent); } });
const els = {}; ['hl-out1', 'hl-out2', 'hl-out3', 'hl-old', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
for (const k of ['hl-out1', 'hl-out2', 'hl-out3']) console.log('UI', k + ':', outs[k].join(' | '));
assert.ok(outs['hl-out2'].join().includes('15,000,000원'));
assert.ok(outs['hl-out3'].join().includes('55,000,000원'));
