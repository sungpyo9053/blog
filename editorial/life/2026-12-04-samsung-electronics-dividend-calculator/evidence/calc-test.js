// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6); console.log('PASS JSON-LD 파싱, 질문', faq.mainEntity.length, '개');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const C = window.samsungDivCalc;
const eq = (r, exp, name) => { for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]); console.log('PASS', name, JSON.stringify(r)); };
eq(C.tax(460100), { gross: 460100, it: 64410, lt: 6440, net: 389250 }, '보통주 100주 x 4,601');
eq(C.tax(37400), { it: 5230, lt: 520, net: 31650 }, '100주 x 374');
eq(C.tax(37200), { it: 5200, lt: 520, net: 31480 }, '100주 x 372');
eq(C.tax(56600), { it: 7920, lt: 790, net: 47890 }, '100주 x 566');
eq(C.tax(5670), { it: 790, lt: 70, net: 4810 }, '우선주 10주 x 567');
eq(C.tax(50), { it: 0, lt: 0, net: 50 }, '소액: 세금 10원 미만 -> 0');
eq(C.tax(0), { it: 0, lt: 0, net: 0 }, '0원');
// 최근 4회 합계
let r = C.calc(100, 0, [[566, 567], [372, 372], [374, 374], [4601, 4601]]);
eq(r.total, { gross: 591300, net: 500270 }, '보통주 100주 최근 4회');
// 보통주 + 우선주 따로 절사
r = C.calc(100, 10, [[566, 567]]);
assert.strictEqual(r.rows[0].c.net + r.rows[0].p.net, 47890 + 4810); assert.strictEqual(r.total.gross, 62270); console.log('PASS 보통 100 + 우선 10, 2025 결산 세후', r.total.net);
// 2025년 연간 1,668원 (주총결과 공시: 기말 566 + 분기 1,102)
assert.strictEqual(365 + 367 + 370, 1102); r = C.calc(1, 0, [[365, 0], [367, 0], [370, 0], [566, 0]]); assert.strictEqual(r.total.gross, 1668); console.log('PASS 2025년 연간 1주 1,668원');
// 세율이 15.4%에 수렴하는지 (큰 금액)
const big = C.tax(100000000); assert.strictEqual(big.it + big.lt, 15400000); console.log('PASS 1억원 -> 세금 15,400,000');
// UI 기본값 렌더 (보통주 100주, 최근 4회 체크) — 최소 DOM 스텁
const vals = { 'sd-c': '100', 'sd-p': '0' };
const defs = [[363, 364, 0], [365, 365, 0], [367, 367, 0], [370, 370, 0], [566, 567, 1], [372, 372, 1], [374, 374, 1], [4601, 4601, 1], ['', '', 0]];
defs.forEach((d, i) => { vals['sd-a' + i] = String(d[0]); vals['sd-b' + i] = String(d[1]); vals['sd-k' + i] = d[2]; });
const outP = [];
const el = id => ({ value: vals[id], checked: !!vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = { 'sd-out': el('sd-out') }; Object.keys(vals).forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
assert.ok(outP.join().includes('세후 389,250원')); assert.ok(outP[outP.length - 1].includes('세후 500,270원'));
console.log('ALL PASS');
