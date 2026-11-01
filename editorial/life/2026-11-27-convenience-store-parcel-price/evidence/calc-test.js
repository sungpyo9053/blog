// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('raw < in string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ', faq, '개 = JSON-LD', faq);
// CU 운임표가 CU 공식 JSON(getAllPricesJson)과 같은지 대조
const cu = JSON.parse(fs.readFileSync(path.join(__dirname, 'cu-getAllPricesJson.json'), 'utf8'));
const arr = n => src.match(new RegExp('var ' + n + '=\\[([^\\]]*)\\]'))[1].split(',').map(Number);
assert.deepStrictEqual(arr('CUS'), cu.localPrices.map(x => +x.same_area));
assert.deepStrictEqual(arr('CUO'), cu.localPrices.map(x => +x.other_area));
assert.deepStrictEqual(arr('CUJ'), cu.localPrices.map(x => +x.jeju_area));
assert.deepStrictEqual(cu.storePrices.map(x => +x.price), [1800, 2100, 2700]);
console.log('PASS CU 국내택배 16구간 x 3권역 = 공식 JSON, 반값 1,800/2,100/2,700');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.parcelCalc;
const get = (R, k) => R.find(x => x.key === k);
const cases = [
  ['1kg 60cm 같은 권역(CU 1kg 미만 아님)', { g: 1000, cm: 60, route: 'same' }, { cuh: 2700, gsh: 2300, cul: 4400, cue: 4600, gsl: 4500, epr: 4000, epn: 2700 }],
  ['500g 30cm 다른 권역(우체국 35cm 미만)', { g: 500, cm: 30, route: 'other' }, { cuh: 2100, gsh: 1900, cul: 4400, cue: 4600, gsl: 4400, epr: null, epn: null }],
  ['350g 40cm 같은 권역', { g: 350, cm: 40, route: 'same' }, { cul: 3400, gsl: 3400, epr: 4000 }],
  ['5kg 80cm 육지→제주', { g: 5000, cm: 80, route: 'tojeju' }, { cuh: 4400, gsh: 4400, cul: 9200, cue: 5100, gsl: 9200, epr: 4500, epn: 3200 }],
  ['3kg 90cm 같은 권역(GS반값·우체국연계 80cm 초과)', { g: 3000, cm: 90, route: 'same' }, { cuh: 2700, gsh: null, cul: 5300, cue: null, gsl: 5400, epr: 4500 }],
  ['6kg 110cm 다른 권역', { g: 6000, cm: 110, route: 'other' }, { cuh: null, gsh: null, cul: 8000, gsl: 7700, epr: 6000, epn: 4700 }],
  ['20kg 150cm 같은 권역', { g: 20000, cm: 150, route: 'same' }, { cul: 8700, gsl: 9000, epr: 13000, epn: 11700 }],
  ['25kg 120cm (편의점 20kg 초과)', { g: 25000, cm: 120, route: 'same' }, { cul: null, gsl: null, epr: 11000, epn: 9700 }],
  ['1kg 50cm 다른 권역 + 도서', { g: 1000, cm: 50, route: 'other', island: true }, { cuh: 4400, gsh: 4000, cul: 8900, cue: 4600, gsl: 9000, epr: 4000 }],
  ['1kg 50cm 제주 + 도서', { g: 1000, cm: 50, route: 'jejuin', island: true }, { cuh: null, gsh: null, cul: null, gsl: null, cue: 4600 }],
  ['1kg 제주 안', { g: 1000, cm: 50, route: 'jejuin' }, { cuh: 2700, gsh: 2300, cul: 4400, gsl: 4500 }],
  ['가액 40만원 1kg', { g: 1000, cm: 50, route: 'same', value: 400000 }, { cuh: 2700, gsh: 2800, cul: 4400, gsl: 4500 }],
  ['가액 70만원 1kg', { g: 1000, cm: 50, route: 'same', value: 700000 }, { cuh: null, gsh: null, cue: null, cul: 6900, gsl: 7000, epr: 4000 }],
  ['가액 100만원 (CU 100만원 이상 불가, GS 100만원 이하)', { g: 1000, cm: 50, route: 'same', value: 1000000 }, { cul: null, gsl: 7000 }],
  ['30kg 160cm', { g: 30000, cm: 160, route: 'same' }, { epr: 13000 }],
  ['31kg', { g: 31000, cm: 100, route: 'same' }, { epr: null, epn: null }],
];
for (const [name, o, exp] of cases) {
  const R = calc(o);
  for (const k of Object.keys(exp)) assert.strictEqual(get(R, k).price, exp[k], name + ' ' + k + '=' + get(R, k).price + ' ' + (get(R, k).no || ''));
  console.log('PASS', name, R.map(x => x.key + ':' + (x.price === null ? 'X(' + x.no + ')' : x.price)).join(' '));
}
let r = calc({ g: 1000, cm: 50, route: 'same', value: 700000 });
assert.ok(get(r, 'epr').cover.includes('2,000원'));
r = calc({ g: 2000, cm: 50, route: 'fromjeju' });
assert.ok(get(r, 'epr').eta.includes('6,500원'));
console.log('PASS 안심소포 70만원 수수료 2,000원, 제주발 익일 6,500원');
// CU 반값 '미만' 경계 vs GS25 '이하' 경계
for (const [g, cu, gs] of [[499, 1800, 1900], [500, 2100, 1900], [501, 2100, 2300], [999, 2100, 2300], [1000, 2700, 2300], [1001, 2700, 2700], [5000, 2700, 2700], [5001, null, null]]) {
  const R = calc({ g, cm: 50, route: 'same' });
  assert.strictEqual(get(R, 'cuh').price, cu, 'CU ' + g); assert.strictEqual(get(R, 'gsh').price, gs, 'GS ' + g);
  console.log('PASS 경계', g + 'g', 'CU반값', cu, 'GS반값', gs);
}
// 표 값 검산: GS 반값 제주 구간, CU 반값 +1,700
assert.deepStrictEqual([500, 1000, 5000].map(g => get(calc({ g, cm: 50, route: 'fromjeju' }), 'gsh').price), [3600, 4000, 4400]);
assert.deepStrictEqual([499, 999, 5000].map(g => get(calc({ g, cm: 50, route: 'fromjeju' }), 'cuh').price), [3500, 3800, 4400]);
assert.deepStrictEqual([500, 1000].map(g => get(calc({ g, cm: 50, route: 'fromjeju' }), 'cuh').price), [3800, 4400]);
console.log('PASS 반값 제주 구간 표 값');
// UI 기본값(1kg, 60cm, 같은 권역) 렌더 확인 — 최소 DOM 스텁
const vals = { 'cp-kg': '1', 'cp-cm': '60', 'cp-route': 'same', 'cp-value': '' };
const cells = []; let minText = '';
const mk = () => ({ style: {}, set textContent(v) { cells.push(v); }, appendChild() {} });
const els = {};
['cp-kg', 'cp-cm', 'cp-route', 'cp-value', 'cp-island'].forEach(id => els[id] = { value: vals[id], checked: false, addEventListener() {} });
els['cp-out'] = { set innerHTML(v) { cells.length = 0; }, appendChild() {} };
els['cp-min'] = { set textContent(v) { minText = v; } };
global.document = { getElementById: id => els[id], createElement: mk };
eval(src);
console.log('UI 기본값 셀:', cells.join(' | '));
console.log('UI 최저:', minText);
assert.ok(cells.includes('2,700원') && minText.includes('GS25 반값택배 2,300원'));
console.log('ALL PASS');
