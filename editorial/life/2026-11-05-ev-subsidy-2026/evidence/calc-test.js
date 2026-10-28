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
const calc = window.evSubsidyCalc;
// [이름, 기본가격, 국비입력, 모드, 차상위, 청년, 자녀, 전환, 기대값]
const cases = [
  ['지침 예시: 국비 300 전환지원금 60', 4800, 300, 'pub', false, false, 0, true, { B: 300, convAdd: 60, total: 360 }],
  ['보도자료 예시: 국비 250 전환지원금 50', 4800, 250, 'pub', false, false, 0, true, { convAdd: 50 }],
  ['보도자료: 중형 580 + 전환 100 = 680', 4800, 580, 'pub', false, false, 0, true, { total: 680 }],
  ['소형 530 + 전환 100 = 630', 4800, 530, 'pub', false, false, 0, true, { total: 630 }],
  ['지침 예시: 차상위 + 3자녀, 국비 500 -> 800', 4800, 500, 'pub', true, false, 3, false, { poorAdd: 100, kidsAdd: 200, total: 800 }],
  ['지침 예시: 청년 생애 첫차 국비 500 -> 추가 100', 4800, 500, 'pub', false, true, 0, false, { youthAdd: 100, total: 600 }],
  ['다자녀 2/4+ 정액', 4800, 400, 'pub', false, false, 5, false, { kidsAdd: 300 }],
  ['자녀 1명은 0', 4800, 400, 'pub', false, false, 1, false, { kidsAdd: 0, total: 400 }],
  ['경계: 5,299만 원 전액', 5299, 580, 'raw', false, false, 0, false, { rate: 1, B: 580 }],
  ['경계: 5,300만 원 50%', 5300, 580, 'raw', false, false, 0, false, { rate: 0.5, B: 290 }],
  ['50% 구간 전환지원금 비례: 290 -> 58', 6000, 580, 'raw', false, false, 0, true, { B: 290, convAdd: 58, total: 348 }],
  ['경계: 8,499만 원 50%', 8499, 500, 'raw', false, false, 0, false, { rate: 0.5, B: 250 }],
  ['경계: 8,500만 원 미지원(추가지원도 0)', 8500, 580, 'pub', true, true, 4, true, { rate: 0, B: 0, total: 0 }],
  ['공시액 모드 50% 구간은 입력값 그대로', 6000, 290, 'pub', false, false, 0, false, { B: 290 }],
  ['지방비 하한 30%', 4800, 580, 'pub', false, false, 0, false, { localMin: 174 }],
];
for (const [name, price, base, mode, poor, youth, kids, conv, exp] of cases) {
  const r = calc(price, base, mode, poor, youth, kids, conv);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'ev-price': '4800', 'ev-size': '580', 'ev-base': '580', 'ev-mode': 'pub', 'ev-kids': '0' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ev-out', 'ev-poor', 'ev-youth', 'ev-conv', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('국비 기준 합계(추정): 580만 원'));
