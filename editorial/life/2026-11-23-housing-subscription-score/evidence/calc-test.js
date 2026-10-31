// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const S = window.subScore, R = window.subRank;
// 별표 1 구간표 전수 검산
const home = [2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32];
home.forEach((p, y) => assert.strictEqual(S(false, y, 0, 0, 0).home, p, 'home ' + y));
assert.strictEqual(S(false, 20, 0, 0, 0).home, 32);
assert.strictEqual(S(true, 10, 0, 0, 0).home, 0, '유주택·30세 미만 미혼 0점');
[5,10,15,20,25,30,35,35].forEach((p, n) => assert.strictEqual(S(false, 0, n, 0, 0).dep, p, 'dep ' + n));
const acct = [[0,1],[5,1],[6,2],[11,2],[12,3],[23,3],[24,4],[60,7],[120,12],[179,16],[180,17],[300,17]];
acct.forEach(([m, p]) => assert.strictEqual(S(false, 0, 0, m, 0).acct, p, 'acct ' + m));
// 배우자 가산(청약홈 예시: 12개월 2점, 24개월 3점, 30개월 3점) + 17점 상한
assert.strictEqual(S(false, 0, 0, 0, 12).spouse, 2);
assert.strictEqual(S(false, 0, 0, 0, 24).spouse, 3);
assert.strictEqual(S(false, 0, 0, 0, 30).spouse, 3);
assert.strictEqual(S(false, 0, 0, 0, 5).spouse, 1);
assert.strictEqual(S(false, 0, 0, 168, 30).acctTotal, 17, '16+3 -> 17 cap');
console.log('PASS 별표 1 구간표·배우자 가산');
const cases = [
  ['본문 예: 무주택 10년·부양 3명·가입 10년 = 54', [false, 10, 3, 120, 0], 54],
  ['만점 84', [false, 15, 6, 180, 0], 84],
  ['FAQ: 30세 미만 미혼·가입 5년 = 12', [true, 0, 0, 60, 0], 12],
];
for (const [n, a, t] of cases) { const r = S(...a); assert.strictEqual(r.total, t, n); console.log('PASS', n, JSON.stringify(r)); }
// 1순위
const base = { type: 'private', area: 'metro', months: 12, count: 0, deposit: 300, res: 'sp', size: '85', head: true, nowin: true, nohouse: true, two: true };
const rk = [
  ['민영 수도권 1년·서울 300만원 85㎡', {}, true],
  ['민영 수도권 11개월', { months: 11 }, false],
  ['민영 서울 102㎡ 300만원 부족', { size: '102' }, false],
  ['민영 광역시 102㎡ 400만원', { res: 'metro', size: '102', deposit: 400 }, true],
  ['민영 규제 2년·세대주 아님', { area: 'reg', months: 24, head: false }, false],
  ['민영 규제 2년·2주택 세대', { area: 'reg', months: 24, two: false }, false],
  ['민영 규제 2년 충족', { area: 'reg', months: 24 }, true],
  ['민영 수도권 밖 6개월·시군 200만원', { area: 'nonmetro', months: 6, res: 'other', deposit: 200 }, true],
  ['국민 수도권 1년 12회', { type: 'national', count: 12 }, true],
  ['국민 수도권 1년 11회', { type: 'national', count: 11 }, false],
  ['국민 규제 24개월 24회', { type: 'national', area: 'reg', months: 24, count: 24 }, true],
  ['국민 규제 5년 내 당첨', { type: 'national', area: 'reg', months: 24, count: 24, nowin: false }, false],
  ['국민 수도권 밖 6개월 6회', { type: 'national', area: 'nonmetro', months: 6, count: 6 }, true],
  ['국민 유주택 세대(신청 대상 아님)', { type: 'national', count: 12, nohouse: false }, false],
  ['국민 위축 1개월', { type: 'national', area: 'shrink', months: 1, count: 0 }, true],
];
for (const [n, o, ok] of rk) { const r = R(Object.assign({}, base, o)); assert.strictEqual(r.ok, ok, n + ' ' + JSON.stringify(r)); console.log('PASS', n, r.blocked ? '신청 대상 아님' : r.ok ? '1순위' : '2순위: ' + r.miss.join(' / ')); }
assert.strictEqual(R(Object.assign({}, base, { type: 'national', count: 12, nohouse: false })).blocked, true);
// 별표 2 예치금 표
assert.deepStrictEqual(window.subDeposit, { sp: { '85': 300, '102': 600, '135': 1000, all: 1500 }, metro: { '85': 250, '102': 400, '135': 700, all: 1000 }, other: { '85': 200, '102': 300, '135': 400, all: 500 } });
console.log('PASS 별표 2 예치금 12칸');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'hs-hy': '10', 'hs-dep': '3', 'hs-ay': '10', 'hs-am': '0', 'hs-sy': '0', 'hs-sm': '0', 'hs-type': 'private', 'hs-area': 'reg', 'hs-cnt': '24', 'hs-dp': '300', 'hs-res': 'sp', 'hs-size': '85' };
const checks = { 'hs-owner': false, 'hs-head': true, 'hs-nowin': true, 'hs-nohouse': true, 'hs-two': true };
const outs = {};
const el = id => ({ value: vals[id], checked: checks[id], style: {}, addEventListener() {}, set innerHTML(v) { outs[id] = []; }, appendChild(p) { outs[id].push(p.textContent); } });
const els = {}; ['hs-score', 'hs-rank', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 가점:', outs['hs-score'].join(' | '));
console.log('UI 1순위:', outs['hs-rank'].join(' | '));
assert.ok(outs['hs-score'][0].includes('54점'));
assert.ok(outs['hs-rank'][0].includes('1순위 통장 요건 충족'));
