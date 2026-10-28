// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.dsrLtvCalc;
// 독립 공식(원리금균등 연간 상환액/원금 1)
const ann = (r, y) => { const i = r / 100 / 12, n = y * 12; return 12 * i / (1 - Math.pow(1 + i, -n)); };
const base = { income: 6000, ratio: 40, existing: 0, credit: 0, creditRate: 5, rate: 4, years: 30, method: 'annuity', stress: 3, typeRatio: 1, price: 0, ltv: 40, first: false, capArea: false };
const run = o => calc(Object.assign({}, base, o));
const cases = [
  ['스트레스 0%: 2400/ann(4%)', {stress: 0}, r => r.dsrMax === Math.floor(2400 / ann(4, 30)) && r.dsrMax === 41892],
  ['지방 0.75%', {stress: 0.75}, r => r.dsrMax === 38340],
  ['수도권 3.0% -> 30,061만원, 월 1,435,158원', {}, r => r.dsrMax === 30061 && r.monthly === 1435158 && Math.abs(r.stressRate - 7) < 1e-9],
  ['DSR 재계산 = 40% 이하', {}, r => r.dsr <= 40 && r.dsr > 39.99],
  ['2금융권 50%', {ratio: 50}, r => r.dsrMax === Math.floor(3000 / ann(7, 30))],
  ['혼합형 5~9년 80% -> 가산 2.4%', {typeRatio: 0.8}, r => Math.abs(r.stressRate - 6.4) < 1e-9 && r.dsrMax === Math.floor(2400 / ann(6.4, 30))],
  ['21년 이상 고정 0% -> 스트레스 없음과 같음', {typeRatio: 0}, r => r.dsrMax === 41892],
  ['신용대출 5000만 5% -> 연 1250, 한도 14,404', {credit: 5000}, r => r.creditAnnual === 1250 && r.dsrMax === 14404],
  ['신용대출 1.2억 -> 하한 1.5% 가산 이자', {credit: 12000}, r => Math.abs(r.creditAnnual - (2400 + 12000 * 0.065)) < 1e-9 && r.dsrMax === 0],
  ['기존 원리금이 DSR 초과 -> 0', {existing: 2500}, r => r.dsrMax === 0 && r.final === 0],
  ['만기일시 10년 상한: 원금/10 + 이자', {method: 'bullet', years: 30, stress: 0}, r => r.dsrMax === Math.floor(2400 / (0.1 + 0.04))],
  ['원금균등 첫해 상환액', {method: 'equal', stress: 0, years: 1}, r => { let s = 0; for (let k = 0; k < 12; k++) s += 1 / 12 + (1 - k / 12) * (0.04 / 12); return r.dsrMax === Math.floor(2400 / s); }],
  ['LTV 40% 시가 9억 -> 3.6억, 최종은 DSR 3억61', {price: 90000, ltv: 40}, r => r.ltvMax === 36000 && r.final === 30061],
  ['시가 20억 수도권 -> 한도 4억', {price: 200000, ltv: 40, capArea: true, income: 20000}, r => r.cap === 40000 && r.ltvMax === 80000 && r.final === 40000],
  ['시가 30억 수도권 -> 2억', {price: 300000, ltv: 40, capArea: true, income: 30000}, r => r.cap === 20000 && r.final === 20000],
  ['경계 15억 -> 6억, 25억 -> 4억', {price: 150000, capArea: true}, r => r.cap === 60000 && run({price: 250000, capArea: true}).cap === 40000],
  ['생애최초 80% 시가 10억 -> 8억이지만 6억 상한', {price: 100000, ltv: 80, first: true, income: 20000}, r => r.ltvMax === 80000 && r.cap === 60000 && r.final === 60000],
  ['다주택자 LTV 0%', {price: 100000, ltv: 0}, r => r.final === 0],
];
for (const [name, o, ok] of cases) { const r = run(o); assert.ok(ok(r), name + ' ' + JSON.stringify(r)); console.log('PASS', name, JSON.stringify({dsrMax: r.dsrMax, ltvMax: r.ltvMax, cap: r.cap, final: r.final, monthly: r.monthly, stressRate: r.stressRate})); }
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'ds-income': '6000', 'ds-ratio': '40', 'ds-exist': '0', 'ds-credit': '0', 'ds-crate': '5', 'ds-rate': '4', 'ds-years': '30', 'ds-method': 'annuity', 'ds-st': '3', 'ds-type': '1', 'ds-price': '', 'ds-ltv': '70', 'ds-cap': '' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ds-out', 'ds-st3', 'ds-st075', 'ds-st0', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('3억 61만원'));
assert.ok(outP.join().includes('1,435,158원'));
