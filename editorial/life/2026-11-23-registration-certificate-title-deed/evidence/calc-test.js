// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
const h3faq = (html.split('<h2 id="faq">')[1].split('<h2')[0].match(/<h3>/g) || []).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ JSON-LD', faq, '= h3', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.deedCheck;
const cases = [
  ['매도·통지서·방문', 'sell', 'info', 'visit', { need: true, fee: 18000, alt: 0, prepHas: '인감증명서', submitHas: '제50조제2항' }],
  ['매도·통지서·전자', 'sell', 'info', 'efile', { need: true, fee: 10000, alt: 0 }],
  ['대출·분실·방문', 'loan', 'none', 'visit', { need: true, fee: 18000, alt: 3, submitHas: '제51조' }],
  ['매도·종이 등기필증·방문', 'sell', 'old', 'visit', { need: true, submitHas: '부칙 제2조' }],
  ['매도·종이 등기필증·전자', 'sell', 'old', 'efile', { submitHas: '확인하지 못했다' }],
  ['대출·전자등기필정보·방문', 'loan', 'elec', 'visit', { notesHas: '확인하지 못했다' }],
  ['말소·분실', 'release', 'none', 'visit', { need: false, fee: 4000, alt: 0, submitHas: '근저당권자' }],
  ['말소·전자', 'release', 'info', 'efile', { fee: 1000 }],
  ['상속·분실·방문', 'inherit', 'none', 'visit', { need: false, fee: 20000, alt: 0, submitHas: '제23조제3항', prepHas: '상속인 전원' }],
  ['상속·전자표준양식', 'inherit', 'info', 'efile', { fee: 17000 }],
];
for (const [name, s, d, w, e] of cases) {
  const r = c(s, d, w);
  if ('need' in e) assert.strictEqual(r.need, e.need, name);
  if ('fee' in e) assert.strictEqual(r.fee, e.fee, name);
  if ('alt' in e) assert.strictEqual(r.alt.length, e.alt, name);
  if (e.prepHas) assert.ok(r.prep.join().includes(e.prepHas), name);
  if (e.submitHas) assert.ok(r.submit.includes(e.submitHas), name);
  if (e.notesHas) assert.ok(r.notes.join().includes(e.notesHas), name);
  assert.ok(r.submit.length > 0, name + ' submit empty');
  console.log('PASS', name, JSON.stringify({ need: r.need, fee: r.fee, alt: r.alt.length }));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'dg-sit': 'sell', 'dg-doc': 'none', 'dg-way': 'visit' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['dg-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(매도·분실·방문):\n ' + outP.join('\n '));
assert.ok(outP.join().includes('18,000원'));
assert.ok(outP.join().includes('법무사·등기소 문의'));
console.log('ALL PASS');
