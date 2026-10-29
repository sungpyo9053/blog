// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
(src.match(/'[^'\n]*'/g) || []).forEach(s => { if (s.indexOf('<') >= 0) throw new Error('< in string ' + s); });
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.jeonseGuaranteeCalc;
const E = 100000000, M = 10000;
const base = { org: 'hug', senior: 0, ptype: 'market', house: 'apt', region: 'metro', days: 730, disc: 0, sgirate: 0 };
const cases = [
  ['HUG 예: 주택가격 1억, 보증금 9,500만 -> 불가', { dep: 9500 * M, price: 1 * E, house: 'villa' }, { ok: false }],
  ['HUG 예: 주택가격 1억, 보증금 9,000만 -> 가능', { dep: 9000 * M, price: 1 * E, house: 'villa' }, { ok: true, limit: 9000 * M }],
  ['HUG 예: 4,000만 + 선순위 5,500만 -> 불가, 한도 3,500만', { dep: 4000 * M, senior: 5500 * M, price: 1 * E, house: 'villa' }, { ok: false, limit: 3500 * M }],
  ['HUG 아파트 3억/시세 5억 730일 -> 0.107%, 642,000', { dep: 3 * E, price: 5 * E }, { ok: true, rate: 0.107, fee: 642000 }],
  ['HUG 수도권 7억 초과 -> 불가', { dep: 7.5 * E, price: 10 * E }, { ok: false }],
  ['HUG 지방 5억 초과 -> 불가', { dep: 5.5 * E, price: 10 * E, region: 'other' }, { ok: false }],
  ['HUG 공시가 2억 빌라 -> 주택가격 2.8억, 2.52억 가능', { dep: 2.52 * E, price: 2 * E, ptype: 'official', house: 'villa' }, { ok: true, price: 2.8 * E }],
  ['HUG 공시가 2억 빌라 2.53억 -> 불가', { dep: 2.53 * E, price: 2 * E, ptype: 'official', house: 'villa' }, { ok: false }],
  ['HUG 기타 1억 이하, 부채비율 80% 초과 -> 0.172%', { dep: 0.9 * E, price: 1 * E, house: 'villa' }, { rate: 0.172 }],
  ['HUG 아파트 5억 초과, 부채비율 75% -> 0.138%', { dep: 6 * E, price: 8.8888889 * E }, { rate: 0.138 }],
  ['HUG 선순위 50% 초과 할증 10%', { dep: 1 * E, senior: 2.5 * E, price: 5 * E }, { ok: true, rate: 0.117, base: 234000, surcharge: 23400, fee: 257400 }],
  ['HUG 60% 할인', { dep: 3 * E, price: 5 * E, disc: 60 }, { base: 642000, discount: 385200, fee: 256800 }],
  ['HF 3억/5억 LTV 60% -> 0.04%, 240,000', { org: 'hf', dep: 3 * E, price: 5 * E }, { ok: true, rate: 0.04, fee: 240000 }],
  ['HF LTV 75% -> 0.11%', { org: 'hf', dep: 3.75 * E, price: 5 * E }, { rate: 0.11 }],
  ['HF LTV 85% -> 0.18%', { org: 'hf', dep: 4.25 * E, price: 5 * E }, { rate: 0.18, ok: true }],
  ['HF 주택가격 12억 초과 -> 불가', { org: 'hf', dep: 5 * E, price: 13 * E }, { ok: false }],
  ['HF 지방 한도 5억', { org: 'hf', dep: 5.5 * E, price: 10 * E, region: 'other' }, { ok: false, limit: 5 * E }],
  ['SGI 요율 직접 입력 0.2% 3억 730일 -> 1,200,000', { org: 'sgi', dep: 3 * E, price: 5 * E, sgirate: 0.2 }, { fee: 1200000 }],
  ['SGI 요율 없음 -> 0', { org: 'sgi', dep: 3 * E, price: 5 * E }, { fee: 0 }],
];
for (const [name, inp, exp] of cases) {
  const r = calc(Object.assign({}, base, inp));
  for (const k of Object.keys(exp)) assert.ok(Math.abs(r[k] - exp[k]) < 1e-6 || r[k] === exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, price: r.price, limit: r.limit, ratio: Math.round(r.ratio * 1000) / 1000, rate: r.rate, base: r.base, surcharge: r.surcharge, discount: r.discount, fee: r.fee }));
}
// HUG 요율표 24칸이 본문 표와 같은지
const tbl = html.match(/<h2 id="hug-fee">[\s\S]*?<\/table>/)[0];
const tblRates = (tbl.match(/연 (0\.\d+)%/g) || []).map(s => parseFloat(s.slice(2)));
const jsRates = JSON.parse(src.match(/var HUG=(\[[\s\S]*?\]\]\]);/)[1]).flat(2);
assert.deepStrictEqual(tblRates, jsRates);
console.log('PASS HUG 요율 24칸 본문 표와 일치');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'jg-org': 'hug', 'jg-dep': '30000', 'jg-senior': '0', 'jg-price': '50000', 'jg-ptype': 'market', 'jg-house': 'apt', 'jg-region': 'metro', 'jg-start': '2025-12-01', 'jg-end': '2027-11-30', 'jg-disc': '0', 'jg-sgirate': '' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['jg-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('642,000원'));
