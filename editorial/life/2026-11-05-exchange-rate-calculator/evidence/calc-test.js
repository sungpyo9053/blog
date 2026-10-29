// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'([^'\\]|\\.)*'/g)) if (m[0].includes('<')) throw new Error('raw < in JS string: ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.fxCalc;
const near = (a, b, eps) => Math.abs(a - b) < (eps || 1e-6);
const cases = [
  ['금감원 2014 예시: USD 수수료율 1.750%', { base: 1023, posted: 1040.9, pref: 0, amount: 1000, amountIn: 'fx', side: 'buy' }, { fee: 17.9, applied: 1040.9, krw: 1040900, saving: 0 }],
  ['USD 1,000달러 우대 50%', { base: 1023, posted: 1040.9, pref: 50, amount: 1000, amountIn: 'fx', side: 'buy' }, { applied: 1031.95, krw: 1031950, saving: 8950 }],
  ['USD 1,000달러 우대 90%', { base: 1023, posted: 1040.9, pref: 90, amount: 1000, amountIn: 'fx', side: 'buy' }, { applied: 1024.79, krw: 1024790, saving: 16110 }],
  ['JPY 100엔 단위: 10만엔 우대 50%', { base: 1001.37, posted: 1018.89, pref: 50, amount: 100000, amountIn: 'fx', side: 'buy', unit: 100 }, { applied: 1010.13, krw: 1010130 }],
  ['USD 현찰 팔 때 500달러 우대 0%', { base: 1023, posted: 1005.1, pref: 0, amount: 500, amountIn: 'fx', side: 'sell' }, { applied: 1005.1, krw: 502550, saving: 0 }],
  ['USD 현찰 팔 때 500달러 우대 50%', { base: 1023, posted: 1005.1, pref: 50, amount: 500, amountIn: 'fx', side: 'sell' }, { applied: 1014.05, krw: 507025, saving: 4475 }],
  ['원화 100만원으로 USD 사기 우대 0%', { base: 1023, posted: 1040.9, pref: 0, amount: 1000000, amountIn: 'krw', side: 'buy' }, { fx: 1000000 / 1040.9, saving: 0 }],
  ['수수료율 모드: 기준 1,000 + 2%, 우대 50%', { base: 1000, posted: NaN, feePct: 2, pref: 50, amount: 100, amountIn: 'fx', side: 'buy' }, { posted: 1020, applied: 1010, krw: 101000, saving: 1000 }],
  ['우대율 상한 100% 초과 입력 -> 100%', { base: 1023, posted: 1040.9, pref: 150, amount: 1, amountIn: 'fx', side: 'buy' }, { applied: 1023 }],
  ['방향 오류 감지: 살 때 고시가 기준보다 낮음', { base: 1023, posted: 1005.1, pref: 0, amount: 1, amountIn: 'fx', side: 'buy' }, { wrongSide: true }],
];
for (const [name, inp, exp] of cases) {
  const r = calc(inp);
  for (const k of Object.keys(exp)) assert.ok(typeof exp[k] === 'boolean' ? r[k] === exp[k] : near(r[k], exp[k], 1e-4), name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r, (k, v) => typeof v === 'number' ? Math.round(v * 10000) / 10000 : v));
}
// 금감원 2014 표의 수수료율 재현 (환전수수료 / 매매기준율)
for (const [cur, b, s, pct] of [['USD', 1023, 1040.9, 1.750], ['JPY', 1001.37, 1018.89, 1.750], ['EUR', 1385.86, 1413.3, 1.980], ['CNY', 164.06, 172.26, 4.998]])
  assert.ok(near(calc({ base: b, posted: s, pref: 0, amount: 1, amountIn: 'fx', side: 'buy' }).feeRate, pct, 0.0006), cur);
console.log('PASS 금감원 2014 수수료율 4개(1.750/1.750/1.980/4.998%)');
// 한국은행 재정환율 예시 산수: 1,100원/달러, 110엔/달러 -> 100엔당 1,000원
assert.ok(near(1100 / 110 * 100, 1000));
console.log('PASS 한국은행 재정환율 예시 100엔당 1,000원');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'fx-cur': 'USD', 'fx-side': 'buy', 'fx-base': '1023', 'fx-posted': '1040.9', 'fx-fee': '', 'fx-pref': '50', 'fx-amt': '1000', 'fx-unit': 'fx' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = String(v); }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['fx-out', 'fx-sample', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('1,031,950원'));
assert.ok(outP.join().includes('8,950원'));
