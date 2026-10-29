// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'([^'\\]|\\.)*'/g)) if (m[0].indexOf('<') >= 0) throw new Error('< in string literal: ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.beotimmokCalc;
const D = { prod: 'general', hh: 'basic', inc: 4500, self: 0, asset: 20000, dep: 20000, area: 59, metro: true, age: 30, homeless: true, m7: false, u25: false, pref: 'none', ec: false, sme: false, want: 0 };
const cases = [
  ['일반 수도권 소득4.5천 보증금2.5억 -> 3.2%, 한도 1.2억, 월 32만', { dep: 25000 }, { ok: true, rate: 3.2, limit: 12000, byRatio: 17500, monthly: 320000 }],
  ['일반 지방 소득3천 보증금1.5억 -> 2.9-0.2=2.7%, 한도 8천', { inc: 3000, dep: 15000, metro: false }, { ok: true, rate: 2.7, limit: 8000 }],
  ['일반 수도권 보증금2억 -> 70% 1.4억 vs 1.2억 => 1.2억', {}, { limit: 12000, byRatio: 14000 }],
  ['청년 소득3천 보증금1억 중기청년 -> 2.5-0.3=2.2%, 한도 8천', { prod: 'youth', inc: 3000, dep: 10000, sme: true }, { ok: true, rate: 2.2, limit: 8000 }],
  ['청년 만35세 -> 나이 미충족', { prod: 'youth', age: 35 }, { ok: false }],
  ['청년 25세 미만 단독 70㎡ -> 면적 미충족, 한도 1.2억', { prod: 'youth', u25: true, area: 70, dep: 30000, age: 23 }, { ok: false, capAmt: 12000 }],
  ['신혼 소득7천 보증금3억 2자녀 -> 3.3-0.5=2.8%, 한도 2.4억', { prod: 'newly', inc: 7000, dep: 30000, m7: true, pref: 'c2' }, { ok: true, rate: 2.8, limit: 24000 }],
  ['신혼 예외 합산9천 본인4.5천 보증금2억 -> 3.3+0.3=3.6%', { prod: 'newly', inc: 9000, self: 4500, m7: true }, { ok: true, rate: 3.6 }],
  ['신혼 합산9천 본인6천 -> 소득 미충족', { prod: 'newly', inc: 9000, self: 6000, m7: true }, { ok: false }],
  ['신혼 혼인요건 미체크 -> 미충족', { prod: 'newly', inc: 5000 }, { ok: false }],
  ['일반 소득5.5천 일반가구 -> 소득 미충족', { inc: 5500 }, { ok: false }],
  ['일반 2자녀 소득5.5천 -> 충족, 3.0%(4~6천, 1억초과=3.2) 2자녀 우대 0.5 -> 2.7', { inc: 5500, hh: 'child2', pref: 'c2' }, { ok: true, rate: 2.7, limit: 16000 }],
  ['일반 순자산 3.46억 -> 미충족', { asset: 34600 }, { ok: false }],
  ['일반 수도권 보증금 3.1억 -> 보증금 미충족', { dep: 31000 }, { ok: false }],
  ['상한: 1자녀0.3+전자계약0.1 -> 0.4, 소득1.5천 보증금4천 -> 2.5-0.4=2.1', { inc: 1500, dep: 4000, pref: 'c1', ec: true }, { rate: 2.1, pref: 0.4 }],
  ['상한: 2자녀0.5+전자계약0.1 -> 0.5 캡 -> 2.0', { inc: 1500, dep: 4000, pref: 'c2', ec: true }, { rate: 2.0, pref: 0.5 }],
  ['하한: 청년 지방 기초수급 소득1.5천 -> 2.2-0.2-1.0=1.0', { prod: 'youth', inc: 1500, dep: 4000, metro: false, pref: 'basic' }, { rate: 1.0 }],
  ['신혼 상품은 장애인 우대 불가 -> 우대 0', { prod: 'newly', inc: 3000, dep: 8000, m7: true, pref: 'dis' }, { pref: 0, rate: 2.3 }],
  ['희망 대출금 5천 -> 월 이자 5천만x3.2%/12', { dep: 25000, want: 5000 }, { loan: 5000, monthly: 133333 }],
];
for (const [name, over, exp] of cases) {
  const r = calc(Object.assign({}, D, over));
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-9 || r[k] === exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, rate: r.rate, pref: r.pref, limit: r.limit, loan: r.loan, monthly: r.monthly }));
}
// 금리표 값 검산 (nhuf-rate-N.json / nhuf-rate-Y.json 과 대조)
const rd = f => Object.values(JSON.parse(fs.readFileSync(path.join(__dirname, f), 'utf8').replace('arrJson', '"arrJson"')).arrJson[0]).filter(v => v !== 'null').map(Number);
const N = rd('nhuf-rate-N.json'), Y = rd('nhuf-rate-Y.json');
const inc = [1500, 3000, 5000, 7000];
let i = 0; for (const x of inc) for (const d of [4000, 8000, 20000]) assert.strictEqual(calc(Object.assign({}, D, { inc: x, dep: d, hh: 'newly', m7: true })).base, N[i++]);
i = 0; for (const x of inc) for (const d of [4000, 8000, 12000, 20000]) assert.strictEqual(calc(Object.assign({}, D, { prod: 'newly', inc: x, dep: d, m7: true })).base, Y[i++]);
console.log('PASS 금리표 일반 12칸·신혼 16칸이 공식 응답과 일치');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'bt-prod': 'general', 'bt-hh': 'basic', 'bt-inc': '4500', 'bt-self': '', 'bt-asset': '20000', 'bt-dep': '20000', 'bt-area': '59', 'bt-region': 'metro', 'bt-age': '30', 'bt-pref': 'none', 'bt-want': '' };
const chk = { 'bt-home': true, 'bt-m7': false, 'bt-u25': false, 'bt-ec': false, 'bt-sme': false };
const outP = [];
const el = id => ({ value: vals[id], checked: chk[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['bt-out', ...Object.keys(vals), ...Object.keys(chk)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
assert.ok(outP.join().includes('연 3.2%'));
assert.ok(outP.join().includes('12,000만원'));
