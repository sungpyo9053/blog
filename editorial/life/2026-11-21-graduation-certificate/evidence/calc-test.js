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
const c = window.gradCertCheck;
// args: level, era, status, lang, method, copies, apost
const cases = [
  ['초중고 정부24 국문 -> 무료', ['school', 'new', 'open', 'ko', 'online', 1, false], { ok: true, fee: 0, where: '정부24(gov.kr)', period: '즉시' }],
  ['초중고 1982 이전 정부24 -> 불가', ['school', 'old', 'open', 'ko', 'online', 1, false], { ok: false, alt: 'old-online' }],
  ['초중고 1982 이전 무인발급기 -> 불가', ['school', 'old', 'open', 'ko', 'kiosk', 1, false], { ok: false, alt: 'old-online' }],
  ['초중고 1982 이전 방문 -> 가능', ['school', 'old', 'open', 'ko', 'visit', 1, false], { ok: true, fee: 0 }],
  ['초중고 우편 -> 약 10일', ['school', 'new', 'open', 'ko', 'post', 2, false], { ok: true, period: '약 10일' }],
  ['초중고 영문 -> 수수료 미확인', ['school', 'new', 'open', 'en', 'online', 1, false], { ok: true, fee: null }],
  ['폐교 정부24 -> 불가', ['school', 'new', 'closed', 'ko', 'online', 1, false], { ok: false, alt: 'closed-online' }],
  ['폐교 방문 -> 교육청, 무료', ['school', 'new', 'closed', 'ko', 'visit', 1, false], { ok: true, fee: 0, where: '학적부를 보관한 시도교육청(교육지원청) 민원실' }],
  ['검정고시 국문 정부24 -> 무료', ['ged', 'new', 'open', 'ko', 'online', 1, false], { ok: true, fee: 0 }],
  ['검정고시 영문 3통 -> 1,800원', ['ged', 'new', 'open', 'en', 'visit', 3, false], { ok: true, fee: 1800 }],
  ['검정고시 1991 이전 온라인 -> 불가', ['ged', 'old', 'open', 'ko', 'online', 1, false], { ok: false, alt: 'ged-old' }],
  ['대학 현존 -> 수수료 미확인', ['univ', 'new', 'open', 'ko', 'online', 1, false], { ok: true, fee: null }],
  ['폐교대학 온라인 -> 사학진흥재단', ['univ', 'new', 'closed', 'ko', 'online', 1, false], { ok: true, where: '한국사학진흥재단 폐교대학 통합 증명발급 서비스(u-haksa.or.kr)' }],
  ['폐교대학 방문 -> 미확인', ['univ', 'new', 'closed', 'ko', 'visit', 1, false], { ok: false, alt: 'univ-closed' }],
  ['학점은행 국문 인터넷 1통 -> 800원', ['cb', 'new', 'open', 'ko', 'online', 1, false], { ok: true, fee: 800 }],
  ['학점은행 국문 인터넷 3통 -> 1,600원', ['cb', 'new', 'open', 'ko', 'online', 3, false], { ok: true, fee: 300 * 3 + 500 + 200 }],
  ['학점은행 영문 인터넷 2통 -> 1,600원', ['cb', 'new', 'open', 'en', 'online', 2, false], { ok: true, fee: 500 * 2 + 500 + 100 }],
  ['학점은행 영문 방문 2통 -> 1,000원', ['cb', 'new', 'open', 'en', 'visit', 2, false], { ok: true, fee: 1000 }],
  ['학점은행 무인발급기 -> 불가', ['cb', 'new', 'open', 'ko', 'kiosk', 1, false], { ok: false, alt: 'cb-method' }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, alt: r.alt, fee: r.fee }));
}
assert.ok(c('school', 'new', 'open', 'en', 'online', 1, true).apostText.includes('온라인은 무료'));
assert.ok(c('school', 'new', 'open', 'ko', 'visit', 2, true).apostText.includes('2,000원'));
assert.ok(c('school', 'new', 'closed', 'ko', 'visit', 1, true).apostText.includes('확인하지 못했다'));
assert.ok(c('univ', 'new', 'open', 'en', 'online', 1, true).apostText.includes('공증'));
assert.ok(c('cb', 'new', 'open', 'en', 'online', 1, true).apostText.includes('02-6747-0404'));
assert.ok(c('school', 'new', 'open', 'ko', 'post', 12, false).extra.join().includes('10장'));
assert.ok(c('school', 'new', 'closed', 'ko', 'visit', 1, false).extra.join().includes('사전예약'));
assert.ok(c('ged', 'new', 'open', 'en', 'online', 1, false).extra.join().includes('중졸·고졸'));
assert.ok(c('cb', 'new', 'open', 'ko', 'online', 1, false).extra.join().includes('3,000원'));
assert.strictEqual(c('cb', 'new', 'open', 'ko', 'visit', 0, false).copies, 1);
assert.strictEqual(c('cb', 'new', 'open', 'ko', 'visit', 99, false).copies, 20);
console.log('PASS 아포스티유·안내 문구·통수 경계 11건');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'gc-level': 'school', 'gc-era': 'new', 'gc-status': 'open', 'gc-lang': 'ko', 'gc-method': 'online', 'gc-copies': '1' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['gc-out', 'gc-apost', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('수수료: 무료'));
