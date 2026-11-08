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
const P = window.parkingFeeCalc;
const di = (reg, label) => P.D[reg].findIndex(o => o[0].indexOf(label) >= 0);
const cases = [
  // [이름, 요금표, 급지 index, 분, 감면 라벨, 환승주차장, custom, 기대 {base, pay}]
  ['서울 노외 1급지 1시간 = 12 x 400', 'seoul-out', 0, 60, '감면 없음', false, null, { base: 4800, pay: 4800 }],
  ['서울 노외 1급지 61분 -> 13단위(올림)', 'seoul-out', 0, 61, '감면 없음', false, null, { base: 5200 }],
  ['서울 노외 1급지 10시간 -> 1일 상한 28,000', 'seoul-out', 0, 600, '감면 없음', false, null, { base: 28000 }],
  ['서울 노외 1급지 25시간 -> 28,000 + 1시간 4,800', 'seoul-out', 0, 1500, '감면 없음', false, null, { base: 32800 }],
  ['서울 노외 2급지 90분 경차 50% -> 2,250 -> 100원 미만 버림 2,200', 'seoul-out', 1, 90, '경차', false, null, { base: 4500, pay: 2200 }],
  ['서울 노외 1급지 4시간 장애인 환승주차장(3h 면제 후 80%) -> 960 -> 900', 'seoul-out', 0, 240, '장애인', true, null, { base: 19200, pay: 900 }],
  ['서울 노외 1급지 2시간 장애인 일반 80% -> 9,600 x 0.2 = 1,920 -> 1,900', 'seoul-out', 0, 120, '장애인', false, null, { pay: 1900 }],
  ['서울 노외 3급지 3시간 전통시장(최초 2h 50%) -> 5,400 - 1,800', 'seoul-out', 2, 180, '전통시장', false, null, { base: 5400, pay: 3600 }],
  ['서울 노외 1급지 전통시장 -> 1급지 제외', 'seoul-out', 0, 60, '전통시장', false, null, { pay: 4800 }],
  ['서울 노외 2급지 3시간 전기차 충전(1h 면제 후 50%)', 'seoul-out', 1, 180, '전기차', false, null, { base: 9000, pay: 3000 }],
  ['서울 노상 1급지 30분 = 6 x 500, 상한 없음', 'seoul-on', 0, 30, '감면 없음', false, null, { base: 3000 }],
  ['서울 노상 1급지 10시간 상한 없음 = 120 x 500', 'seoul-on', 0, 600, '감면 없음', false, null, { base: 60000 }],
  ['송파 노외 5급지 2시간 = 24 x 50', 'songpa-out', 4, 120, '감면 없음', false, null, { base: 1200 }],
  ['송파 노외 3급지 2시간 전통시장 90분 30% -> 3,600 - 810 = 2,790 -> 2,700', 'songpa-out', 2, 120, '전통시장', false, null, { base: 3600, pay: 2700 }],
  ['부산 노외 1급지(가) 1시간 = 6 x 700', 'busan-out', 0, 60, '감면 없음', false, null, { base: 4200 }],
  ['부산 노외 1급지(가) 6시간 -> 1일 21,000', 'busan-out', 0, 360, '감면 없음', false, null, { base: 21000 }],
  ['부산 노상 1급지(가) 6시간 -> 상한 없음 25,200', 'busan-on', 0, 360, '감면 없음', false, null, { base: 25200 }],
  ['부산 노외 2급지 2시간 장애인(1h 면제 후 50%) -> 900, 단수처리 없음', 'busan-out', 2, 120, '장애인', false, null, { base: 3600, pay: 900 }],
  ['부산 노외 4급지 3시간 전통시장(1h 면제, 추가 1h 50%) -> 1,800 - 600 - 300', 'busan-out', 4, 180, '전통시장', false, null, { base: 1800, pay: 900 }],
  ['인천 1급지 30분 = 최초 1,000', 'incheon', 0, 30, '감면 없음', false, null, { base: 1000 }],
  ['인천 1급지 1시간 = 1,000 + 2 x 500', 'incheon', 0, 60, '감면 없음', false, null, { base: 2000 }],
  ['인천 1급지 4시간 59분 = 1,000 + 18 x 500', 'incheon', 0, 299, '감면 없음', false, null, { base: 10000 }],
  ['인천 2급지 5시간 -> 전일 6,000', 'incheon', 1, 300, '감면 없음', false, null, { base: 6000 }],
  ['인천 2급지 4시간 = 600 + 14 x 300 = 4,800', 'incheon', 1, 240, '감면 없음', false, null, { base: 4800 }],
  ['인천 1급지 2시간 장애인(1h 면제 후 80%) -> 2,000 x 0.2 = 400', 'incheon', 0, 120, '장애인', false, null, { base: 4000, pay: 400 }],
  ['인천 3급지 2시간 경차 60% -> 1,600 x 0.4 = 640 -> 600', 'incheon', 2, 120, '경차', false, null, { base: 1600, pay: 600 }],
  ['직접 입력 10분당 600원 35분 -> 4단위', 'custom', 0, 35, '감면 없음', false, { u: 10, f: 600, d: 0 }, { base: 2400, pay: 2400 }],
  ['직접 입력 5분당 440원 1일 31,600원 8시간 -> 31,600', 'custom', 0, 480, '감면 없음', false, { u: 5, f: 440, d: 31600 }, { base: 31600 }],
  ['0분 -> 0원', 'seoul-out', 0, 0, '감면 없음', false, null, { base: 0, pay: 0 }],
];
for (const [name, r, gi, min, lab, tlot, cu, exp] of cases) {
  const reg = r === 'custom' ? 'custom' : P.T[r].d;
  const i = di(reg, lab); assert.ok(i >= 0, name + ' discount label');
  const x = P.calc(r, gi, min, i, tlot, cu);
  for (const k of Object.keys(exp)) assert.strictEqual(x[k], exp[k], name + ' ' + k + '=' + x[k]);
  console.log('PASS', name, JSON.stringify({ base: x.base, pay: x.pay }));
}
// 본문 표와 계산기 상수 대조 (조례 별표 1)
assert.deepStrictEqual(P.T['seoul-out'].g.map(g => [g[1], g[2]]), [[400, 28000], [250, 18000], [150, 10000]]);
assert.deepStrictEqual(P.T['seoul-on'].g.map(g => g[1]), [500, 250, 150]);
assert.deepStrictEqual(P.T['songpa-on'].g.map(g => g[1]), [500, 250, 150, 100, 50]);
assert.deepStrictEqual(P.T['busan-out'].g.map(g => [g[1], g[2]]), [[700, 21000], [500, 15000], [300, 8000], [200, 4700], [100, 2400]]);
assert.deepStrictEqual(P.T['incheon'].g.map(g => [g[3], g[1], g[2]]), [[1000, 500, 10000], [600, 300, 6000], [400, 200, 4000], [300, 150, 3000]]);
console.log('PASS 요금표 상수 5종');
// UI 기본값 렌더 (서울 노외 1급지 2시간, 감면 없음) — 최소 DOM 스텁
const vals = { 'pk-region': 'seoul-out', 'pk-grade': '0', 'pk-disc': '0', 'pk-h': '2', 'pk-m': '0', 'pk-cu': '10', 'pk-cf': '500', 'pk-cd': '0' };
const outP = [];
const mk = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { if (id === 'pk-out') outP.length = 0; }, appendChild(p) { if (id === 'pk-out') outP.push(p.textContent); } });
const els = {}; ['pk-out', 'pk-custom', 'pk-tlot', 'pk-tlot-row', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('9,600원'));
