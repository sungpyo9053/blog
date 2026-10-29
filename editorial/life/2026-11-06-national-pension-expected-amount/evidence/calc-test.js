// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('< inside string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.npsPensionCalc;
const A = 3193511, K = 1.29;
// 1) 공단 노령연금 예상연금월액표(evidence 원본) 전 칸 대조
const raw = fs.readFileSync(path.join(__dirname, 'nps-OHAF0056M0-old-age-pension-table.html'), 'utf8');
const txt = raw.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
const i = txt.indexOf('연금보험료 ( 9.5% )'), seg = txt.slice(i, txt.indexOf('유의사항', i));
const re = /(\d+) ([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+)/g;
let m, n = 0;
while ((m = re.exec(seg))) {
  const v = m.slice(2).map(s => +s.replace(/,/g, ''));
  [10, 15, 20, 25, 30, 35, 40].forEach((y, j) => {
    const r = calc({ months: y * 12, A, B: v[0], K, mode: 'normal', k: 0 });
    assert.strictEqual(r.total, v[2 + j], 'B=' + v[0] + ' ' + y + 'y got ' + r.total);
    n++;
  });
}
assert.strictEqual(n, 448);
console.log('PASS 공단 예상연금월액표 ' + n + '칸 전부 일치 (B 41만~659만, 10~40년)');
// 2) 개별 사례
const cases = [
  ['B300만 20년', { months: 240, B: 3000000, mode: 'normal' }, { base: 665800, total: 665800, pct: 100 }],
  ['B300만 40년 = 20년의 2배', { months: 480, B: 3000000, mode: 'normal' }, { total: 1331600, pct: 200 }],
  ['B300만 15년 6개월', { months: 186, B: 3000000, mode: 'normal' }, { pct: 77.5 }],
  ['9년 11개월 -> 반환일시금', { months: 119, B: 3000000, mode: 'normal' }, { refund: true }],
  ['10년 정확히 -> 50%', { months: 120, B: 3000000, mode: 'normal' }, { refund: false, total: 332900 }],
  ['조기 5년 70%', { months: 240, B: 3000000, mode: 'early', k: 5 }, { adj: 466060 }],
  ['조기 1년 94%', { months: 240, B: 3000000, mode: 'early', k: 1 }, { adj: 625850 }],
  ['연기 5년 136%', { months: 240, B: 3000000, mode: 'defer', k: 5 }, { adj: 905480 }],
  ['연기 1년 107.2%', { months: 240, B: 3000000, mode: 'defer', k: 1 }, { adj: 713730 }],
  ['조기 9년 입력 -> 5년으로 제한', { months: 240, B: 3000000, mode: 'early', k: 9 }, { adj: 466060 }],
  ['부양가족 배우자+자녀2', { months: 240, B: 3000000, mode: 'normal', spouse: true, kids: 2 }, { family: 59610, total: 725410 }],
  ['상한: B41만 25년 -> 41만', { months: 300, B: 410000, mode: 'normal' }, { total: 410000, capped: true }],
  ['가중 상수 1.301 (2016~2035)', { months: 240, B: 3000000, mode: 'normal', K: 1.30125 }, { base: 671600 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(Object.assign({ A, K, k: 0 }, o));
  for (const k of Object.keys(exp)) assert.ok(r[k] === exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 3) UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'np-y': '20', 'np-m': '0', 'np-b': '3000000', 'np-a': '3193511', 'np-k': '1.29', 'np-mode': 'early', 'np-k2': '5', 'np-kid': '0' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['np-out', 'np-sp', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(20년, B 300만, 조기 5년):', outP.join(' | '));
assert.ok(outP.join().includes('665,800원'));
assert.ok(outP.join().includes('466,060원'));
console.log('ALL PASS');
