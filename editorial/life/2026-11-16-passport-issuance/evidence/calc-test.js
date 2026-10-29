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
const c = window.passportCheck;
const cases = [
  ['30세 최초 복수 58면 방문 -> 52,000원 10년', [30, 'first', 'multi', 58, 'visit'], { ok: true, fee: 52000, valid: '10년' }],
  ['30세 최초 복수 26면 -> 49,000원', [30, 'first', 'multi', 26, 'visit'], { ok: true, fee: 49000 }],
  ['18세 경계 -> 성인 10년 52,000원', [18, 'renew', 'multi', 58, 'online'], { ok: true, fee: 52000, valid: '10년' }],
  ['17세 58면 -> 44,000원 5년', [17, 'first', 'multi', 58, 'visit'], { ok: true, fee: 44000, valid: '5년' }],
  ['8세 경계 26면 -> 41,000원', [8, 'renew', 'multi', 26, 'visit'], { ok: true, fee: 41000 }],
  ['7세 58면 -> 35,000원', [7, 'first', 'multi', 58, 'visit'], { ok: true, fee: 35000 }],
  ['0세 26면 -> 32,000원', [0, 'first', 'multi', 26, 'visit'], { ok: true, fee: 32000 }],
  ['단수 -> 17,000원', [40, 'first', 'single', 58, 'visit'], { ok: true, fee: 17000 }],
  ['남은 유효기간 재발급 방문 -> 27,000원', [40, 'change', 'remain', 58, 'visit'], { ok: true, fee: 27000 }],
  ['긴급 -> 50,000원 1일', [40, 'renew', 'urgent', 58, 'visit'], { ok: true, fee: 50000, period: '정부24 처리기간 총 1일' }],
  ['최초 + 온라인 -> 불가', [30, 'first', 'multi', 58, 'online'], { ok: false, alt: 'online-first' }],
  ['분실 재발급 + 온라인 -> 불가', [30, 'change', 'multi', 58, 'online'], { ok: false, alt: 'online-change' }],
  ['남은 유효기간 + 온라인 -> 불가', [30, 'renew', 'remain', 58, 'online'], { ok: false, alt: 'online-remain' }],
  ['긴급 + 온라인 -> 불가', [30, 'renew', 'urgent', 58, 'online'], { ok: false, alt: 'online-urgent' }],
  ['남은 유효기간 + 최초 -> 불가', [30, 'first', 'remain', 58, 'visit'], { ok: false, alt: 'remain-first' }],
  ['나이 빈칸(NaN) -> 불가', [NaN, 'first', 'multi', 58, 'visit'], { ok: false, alt: 'age' }],
  ['10세 온라인 재발급 -> 44,000원', [10, 'renew', 'multi', 58, 'online'], { ok: true, fee: 44000 }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, fee: r.fee, valid: r.valid, alt: r.alt }));
}
assert.ok(c(10, 'first', 'multi', 58, 'visit').need.join().includes('법정대리인 동의서'));
assert.ok(c(10, 'renew', 'multi', 58, 'online').note.join().includes('KB스타뱅킹은 준비 중'));
assert.ok(c(30, 'renew', 'multi', 58, 'online').need.join().includes('500KB'));
assert.ok(c(30, 'renew', 'multi', 58, 'online').note.join().includes('우편배송은 안 된다'));
assert.ok(c(25, 'first', 'multi', 58, 'visit').note.join().includes('국외여행허가'));
assert.ok(!c(38, 'first', 'multi', 58, 'visit').note.join().includes('국외여행허가'));
assert.ok(!c(17, 'first', 'multi', 58, 'visit').note.join().includes('국외여행허가'));
assert.ok(c(30, 'renew', 'multi', 58, 'visit').note.join().includes('2026년 6월 1일'));
assert.ok(c(30, 'renew', 'urgent', 58, 'visit').need.join().includes('사유서'));
assert.ok(c(30, 'first', 'multi', 58, 'visit').period.includes('8일'));
console.log('PASS 준비물·안내 문구 10건');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'pp-age': '30', 'pp-purpose': 'first', 'pp-type': 'multi', 'pp-pages': '58', 'pp-method': 'visit' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['pp-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('52,000원'));
