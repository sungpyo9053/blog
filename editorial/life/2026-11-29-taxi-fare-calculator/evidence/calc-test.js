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
const calc = window.taxiFareCalc;
const cases = [
  ['경기도 공식 예: 표준형 5km, 신호대기 5분, 아침 -> ≒8,400원', 'gyeonggi', 5, 5, '08:00', 0, { fare: 8400 }],
  ['서울 같은 조건(단가 동일) -> 8,400원', 'seoul', 5, 5, '08:00', 0, { fare: 8400 }],
  ['경계: 서울 정확히 1.6km 주간 -> 4,800원', 'seoul', 1.6, 0, '12:00', 0, { fare: 4800, night: 0 }],
  ['경계: 1.6km + 131m 주간 -> 4,900원', 'seoul', 1.731, 0, '12:00', 0, { fare: 4900 }],
  ['경계: 21:59 탑승 1.6km -> 주간 4,800원', 'seoul', 1.6, 0, '21:59', 0, { fare: 4800, night: 0 }],
  ['경계: 22:00 정각 -> 심야 20% 5,800원', 'seoul', 1.6, 0, '22:00', 0, { fare: 5800, night: 0.2 }],
  ['경계: 22:59 -> 20% 5,800원', 'seoul', 1.6, 0, '22:59', 0, { fare: 5800, night: 0.2 }],
  ['경계: 23:00 정각 -> 40% 6,700원', 'seoul', 1.6, 0, '23:00', 0, { fare: 6700, night: 0.4 }],
  ['경계: 00:00 -> 40% 6,700원', 'seoul', 1.6, 0, '00:00', 0, { fare: 6700, night: 0.4 }],
  ['경계: 01:59 -> 40% 6,700원', 'seoul', 1.6, 0, '01:59', 0, { fare: 6700, night: 0.4 }],
  ['경계: 02:00 정각 -> 20% 5,800원', 'seoul', 1.6, 0, '02:00', 0, { fare: 5800, night: 0.2 }],
  ['경계: 03:59 -> 20% 5,800원', 'seoul', 1.6, 0, '03:59', 0, { fare: 5800, night: 0.2 }],
  ['경계: 04:00 정각 -> 주간 4,800원', 'seoul', 1.6, 0, '04:00', 0, { fare: 4800, night: 0 }],
  ['서울 심야 단가: 23시 1.6km+131m -> 6,700+140=6,840 -> 6,800원', 'seoul', 1.731, 0, '23:30', 0, { fare: 6800 }],
  ['서울 심야 단가: 22시 저속 30초 -> 5,800+120=5,920 -> 5,900원', 'seoul', 1.6, 0.5, '22:30', 0, { fare: 5900 }],
  ['서울 시계외 주간: 1.6km+131m(경계 밖) -> 4,800+120=4,920 -> 4,900원', 'seoul', 1.731, 0, '12:00', 1, { fare: 4900, outTotal: 0.2 }],
  ['서울 시계외+심야40% = 60%: 1.6km+1310m 경계 밖 -> 6,700+10x160=8,300원', 'seoul', 2.91, 0, '23:30', 5, { fare: 8300 }],
  ['경기 심야 23:00 -> 4,800x1.3=6,240 -> 6,200원', 'gyeonggi', 1.6, 0, '23:00', 0, { fare: 6200, night: 0.3 }],
  ['경기 22:59 -> 주간 4,800원', 'gyeonggi', 1.6, 0, '22:59', 0, { fare: 4800, night: 0 }],
  ['경기 04:00 -> 주간', 'gyeonggi', 1.6, 0, '04:00', 0, { night: 0 }],
  ['경기 심야+시계외 -> 중복률 미확인 플래그', 'gyeonggi', 5, 0, '23:30', 2, { flag: true }],
  ['부산 정확히 2km 주간 -> 4,800원', 'busan', 2, 0, '12:00', 0, { fare: 4800 }],
  ['부산 1.6km(기본거리 2km 안) -> 4,800원', 'busan', 1.6, 0, '12:00', 0, { fare: 4800 }],
  ['부산 23:00 -> 20%', 'busan', 2, 0, '23:00', 0, { night: 0.2, fare: 5800 }],
  ['부산 00:00 -> 30% 6,240 -> 6,200원', 'busan', 2, 0, '00:00', 0, { night: 0.3, fare: 6200 }],
  ['부산 02:00 -> 20%', 'busan', 2, 0, '02:00', 0, { night: 0.2 }],
  ['부산 04:00 -> 주간', 'busan', 2, 0, '04:00', 0, { night: 0 }],
  ['부산 주간 시계외 30%', 'busan', 3, 0, '12:00', 1, { outTotal: 0.3 }],
  ['부산 23시 복합 40%', 'busan', 3, 0, '23:30', 1, { outTotal: 0.4 }],
  ['부산 01시 복합 50%', 'busan', 3, 0, '01:00', 1, { outTotal: 0.5 }],
];
for (const [name, r, km, slow, t, out, exp] of cases) {
  const x = calc(r, km, slow, t, out);
  for (const k of Object.keys(exp)) assert.ok(x[k] === exp[k] || Math.abs(x[k] - exp[k]) < 1e-9, name + ' ' + k + '=' + x[k]);
  console.log('PASS', name, JSON.stringify(x));
}
// 본문 거리별 요금표 검산
const table = [[3, 3, [6500, 7800, 9000, 8400, 6100]], [5, 5, [8400, 10100, 11700, 10900, 8000]], [10, 8, [12800, 15400, 17900, 16700, 12300]],
  [15, 10, [17000, 20500, 23800, 22100, 16500]], [20, 12, [21200, 25500, 29700, 27600, 20600]], [30, 15, [29500, 35400, 41300, 38300, 28700]]];
for (const [km, s, row] of table) {
  const got = [calc('seoul', km, s, '12:00', 0), calc('seoul', km, s, '22:30', 0), calc('seoul', km, s, '23:30', 0), calc('gyeonggi', km, s, '23:30', 0), calc('busan', km, s, '12:00', 0)].map(r => r.fare);
  assert.deepStrictEqual(got, row, km + 'km');
  for (const v of row) assert.ok(html.includes('<td>' + v.toLocaleString('en-US') + '원</td>'), v + ' in html');
}
assert.strictEqual(calc('seoul', 20, 12, '12:00', 10).fare, 22800);
assert.strictEqual(calc('seoul', 20, 12, '23:30', 10).fare, 31300);
console.log('PASS 본문 요금표 30칸 + 시계외 예 2개');
// UI 기본값(서울 5km, 저속 5분, 12:00) 렌더 확인 — 최소 DOM 스텁
const vals = { 'tx-region': 'seoul', 'tx-km': '5', 'tx-slow': '5', 'tx-time': '12:00', 'tx-out': '0', 'tx-toll': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['tx-out-box', 'tx-t22', 'tx-t23', 'tx-t02', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('8,400원'));
