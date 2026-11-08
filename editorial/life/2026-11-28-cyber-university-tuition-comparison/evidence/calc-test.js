// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.cyberTuitionCalc, S = window.cyberTuitionData;
const rate = n => S.find(x => x[0] === n)[1];
// 단가는 본문 비교표와 같아야 한다
const table = { '건양사이버대': 73000, '경희사이버대': 84000, '고려사이버대': 76000, '국제사이버대': 73000, '글로벌사이버대': 74000, '대구사이버대': 78000, '디지털서울문화예술대': 89500, '부산디지털대': 74000, '사이버한국외대': 83000, '서울디지털대': 67500, '서울사이버대': 82000, '세종사이버대': 84000, '숭실사이버대': 80000, '한국열린사이버대': 75000, '한양사이버대': 84000, '화신사이버대': 73000 };
for (const [k, v] of Object.entries(table)) { assert.strictEqual(rate(k), v, k); assert.ok(html.includes((v * 18).toLocaleString('en-US') + '원'), k + ' 18학점 표'); }
console.log('PASS 단가 16곳 + 18학점 표 금액');
const cases = [
  ['경희 140학점 18학점씩 감면 없음', [84000, 18, 140, 0, 0, 99000, 0], { sems: 8, total: 11859000, firstSem: 1611000, nextSem: 1512000 }],
  ['경희 직장인 30% 2학기', [84000, 18, 140, 30, 2, 99000, 0], { total: 10951800, firstSem: 1058400 + 99000, nextSem: 1058400 }],
  ['73,000원 140학점 실입학비용 없음', [73000, 18, 140, 0, 0, 0, 0], { total: 10220000 }],
  ['방송통신대 계열1 8학기', [0, 18, 140, 0, 0, 0, 343800], { sems: 8, total: 2750400, year: 687600 }],
  ['3학년 편입 82,000원 70학점', [82000, 18, 70, 0, 0, 99000, 0], { sems: 4, total: 5839000 }],
  ['서울디지털 25% 졸업까지', [67500, 18, 140, 25, 0, 0, 0], { firstSem: 911250, total: 7087500 }],
  ['감면 100%', [78000, 18, 36, 100, 0, 66000, 0], { total: 66000 }],
];
for (const [name, a, exp] of cases) {
  const r = calc(...a);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ sems: r.sems, firstSem: r.firstSem, nextSem: r.nextSem, year: r.year, total: r.total }));
}
// UI 기본값(첫 학교, 18학점, 140학점) 렌더 확인 — 최소 DOM 스텁
const vals = { 'cu-school': '1', 'cu-knou': '343800', 'cu-credits': '18', 'cu-sch': '0', 'cu-rate': '0', 'cu-sem': '0', 'cu-grad': '140' };
const outP = [];
const mk = id => ({ id, value: vals[id], checked: true, style: {}, opts: [], addEventListener() {}, appendChild(c) { if (id === 'cu-out') outP.push(c.textContent); else this.opts.push(c); }, set innerHTML(v) { if (id === 'cu-out') outP.length = 0; else this.opts = []; } });
const els = {}; ['cu-out', 'cu-knou-row', 'cu-first', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
// fillSch가 감면 선택을 'none'으로 비웠으므로 기본 상태는 경희, 감면 없음
console.log('학교 목록 수:', els['cu-school'].opts.length, '| 경희 장학 옵션 수:', els['cu-sch'].opts.length);
console.log('UI 기본값 출력(경희, 18학점, 140학점):', outP.join(' | '));
assert.ok(outP.join().includes('11,859,000원'));
