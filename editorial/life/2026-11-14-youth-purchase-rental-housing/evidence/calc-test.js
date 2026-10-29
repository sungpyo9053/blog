// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const chk = window.youthBuyRentCheck, rent = window.youthBuyRentRent;
const o = (x) => Object.assign({ age: 27, student: false, married: false, own: false, p1: 'none', same: false, income: 0, parents: 2, pincome: 0, asset: 0, car: 0, passet: 0, pcar: 0, pnohouse: false, dis: 0, sub: 0 }, x);
const cases = [
  // 2026.9.17. 서울지역본부 공고 금액 경계
  ['2순위 3인 한도 8,168,429원 경계 충족', o({ income: 3000000, pincome: 5168429 }), { rank: 2, limit2: 8168429, ok2inc: true }],
  ['2순위 3인 1원 초과 -> 3순위로', o({ income: 3000000, pincome: 5168430 }), { rank: 3, ok2inc: false }],
  ['2순위 2인(부모 1명) 한도 6,452,897원', o({ parents: 1, income: 2000000, pincome: 4452897 }), { rank: 2, n: 2, limit2: 6452897 }],
  ['2순위 부모 없음 -> 1인 4,576,036원', o({ parents: 0, income: 4576036, pincome: 9999999 }), { rank: 2, n: 1, limit2: 4576036, inc2: 4576036 }],
  ['2순위 자산 본인+부모 3억 4,500만 경계', o({ asset: 45000000, passet: 300000000 }), { ok2asset: true, rank: 2 }],
  ['2순위 자산 초과 -> 3순위', o({ asset: 45000000, passet: 300000001 }), { ok2asset: false, rank: 3 }],
  ['2순위 부모 차 4,543만 -> 2순위 불가', o({ pcar: 45430000 }), { ok2car: false, rank: 3 }],
  ['3순위 본인 4,576,036원 경계', o({ income: 4576036, pincome: 9000000 }), { rank: 3, ok3inc: true }],
  ['3순위 1원 초과 -> 순위 없음', o({ income: 4576037, pincome: 9000000 }), { rank: 0, ok3inc: false }],
  ['3순위 자산 2억 5,100만 경계', o({ income: 3000000, pincome: 9000000, asset: 251000000 }), { rank: 3, ok3asset: true }],
  ['3순위 자동차 4,542만 경계 / 4,543만 초과', o({ income: 3000000, pincome: 9000000, car: 45420000 }), { rank: 3, ok3car: true }],
  ['3순위 자동차 4,543만 초과', o({ income: 3000000, pincome: 9000000, car: 45430000 }), { rank: 0, ok3car: false }],
  // 1순위
  ['본인 수급자 -> 1순위, 가점 3', o({ p1: 'rs', income: 99999999 }), { rank: 1, points: 3, ratio: 0.4, deposit: 1000000 }],
  ['부모 수급자, 29세 분리거주 -> 1순위', o({ p1: 'rp', age: 29 }), { rank: 1, r1: true }],
  ['부모 수급자, 30세 분리거주 -> 1순위 아님', o({ p1: 'rp', age: 30 }), { r1: false, rank: 2 }],
  ['부모 수급자, 35세 같은 주민등록 -> 1순위', o({ p1: 'rp', age: 35, same: true }), { rank: 1, points: 3 }],
  ['본인 차상위 -> 1순위, 수급자 가점 없음', o({ p1: 'ns', sub: 2 }), { rank: 1, points: 2 }],
  ['한부모 지원대상 -> 1순위 3점', o({ p1: 'sp' }), { rank: 1, points: 3 }],
  // 기본 자격
  ['혼인 중 -> 불가', o({ married: true }), { base: false, rank: 0 }],
  ['본인 주택 소유 -> 불가', o({ own: true }), { base: false, rank: 0 }],
  ['40세 일반 -> 불가', o({ age: 40 }), { base: false, rank: 0 }],
  ['40세 취업준비생 -> 가능', o({ age: 40, student: true }), { base: true, rank: 2 }],
  ['18세 대학생 -> 가능', o({ age: 18, student: true }), { base: true }],
  ['19세 / 39세 경계', o({ age: 39 }), { ageOk: true }],
  // 가점
  ['2순위 소득 50% 이하(3인 4,084,215원) 3점 + 부모무주택 2 + 청약 3', o({ income: 2000000, pincome: 2084215, pnohouse: true, sub: 3 }), { rank: 2, points: 8 }],
  ['2순위 50% 1원 초과 -> 소득 가점 없음', o({ income: 2000000, pincome: 2084216 }), { rank: 2, points: 0 }],
  ['3순위 본인 2,669,354원 이하 3점', o({ income: 2669354, pincome: 9000000 }), { rank: 3, points: 3, ratio: 0.5, deposit: 2000000 }],
  ['본인 장애 2점', o({ dis: 2, income: 3000000, pincome: 3000000 }), { rank: 2, points: 2 }],
  ['부모 없음이면 부모 무주택 가점 없음', o({ parents: 0, pnohouse: true, income: 3000000 }), { rank: 2, points: 0 }],
];
for (const [name, input, exp] of cases) {
  const r = chk(input);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ rank: r.rank, points: r.points }));
}
// 임대료: 공고 예시 300만 원 추가 -> 월 15,000원 감소
let t = rent(600000, 0.5, 3000000);
assert.deepStrictEqual([t.monthly, t.cut, t.after, t.maxExtra, t.capped], [300000, 15000, 285000, 36000000, false]);
console.log('PASS 공고 예시: 보증금 300만 원 추가 -> 월 15,000원 감소', JSON.stringify(t));
t = rent(600000, 0.4, 50000000);
assert.deepStrictEqual([t.monthly, t.cut, t.after, t.capped], [240000, 144000, 96000, true]);
console.log('PASS 전환 한도 60% 적용', JSON.stringify(t));
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'yb-age': '27', 'yb-p1': 'none', 'yb-income': '2800000', 'yb-parents': '2', 'yb-pincome': '5000000', 'yb-asset': '3000', 'yb-car': '0', 'yb-passet': '30000', 'yb-pcar': '1500', 'yb-dis': '0', 'yb-sub': '3', 'yb-market': '600000', 'yb-extra': '0' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['yb-out', 'yb-student', 'yb-married', 'yb-own', 'yb-same', 'yb-pnohouse', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
assert.ok(outP[0].includes('2순위'));
assert.ok(outP.join().includes('300,000원'));
console.log('ALL PASS');
