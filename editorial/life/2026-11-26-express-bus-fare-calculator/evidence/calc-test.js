// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const F = window.busFareCalc, C = window.busCancelFee, R = window.busFareData;
const find = (route, cls) => R.find(r => r[0] === route)[2].find(c => c[0] === cls);
// 조회값 대조 (evidence/kobus-fares-summary.json.txt)
assert.deepStrictEqual(find('서울경부→부산', '우등'), ['우등', 43300, 21700, 0]);
assert.deepStrictEqual(find('서울경부→부산', '고속'), ['고속', 29100, 14600, 23300]);
assert.deepStrictEqual(find('센트럴시티(서울)→광주(유·스퀘어)', '프리미엄'), ['프리미엄', 43500, 21800, 0]);
assert.deepStrictEqual(find('동서울→강릉', '프리미엄'), ['프리미엄', 37000, 13700, 0]);
assert.strictEqual(R.length, 22);
console.log('PASS 조회 요금 데이터 22개 노선');
const cases = [
  ['부산 우등 성인2+초등1 왕복', { adult: 43300, child: 21700, teen: 0, na: 2, nc: 1, nt: 0, ns: 0, sr: 0, rt: true }, { oneWay: 108300, total: 216600, tickets: 6 }],
  ['부산 고속 성인1+중고생1 편도', { adult: 29100, child: 14600, teen: 23300, na: 1, nc: 0, nt: 1, ns: 0, sr: 0, rt: false }, { oneWay: 52400, total: 52400 }],
  ['청소년 요금 없음 -> 성인 요금', { adult: 43300, child: 21700, teen: 0, na: 0, nc: 0, nt: 1, ns: 0, sr: 0, rt: false }, { teenFare: 43300, total: 43300 }],
  ['포항 우등 경로 20%', { adult: 37500, child: 18800, teen: 30000, na: 0, nc: 0, nt: 0, ns: 1, sr: 20, rt: false }, { seniorFare: 30000, total: 30000 }],
];
for (const [name, p, exp] of cases) {
  const r = F(p);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 취소 수수료: day 0 월~목,1 금~일,2 공휴일·명절 / when 0..4 / after 600|700
const cc = [
  ['43,300 금~일 1일전 7.5% -> 3,247.5 절사 3,200', [43300, 1, 1, 600], { rate: 7.5, fee: 3200, refund: 40100 }],
  ['43,300 월~목 1일전 5% -> 2,100', [43300, 0, 1, 600], { rate: 5, fee: 2100, refund: 41200 }],
  ['43,300 금~일 3시간 미만 15% -> 6,400', [43300, 1, 2, 600], { rate: 15, fee: 6400, refund: 36900 }],
  ['43,300 출발 후 60% -> 25,900', [43300, 0, 3, 600], { rate: 60, fee: 25900, refund: 17400 }],
  ['43,300 출발 후 2027.5~ 70% -> 30,310 -> 30,300', [43300, 2, 3, 700], { rate: 70, fee: 30300, refund: 13000 }],
  ['2일 전 0%', [67400, 2, 0, 600], { rate: 0, fee: 0, refund: 67400 }],
  ['도착 예정 초과 100%', [9700, 1, 4, 600], { rate: 100, fee: 9700, refund: 0 }],
  ['수수료 100원 미만 -> 원 단위 절사 (1,850 x 5% = 92.5 -> 90)', [1850, 0, 1, 600], { fee: 90, refund: 1760 }],
  ['천안 고속 7,400 공휴일 3시간 미만 20% -> 1,480 -> 1,400', [7400, 2, 2, 600], { fee: 1400, refund: 6000 }],
];
for (const [name, a, exp] of cc) {
  const r = C(...a);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'eb-na': '1', 'eb-nc': '0', 'eb-nt': '0', 'eb-ns': '0', 'eb-sr': '0', 'eb-day': '0', 'eb-when': '2', 'eb-after': '600', 'eb-route': '0', 'eb-cls': '0' };
const out = [];
const mk = id => ({ id, value: vals[id] || '', checked: false, style: {}, addEventListener() {}, appendChild(c) { if (id === 'eb-out') out.push(c.textContent); }, set innerHTML(v) { if (id === 'eb-out') out.length = 0; } });
const els = {}; ['eb-route', 'eb-cls', 'eb-adult', 'eb-child', 'eb-teen', 'eb-rt', 'eb-out', ...Object.keys(vals)].forEach(id => els[id] = els[id] || mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', out.join(' | '));
assert.ok(out.join().includes('원'));
