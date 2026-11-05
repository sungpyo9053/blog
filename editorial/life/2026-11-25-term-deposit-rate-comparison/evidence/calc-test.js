// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^'\n]*'/g) || []) if (s.includes('<')) throw new Error('< in string ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld);
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq.mainEntity.length, h3faq);
console.log('PASS 스크립트 규칙 / JSON-LD 파싱, FAQ', h3faq, '개 일치');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { calc, compare } = window.depositRateCompare;
const P = 10000000;
const cases = [
  ['1천만 3.0% 12개월 단리', [P, 3.0, 0, false, 12, 's', 'gen'], { interest: 300000, incTax: 42000, locTax: 4200, after: 253800 }],
  ['1천만 3.0% 12개월 월복리', [P, 3.0, 0, false, 12, 'm', 'gen'], { interest: 304159, incTax: 42580, locTax: 4250, after: 257329 }],
  ['예시1 A 2.8+0.5 충족', [P, 2.8, 0.5, true, 12, 's', 'gen'], { rate: 3.3, interest: 330000, after: 279180 }],
  ['예시1 A 미충족', [P, 2.8, 0.5, false, 12, 's', 'gen'], { rate: 2.8, after: 236880 }],
  ['예시1 B 3.1', [P, 3.1, 0, true, 12, 's', 'gen'], { after: 262260 }],
  ['예시1 C 2.6+1.0 미충족', [P, 2.6, 1.0, false, 12, 's', 'gen'], { rate: 2.6, after: 219960 }],
  ['예시2 6개월 3.2%', [P, 3.2, 0, false, 6, 's', 'gen'], { interest: 160000, after: 135360, annual: 2.707 }],
  ['예시2 12개월 3.0% 연환산', [P, 3.0, 0, false, 12, 's', 'gen'], { annual: 2.538 }],
  ['예시3 단리 3.05%', [P, 3.05, 0, false, 12, 's', 'gen'], { after: 258030 }],
  ['비과세', [P, 3.0, 0, false, 12, 's', 'free'], { tax: 0, after: 300000 }],
  ['6개월 연3% = 원금 1.5%', [P, 3.0, 0, false, 6, 's', 'gen'], { interest: 150000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
const res = compare(P, [
  { name: 'A', base: 2.8, bonus: 0.5, met: true, months: 12, type: 's' },
  { name: 'B', base: 3.1, bonus: 0, met: true, months: 12, type: 's' },
  { name: 'C', base: 2.6, bonus: 1.0, met: false, months: 12, type: 's' }], 'gen');
assert.strictEqual(res.best.name, 'A');
assert.deepStrictEqual(res.rows.map(r => r.gap), [0, 16920, 59220]);
assert.strictEqual(res.rows[0].baseOnly, 236880);
assert.strictEqual(262260 - 236880, 25380);
assert.strictEqual(res.overLimit, false);
assert.strictEqual(compare(99800000, [{ name: 'X', base: 3, bonus: 0, met: false, months: 12, type: 's' }], 'gen').overLimit, true);
console.log('PASS compare 예시1: 1위 A, 차이', res.rows.map(r => r.gap).join('/'), '/ A 우대 미충족 시', res.rows[0].baseOnly);
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'tdc-p': '10000000', 'tdc-tax': 'gen',
  'tdc-n1': '', 'tdc-b1': '2.8', 'tdc-u1': '0.5', 'tdc-m1': '1', 'tdc-t1': '12', 'tdc-c1': 's',
  'tdc-n2': '', 'tdc-b2': '3.1', 'tdc-u2': '0', 'tdc-m2': '1', 'tdc-t2': '12', 'tdc-c2': 's',
  'tdc-n3': '', 'tdc-b3': '2.6', 'tdc-u3': '1.0', 'tdc-m3': '0', 'tdc-t3': '12', 'tdc-c3': 's' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = { 'tdc-out': el('tdc-out') }; Object.keys(vals).forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
const joined = outP.join('|');
['279,180원', '262,260원', '219,960원', '16,920원 적음', '236,880원'].forEach(s => assert.ok(joined.includes(s), s));
// 기간 섞임 경고
vals['tdc-t1'] = '6'; Object.keys(vals).forEach(id => els[id] = el(id)); els['tdc-out'] = el('tdc-out'); eval(src);
assert.ok(outP.join().includes('세후 연 환산 수익률로 비교'));
// 세 번째 상품 비우면 2개만
vals['tdc-t1'] = '12'; vals['tdc-b3'] = ''; Object.keys(vals).forEach(id => els[id] = el(id)); els['tdc-out'] = el('tdc-out'); eval(src);
assert.ok(!outP.join().includes('상품 C'));
console.log('PASS 기간 섞임 경고, 상품 C 비우면 제외');
