// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('raw < in string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.baeminClubCalc;
// calc(fee,aN,aTip,hN,hTip,hDisc,pay,rate)
const cases = [
  ['기본값: 알뜰 3회 x 2,500', [3990, 3, 2500, 0, 0, 0, 0, 0], { without: 7500, withClub: 3990, saving: 3510, breakEven: 2 }],
  ['배달팁 1,000 -> 4회', [3990, 1, 1000, 0, 0, 0, 0, 0], { breakEven: 4 }],
  ['배달팁 1,500 -> 3회', [3990, 1, 1500, 0, 0, 0, 0, 0], { breakEven: 3 }],
  ['배달팁 2,000 -> 2회', [3990, 1, 2000, 0, 0, 0, 0, 0], { breakEven: 2 }],
  ['배달팁 3,500 -> 2회', [3990, 1, 3500, 0, 0, 0, 0, 0], { breakEven: 2 }],
  ['배달팁 4,000 -> 1회', [3990, 1, 4000, 0, 0, 0, 0, 0], { breakEven: 1, saving: 10 }],
  ['주문 0회 -> 구독료만큼 손해', [3990, 0, 2500, 0, 0, 0, 0, 0], { saving: -3990 }],
  ['5% 6만원 -> 포인트 3,000 한도, 실부담 990', [3990, 0, 0, 0, 0, 0, 60000, 5], { points: 3000, withClub: 990, breakEven: null }],
  ['5% 10만원 -> 한도 3,000, 팁 990 1회 본전', [3990, 1, 990, 0, 0, 0, 100000, 5], { points: 3000, breakEven: 1 }],
  ['2% 3만원 -> 600', [3990, 2, 2000, 0, 0, 0, 30000, 2], { points: 600, withClub: 3390 }],
  ['한집 2회 팁 3,000 할인 1,000', [3990, 1, 2500, 2, 3000, 1000, 0, 0], { without: 8500, withClub: 7990, hjSave: 2000, breakEven: 1 }],
  ['할인액이 팁보다 크면 팁까지만', [3990, 0, 0, 1, 1000, 5000, 0, 0], { withClub: 3990, hjSave: 1000 }],
];
for (const [name, a, exp] of cases) {
  const r = calc(...a);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표 검산
[[1000, 4], [1500, 3], [2000, 2], [2500, 2], [3000, 2], [3500, 2], [4000, 1]].forEach(([t, n]) => {
  assert.strictEqual(calc(3990, 1, t, 0, 0, 0, 0, 0).breakEven, n);
  assert.ok(html.includes('<td>' + t.toLocaleString('en-US') + '원</td><td>' + n + '회</td><td>' + (t * n).toLocaleString('en-US') + '원</td>'));
});
[[30000, 600, 1500], [60000, 1200, 3000], [100000, 2000, 3000], [150000, 3000, 3000]].forEach(([p, a, b]) => {
  assert.strictEqual(calc(0, 0, 0, 0, 0, 0, p, 2).points, a); assert.strictEqual(calc(0, 0, 0, 0, 0, 0, p, 5).points, b);
});
console.log('PASS 본전 표 7행 + 포인트 표 4행');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'bc-fee': '3990', 'bc-an': '3', 'bc-at': '2500', 'bc-hn': '0', 'bc-ht': '0', 'bc-hd': '0', 'bc-pay': '0', 'bc-rate': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['bc-out', 'bc-f3990', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('3,510원'));
