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
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.familyCertCheck;
const cases = [
  ['본인 인터넷 일반 -> 무료, 인증서', ['self', 'web', 'general', 3, false], { ok: true, fee: 0 }],
  ['부모 것 인터넷 -> 가능(법 14조의2)', ['family', 'web', 'general', 1, false], { ok: true, fee: 0 }],
  ['조부모 것 인터넷 -> 불가, 방문 안내', ['lineal', 'web', 'general', 1, false], { ok: false, alt: 'visit' }],
  ['대리인 인터넷 -> 불가', ['proxy', 'web', 'general', 1, false], { ok: false, alt: 'visit' }],
  ['형제자매 인터넷 -> 불가, 소명 사유', ['other', 'web', 'general', 1, false], { ok: false, alt: 'visit-reason' }],
  ['본인 무인발급기 2통 -> 1,000원', ['self', 'kiosk', 'general', 2, false], { ok: true, fee: 1000 }],
  ['가족 것 무인발급기 -> 불가(본인만)', ['family', 'kiosk', 'general', 1, false], { ok: false, alt: 'web' }],
  ['영문 무인발급기 -> 불가', ['self', 'kiosk', 'english', 1, false], { ok: false, alt: 'web' }],
  ['본인 방문 3통 -> 3,000원', ['self', 'visit', 'detail', 3, false], { ok: true, fee: 3000 }],
  ['조부모 것 방문 -> 1,000원', ['lineal', 'visit', 'general', 1, false], { ok: true, fee: 1000 }],
  ['대리인 방문 -> 위임장', ['proxy', 'visit', 'general', 1, false], { ok: true, fee: 1000 }],
  ['수급자 방문 -> 면제 0원', ['self', 'visit', 'general', 2, true], { ok: true, fee: 0 }],
  ['형제자매 방문 -> 원칙 불가', ['other', 'visit', 'general', 1, false], { ok: false, alt: 'visit-reason' }],
  ['통수 0 입력 -> 1통으로', ['self', 'visit', 'general', 0, false], { ok: true, fee: 1000 }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
assert.ok(c('proxy', 'visit', 'general', 1, false).need.join().includes('위임장'));
assert.ok(c('self', 'web', 'english', 1, false).need.join().includes('여권 영문명'));
assert.ok(c('self', 'web', 'detail', 1, false).note.join().includes('제14조제5항'));
console.log('PASS 준비물·안내 문구 3건');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'fc-who': 'self', 'fc-where': 'web', 'fc-kind': 'general', 'fc-count': '1' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['fc-out', 'fc-exempt', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('무료'));
