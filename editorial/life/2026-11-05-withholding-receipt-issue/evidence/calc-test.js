// ko.html의 서류 찾기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1, 'script 1개');
const src = scripts[0];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'[^']*'/g)) if (s.indexOf('<') >= 0) throw new Error('< in string ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld);
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq.mainEntity.length, h3faq, 'FAQ JSON-LD 개수 = 본문 FAQ 개수');
console.log('PASS FAQ', h3faq, '개, JSON-LD 일치');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const pick = window.withholdingReceiptPick;
const cases = [
  ['재직자 2월 본인확인 -> 회사만', 'self', 2, 'work', r => r.where.length === 1 && r.where[0].includes('회사')],
  ['재직자 3월 -> 회사 + 홈택스, 4월 말 안내', 'self', 3, 'work', r => r.where.length === 2 && r.timing.includes('3월 10일') && r.timing.includes('4월 말')],
  ['재직자 4월 -> 같은 안내', 'tax', 4, 'work', r => r.timing.includes('4월 말') && r.prep.includes('종합소득세')],
  ['재직자 5월 -> 홈택스', 'self', 5, 'work', r => r.where.length === 1 && r.where[0].includes('지급명세서 등 제출내역')],
  ['퇴사자 1월 -> 1월 중순 선제공', 'self', 1, 'left', r => r.timing.includes('1월 중순') && r.where[0].includes('퇴사')],
  ['외부제출 5월 -> 소득금액증명 작년분', 'external', 5, 'work', r => r.doc.includes('소득금액증명(작년') && r.fee.includes('수수료 없음')],
  ['외부제출 4월 -> 아직 작년분 없음', 'external', 4, 'left', r => r.doc.includes('전전년도') && r.timing.includes('5월 1일')],
  ['이직 -> 원천징수영수증+원천징수부 사본', 'jobchange', 11, 'left', r => r.doc.includes('원천징수부 사본') && r.timing.includes('제197조')],
  ['청년도약 -> 중도퇴사자용 불인정', 'youth', 7, 'left', r => r.doc.includes('퇴직소득원천징수영수증') && r.prep.includes('불인정') === false && r.prep.includes('인정되지 않는다')],
];
for (const [name, p, m, s, ok] of cases) {
  const r = pick(p, m, s);
  assert.ok(ok(r), name + ' ' + JSON.stringify(r));
  console.log('PASS', name, '|', r.doc, '|', r.where.join(' / '));
}
// 12개월 x 5목적 x 2상태 모두 빈 칸 없이 나오는지
for (const p of ['self', 'tax', 'external', 'jobchange', 'youth']) for (let m = 1; m <= 12; m++) for (const s of ['work', 'left']) {
  const r = pick(p, m, s);
  assert.ok(r.doc.length && r.where.length && r.timing.length && r.fee.length && r.prep.length, p + m + s);
}
console.log('PASS 120개 조합 빈 칸 없음');
// UI 기본값(내 소득 확인, 11월, 재직) 렌더 — 최소 DOM 스텁
const vals = { 'wr-purpose': 'self', 'wr-month': '11', 'wr-status': 'work' };
const outP = [];
const mk = () => ({ style: {}, kids: [], appendChild(c) { this.kids.push(c) }, set textContent(v) { this._t = v }, get textContent() { return this._t !== undefined ? this._t : this.kids.map(k => k.textContent).join('') } });
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['wr-out'] = { set innerHTML(v) { outP.length = 0 }, appendChild(p) { outP.push(p.textContent) } };
global.document = { getElementById: id => els[id], createElement: mk, createTextNode: t => ({ textContent: t }) };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
assert.strictEqual(outP.length, 5);
assert.ok(outP[1].includes('지급명세서 등 제출내역'));
