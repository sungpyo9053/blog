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
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>(.*?)<\/h3>/g).map(s => s.slice(4, -5));
assert.deepStrictEqual(h3faq.length, faq.mainEntity.length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.removedRegisterCheck;
const cases = [
  ['기록된 본인 인터넷 등본 -> 무료', ['self', 'death', 'web', 'deungbon', 3, false], { ok: true, fee: 0 }],
  ['기록된 본인 인터넷 이미지 -> 무료', ['self', 'roots', 'web', 'image', 1, false], { ok: true, fee: 0 }],
  ['직계혈족(미기록) 인터넷 -> 불가, 창구', ['family', 'roots', 'web', 'deungbon', 1, false], { ok: false, alt: 'visit' }],
  ['대리인 인터넷 -> 불가', ['proxy', 'inherit', 'web', 'deungbon', 1, false], { ok: false, alt: 'visit' }],
  ['본인 무인발급기 등본 2통 -> 1,000원', ['self', 'death', 'kiosk', 'deungbon', 2, false], { ok: true, fee: 1000 }],
  ['본인 무인발급기 초본 2통 -> 600원', ['self', 'death', 'kiosk', 'chobon', 2, false], { ok: true, fee: 600 }],
  ['무인발급기 이미지 -> 불가', ['self', 'death', 'kiosk', 'image', 1, false], { ok: false, alt: 'kiosk-kind' }],
  ['무인발급기 열람 -> 불가', ['self', 'death', 'kiosk', 'view', 1, false], { ok: false, alt: 'kiosk-kind' }],
  ['직계혈족 무인발급기 -> 불가', ['family', 'death', 'kiosk', 'deungbon', 1, false], { ok: false, alt: 'visit' }],
  ['직계혈족 창구 등본 2통 -> 2,000원', ['family', 'roots', 'visit', 'deungbon', 2, false], { ok: true, fee: 2000 }],
  ['본인 창구 초본 3통 -> 1,500원', ['self', 'submit', 'visit', 'chobon', 3, false], { ok: true, fee: 1500 }],
  ['창구 이미지 등본 -> 1,000원', ['family', 'death', 'visit', 'image', 1, false], { ok: true, fee: 1000 }],
  ['창구 열람 2건 -> 400원', ['self', 'roots', 'visit', 'view', 2, false], { ok: true, fee: 400 }],
  ['대리인 창구 -> 1,000원 + 위임장', ['proxy', 'roots', 'visit', 'deungbon', 1, false], { ok: true, fee: 1000 }],
  ['수급자 창구 -> 면제 0원', ['family', 'death', 'visit', 'deungbon', 2, true], { ok: true, fee: 0 }],
  ['형제자매 상속인 확인 창구 -> 소명자료로 가능', ['other', 'inherit', 'visit', 'deungbon', 1, false], { ok: true, fee: 1000 }],
  ['형제자매 기관 제출 창구 -> 소명자료로 가능', ['other', 'submit', 'visit', 'chobon', 1, false], { ok: true, fee: 500 }],
  ['형제자매 조상 확인 창구 -> 불가', ['other', 'roots', 'visit', 'deungbon', 1, false], { ok: false, alt: 'other' }],
  ['형제자매 인터넷 -> 불가', ['other', 'inherit', 'web', 'deungbon', 1, false], { ok: false, alt: 'visit' }],
  ['통수 0 입력 -> 1통으로', ['self', 'death', 'visit', 'deungbon', 0, false], { ok: true, fee: 1000 }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, fee: r.fee, alt: r.alt }));
}
assert.ok(c('proxy', 'roots', 'visit', 'deungbon', 1, false).need.join().includes('위임장'));
assert.ok(c('self', 'roots', 'web', 'deungbon', 1, false).need.join().includes('호주 성명 또는 본적'));
assert.ok(c('other', 'inherit', 'visit', 'deungbon', 1, false).need.join().includes('소명자료'));
console.log('PASS 준비물 3건');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'jj-who': 'self', 'jj-purpose': 'death', 'jj-where': 'web', 'jj-kind': 'deungbon', 'jj-count': '1' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['jj-out', 'jj-exempt', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('무료'));
vals['jj-who'] = 'family'; vals['jj-where'] = 'visit'; vals['jj-count'] = '2';
eval(src);
console.log('UI 직계혈족 창구 2통:', outP.join(' | '));
assert.ok(outP.join().includes('2,000원'));
