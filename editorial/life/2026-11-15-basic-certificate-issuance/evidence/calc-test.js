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
assert.strictEqual(faq.mainEntity.length, (html.match(/<h3>[^<]*\?<\/h3>/g) || []).length, 'FAQ h3 수와 JSON-LD 수 일치');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.basicCertCheck;
const cases = [
  ['일반 본인 인터넷 -> 무료', ['general', 'web', 'self', 3, false], { ok: true, fee: 0, kind: '일반증명서' }],
  ['개명 인터넷 -> 특정(개명·성본변경)', ['name', 'web', 'self', 1, false], { ok: true, kind: '특정증명서(개명·성본변경)' }],
  ['친권 확인 부모가 인터넷 -> 특정(친권 현재)', ['custody', 'web', 'family', 1, false], { ok: true, fee: 0, kind: '특정증명서(친권·미성년후견 현재)' }],
  ['정부24 -> 불가, efamily 안내', ['general', 'gov24', 'self', 1, false], { ok: false, alt: 'gov24' }],
  ['조부모 것 인터넷 -> 불가, 방문', ['general', 'web', 'lineal', 1, false], { ok: false, alt: 'visit' }],
  ['대리인 인터넷 -> 불가, 방문', ['general', 'web', 'proxy', 1, false], { ok: false, alt: 'visit' }],
  ['형제자매 인터넷 -> 불가, 위임·소명', ['general', 'web', 'other', 1, false], { ok: false, alt: 'reason' }],
  ['본인 무인발급기 2통 -> 1,000원', ['general', 'kiosk', 'self', 2, false], { ok: true, fee: 1000 }],
  ['가족 것 무인발급기 -> 불가', ['general', 'kiosk', 'family', 1, false], { ok: false, alt: 'kiosk' }],
  ['본인 방문 3통 -> 3,000원', ['detail', 'visit', 'self', 3, false], { ok: true, fee: 3000, kind: '상세증명서' }],
  ['조부모 것 방문 -> 1,000원', ['death', 'visit', 'lineal', 1, false], { ok: true, fee: 1000 }],
  ['대리인 방문 -> 1,000원', ['general', 'visit', 'proxy', 1, false], { ok: true, fee: 1000 }],
  ['수급자 방문 2통 -> 0원', ['general', 'visit', 'self', 2, true], { ok: true, fee: 0 }],
  ['형제자매 방문 -> 원칙 불가', ['general', 'visit', 'other', 1, false], { ok: false, alt: 'reason' }],
  ['출생신고 직후 부모 방문 1통 -> 면제 0원', ['newborn', 'visit', 'family', 1, false], { ok: true, fee: 0 }],
  ['출생신고 직후 부모 방문 3통 -> 2,000원', ['newborn', 'visit', 'family', 3, false], { ok: true, fee: 2000 }],
  ['출생신고 직후 본인 선택 -> 부모 선택 안내', ['newborn', 'web', 'self', 1, false], { ok: false, alt: 'newborn' }],
  ['통수 0 입력 -> 1통', ['general', 'visit', 'self', 0, false], { ok: true, fee: 1000 }],
  ['통수 빈칸 -> 1통', ['general', 'kiosk', 'self', '', false], { ok: true, fee: 500 }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.ok(c('general', 'visit', 'proxy', 1, false).need.join().includes('위임장'));
assert.ok(c('detail', 'web', 'self', 1, false).note.join().includes('제14조제5항'));
assert.ok(c('name', 'kiosk', 'self', 1, false).note.join().includes('확인하지 못했다'));
console.log('PASS 준비물·안내 문구 3건');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'bc-purpose': 'general', 'bc-where': 'web', 'bc-who': 'self', 'bc-count': '1' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['bc-out', 'bc-exempt', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('무료'));
