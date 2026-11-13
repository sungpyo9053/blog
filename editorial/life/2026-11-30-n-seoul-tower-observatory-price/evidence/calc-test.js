// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faqN = JSON.parse(ld).mainEntity.length;
const h3InFaq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faqN, h3InFaq, 'FAQ JSON-LD count matches h3');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.nseoulTowerCalc;
const P = (tower, cable, adult, child, senior, infant, dAdult, dChild, dComp) => ({ tower, cable, adult, child, senior, infant, dAdult, dChild, dComp });
const cases = [
  ['부부+초등1 전망대+왕복', P('yes', 'round', 2, 1, 0, 0, 0, 0, 0), 122500, 0],
  ['부부+초등1 전망대+편도', P('yes', 'one', 2, 1, 0, 0, 0, 0, 0), 114000, 0],
  ['연인 전망대+왕복', P('yes', 'round', 2, 0, 0, 0, 0, 0, 0), 88000, 0],
  ['대인1 전망대만', P('yes', 'none', 1, 0, 0, 0, 0, 0, 0), 29000, 0],
  ['경로2+소인1 전망대+왕복', P('yes', 'round', 0, 1, 2, 0, 0, 0, 0), 103500, 0],
  ['장애인 본인+동반 전망대+왕복', P('yes', 'round', 0, 0, 0, 0, 1, 0, 1), 67100, 0],
  ['우대 소인 전망대+편도', P('yes', 'one', 0, 0, 0, 0, 0, 1, 0), 25100, 0],
  ['케이블카만 대인2 편도', P('no', 'one', 2, 0, 0, 0, 0, 0, 0), 24000, 0],
  ['유아1+대인1 전망대만', P('yes', 'none', 1, 0, 0, 1, 0, 0, 0), 29000, 1],
  ['유아2+대인1 전망대+왕복(초과분 소인 요금+케이블카 미확인)', P('yes', 'round', 1, 0, 0, 2, 0, 0, 0), 67000, 2],
  ['동반자 초과 경고', P('yes', 'none', 0, 0, 0, 0, 1, 0, 2), 60900, 1],
  ['음수·빈값 방어', P('yes', 'round', -3, '', 'x', 0, 0, 0, 0), 0, 0],
];
for (const [name, o, total, notes] of cases) {
  const r = calc(o);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  assert.strictEqual(r.notes.length, notes, name + ' notes=' + r.notes.length);
  console.log('PASS', name, r.total.toLocaleString('ko-KR') + '원', r.notes.join(' / '));
}
const vals = { 'nst-tower': 'yes', 'nst-cable': 'round', 'nst-adult': '2', 'nst-child': '1', 'nst-senior': '0', 'nst-infant': '1', 'nst-d-adult': '0', 'nst-d-child': '0', 'nst-d-comp': '0' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['nst-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('122,500원'));
console.log('FAQ', faqN, '개 JSON-LD = h3 일치');
