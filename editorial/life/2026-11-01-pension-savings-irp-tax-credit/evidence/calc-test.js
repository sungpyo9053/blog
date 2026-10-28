// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.pensionCreditCalc;
const M = 10000;
const cases = [
  ['한도 초과: 연금저축 800 + IRP 500, 총급여 5,000 -> 900만, 1,485,000', { type: 'wage', income: 5000 * M, ps: 800 * M, irp: 500 * M, isa: 0 }, { psOk: 600 * M, eligible: 900 * M, excluded: 400 * M, refund: 1485000 }],
  ['연금저축 단독 700 -> 600만만 인정', { type: 'wage', income: 4000 * M, ps: 700 * M, irp: 0, isa: 0 }, { eligible: 600 * M, refund: 990000 }],
  ['IRP 단독 900 -> 900만', { type: 'wage', income: 7000 * M, ps: 0, irp: 900 * M, isa: 0 }, { eligible: 900 * M, refund: 1188000, high: true }],
  ['경계: 총급여 정확히 5,500만 -> 16.5%', { type: 'wage', income: 5500 * M, ps: 600 * M, irp: 300 * M, isa: 0 }, { high: false, tax: 1350000, local: 135000, refund: 1485000 }],
  ['경계: 총급여 5,500만 1원 -> 13.2%', { type: 'wage', income: 5500 * M + 1, ps: 600 * M, irp: 300 * M, isa: 0 }, { high: true, tax: 1080000, local: 108000, refund: 1188000 }],
  ['종합소득금액 4,500만 이하 15% / 4,600만 12%', { type: 'global', income: 4600 * M, ps: 300 * M, irp: 0, isa: 0 }, { high: true, refund: 396000 }],
  ['ISA 2,000만 IRP 전환 + 기존 900 -> 추가 200, 1,100만', { type: 'wage', income: 5000 * M, ps: 600 * M, irp: 300 * M, isa: 2000 * M, isaTo: 'irp' }, { extra: 200 * M, eligible: 1100 * M, refund: 1815000 }],
  ['ISA 3,000만 -> 추가 300 상한, 1,200만', { type: 'wage', income: 5000 * M, ps: 600 * M, irp: 300 * M, isa: 3000 * M, isaTo: 'irp' }, { extra: 300 * M, eligible: 1200 * M, refund: 1980000 }],
  ['ISA 5,000만 -> 여전히 300 상한', { type: 'wage', income: 8000 * M, ps: 600 * M, irp: 300 * M, isa: 5000 * M, isaTo: 'irp' }, { extra: 300 * M, eligible: 1200 * M, refund: 1584000 }],
  ['ISA 3,000만만 IRP로(다른 납입 0) -> 900 + 300', { type: 'wage', income: 5000 * M, ps: 0, irp: 0, isa: 3000 * M, isaTo: 'irp' }, { eligible: 1200 * M }],
  ['ISA 3,000만을 연금저축으로 -> 600 + 300', { type: 'wage', income: 5000 * M, ps: 0, irp: 0, isa: 3000 * M, isaTo: 'ps' }, { eligible: 900 * M }],
  ['소액 ISA 100만 + 900 꽉 -> 추가 10만', { type: 'wage', income: 5000 * M, ps: 600 * M, irp: 300 * M, isa: 100 * M, isaTo: 'irp' }, { extra: 10 * M, eligible: 910 * M }],
];
for (const [name, o, exp] of cases) {
  const r = calc(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ eligible: r.eligible, extra: r.extra, rate: r.rate, refund: r.refund }));
}
// 표 값 검산
[[300, 495000, 396000], [600, 990000, 792000], [900, 1485000, 1188000]].forEach(([a, lo, hi]) => {
  assert.strictEqual(calc({ type: 'wage', income: 5000 * M, ps: 0, irp: a * M, isa: 0 }).refund, lo);
  assert.strictEqual(calc({ type: 'wage', income: 6000 * M, ps: 0, irp: a * M, isa: 0 }).refund, hi);
});
console.log('PASS 표 값 6개');
// UI 기본값 렌더 + 결정세액 한계 안내 문구 확인 (최소 DOM 스텁)
const vals = { 'pc-type': 'wage', 'pc-inc': '5000', 'pc-ps': '600', 'pc-irp': '300', 'pc-isa': '0', 'pc-isato': 'irp' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, textContent: '', addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['pc-out', 'pc-inc-label', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('1,485,000원'));
assert.ok(outP.join().includes('결정세액은 개인마다 달라 계산하지 못합니다'));
console.log('PASS 결정세액 한계 안내 문구 출력');
