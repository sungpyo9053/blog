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
const calc = window.lwaCalc;
const C = (a, t, c, s) => ({ adult: a, teen: t, child: c, senior: s });
const cases = [
  // name, cnt, disc, total, regular
  ['부부+초등1 정가', C(2, 0, 1, 0), 'none', 107000, 107000],
  ['부부+초등1 다인권', C(2, 0, 1, 0), 'multi', 77000, 107000],
  ['부부+초등1 송파', C(2, 0, 1, 0), 'songpa', 69500, 107000],
  ['부부+초등1 문화누리(2명)', C(2, 0, 1, 0), 'nuri', 80000, 107000],
  ['부부+초등2 다인권', C(2, 0, 2, 0), 'multi', 101000, 140000],
  ['부부+초등2 통신사', C(2, 0, 2, 0), 'telco', 98000, 140000],
  ['부부+초등2 송파', C(2, 0, 2, 0), 'songpa', 91000, 140000],
  ['조부모2+손주1 경로만', C(0, 0, 1, 2), 'none', 80000, 99000],
  ['조부모2+손주1 다인권', C(0, 0, 1, 2), 'multi', 77000, 99000],
  ['부부+중1+초1 다인권', C(2, 1, 1, 0), 'multi', 101000, 144000],
  ['부부+중1+초1 학생', C(2, 1, 1, 0), 'student', 131000, 144000],
  ['어른5 다인권(4+1)', C(5, 0, 0, 0), 'multi', 138000, 185000],
  ['어른6 다인권(3+3)', C(6, 0, 0, 0), 'multi', 154000, 222000],
  ['어른7 다인권(4+3)', C(7, 0, 0, 0), 'multi', 178000, 259000],
  ['어른2 다인권(묶음 없음)', C(2, 0, 0, 0), 'multi', 74000, 74000],
  ['어른2 아쿠아나잇', C(2, 0, 0, 0), 'night', 48000, 74000],
  ['장애인+동반1+1명', C(3, 0, 0, 0), 'welfare', 81000, 111000],
  ['연간회원 동반 4명(3명 한도)', C(4, 0, 0, 0), 'annualComp', 106000, 148000],
  ['임신부 어른2', C(2, 0, 0, 0), 'pregnant', 59000, 74000],
  ['누리+가족관계증명서 4명', C(2, 0, 2, 0), 'nuriFamily', 89000, 140000],
  ['홈페이지 회원(어린이 정가)', C(1, 1, 1, 0), 'member', 95000, 107000],
  ['경로 단독(누리 미적용)', C(0, 0, 0, 1), 'nuri', 23500, 33000],
  ['음수·빈값 방어', C(-3, '', 'x', null), 'none', 0, 0],
];
for (const [name, cnt, disc, total, regular] of cases) {
  const r = calc(cnt, disc, 0);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  assert.strictEqual(r.regular, regular, name + ' regular=' + r.regular);
  console.log('PASS', name, '총액', r.total.toLocaleString('ko-KR') + '원', '정가', r.regular.toLocaleString('ko-KR') + '원');
}
// 마린마스터 140,000원 본전: 어른 정가 4회째, 어린이 5회째
const yr = (cnt, v) => { const r = calc(cnt, 'none', v); return [r.yearTotal, r.annual]; };
let [y, a] = yr(C(1, 0, 0, 0), 3); assert.ok(a > y, '어른 3회는 연간권이 비쌈');
[y, a] = yr(C(1, 0, 0, 0), 4); assert.ok(y > a, '어른 4회부터 이득');
[y, a] = yr(C(0, 0, 1, 0), 4); assert.ok(a > y, '어린이 4회는 연간권이 비쌈');
[y, a] = yr(C(0, 0, 1, 0), 5); assert.ok(y > a, '어린이 5회부터 이득');
assert.ok(3 * 37000 < 119000 && 4 * 37000 > 119000 && 3 * 33000 < 119000 && 4 * 33000 > 119000, '119,000원 4회째');
console.log('PASS 마린마스터 본전(어른 4회째, 어린이 5회째, 우대가 119,000원 4회째)');
const vals = { 'lwa-adult': '2', 'lwa-teen': '0', 'lwa-child': '1', 'lwa-senior': '0', 'lwa-infant': '1', 'lwa-disc': 'none', 'lwa-visits': '1' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['lwa-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('107,000원')); assert.ok(outP.some(t => t.includes('77,000원')));
console.log('ALL PASS');
