// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faqN = JSON.parse(ld).mainEntity.length;
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.forestCalc;
const O = (x) => Object.assign({ kind: 'cabin', cap: 4, date: '2027-01-15', nights: 1, eve: [], disc: 'none', adult: 2, teen: 0, kid: 0, car: 'mid', eco: false }, x);
const cases = [
  ['예시1 겨울 금요일 4인 숲속의집 2박', O({ nights: 2, kid: 2 }), { base: 164000, pay: 164000, entryDay: 0, parkDay: 3000, penaltyBasis: 'off-wkend' }, r => { assert.strictEqual(r.penalty[4].cut, 32800); assert.ok(r.open.includes('2026년 12월 4일')); }],
  ['예시2 수요일 휴양관 4인 다자녀', O({ kind: 'hall', date: '2027-01-13', disc: 'multi' }), { base: 44000, discount: 13200, pay: 30800, parkDay: 0, penaltyBasis: 'off-week' }, r => assert.ok(r.open.includes('2026-12-09(수)')) ],
  ['예시3 성수기 화요일 6인 2박', O({ cap: 6, date: '2027-07-20', nights: 2 }), { base: 268000, penaltyBasis: 'peak-week' }, r => { assert.strictEqual(r.penalty[2].cut, 80400); assert.strictEqual(r.penalty[2].refund, 187600); assert.strictEqual(r.entryDay, 2000); assert.ok(r.open.includes('성수기')); }],
  ['PDF: 2026-12-15(화) 사용분은 2026-11-04(수) 오픈', O({ date: '2026-12-15' }), {}, r => assert.ok(r.open.includes('2026-11-04(수)'))],
  ['PDF: 2026-12-09(수) 사용분은 2026-11-04(수) 오픈', O({ date: '2026-12-09' }), {}, r => assert.ok(r.open.includes('2026-11-04(수)'))],
  ['PDF: 2027-01-19(화) 사용분은 2026-12-09(수) 오픈', O({ date: '2027-01-19' }), {}, r => assert.ok(r.open.includes('2026-12-09(수)'))],
  ['목 입실 2박 = 주중+주말', O({ date: '2026-12-10', nights: 2 }), { base: 45000 + 82000 }, r => assert.deepStrictEqual(r.nights.map(x => x.type), ['off', 'weekend'])],
  ['공휴일 전날 체크 → 주말 요금, 위약금 주말', O({ date: '2027-02-08', eve: [true] }), { base: 82000, penaltyBasis: 'off-wkend' }],
  ['성수기 경계 7/14 비수기, 7/15 성수기, 8/24 성수기, 8/25 비수기', O({ date: '2027-07-14' }), { base: 45000 }, () => {
    assert.strictEqual(calc(O({ date: '2027-07-15' })).nights[0].type, 'peak');
    assert.strictEqual(calc(O({ date: '2027-08-24' })).nights[0].type, 'peak');
    assert.strictEqual(calc(O({ date: '2027-08-25' })).nights[0].type, 'off'); }],
  ['중증 장애인 비수기 주중 객실 50%, 주말 10%', O({ date: '2027-01-14', nights: 2, disc: 'high' }), { base: 127000, discount: 22500 + 8200, parkDay: 0 }],
  ['야영데크 6인 지역주민: 주중 20%, 주말 10%', O({ kind: 'deck', cap: 6, date: '2027-01-14', nights: 2, disc: 'local' }), { base: 31500, discount: 3000 + 1650, parkDay: 3000 }],
  ['야영데크 4인은 요금 없음', O({ kind: 'deck', cap: 4 }), { ok: false }],
  ['직접 입력(캠핑카 22,000/35,000) 경형 저공해', O({ kind: 'customCamp', off: '22,000', peak: 35000, date: '2027-05-05', car: 'light', eco: true, adult: 2, teen: 1, kid: 1 }), { base: 22000, parkDay: 750, entryDay: 2900 }],
  ['3박 초과 입력은 3박으로', O({ date: '2027-01-11', nights: 7 }), { base: 45000 * 3 }],
  ['잘못된 날짜', O({ date: '2027-02-30' }), { ok: false }],
  ['위약금 성수기 주말 1일 전 90%', O({ cap: 6, date: '2027-07-23' }), { base: 134000, penaltyBasis: 'peak-wkend' }, r => assert.strictEqual(r.penalty[4].cut, 120600)],
];
for (const [name, o, exp, extra] of cases) {
  const r = calc(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  if (extra) extra(r);
  console.log('PASS', name, r.ok === false ? r.msg : JSON.stringify({ base: r.base, discount: r.discount, pay: r.pay, entryDay: r.entryDay, parkDay: r.parkDay, pen: r.penaltyBasis, open: r.open }));
}
// 본문 요금표와 evidence/fee-summary.txt 최빈값 대조
const sum = fs.readFileSync(path.join(__dirname, 'fee-summary.txt'), 'utf8');
const top = (k, cap) => { const m = sum.match(new RegExp('^' + k + '\\t' + cap + '\\t\\d+\\t\\d+\\t(\\d+)/(\\d+)', 'm')); return [+m[1], +m[2]]; };
for (const cap of [3, 4, 5, 6, 8, 10, 12]) {
  assert.deepStrictEqual(calc(O({ cap, date: '2027-01-13' })).base, top('숲속의집', cap)[0]);
  assert.deepStrictEqual(calc(O({ cap, date: '2027-01-15' })).base, top('숲속의집', cap)[1]);
  assert.deepStrictEqual(calc(O({ kind: 'hall', cap, date: '2027-01-13' })).base, top('휴양관', cap)[0]);
  assert.deepStrictEqual(calc(O({ kind: 'hall', cap, date: '2027-01-15' })).base, top('휴양관', cap)[1]);
}
for (const cap of [5, 6]) assert.deepStrictEqual([calc(O({ kind: 'deck', cap, date: '2027-01-13' })).base, calc(O({ kind: 'deck', cap, date: '2027-01-15' })).base], top('camp-데크', cap));
console.log('PASS 요금표 30개 값 = 국립 48곳 최빈값');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'nf-kind': 'cabin', 'nf-cap': '4', 'nf-off': '45000', 'nf-peak': '82000', 'nf-date': '2027-01-15', 'nf-nights': '2', 'nf-disc': 'none', 'nf-adult': '2', 'nf-teen': '0', 'nf-kid': '2', 'nf-car': 'mid' };
const out = [];
const mk = () => { const e = { style: {}, children: [], appendChild(c) { this.children.push(c); }, set textContent(v) { this._t = v; }, get textContent() { return this._t || this.children.map(c => c.textContent).join(''); } }; return e; };
const els = {};
['nf-eve1', 'nf-eve2', 'nf-eve3', 'nf-eco', 'nf-custom-box', ...Object.keys(vals)].forEach(id => els[id] = { value: vals[id], checked: false, style: {}, addEventListener() {} });
els['nf-out'] = { set innerHTML(v) { out.length = 0; }, appendChild(p) { out.push(p.textContent); } };
global.document = { getElementById: id => els[id], createElement: mk };
eval(src);
console.log('UI 기본값 출력:\n  ' + out.join('\n  '));
assert.ok(out.join().includes('164,000원'));
assert.strictEqual(els['nf-custom-box'].style.display, 'none');
// 글 구조
const vis = html.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<[^>]+>/g, '').replace(/\s+/g, '');
const h2 = (html.match(/<h2/g) || []).length, h3 = (html.match(/<h3/g) || []).length;
console.log('visible chars(공백 제외):', vis.length, 'H2:', h2, 'H3:', h3, 'FAQ JSON-LD:', faqN);
