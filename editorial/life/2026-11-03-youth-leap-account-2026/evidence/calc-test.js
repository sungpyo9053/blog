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
const calc = window.youthLeapCalc;
const cases = [
  ['공식표: 2,400 이하 70만 -> 33,000', 'w', 2000, 700000, 60, 0, { band: 0, monthly: 33000, contrib: 1980000 }],
  ['공식표: 3,600 이하 70만 -> 29,000', 'w', 3600, 700000, 60, 0, { band: 1, monthly: 29000 }],
  ['공식표: 4,800 이하 70만 -> 25,200', 'w', 4000, 700000, 60, 0, { band: 2, monthly: 25200 }],
  ['공식표: 6,000 이하 70만 -> 21,000', 'w', 6000, 700000, 60, 0, { band: 3, monthly: 21000 }],
  ['Ⅰ구간만: 2,400 이하 40만 -> 24,000', 'w', 2400, 400000, 60, 0, { monthly: 24000 }],
  ['FAQ 예: 총급여 2천 50만 -> 24,000+3,000', 'w', 2000, 500000, 60, 0, { monthly: 27000 }],
  ['3,600 이하 50만 -> 23,000', 'w', 3000, 500000, 60, 0, { monthly: 23000 }],
  ['4,800 이하 60만 -> 22,200', 'w', 4500, 600000, 60, 0, { monthly: 22200 }],
  ['6,000 초과~7,500: 기여금 0', 'w', 7000, 700000, 60, 0, { band: 4, monthly: 0 }],
  ['7,500 초과: 가입 요건 밖', 'w', 8000, 700000, 60, 0, { band: 5, monthly: 0 }],
  ['종합소득 1,600 -> 0구간', 'g', 1600, 700000, 60, 0, { band: 0, monthly: 33000 }],
  ['종합소득 1,601 -> 1구간', 'g', 1601, 700000, 60, 0, { band: 1, monthly: 29000 }],
  ['종합소득 6,300 -> 비과세만', 'g', 6300, 700000, 60, 0, { band: 4 }],
  ['소득 0 -> 기여금 없음', 'w', 0, 700000, 60, 0, { band: -1, monthly: 0 }],
  ['이자: 70만 60개월 4.5% -> 4,803,750', 'w', 3000, 700000, 60, 4.5, { principal: 42000000, interest: 4803750, contrib: 1740000, contrib60: 1044000, total: 42000000 + 1740000 + 4803750 }],
  ['이자: 10만 12개월 4% -> 26,000', 'w', 2000, 100000, 12, 4, { interest: 26000, monthly: 6000 }],
];
for (const [name, type, inc, m, n, r, exp] of cases) {
  const x = calc(type, inc, m, n, r);
  for (const k of Object.keys(exp)) assert.strictEqual(x[k], exp[k], name + ' ' + k + '=' + x[k]);
  console.log('PASS', name, JSON.stringify(x));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'ya-type': 'w', 'ya-inc': '3000', 'ya-m': '700000', 'ya-n': '60', 'ya-r': '4.5' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ya-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('29,000원'));
assert.ok(outP.join().includes('48,543,750원'));
