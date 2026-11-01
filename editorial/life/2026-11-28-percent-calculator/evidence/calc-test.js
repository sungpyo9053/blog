// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); console.log('JSON-LD OK, Q', faq.mainEntity.length);
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(h3faq, faq.mainEntity.length); console.log('FAQ h3 == JSON-LD Q:', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { calc, rnd, lines } = window.percentCalc;
const near = (x, y) => Math.abs(x - y) < 1e-9;
const cases = [
  // [이름, mode, a, b, {기대값}]  value는 소수 2자리 반올림 비교
  ['of 50,000의 15%', 'of', 50000, 15, { value: 7500 }],
  ['of 1,250,000의 3.3%', 'of', 1250000, 3.3, { value: 41250 }],
  ['of 80의 120%', 'of', 80, 120, { value: 96 }],
  ['of 200의 0.5%', 'of', 200, 0.5, { value: 1 }],
  ['of 음수 -40,000의 25%', 'of', -40000, 25, { value: -10000 }],
  ['of 36,000의 15%', 'of', 36000, 15, { value: 5400 }],
  ['share 45/60', 'share', 45, 60, { value: 75 }],
  ['share 7/9', 'share', 7, 9, { value: 77.78 }],
  ['share 1/3', 'share', 1, 3, { value: 33.33 }],
  ['share 130/100', 'share', 130, 100, { value: 130 }],
  ['share 620,000/2,480,000', 'share', 620000, 2480000, { value: 25 }],
  ['share B=0 -> 오류', 'share', 5, 0, { ok: false }],
  ['change 20,000->23,000', 'change', 20000, 23000, { value: 15, diff: 3000 }],
  ['change 50,000->40,000', 'change', 50000, 40000, { value: -20 }],
  ['change 80->100', 'change', 80, 100, { value: 25 }],
  ['change 100->80', 'change', 100, 80, { value: -20 }],
  ['change 0->500 -> 오류', 'change', 0, 500, { ok: false }],
  ['change 음수 -200->100 = +150', 'change', -200, 100, { value: 150, negBase: true }],
  ['change 음수 -100->-50 = +50(적자 축소)', 'change', -100, -50, { value: 50, negBase: true }],
  ['change 음수 -100->-150 = -50(적자 확대)', 'change', -100, -150, { value: -50 }],
  ['pp 50->60', 'pp', 50, 60, { pp: 10, rel: 20 }],
  ['pp 3.5->4', 'pp', 3.5, 4, { pp: 0.5, rel: 14.29 }],
  ['pp 2->1.5', 'pp', 2, 1.5, { pp: -0.5, rel: -25 }],
  ['pp 40->50', 'pp', 40, 50, { pp: 10, rel: 25 }],
  ['pp 3->4 (FAQ)', 'pp', 3, 4, { pp: 1, rel: 33.33 }],
  ['pp 0->5 rel 없음', 'pp', 0, 5, { pp: 5, rel: null }],
  ['sale 89,000 30%', 'sale', 89000, 30, { price: 62300, disc: 26700 }],
  ['sale 45,900 15%', 'sale', 45900, 15, { price: 39015, disc: 6885 }],
  ['sale 100% -> 0원', 'sale', 10000, 100, { price: 0, disc: 10000 }],
  ['sale 할인율 101 -> 오류', 'sale', 10000, 101, { ok: false }],
  ['sale 할인율 음수 -> 오류', 'sale', 10000, -5, { ok: false }],
  ['sale 반올림 999원 33%', 'sale', 999, 33, { price: 669, disc: 330 }],
  ['rate 120,000->84,000', 'rate', 120000, 84000, { value: 30, disc: 36000 }],
  ['rate 39,900->29,900', 'rate', 39900, 29900, { value: 25.06 }],
  ['rate 판매가>정가 -> 음수(인상)', 'rate', 10000, 12000, { value: -20 }],
  ['rate 정가 0 -> 오류', 'rate', 0, 100, { ok: false }],
  ['orig 56,000 20%', 'orig', 56000, 20, { value: 70000 }],
  ['orig 70,000 30% (FAQ)', 'orig', 70000, 30, { value: 100000 }],
  ['orig 100% -> 오류', 'orig', 1000, 100, { ok: false }],
  ['orig 반올림 10,000 33%', 'orig', 10000, 33, { value: 14925 }],
  ['vatAdd 100,000', 'vatAdd', 100000, NaN, { supply: 100000, vat: 10000, total: 110000 }],
  ['vatOut 55,000', 'vatOut', 55000, NaN, { supply: 50000, vat: 5000, total: 55000 }],
  ['vatOut 10,000', 'vatOut', 10000, NaN, { supply: 9091, vat: 909 }],
  ['vatOut 110,000', 'vatOut', 110000, NaN, { supply: 100000, vat: 10000 }],
  ['vatAdd 음수 -> 오류', 'vatAdd', -1, NaN, { ok: false }],
  ['NaN 입력 -> 오류', 'of', NaN, 5, { ok: false }],
  ['B 빈칸 -> 오류', 'of', 5, NaN, { ok: false }],
];
for (const [name, mode, a, b, exp] of cases) {
  const r = calc(mode, a, b);
  for (const k of Object.keys(exp)) {
    const got = (typeof r[k] === 'number' && typeof exp[k] === 'number' && !Number.isInteger(exp[k])) ? rnd(r[k], 2) : (typeof r[k] === 'number' ? rnd(r[k], 6) : r[k]);
    assert.ok(got === exp[k] || (typeof got === 'number' && near(got, exp[k])), name + ' ' + k + '=' + r[k]);
  }
  console.log('PASS', name, JSON.stringify(r), r.ok ? '' : r.err);
}
// 반올림
const R = [[1.005, 2, 1.01], [2.675, 2, 2.68], [-2.345, 2, -2.35], [33.3333, 0, 33], [0.5, 0, 1], [-0.5, 0, -1], [1.45, 1, 1.5], [-0.004, 2, 0], [123456.785, 2, 123456.79], [14.285714, 2, 14.29], [123456789.125, 2, 123456789.13], [100000000, 4, 100000000], [1e-7, 2, 0], [77.77777777777779, 2, 77.78]];
for (const [x, d, e] of R) { assert.strictEqual(rnd(x, d), e, 'rnd ' + x); assert.ok(!Object.is(rnd(x, d), -0)); console.log('PASS rnd', x, d, '->', rnd(x, d)); }
// 표 값: 중복 할인, 10% 올렸다 내리기, 1/3 세 번 합
assert.ok(near(rnd((1 - 0.8 * 0.9) * 100, 2), 28)); assert.ok(near(rnd((1 - 0.7 * 0.8) * 100, 2), 44)); assert.ok(near(rnd((1 - 0.5 * 0.5) * 100, 2), 75));
assert.strictEqual(rnd(100 * 1.1 * 0.9, 2), 99); assert.strictEqual(rnd(calc('share', 1, 3).value, 2) * 3, 99.99);
assert.strictEqual(rnd(3.5 * 1.005, 4), 3.5175); assert.strictEqual(110000 * 0.9, 99000); assert.strictEqual(56000 * 1.2, 67200); assert.strictEqual(70000 * 1.3, 91000);
console.log('PASS 본문 표·문장 값 (중복할인 28/44/75, 99, 99.99, 3.5175, 99,000, 67,200, 91,000)');
// 출력 문구
const show = (m, a, b, d = 2) => lines(calc(m, a, b), a, b, d).join(' | ');
for (const [m, a, b, d] of [['of', 50000, 15], ['share', 45, 60], ['change', 20000, 23000], ['change', -200, 100], ['change', 0, 500], ['pp', 3.5, 4], ['pp', 0, 5], ['sale', 89000, 30], ['rate', 10000, 12000], ['orig', 56000, 20], ['vatOut', 10000, NaN], ['share', 1, 3, 0]]) console.log('UI', m, a, b, '=>', show(m, a, b, d));
assert.ok(show('of', 50000, 15).includes('= 7,500'));
assert.ok(show('pp', 3.5, 4).includes('0.5%p 상승'));
assert.ok(show('change', -200, 100).includes('150% 증가'));
// DOM 스텁으로 모드 전환 렌더 확인
const els = {}; const outP = [];
const mk = (id, v) => ({ value: v, style: {}, textContent: '', h: {}, addEventListener(t, f) { this.h[t] = f; }, set innerHTML(x) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
[['pc-mode', 'of'], ['pc-a', ''], ['pc-b', ''], ['pc-dec', '2'], ['pc-la'], ['pc-lb'], ['pc-bwrap'], ['pc-out']].forEach(([i, v]) => els[i] = mk(i, v));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본(of):', outP.join(' | ')); assert.ok(outP.join().includes('7,500'));
els['pc-mode'].value = 'vatAdd'; els['pc-mode'].h.change();
console.log('UI vatAdd:', outP.join(' | '), '/ B칸 display', els['pc-bwrap'].style.display); assert.strictEqual(els['pc-bwrap'].style.display, 'none'); assert.ok(outP.join().includes('110,000원'));
els['pc-mode'].value = 'share'; els['pc-mode'].h.change(); els['pc-b'].value = '0'; els['pc-b'].h.input();
console.log('UI share B=0:', outP.join(' | ')); assert.ok(outP.join().includes('0으로는 나눌 수 없습니다'));
console.log('ALL PASS');
