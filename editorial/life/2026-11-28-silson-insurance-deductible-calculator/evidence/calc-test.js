// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^']*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.silsonCalc;
const base = { care: 'out', hosp: 'clinic', cov: 0, non: 0, ntype: 'gen', rate: 0.2, sp3: true, sev: false, nhis: 30, ded1: 5000 };
const cases = [
  ['금융위 5세대 예시: 병원 통원 급여 20만, 본인부담률 40% -> 공제 8만, 보험금 12만', { gen: '5', hosp: 'hospital', cov: 200000, nhis: 40 }, { ded: 80000, paid: 120000 }],
  ['금감원 2016 예시: 상급종합 통원 50만, 20%형 -> 공제 10만, 한도 30만', { gen: '2b', hosp: 'tertiary', cov: 500000 }, { ded: 100000, paid: 300000, over: 100000 }],
  ['본문 예1 1세대 의원 2.5만', { gen: '1', cov: 25000 }, { paid: 20000 }],
  ['본문 예1 2세대 초기 의원 2.5만', { gen: '2a', cov: 25000 }, { paid: 15000 }],
  ['본문 예1 2세대 후기', { gen: '2b', cov: 25000 }, { paid: 15000 }],
  ['본문 예1 3세대', { gen: '3', cov: 25000 }, { paid: 15000 }],
  ['본문 예1 4세대', { gen: '4', cov: 25000 }, { paid: 15000 }],
  ['본문 예1 5세대 30%', { gen: '5', cov: 25000, nhis: 30 }, { ded: 10000, paid: 15000 }],
  ['본문 4세대 의원 급여 3만 -> 2만', { gen: '4', cov: 30000 }, { ded: 10000, paid: 20000 }],
  ['본문 예2 2세대 초기 병원 도수 10만', { gen: '2a', hosp: 'hospital', non: 100000, ntype: 'big3' }, { paid: 85000 }],
  ['본문 예2 2세대 후기', { gen: '2b', hosp: 'hospital', non: 100000, ntype: 'big3' }, { paid: 80000 }],
  ['본문 예2 3세대 특약 가입', { gen: '3', hosp: 'hospital', non: 100000, ntype: 'big3' }, { ded: 30000, paid: 70000 }],
  ['본문 예2 3세대 특약 미가입', { gen: '3', hosp: 'hospital', non: 100000, ntype: 'big3', sp3: false }, { paid: 0, unc: 100000 }],
  ['본문 예2 4세대', { gen: '4', hosp: 'hospital', non: 100000, ntype: 'big3' }, { paid: 70000 }],
  ['본문 예2 5세대 중증', { gen: '5', hosp: 'hospital', non: 100000, ntype: 'big3', sev: true }, { paid: 70000 }],
  ['본문 예2 5세대 비중증 -> 보장 제외', { gen: '5', hosp: 'hospital', non: 100000, ntype: 'big3' }, { paid: 0, unc: 100000 }],
  ['본문 예3 1세대 입원 100만', { gen: '1', care: 'in', hosp: 'general', cov: 600000, non: 400000 }, { paid: 1000000 }],
  ['본문 예3 2세대 초기', { gen: '2a', care: 'in', hosp: 'general', cov: 600000, non: 400000 }, { paid: 900000 }],
  ['본문 예3 2세대 후기 20%', { gen: '2b', care: 'in', hosp: 'general', cov: 600000, non: 400000 }, { paid: 800000 }],
  ['본문 예3 3세대 급여20%', { gen: '3', care: 'in', hosp: 'general', cov: 600000, non: 400000 }, { paid: 800000 }],
  ['본문 예3 3세대 급여10%', { gen: '3', care: 'in', hosp: 'general', cov: 600000, non: 400000, rate: 0.1 }, { paid: 860000 }],
  ['본문 예3 4세대', { gen: '4', care: 'in', hosp: 'general', cov: 600000, non: 400000 }, { paid: 760000 }],
  ['본문 예3 5세대 중증', { gen: '5', care: 'in', hosp: 'general', cov: 600000, non: 400000, sev: true }, { paid: 760000 }],
  ['본문 예3 5세대 비중증', { gen: '5', care: 'in', hosp: 'general', cov: 600000, non: 400000 }, { paid: 680000 }],
  ['4세대 비급여 통원 공제 3만 최소', { gen: '4', non: 50000 }, { ded: 30000, paid: 20000 }],
  ['4세대 통원 한도 20만', { gen: '4', hosp: 'tertiary', cov: 1000000 }, { ded: 200000, paid: 200000, over: 600000 }],
  ['4세대 급여 입원 연 자기부담 200만 상한(한 건)', { gen: '4', care: 'in', hosp: 'tertiary', cov: 20000000 }, { ded: 2000000, paid: 18000000 }],
  ['5세대 중증 비급여 입원 종합병원 500만 상한', { gen: '5', care: 'in', hosp: 'general', non: 20000000, sev: true }, { ded: 5000000, paid: 15000000 }],
  ['5세대 비중증 입원 의원 회당 300만 한도', { gen: '5', care: 'in', non: 10000000 }, { ded: 5000000, paid: 3000000, over: 2000000 }],
  ['5세대 비중증 MRI 통원 30만 -> max(15만,5만) 공제', { gen: '5', hosp: 'hospital', non: 300000, ntype: 'mri' }, { ded: 150000, paid: 150000 }],
  ['2세대 초기 약국 8천원 공제', { gen: '2a', hosp: 'pharmacy', cov: 12000 }, { paid: 4000 }],
  ['소액: 공제가 진료비보다 크면 0원', { gen: '4', non: 20000 }, { ded: 20000, paid: 0 }],
];
for (const [name, inp, exp] of cases) {
  const r = calc(Object.assign({}, base, inp));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ total: r.total, ded: r.ded, unc: r.unc, over: r.over, paid: r.paid }));
}
// UI 기본값(4세대, 통원, 의원, 급여 3만원) 렌더 확인 — 최소 DOM 스텁
const vals = { 'sl-gen': '4', 'sl-care': 'out', 'sl-hosp': 'clinic', 'sl-cov': '30000', 'sl-non': '0', 'sl-ntype': 'gen', 'sl-rate': '0.2', 'sl-sp3': 'y', 'sl-sev': 'n', 'sl-nhis': '30', 'sl-ded1': '5000' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['sl-out', 'sl-row-rate', 'sl-row-sp3', 'sl-row-sev', 'sl-row-nhis', 'sl-row-ded1', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('예상 보험금: 20,000원'));
console.log('ALL PASS', cases.length + 1);
