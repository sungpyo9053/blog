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
const calc = window.epostParcelCalc;
const base = { w: 2, a: 30, b: 20, c: 10, m: 'reg', r: 'land', cod: false, ins: false, v: 0, pre: false, q: 1 };
const C = (o) => calc(Object.assign({}, base, o));
const cases = [
  ['창구 등기 2kg 60cm', {}, { ok: true, base: 4000, total: 4000 }],
  ['창구 등기 4kg 70cm', { w: 4 }, { base: 4500 }],
  ['크기 우선: 2kg 110cm -> 6,000', { a: 50, b: 40, c: 20 }, { base: 6000 }],
  ['크기 우선: 1kg 130cm -> 13,000', { w: 1, a: 60, b: 40, c: 30 }, { base: 13000 }],
  ['창구 등기 30kg', { w: 30, a: 60, b: 50, c: 40 }, { base: 13000 }],
  ['경계 3kg 정확히 -> 4,000', { w: 3 }, { base: 4000 }],
  ['경계 3.1kg -> 4,500', { w: 3.1 }, { base: 4500 }],
  ['제주발 익일 3kg', { r: 'fromnext' }, { base: 6500 }],
  ['제주발 익일 25kg', { w: 25, a: 50, b: 40, c: 30, r: 'fromnext' }, { base: 13500 }],
  ['제주발 D+2 = 육지 요금', { r: 'fromd2' }, { base: 4000, days: 'D+2일 배달' }],
  ['육지->제주 D+2', { r: 'tojeju' }, { base: 4000, days: 'D+2일 배달' }],
  ['일반 6kg', { m: 'gen', w: 6 }, { base: 3700, days: 'D+3일 배달' }],
  ['일반 30kg', { m: 'gen', w: 30 }, { base: 11700 }],
  ['일반 제주 -> 확인 못함', { m: 'gen', r: 'tojeju' }, { ok: false }],
  ['일반 착불 무시', { m: 'gen', cod: true }, { fee: 0, total: 2700 }],
  ['방문 3kg 90cm -> 8,000', { m: 'visit', w: 3, a: 40, b: 30, c: 20 }, { base: 8000 }],
  ['방문 5kg 80cm', { m: 'visit', w: 5 }, { base: 5000 }],
  ['방문 제주발 익일 25kg', { m: 'visit', r: 'fromnext', w: 25 }, { base: 16500 }],
  ['방문 30kg', { m: 'visit', w: 30 }, { base: 14000 }],
  ['착불 +500', { cod: true }, { fee: 500, total: 4500 }],
  ['안심 100만원 -> 3,500', { ins: true, v: 100 }, { fee: 3500, total: 7500 }],
  ['안심 300만원 -> 13,500', { ins: true, v: 300 }, { fee: 13500 }],
  ['안심 50만원 -> 1,000', { ins: true, v: 50 }, { fee: 1000 }],
  ['안심 310만원 거부', { ins: true, v: 310 }, { ok: false }],
  ['안심 55만원 거부(10만원 단위)', { ins: true, v: 55 }, { ok: false }],
  ['사전접수 1개 3%: 3,880', { pre: true }, { disc: 120, total: 3880 }],
  ['사전접수 3개 5%', { pre: true, q: 3 }, { disc: 200, total: 3800 }],
  ['사전접수 10개 10%', { pre: true, q: 10 }, { total: 3600 }],
  ['사전접수 50개 15%', { pre: true, q: 50 }, { total: 3400 }],
  ['감액은 수수료 제외: 착불+3%', { pre: true, cod: true }, { total: 4000 - 120 + 500 }],
  ['방문 사전결제 -500', { m: 'visit', pre: true }, { total: 4500 }],
  ['방문 착불은 -500 없음', { m: 'visit', pre: true, cod: true }, { disc: 0, total: 5500 }],
  ['30.5kg 거부', { w: 30.5 }, { ok: false }],
  ['한 변 101cm 거부', { a: 101, b: 20, c: 10 }, { ok: false }],
  ['합 161cm 거부', { a: 81, b: 50, c: 30 }, { ok: false }],
  ['합 160cm 허용', { w: 5, a: 80, b: 50, c: 30 }, { ok: true, base: 13000 }],
  ['합 34cm 거부', { a: 17, b: 12, c: 5 }, { ok: false }],
  ['무게 0 거부', { w: 0 }, { ok: false }],
];
for (const [name, o, exp] of cases) {
  const r = C(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k] + ' ' + r.err.join('/'));
  console.log('PASS', name, '->', r.ok ? (r.tier + ' 기본 ' + r.base + ' 수수료 ' + r.fee + ' 감액 ' + r.disc + ' 합계 ' + r.total) : r.err.join(' '));
}
// 본문 표 값 검산 (창구 등기·제주 익일·일반 8단계, 방문 4단계)
const W8 = [3, 5, 7, 10, 15, 20, 25, 30], V4 = [5, 10, 20, 30];
const T = { reg: [4000, 4500, 5000, 6000, 7000, 8000, 11000, 13000], jeju: [6500, 7000, 7500, 8500, 9500, 10500, 13500, 15500], gen: [2700, 3200, 3700, 4700, 5700, 6700, 9700, 11700] };
W8.forEach((w, i) => {
  assert.strictEqual(C({ w, a: 20, b: 20, c: 20 }).base, T.reg[i]);
  assert.strictEqual(C({ w, a: 20, b: 20, c: 20, r: 'fromnext' }).base, T.jeju[i]);
  assert.strictEqual(C({ w, a: 20, b: 20, c: 20, m: 'gen' }).base, T.gen[i]);
});
V4.forEach((w, i) => {
  assert.strictEqual(C({ w, a: 20, b: 20, c: 20, m: 'visit' }).base, [5000, 8000, 10000, 14000][i]);
  assert.strictEqual(C({ w, a: 20, b: 20, c: 20, m: 'visit', r: 'fromnext' }).base, [7500, 10500, 12500, 16500][i]);
});
console.log('PASS 표 값 32개');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'ep-w': '2', 'ep-a': '30', 'ep-b': '20', 'ep-c': '15', 'ep-m': 'reg', 'ep-r': 'land', 'ep-v': '100', 'ep-q': '1' };
const checks = { 'ep-cod': false, 'ep-ins': false, 'ep-pre': false };
const outP = [];
const el = id => ({ value: vals[id], checked: checks[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ep-out', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('4,000원'));
