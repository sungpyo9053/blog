// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검증
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
assert.strictEqual(faq.mainEntity.length, (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.poaCheck;
const T = new Date(2026, 9, 29); // 2026-10-29
const cases = [
  ['인감 성인 -> 가능, 13호, 600원', ['seal', 'adult', '', false, T], { ok: true, fee: '1통 600원' }],
  ['인감 대리인 17세 미만 -> 불가', ['seal', 'adult', '', true, T], { ok: false }],
  ['인감 작성 2026-08-01 -> 유효(기준일 2027-02-01)', ['seal', 'adult', '2026-08-01', false, T], { ok: true, expired: false }],
  ['인감 작성 2026-04-20 -> 6개월 기준일 지남', ['seal', 'adult', '2026-04-20', false, T], { expired: true }],
  ['인감 작성 2026-05-05 -> 기준일 2026-11-05, 2주 안', ['seal', 'adult', '2026-05-05', false, T], { expired: true }],
  ['등초본 -> 가능, 400원', ['resident', 'adult', '', false, T], { ok: true, fee: '1통 400원' }],
  ['가족관계 -> 가능, 1,000원', ['family', 'adult', '', false, T], { ok: true, fee: '1통 1,000원' }],
  ['지방세 납세증명 -> 가능, 수수료 없음', ['localtax', 'adult', '', false, T], { ok: true, fee: '수수료 없음' }],
  ['본인서명사실확인서 -> 불가', ['signature', 'adult', '', false, T], { ok: false }],
  ['그 밖의 민원 -> 일반 위임장', ['other', 'adult', '', false, T], { ok: true }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, fee: r.fee, expired: r.expired }));
}
assert.ok(c('seal', 'adult', '2026-08-01', false, T).validity.includes('2027-02-01'));
assert.ok(c('seal', 'adult', '2026-08-31', false, T).validity.includes('2027-02-28')); // 말일 보정
assert.ok(c('seal', 'adult', '2026-12-01', false, T).validity.includes('오늘보다 뒤'));
assert.ok(c('seal', 'minor', '', false, T).principal.join().includes('법정대리인 동의서'));
assert.ok(c('seal', 'abroad', '', false, T).principal.join().includes('재외공관'));
assert.ok(c('seal', 'adult', '', false, T).form.includes('제13호'));
assert.ok(c('resident', 'adult', '', false, T).form.includes('제9호'));
assert.ok(c('localtax', 'adult', '', false, T).form.includes('제3호'));
assert.ok(c('family', 'minor', '', false, T).note.join().includes('법정대리인'));
assert.ok(c('resident', 'adult', '', false, T).validity.includes('확인하지 못했다'));
assert.ok(c('seal', 'adult', '', false, T).note.join().includes('온라인'));
console.log('PASS 서식·유효기간·준비물 문구 11건');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'poa-doc': 'seal', 'poa-who': 'adult', 'poa-date': '' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['poa-out', 'poa-young', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('대리 신청 가능'));
