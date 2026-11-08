// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity;
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq.length, h3faq, 'FAQ JSON-LD count');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.coexAquaCalc;
const C = (a, c, s) => ({ adult: a, child: c, senior: s });
const cases = [
  // name, cnt, disc, online, onsite
  ['부부+초등1 할인없음', C(2, 1, 0), 'none', 78000, 101000],
  ['부부+초등1 문화누리카드', C(2, 1, 0), 'nuri', 78000, 60600],
  ['부부+중1+초1', C(3, 1, 0), 'none', 106000, 136000],
  ['조부모2+손주1', C(0, 1, 2), 'none', 78000, 80000],
  ['장애인 어린이+부모2', C(2, 1, 0), 'r30', 78000, 70700],
  ['대인1 문화가 있는 날', C(1, 0, 0), 'culture', 28000, 20000],
  ['대인3+소인1 문화가 있는 날(본인 1명만)', C(3, 1, 0), 'culture', 106000, 121000],
  ['대인5 30%(4명 한도)', C(5, 0, 0), 'r30', 134000, 133000],
  ['대인2 KT 15%', C(2, 0, 0), 'telco', 53000, 59500],
  ['소인2 스타필드 20%', C(0, 2, 0), 'starfield', 50000, 49600],
  ['경로1 15%(경로 우대가 더 쌈)', C(0, 0, 1), 'telco', 28000, 24500],
  ['경로1 누리 40%', C(0, 0, 1), 'nuri', 28000, 21000],
  ['싱글패스 동반 대인4(3명 한도)', C(4, 0, 0), 'annual', 106000, 108500],
  ['음수·빈값 방어', C(-3, '', 'x'), 'none', 0, 0],
];
for (const [name, cnt, disc, on, site] of cases) {
  const r = calc(cnt, disc, 0);
  assert.strictEqual(r.online, on, name + ' online=' + r.online);
  assert.strictEqual(r.onsite, site, name + ' onsite=' + r.onsite);
  console.log('PASS', name, '온라인', r.online.toLocaleString('ko-KR') + '원', '현장', r.onsite.toLocaleString('ko-KR') + '원');
}
// 연간이용권 본전: 대인 현장 3회, 온라인 4회, 소인 온라인 4회
const yr = (cnt, disc, v) => { const r = calc(cnt, disc, v); return [r.yearTotal, r.annualFresh]; };
let [y, a] = yr(C(1, 0, 0), 'culture', 2); assert.ok(a > y);
assert.strictEqual(3 * 35000 > 99000, true); assert.strictEqual(3 * 28000 > 99000, false); assert.strictEqual(4 * 28000 > 99000, true);
[y, a] = yr(C(1, 0, 0), 'none', 3); assert.ok(a > y, '대인 온라인 3회는 연간권이 비쌈');
[y, a] = yr(C(1, 0, 0), 'none', 4); assert.ok(y > a, '대인 온라인 4회부터 연간권 이득');
[y, a] = yr(C(0, 1, 0), 'none', 4); assert.ok(y > a, '소인 온라인 4회부터 연간권 이득');
[y, a] = yr(C(0, 1, 0), 'none', 3); assert.ok(a > y);
console.log('PASS 연간이용권 본전(대인·소인 온라인 4회째)');
assert.strictEqual(calc(C(0, 2, 0), 'none', 0).needGuardian, true);
assert.strictEqual(calc(C(1, 2, 0), 'none', 0).needGuardian, false);
console.log('PASS 보호자 동반 경고');
const vals = { 'cx-adult': '2', 'cx-child': '1', 'cx-senior': '0', 'cx-infant': '1', 'cx-disc': 'none', 'cx-visits': '1' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['cx-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('78,000원')); assert.ok(outP[1].includes('101,000원'));
console.log('ALL PASS');
