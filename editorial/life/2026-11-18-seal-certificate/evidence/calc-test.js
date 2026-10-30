// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'([^'\\]|\\.)*'/g)) if (m[0].includes('<')) throw new Error('raw < in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld);
const h3 = [...html.split('<h2 id="faq">')[1].matchAll(/<h3>(.*?)<\/h3>/g)].map(m => m[1]);
assert.deepStrictEqual(faq.mainEntity.map(q => q.name), h3);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.sealCheck;
const cases = [
  ['정부24 본인 행정기관 제출 -> 가능 무료', 'admin', 'self', 'online', { ok: 'yes', fee: '무료' }, '인증서'],
  ['정부24 본인 개인 간 일반용 -> 가능', 'private', 'self', 'online', { ok: 'yes', fee: '무료' }, '제출처'],
  ['정부24 대리 -> 불가', 'admin', 'agent', 'online', { ok: 'no' }, '본인만'],
  ['정부24 부동산 매도용 -> 불가', 'realty', 'self', 'online', { ok: 'no' }, '매도용'],
  ['정부24 자동차 매도용 -> 불가', 'car', 'self', 'online', { ok: 'no' }, '매도용'],
  ['정부24 금융기관 제출 -> 불가', 'finance', 'self', 'online', { ok: 'no' }, '금융기관'],
  ['정부24 법원 제출 -> 불가', 'court', 'self', 'online', { ok: 'no' }, '법원'],
  ['무인발급기 -> 확인하지 못함', 'admin', 'self', 'kiosk', { ok: 'unknown', fee: '확인하지 못했다' }, '확인하지 못했다'],
  ['방문 본인 일반 -> 600원', 'finance', 'self', 'visit', { ok: 'yes' }, '신분증'],
  ['방문 대리 -> 위임장 17세', 'admin', 'agent', 'visit', { ok: 'yes' }, '별지 제13호'],
  ['방문 본인 부동산 매도 -> 매수자 정보', 'realty', 'self', 'visit', { ok: 'yes' }, '매수자'],
  ['방문 대리 자동차 매도 -> 매수자 정보', 'car', 'agent', 'visit', { ok: 'yes' }, '매수자'],
];
for (const [name, p, w, m, exp, word] of cases) {
  const r = c(p, w, m);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  assert.ok((r.verdict + r.items.join()).includes(word), name + ' missing ' + word);
  if (m === 'visit') assert.ok(r.fee.startsWith('1통 600원'), name + ' fee');
  if (w === 'agent') { assert.ok(r.alt[0].includes('대리 발급이 안 된다')); assert.ok(r.items.join().includes('17세') || m !== 'visit'); }
  else { assert.ok(r.alt[0].includes('2028년 12월 31일')); assert.strictEqual(r.alt[1].includes('대신할 수 있다'), p === 'admin'); }
  console.log('PASS', name, '|', r.verdict, '|', r.fee);
}
// UI 기본값(행정기관 제출·본인·방문) 렌더 확인 — 최소 DOM 스텁
const vals = { 'seal-purpose': 'admin', 'seal-who': 'self', 'seal-method': 'visit' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['seal-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('수수료: 1통 600원'));
console.log('PASS FAQ JSON-LD', faq.mainEntity.length, '문항이 본문 h3와 일치');
