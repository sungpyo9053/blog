// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/(['"])[^'"\n]*</.test(src)) throw new Error('raw < inside JS string');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.vatCalc;
const eq = (name, r, exp) => { for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]); console.log('PASS', name, JSON.stringify(r)); };
eq('공급가액 1,000,000 -> 부가세 100,000', c.fromSupply(1000000), { vat: 100000, total: 1100000 });
eq('공급가액 3,000,000 -> 합계 3,300,000', c.fromSupply(3000000), { vat: 300000, total: 3300000 });
eq('역산 합계 33,000 (제29조⑦ 110분의 100)', c.fromTotal(33000), { supply: 30000, vat: 3000 });
eq('역산 반올림 합계 10,000 -> 9,091 + 909', c.fromTotal(10000), { supply: 9091, vat: 909 });
eq('역산 반올림 합계 55,555 -> 50,505 + 5,050', c.fromTotal(55555), { supply: 50505, vat: 5050 });
eq('역산 내림쪽 합계 10,004 -> 9,095 + 909', c.fromTotal(10004), { supply: 9095, vat: 909 });
// 역산 합계 보존 + 0.5 끝수 없음 전수 확인
for (let t = 1; t <= 200000; t++) { const r = c.fromTotal(t); assert.strictEqual(r.supply + r.vat, t); assert.notStrictEqual((t * 10) % 11 * 2, 11); }
console.log('PASS 역산 1~200,000원 전부 공급가액+부가세=합계');
eq('간이 음식점 6,000만 매입 2,200만 -> 790,000', c.simple(60000000, 15, 22000000), { gross: 900000, credit: 110000, tax: 790000, exempt: false });
eq('간이 4,000만 -> 납부면제', c.simple(40000000, 40, 0), { exempt: true, tax: 0 });
eq('간이 경계 4,800만 정확히 -> 면제 아님', c.simple(48000000, 15, 0), { exempt: false, tax: 720000 });
eq('간이 공제 초과 -> 0 (제63조⑥)', c.simple(50000000, 15, 300000000), { gross: 750000, credit: 1500000, tax: 0 });
eq('간이 1억 400만 -> 기준 초과 경고', c.simple(104000000, 30, 0), { tax: 3120000, overLimit: true });
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'vat-mode': 'supply', 'vat-amt': '1000000', 'vat-biz': '15', 'vat-buy': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, textContent: '', addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['vat-out', 'vat-simple', 'vat-amt-label', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('1,100,000원'));
vals['vat-mode'] = 'simple'; vals['vat-amt'] = '60000000'; vals['vat-buy'] = '22000000';
Object.keys(vals).forEach(k => els[k].value = vals[k]); eval(src);
console.log('UI 간이 출력:', outP.join(' | '));
assert.ok(outP.join().includes('790,000원'));
