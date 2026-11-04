// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.iphoneBatteryCalc, M = window.iphoneBatteryModels;
// 계산기 가격 = Apple 위젯 JSON(보증 제외) 가격, AC+ JSON은 전부 0원
const won = s => parseInt(s.replace(/[^0-9]/g, ''), 10);
const pick = f => { const o = {}; for (const p of JSON.parse(fs.readFileSync(path.join(__dirname, f), 'utf8')).products) for (const c of (p.childrenProducts || [p])) for (const s of c.services) if (s.serviceLabel === '배터리 서비스') o[c.product_loc_title] = won(s.price); return o; };
const oow = pick('pricing-estimate-OOW.json'), acp = pick('pricing-estimate-ACplus.json');
assert.strictEqual(M.length - 1, Object.keys(oow).length);
for (const [name, price] of M.slice(0, -1)) { assert.strictEqual(price, oow[name], name); assert.strictEqual(acp[name], 0, name + ' AC+'); }
console.log('PASS 모델 ' + (M.length - 1) + '개 가격 = Apple OOW JSON, AC+ JSON 전부 0원');
const idx = n => M.findIndex(m => m[0] === n);
const cases = [
  ['15 보증 제외', idx('iPhone 15'), 'n', '85', { price: 146000, cost: 146000, status: 'paid' }],
  ['15 보증 제외 78%', idx('iPhone 15'), 'n', '78', { cost: 146000, status: 'paid-low' }],
  ['15 AC+ 78% 무상', idx('iPhone 15'), 'y', '78', { cost: 0, status: 'ac-free' }],
  ['15 AC+ 80% 경계는 조건 밖', idx('iPhone 15'), 'y', '80', { cost: null, status: 'ac-over' }],
  ['15 AC+ 79.9%', idx('iPhone 15'), 'y', '79.9', { cost: 0, status: 'ac-free' }],
  ['15 AC+ 빈칸', idx('iPhone 15'), 'y', '', { status: 'ac-nocap' }],
  ['SE3 100,000', idx('iPhone SE(3세대)'), 'n', '', { cost: 100000, status: 'paid' }],
  ['13 mini 129,000', idx('iPhone 13 mini'), 'n', '90', { cost: 129000 }],
  ['16 Pro 179,000', idx('iPhone 16 Pro'), 'n', '90', { cost: 179000 }],
  ['16e 146,000', idx('iPhone 16e'), 'n', '90', { cost: 146000 }],
  ['Air 179,000', idx('iPhone Air'), 'n', '90', { cost: 179000 }],
  ['18 Pro Max 199,000', idx('iPhone 18 Pro Max'), 'n', '90', { cost: 199000 }],
  ['XR 129,000 (최상위 항목)', idx('iPhone XR'), 'n', '90', { cost: 129000 }],
  ['Duo 349,000', idx('iPhone Duo'), 'n', '90', { cost: 349000 }],
  ['목록 밖 모델', M.length - 1, 'y', '70', { price: null, status: 'unknown' }],
];
for (const [name, i, ac, cap, exp] of cases) {
  const r = calc(i, ac, cap);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표 금액이 계산기 데이터와 같은지
for (const v of [100000, 129000, 146000, 179000, 199000, 349000]) assert.ok(html.includes('<td>' + v.toLocaleString('en-US') + '원</td>'), 'table ' + v);
console.log('PASS 본문 표 6개 가격대');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'ib-model': String(idx('iPhone 15')), 'ib-ac': 'n', 'ib-cap': '78' };
const outP = [], opts = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(c) { if (id === 'ib-out') outP.push(c.textContent); else opts.push(c); } });
const els = {}; ['ib-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
assert.strictEqual(opts.length, M.length);
assert.ok(opts[idx('iPhone 15')].selected, 'default iPhone 15');
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('146,000원'));
