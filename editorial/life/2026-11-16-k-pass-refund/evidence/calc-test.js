// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g) || []) if (lit.includes('<')) throw new Error('< in string ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld);
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq.mainEntity.length, h3faq);
console.log('PASS script/JSON-LD 위생 검사, FAQ', h3faq, '개 일치');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.kpassRefundCalc;
const cases = [
  ['정책브리핑 예: 청년 수도권 월 13만원 전부 3천원 이상(40회 x 3,250) -> 플러스형 4만원', 'youth', 'metro', [[0, 0], [40, 3250]], 0, false, false, { total: 130000, plus: 40000, general: 0, basic: 39000, best: 40000, pick: 'plus' }],
  ['일반 수도권 44회 x 1,550 -> 기본형 13,640', 'gen', 'metro', [[44, 1550], [0, 3000]], 0, true, false, { total: 68200, basic: 13640, general: 6200, plus: 0, best: 13640, pick: 'basic' }],
  ['일반 수도권 60회 x 1,550 -> 일반형 31,000', 'gen', 'metro', [[60, 1550], [0, 3000]], 0, true, false, { total: 93000, basic: 18600, general: 31000, best: 31000, pick: 'general' }],
  ['14회 -> 0원(소멸)', 'gen', 'metro', [[14, 1550], [0, 0]], 0, true, false, { trips: 14, eligible: false, best: 0 }],
  ['14회 가입 첫 달 -> 지급', 'gen', 'metro', [[14, 1550], [0, 0]], 0, true, true, { eligible: true, best: 4340 }],
  ['시차: 일반 20회 x 1,500 중 10회 시차 -> 3,000+7,500', 'gen', 'metro', [[20, 1500], [0, 0]], 10, true, false, { basic: 10500 }],
  ['시차 끔 -> 20%만', 'gen', 'metro', [[20, 1500], [0, 0]], 10, false, false, { basic: 6000 }],
  ['저소득 50,000원 -> 26,650', 'low', 'metro', [[25, 2000], [0, 0]], 0, false, false, { basic: 26650, best: 26650 }],
  ['혼합: 일반 일반지방권 30회x1,500 + 20회x3,500', 'gen', 'local', [[30, 1500], [20, 3500]], 0, false, false, { total: 115000, under3000: 45000, general: 0, plus: 20000, basic: 23000, best: 23000, pick: 'basic' }],
  ['3자녀 특별지원 50회x1,500 -> 일반형 45,000', 'multi3', 'special', [[50, 1500], [0, 0]], 0, false, false, { general: 45000, basic: 37500, best: 45000, pick: 'general' }],
  ['첫 줄에 3,000원 이상 넣으면 플러스형 통행으로 분류', 'gen', 'metro', [[40, 3000], [0, 0]], 0, false, false, { under3000: 0, general: 0, plus: 20000 }],
];
for (const [name, t, rg, rows, pk, on, first, exp] of cases) {
  const r = calc(t, rg, rows, pk, on, first);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 기준금액 표(본문 table)와 계산기 상수 대조
const won = s => s.split('/').map(x => { const m = x.trim().match(/(\d+)만(?: (\d)천)?/); return (+m[1]) * 10000 + (m[2] ? +m[2] * 1000 : 0); });
const rowsHtml = html.split('<h2 id="fixed">')[1].split('</table>')[0].match(/<tr><td>[^]*?<\/tr>/g);
const regionKey = { '수도권': 'metro', '일반지방권': 'local', '우대지원지역': 'pref', '특별지원지역': 'special' };
for (const tr of rowsHtml) {
  const td = [...tr.matchAll(/<td>([^<]*)<\/td>/g)].map(m => m[1]);
  const rg = regionKey[td[0]];
  [['gen', td[1]], ['youth', td[2]], ['multi3', td[3]], ['low', td[3]]].forEach(([t, cell]) => {
    const [g, p] = won(cell);
    const r = calc(t, rg, [[100, 2000], [0, 0]], 0, false, false);
    assert.strictEqual(r.baseGeneral, g, td[0] + t); assert.strictEqual(r.basePlus, p, td[0] + t);
  });
}
console.log('PASS 기준금액 표 16칸 = 계산기 상수');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'kp-type': 'gen', 'kp-region': 'metro', 'kp-na': '44', 'kp-fa': '1550', 'kp-nb': '0', 'kp-fb': '3000', 'kp-peak': '0' };
const outP = [];
const el = id => ({ value: vals[id], checked: id === 'kp-peakon', style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['kp-out', 'kp-peakon', 'kp-first', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('13,640원 (기본형 자동 적용)'));
