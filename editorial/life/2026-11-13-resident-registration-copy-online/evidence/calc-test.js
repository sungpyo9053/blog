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
const c = window.residentCopyCheck;
const cases = [
  ['본인 정부24 등본 -> 무료', ['copy', 'web', 'self', 3, false], { ok: true, fee: 0, unit: 0 }],
  ['세대원 정부24 초본 -> 무료(법29③, FAQ1063)', ['abstract', 'web', 'member', 1, false], { ok: true, fee: 0 }],
  ['대리인 정부24 -> 불가(온라인 대리 불가)', ['copy', 'web', 'proxy', 1, false], { ok: false, alt: 'visit' }],
  ['따로 사는 가족 정부24 -> 불가', ['abstract', 'web', 'family', 1, false], { ok: false, alt: 'visit' }],
  ['본인 무인발급기 2통 -> 400원(200x2)', ['copy', 'kiosk', 'self', 2, false], { ok: true, fee: 400, unit: 200 }],
  ['대리인 무인발급기 -> 불가', ['copy', 'kiosk', 'proxy', 1, false], { ok: false }],
  ['가족 무인발급기 -> 불가', ['copy', 'kiosk', 'family', 1, false], { ok: false }],
  ['본인 창구 3통 -> 1,200원', ['copy', 'visit', 'self', 3, false], { ok: true, fee: 1200, unit: 400 }],
  ['위임 창구 -> 400원', ['abstract', 'visit', 'proxy', 1, false], { ok: true, fee: 400 }],
  ['가족 창구 등본 -> 400원', ['copy', 'visit', 'family', 1, false], { ok: true, fee: 400 }],
  ['수급자 창구 -> 0원', ['copy', 'visit', 'self', 2, true], { ok: true, fee: 0 }],
  ['통수 0 입력 -> 1통', ['copy', 'visit', 'self', 0, false], { ok: true, fee: 400 }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, fee: r.fee, unit: r.unit, alt: r.alt }));
}
assert.ok(c('copy', 'visit', 'proxy', 1, false).need.join().includes('위임장'));
assert.ok(c('copy', 'visit', 'family', 1, false).note.join().includes('세대주'));
assert.ok(c('abstract', 'visit', 'family', 1, false).note.join().includes('마·바목'));
assert.ok(c('copy', 'kiosk', 'self', 1, false).need.join().includes('모바일 주민등록증'));
assert.ok(c('copy', 'kiosk', 'self', 1, true).note.join().includes('확인하지 못했다'));
console.log('PASS 준비물·안내 문구 5건');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'rr-doc': 'copy', 'rr-where': 'web', 'rr-who': 'self', 'rr-count': '1' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['rr-out', 'rr-exempt', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('무료'));
