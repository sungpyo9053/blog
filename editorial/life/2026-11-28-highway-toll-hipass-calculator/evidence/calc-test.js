// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g)) if (lit.indexOf('<') >= 0) throw new Error('< in string literal ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
assert.strictEqual(faq, (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length);
console.log('PASS JSON-LD 파싱, FAQ', faq, '개 = 본문 h3 수');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.hwTollCalc;
const B = { lane: 'four', day: 'weekday', time: '12:00', hipass: true, disc: 'none' };
const C = (o) => calc(Object.assign({}, B, o));
const cases = [
  // 공식 조회(hipass-fare-api-samples.txt) 서울->부산: 18600,19000,19700,26100,30700,경차 9300 / 주말 1종 19500, 경차 9750
  ['서울~부산 1종 400km', { mode: 'closed', cls: 'c1', km: 400 }, 18600],
  ['서울~부산 2종', { mode: 'closed', cls: 'c2', km: 400 }, 19000],
  ['서울~부산 3종', { mode: 'closed', cls: 'c3', km: 400 }, 19700],
  ['서울~부산 4종', { mode: 'closed', cls: 'c4', km: 400 }, 26100],
  ['서울~부산 5종', { mode: 'closed', cls: 'c5', km: 400 }, 30700],
  ['서울~부산 경차', { mode: 'closed', cls: 'light', km: 400 }, 9300],
  ['서울~부산 주말 1종(5% 할증, 19530->19500)', { mode: 'closed', cls: 'c1', km: 400, day: 'weekend', time: '13:00' }, 19500],
  ['서울~부산 주말 경차(19500의 절반)', { mode: 'closed', cls: 'light', km: 400, day: 'weekend', time: '13:00' }, 9750],
  ['서울~부산 주말 2종 할증 없음', { mode: 'closed', cls: 'c2', km: 400, day: 'weekend', time: '13:00' }, 19000],
  ['주말 21:00 출구 -> 할증 없음', { mode: 'closed', cls: 'c1', km: 400, day: 'weekend', time: '21:00' }, 18600],
  ['주말 06:59 -> 할증 없음', { mode: 'closed', cls: 'c1', km: 400, day: 'weekend', time: '06:59' }, 18600],
  ['주말 07:00 -> 할증', { mode: 'closed', cls: 'c1', km: 400, day: 'weekend', time: '07:00' }, 19500],
  // 공식 조회 서울->대전 8200 / 주말 8600, 경차 4100 / 주말 4300
  ['서울~대전 직접입력 주말', { mode: 'direct', cls: 'c1', fare: 8200, day: 'weekend', time: '14:00' }, 8600],
  ['서울~대전 경차 직접입력(6종 칸 4100) 주말', { mode: 'direct', cls: 'light', fare: 4100, day: 'weekend', time: '14:00' }, 4300],
  // 공식 조회 수원신갈->기흥 1200 / 출퇴근A 600, B 960, 경차 600 그대로, 4종 1300 그대로
  ['수원신갈~기흥 06:00 출퇴근 50%', { mode: 'direct', cls: 'c1', fare: 1200, time: '06:00', short: true }, 600],
  ['수원신갈~기흥 08:00 출퇴근 20%', { mode: 'direct', cls: 'c1', fare: 1200, time: '08:00', short: true }, 960],
  ['경차 08:00 -> 600 그대로', { mode: 'direct', cls: 'light', fare: 600, time: '08:00', short: true }, 600],
  ['4종 08:00 -> 1300 그대로', { mode: 'direct', cls: 'c4', fare: 1300, time: '08:00', short: true }, 1300],
  ['경계 07:00 -> 20%', { mode: 'direct', cls: 'c1', fare: 1200, time: '07:00', short: true }, 960],
  ['경계 09:00 -> 할인 없음', { mode: 'direct', cls: 'c1', fare: 1200, time: '09:00', short: true }, 1200],
  ['경계 04:59 -> 할인 없음', { mode: 'direct', cls: 'c1', fare: 1200, time: '04:59', short: true }, 1200],
  ['경계 18:00 -> 20%', { mode: 'direct', cls: 'c1', fare: 1200, time: '18:00', short: true }, 960],
  ['경계 20:00 -> 50%', { mode: 'direct', cls: 'c1', fare: 1200, time: '20:00', short: true }, 600],
  ['경계 22:00 -> 할인 없음', { mode: 'direct', cls: 'c1', fare: 1200, time: '22:00', short: true }, 1200],
  ['하이패스 아님 -> 출퇴근 없음', { mode: 'direct', cls: 'c1', fare: 1200, time: '06:00', short: true, hipass: false }, 1200],
  ['20km 이상 -> 출퇴근 없음', { mode: 'direct', cls: 'c1', fare: 1200, time: '06:00', short: false }, 1200],
  ['주말엔 출퇴근 없음(할증만)', { mode: 'direct', cls: 'c1', fare: 1200, time: '08:00', short: true, day: 'weekend' }, 1300],
  ['폐쇄식 19.9km 06:00 -> 50%', { mode: 'closed', cls: 'c1', km: 19.9, time: '06:00' }, 900],
  ['폐쇄식 20km 06:00 -> 할인 없음', { mode: 'closed', cls: 'c1', km: 20, time: '06:00' }, 1800],
  // 개방식 표
  ['개방식 성남 1종', { mode: 'open', cls: 'c1', gate: '성남' }, 1000],
  ['개방식 금토 경차', { mode: 'open', cls: 'light', gate: '금토' }, 550],
  ['개방식 김포 5종', { mode: 'open', cls: 'c5', gate: '김포' }, 1100],
  // 차로
  ['6차로 100km 1종: 900+100x53.16=6216 -> 6200', { mode: 'closed', cls: 'c1', km: 100, lane: 'six' }, 6200],
  ['2차로만 30km 1종: 450+30x22.15=1114.5 -> 1100', { mode: 'closed', cls: 'c1', km: 30, lane: 'two' }, 1100],
  // 감면(가장 높은 감면율 하나)
  ['전기차 100km 30%: 5300 -> 3710', { mode: 'closed', cls: 'c1', km: 100, disc: 'ev' }, 3710],
  ['전기차 + 출퇴근 50% -> 50%', { mode: 'direct', cls: 'c1', fare: 1200, time: '06:00', short: true, disc: 'ev' }, 600],
  ['전기 경차 -> 경차 50%', { mode: 'closed', cls: 'light', km: 100, disc: 'ev' }, 2650],
  ['장애인 50%', { mode: 'closed', cls: 'c1', km: 100, disc: 'disabled' }, 2650],
  ['국가유공자 1~5급 면제', { mode: 'closed', cls: 'c1', km: 100, disc: 'merit15' }, 0],
  ['다자녀 3자녀 평일 -> 미적용', { mode: 'closed', cls: 'c1', km: 100, disc: 'kids3' }, 5300],
  ['다자녀 3자녀 주말: 5300x1.05=5565->5600, x0.8=4480', { mode: 'closed', cls: 'c1', km: 100, disc: 'kids3', day: 'weekend', time: '12:00' }, 4480],
  ['다자녀 2자녀 주말: 5600x0.9=5040', { mode: 'closed', cls: 'c1', km: 100, disc: 'kids2', day: 'weekend', time: '12:00' }, 5040],
  ['명절 면제', { mode: 'closed', cls: 'c5', km: 400, day: 'holiday' }, 0],
];
for (const [name, o, exp] of cases) {
  const r = C(o);
  assert.strictEqual(r.fare, exp, name + ' -> ' + JSON.stringify(r));
  console.log('PASS', name, '=', r.fare, '(' + r.label + ')');
}
// 본문 거리별 표 값 검산
const table = { 10: [1300, 650, 1400, 1400, 1500, 1600, 1400], 30: [2200, 1100, 2300, 2300, 2800, 3100, 2300], 50: [3100, 1550, 3200, 3200, 4000, 4600, 3300], 100: [5300, 2650, 5400, 5600, 7200, 8300, 5600], 200: [9800, 4900, 9900, 10300, 13500, 15800, 10300], 300: [14200, 7100, 14500, 15000, 19800, 23200, 14900], 400: [18600, 9300, 19000, 19700, 26100, 30700, 19500] };
for (const k of Object.keys(table)) {
  const got = ['c1', 'light', 'c2', 'c3', 'c4', 'c5'].map(cls => C({ mode: 'closed', cls, km: +k }).fare);
  got.push(C({ mode: 'closed', cls: 'c1', km: +k, day: 'weekend' }).fare);
  assert.deepStrictEqual(got, table[k], k + 'km ' + got);
  const row = html.match(new RegExp('<tr><td>' + k + 'km</td>(.*?)</tr>'))[1].match(/<td>([\d,]+)<\/td>/g).map(x => +x.replace(/\D/g, ''));
  assert.deepStrictEqual(row, table[k], '본문 표 ' + k + 'km');
}
console.log('PASS 거리별 표 49칸 = 계산기 = 본문');
// 개방식 표: 본문과 스크립트 데이터 일치
let nOpen = 0;
for (const m of html.matchAll(/<tr><td>([가-힣]+)<\/td>((?:<td>[\d,]+<\/td>){6})<\/tr>/g)) {
  const v = m[2].match(/[\d,]+/g).map(x => +x.replace(/,/g, ''));
  ['c1', 'c2', 'c3', 'c4', 'c5'].forEach((cls, i) => assert.strictEqual(C({ mode: 'open', cls, gate: m[1] }).fare, v[i], m[1] + cls));
  assert.strictEqual(C({ mode: 'open', cls: 'light', gate: m[1] }).fare, v[5], m[1] + ' 경차');
  nOpen++;
}
assert.strictEqual(nOpen, 18);
console.log('PASS 개방식 요금표 18곳 본문 = 계산기');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'hw-mode': 'closed', 'hw-cls': 'c1', 'hw-km': '100', 'hw-lane': 'four', 'hw-gate': '', 'hw-fare': '8200', 'hw-day': 'weekday', 'hw-time': '12:00', 'hw-disc': 'none' };
const checks = { 'hw-hipass': true, 'hw-short': false };
const outP = [];
const mk = id => ({ value: vals[id], checked: checks[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { if (id === 'hw-out') outP.push(p.textContent); } });
const els = {}; ['hw-out', 'hw-row-km', 'hw-row-lane', 'hw-row-gate', 'hw-row-fare', 'hw-row-short', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('5,300원'));
