// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'[^'\n]*'/g)) if (m[0].includes('<')) throw new Error('raw < in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const S = window.savingsInterestCalc;
function chk(name, r, exp) {
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 0.005, name + ' ' + k + '=' + r[k] + ' expected ' + exp[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 금융감독원 금융꿀팁146: 월 50만, 1년, 3.5% 적금 세전 113,750 / 같은 총액 예금 210,000
chk('금감원 예시 적금 50만x12 3.5%', S.calc(500000, 3.5, 12, false, 'normal'), { pre: 113750, depSame: 210000 });
// 본문 대표 예시
chk('월50만 5% 12개월 단리 일반', S.calc(500000, 5, 12, false, 'normal'), { principal: 6000000, pre: 162500, it: 22750, lt: 2270, post: 137480, total: 6137480, avg: 6.5 });
assert.ok(Math.abs(S.calc(500000, 5, 12, false, 'normal').depEq - 5 * 13 / 24) < 1e-9); console.log('PASS 예금 환산 = r(n+1)/2n');
chk('월50만 5% 12개월 월복리', S.calc(500000, 5, 12, true, 'normal'), { pre: 165008 });
chk('월50만 5% 36개월 단리/월복리', { s: S.calc(500000, 5, 36, false, 'normal').pre, c: S.calc(500000, 5, 36, true, 'normal').pre }, { s: 1387500, c: 1457403 });
chk('세금우대 9.5%', S.calc(500000, 5, 12, false, 'pref'), { it: 14620, rt: 810, lt: 0, post: 147070 });
chk('비과세', S.calc(500000, 5, 12, false, 'none'), { tax: 0, post: 162500 });
chk('FAQ 월100만 5% 12개월', S.calc(1000000, 5, 12, false, 'normal'), { pre: 325000, it: 45500, lt: 4550, post: 274950, total: 12274950 });
chk('6개월 연6% 월50만', S.calc(500000, 6, 6, false, 'normal'), { pre: 52500 });
// 금융상품한눈에 예시(월10만 12개월 6.00%): 세전 39,000 — 사이트 세후 33,020은 반올림 세후이율 5.08% 기준이라 원천징수 계산(33,000)과 20원 차이
chk('금융상품한눈에 월10만 6% 세전', S.calc(100000, 6, 12, false, 'normal'), { pre: 39000, post: 33000 });
// 표 값 검산 (월 50만, 단리, 15.4%)
const table = { 3: [22220, 82490, 317250, 704300], 4: [29610, 109980, 423000, 939060], 5: [37020, 137480, 528750, 1173830] };
const eq = { 3: [1.75, 1.63, 1.56, 1.54], 4: [2.33, 2.17, 2.08, 2.06], 5: [2.92, 2.71, 2.60, 2.57] };
for (const r of [3, 4, 5]) [6, 12, 24, 36].forEach((n, i) => { const c = S.calc(500000, r, n, false, 'normal'); assert.strictEqual(c.post, table[r][i]); assert.strictEqual(Math.round(c.depEq * 100) / 100, eq[r][i]); });
console.log('PASS 표 값 12개 + 예금 환산 12개');
// 중도해지이율: 금감원 예시표(정기예금 1천만, 1년, 3%) 3/6/9/11개월 해지 이자 9,375 / 45,000 / 118,125 / 201,667
[[3, 9375], [6, 45000], [9, 118125], [11, 201667]].forEach(([m, v]) => { const er = S.earlyRate(3, 12, m); assert.strictEqual(Math.round(10000000 * er / 100 * m / 12), v); });
assert.strictEqual(S.earlyRate(3, 12, 2), 0.1);
console.log('PASS 금감원 예금 중도해지 예시 4개 + 3개월 미만 0.1%');
chk('적금 6개월 차 해지 (본문)', S.early(500000, 5, 12, 6, 'normal'), { rate: 1.5, pre: 13125, principal: 3000000 });
// 목표 역산
const n1 = S.need(10000000, 5, 12, false, 'normal');
assert.ok(S.calc(n1, 5, 12, false, 'normal').total >= 10000000 && S.calc(n1 - 1000, 5, 12, false, 'normal').total < 10000000);
console.log('PASS 목표 1,000만 원 역산 월', n1);
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'sv-amt': '500000', 'sv-rate': '5', 'sv-months': '12', 'sv-kind': 'free', 'sv-comp': '0', 'sv-tax': 'normal', 'sv-early': '6', 'sv-goal': '10000000' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['sv-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력:\n ' + outP.join('\n '));
assert.ok(outP.join().includes('137,480원') && outP.join().includes('6,137,480원') && outP.join().includes('2.71%'));
console.log('PASS UI, FAQ JSON-LD 질문 수', faq);
