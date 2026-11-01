// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.includes('<')) throw new Error('< in string literal ' + m);
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const calc = window.basicPensionCalc;
const M = 10000;
const base = { kind: 'single', w1: 0, w2: 0, n1: 0, n2: 0, t1: 'old', t2: 'old', a1: -1, a2: -1, pub: 0, intr: 0, oth: 0, region: 'big', gen: 0, fin: 0, debt: 0, lux: 0 };
const run = o => calc(Object.assign({}, base, o));
const near = (a, b, msg) => assert.ok(Math.abs(a - b) < 0.5, msg + ' got ' + a + ' expected ' + b);
const cases = [
  ['누리집 예: 단독 근로 200만+국민연금 30만 -> 소득평가액 88.8만', { w1: 200 * M, n1: 30 * M }, r => near(r.inc.earn + r.inc.other, 888000, 'eval')],
  ['누리집 예: 부부 본인 200만+연금 30만, 배우자 150만 -> 112.6만', { kind: 'both', w1: 200 * M, n1: 30 * M, w2: 150 * M }, r => near(r.inc.earn + r.inc.other, 1126000, 'eval')],
  ['소득·재산 0 단독 -> 349,700', {}, r => near(r.lo.total, 349700, 'pay')],
  ['부부 둘 다 0 -> 각 279,760, 합 559,520(보도자료)', { kind: 'both' }, r => { near(r.lo.a1, 279760, 'a1'); near(r.lo.total, 559520, 'tot'); near(r.lo.couple, 139880, 'couple') }],
  ['부부 1인 수급 -> 349,700, 부부감액 없음', { kind: 'one', w2: 300 * M }, r => { near(r.lo.total, 349700, 'pay'); assert.strictEqual(r.lo.couple, 0) }],
  ['재산 대도시 단독 경계 8억7,600만 -> 대상, 최저 34,970', { gen: 87600 * M }, r => { near(r.inc.total, 2470000, 'inc'); assert.ok(r.lo.eligible); near(r.lo.total, 34970, 'pay') }],
  ['8억7,601만 -> 탈락', { gen: 87601 * M }, r => assert.ok(!r.lo.eligible)],
  ['기본재산 미달분은 금융재산에서 안 뺌: 일반 5천만+금융 1억', { gen: 5000 * M, fin: 10000 * M }, r => near(r.inc.prop, 8000 * M * 0.04 / 12, 'prop')],
  ['부채 > 재산 -> 0 하한', { gen: 20000 * M, debt: 30000 * M }, r => near(r.inc.prop, 0, 'prop')],
  ['고급차 4,500만 -> 소득인정액 4,500만, 탈락', { lux: 4500 * M }, r => assert.ok(!r.lo.eligible)],
  ['이자소득 월 4만 공제', { intr: 10 * M }, r => near(r.inc.other, 60000, 'other')],
  ['근로 116만 이하 -> 0', { w1: 100 * M }, r => near(r.inc.earn, 0, 'earn')],
  ['근로만 단독 경계 4,688,571 -> 대상', { w1: 4688571 }, r => assert.ok(r.lo.eligible)],
  ['소득역전: 소득인정액 230만 -> 17만', { oth: 230 * M }, r => { near(r.lo.total, 170000, 'pay'); near(r.lo.cut, 179700, 'cut') }],
  ['소득역전: 245만 -> 최저 34,970', { oth: 245 * M }, r => near(r.lo.total, 34970, 'pay')],
  ['부부 둘: 350만 -> 452,000, 각 226,000', { kind: 'both', oth: 350 * M }, r => { near(r.lo.total, 452000, 'tot'); near(r.lo.a1, 226000, 'a1') }],
  ['부부 둘: 395만 -> 최저 합 69,940', { kind: 'both', oth: 395 * M }, r => near(r.lo.total, 69940, 'tot')],
  ['국민연금 50만(<=524,550) -> 감액 없음', { n1: 50 * M }, r => near(r.p1[0], 349700, 'p1')],
  ['국민연금 524,550 경계 -> 감액 없음', { n1: 524550 }, r => near(r.p1[0], 349700, 'p1')],
  ['국민연금 60만, A 모름 -> 274,250 ~ 349,700', { n1: 60 * M }, r => { near(r.p1[0], 274250, 'lo'); near(r.p1[1], 349700, 'hi'); near(r.lo.total, 274250, 'pay') }],
  ['국민연금 60만, A 30만 -> max(274,250, 324,550)=324,550', { n1: 60 * M, a1: 30 * M }, r => { near(r.p1[0], 324550, 'p'); near(r.hi.total, 324550, 'hi') }],
  ['국민연금 60만, A 10만 -> 상한 349,700', { n1: 60 * M, a1: 10 * M }, r => near(r.p1[0], 349700, 'p')],
  ['국민연금 100만, A 40만 -> 257,883', { n1: 100 * M, a1: 40 * M }, r => near(r.p1[0], 349700 - 400000 * 2 / 3 + 174850, 'p')],
  ['국민연금 100만, A 60만 -> 부가연금 174,850', { n1: 100 * M, a1: 60 * M }, r => near(r.p1[0], 174850, 'p')],
  ['국민연금 100만, A 모름 -> 174,850 ~ 349,700', { n1: 100 * M }, r => { near(r.p1[0], 174850, 'lo'); near(r.p1[1], 349700, 'hi') }],
  ['유족연금 100만 -> 기준연금액', { n1: 100 * M, t1: 'full' }, r => near(r.p1[0], 349700, 'p')],
  ['부부 둘, 배우자만 A급여 감액(174,850) + 소득역전 -> 비례 배분·1인 최저 34,970', { kind: 'both', n2: 100 * M, a2: 60 * M, oth: 290 * M }, r => {
    // 소득인정액 290만+100만=390만, c1=279,760 c2=139,880 합 419,640 -> 상한 395.2만-390만=52,000 -> 최저 69,940
    near(r.inc.total, 3900000, 'inc'); const T = 69940; near(r.lo.a1, Math.max(T * 279760 / 419640, 34970), 'a1'); near(r.lo.a2, 34970, 'a2 floor') }],
];
for (const [name, o, chk] of cases) { chk(run(o)); console.log('PASS', name); }
// 글의 최대치 표 값 검산 (선정기준액에서 거꾸로)
const t = [[{ gen: 87600 * M }, 2470000], [{ region: 'mid', gen: 82600 * M }, 2470000], [{ region: 'rural', gen: 81350 * M }, 2470000], [{ fin: 76100 * M }, 2470000],
  [{ kind: 'both', gen: 132060 * M }, 3952000], [{ kind: 'both', region: 'mid', gen: 127060 * M }, 3952000], [{ kind: 'both', region: 'rural', gen: 125810 * M }, 3952000], [{ kind: 'both', fin: 120560 * M }, 3952000]];
for (const [o, sel] of t) near(run(o).inc.total, sel, JSON.stringify(o));
near(run({ kind: 'both', w1: 6805714 }).inc.total, 3952000, 'couple single earner'); near(run({ kind: 'both', w1: 3982857, w2: 3982857 }).inc.total, 3952000, 'couple two earners');
near(run({ gen: 70000 * M }).inc.total, 1883333.3, 'FAQ 7억'); near(run({ gen: 70000 * M }).lo.total, 349700, 'FAQ 7억 pay');
near(run({ w1: 300 * M }).inc.total, 1288000, 'FAQ 300만');
console.log('PASS 최대치 표 8칸 + 근로소득 2칸 + FAQ 숫자');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'bp-kind': 'single', 'bp-w1': '0', 'bp-w2': '0', 'bp-n1': '0', 'bp-n2': '0', 'bp-t1': 'old', 'bp-t2': 'old', 'bp-a1': '', 'bp-a2': '', 'bp-pub': '0', 'bp-int': '0', 'bp-oth': '0', 'bp-region': 'big', 'bp-gen': '20000', 'bp-fin': '3000', 'bp-debt': '0', 'bp-lux': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = { 'bp-out': el('bp-out') }; Object.keys(vals).forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
assert.ok(outP.join().includes('349,700원'));
