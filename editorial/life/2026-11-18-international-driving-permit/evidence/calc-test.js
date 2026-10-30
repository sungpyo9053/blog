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
const c = window.idpCheck;
const cases = [
  ['기본: 시험장 2026-11-20 -> 9,000원, 기준일 2027-11-20', ['2026-11-20', '2026-12-20', '2027-01-05', 'geneva', 'center'], { ok: true, fee: 9000, expiry: '2027-11-20' }],
  ['윤년 2028-02-29 -> 2029-02-28', ['2028-02-29', '2028-03-10', '', 'geneva', 'center'], { ok: true, expiry: '2029-02-28' }],
  ['연말 2026-12-31 -> 2027-12-31', ['2026-12-31', '2026-12-31', '', 'taiwan', 'police'], { ok: true, expiry: '2027-12-31' }],
  ['발급일 > 출국일 -> 불가', ['2026-12-21', '2026-12-20', '', 'geneva', 'center'], { ok: false, alt: 'late' }],
  ['해외 체류 중 대리 -> 출국 후 발급 허용', ['2027-03-01', '2026-12-20', '', 'geneva', 'proxyabroad'], { ok: true, expiry: '2028-03-01' }],
  ['발급일 빈칸 -> 불가', ['', '2026-12-20', '', 'geneva', 'center'], { ok: false, alt: 'issue' }],
  ['출국일 빈칸 -> 불가', ['2026-11-20', '', '', 'geneva', 'center'], { ok: false, alt: 'depart' }],
  ['지자체 -> 9,000원', ['2026-11-20', '2026-12-20', '', 'geneva', 'local'], { ok: true, fee: 9000 }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, fee: r.fee, expiry: r.expiry, alt: r.alt }));
}
const j = (r) => r.need.join() + '|' + r.note.join() + '|' + r.place;
assert.ok(j(c('2026-11-20', '2026-12-19', '', 'geneva', 'airport')).includes('주말'));        // 2026-12-19 토요일
assert.ok(j(c('2026-11-20', '2026-12-21', '', 'geneva', 'airport')).includes('평일 9~18시')); // 월요일
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'geneva', 'proxy')).includes('위임장'));
assert.ok(!j(c('2026-11-20', '2026-12-20', '', 'geneva', 'proxy')).includes('출입국사실증명서'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'geneva', 'proxyabroad')).includes('출입국사실증명서'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'geneva', 'online')).includes('450건'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'geneva', 'online')).includes('확인하지 못했다'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'geneva', 'local')).includes('여권 수수료'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'geneva', 'police')).includes('발급 여부 확인'));
assert.ok(j(c('2026-11-20', '2026-12-20', '2027-12-01', 'geneva', 'center')).includes('귀국 예정일이 유효기간 기준일'));
assert.ok(!j(c('2026-11-20', '2026-12-20', '2027-11-20', 'geneva', 'center')).includes('귀국 예정일이 유효기간 기준일'));
assert.ok(j(c('2026-11-20', '2026-11-21', '2027-12-01', 'geneva', 'center')).includes('1년을 넘는다'));
assert.ok(j(c('2026-11-20', '2026-12-20', '2026-12-10', 'geneva', 'center')).includes('출국일보다 빠르다'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'taiwan', 'center')).includes('NT$150'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'vietnam', 'center')).includes('B 범주'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'vienna', 'center')).includes('확인하지 못했다'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'other', 'center')).includes('중국 본토'));
assert.ok(j(c('2026-11-20', '2026-12-20', '', 'geneva', 'center')).includes('여권을 함께'));
console.log('PASS 준비물·안내 문구 18건');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'idp-issue': '2026-11-20', 'idp-depart': '2026-12-20', 'idp-return': '2027-01-05', 'idp-country': 'geneva', 'idp-method': 'center' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['idp-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('9,000원'));
assert.ok(outP.join().includes('2027-11-20'));
