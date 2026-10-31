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
const c = window.militaryCertCheck;
const cases = [
  ['예비역 취업 정부24 본인 -> 가능', ['done', 'job', 'ko', 'gov24', 'self'], { ok: true }],
  ['예비역 방문 본인 -> 가능, 수수료 없음', ['done', 'job', 'ko', 'visit', 'self'], { ok: true, where: '가까운 지방병무청 민원실(병무민원상담 1588-9090)' }],
  ['현역 취업 -> 불가', ['serving', 'job', 'ko', 'gov24', 'self'], { ok: false, alt: 'serving' }],
  ['현역 입영사실 -> 가능', ['serving', 'enlist', 'ko', 'gov24', 'self'], { ok: true }],
  ['사망자 정부24 -> 불가', ['deceased', 'other', 'ko', 'gov24', 'family'], { ok: false, alt: 'deceased-online' }],
  ['사망자 무인발급기 -> 불가', ['deceased', 'other', 'ko', 'kiosk', 'family'], { ok: false, alt: 'deceased-online' }],
  ['사망자 본인 -> 불가', ['deceased', 'other', 'ko', 'visit', 'self'], { ok: false, alt: 'deceased-self' }],
  ['사망자 가족 방문 -> 가능', ['deceased', 'other', 'ko', 'visit', 'family'], { ok: true }],
  ['전역 1개월 이내 무인발급기 -> 불가', ['done_recent', 'job', 'ko', 'kiosk', 'self'], { ok: false, alt: 'kiosk-recent' }],
  ['전역 1개월 이내 정부24 -> 가능', ['done_recent', 'job', 'ko', 'gov24', 'self'], { ok: true }],
  ['해외 대리 -> 불가', ['done', 'job', 'ko', 'abroad', 'proxy'], { ok: false, alt: 'abroad-proxy' }],
  ['해외 본인 -> 가능', ['done', 'job', 'ko', 'abroad', 'self'], { ok: true }],
  ['정부24 가족 -> 확인 못함', ['done', 'job', 'ko', 'gov24', 'family'], { ok: null, alt: 'online-proxy' }],
  ['영문 정부24 -> 확인 못함', ['done', 'job', 'en', 'gov24', 'self'], { ok: null, alt: 'en-unverified' }],
  ['영문 방문 -> 가능', ['done', 'job', 'en', 'visit', 'self'], { ok: true }],
  ['면제 방문 대리 -> 가능', ['exempt', 'exam', 'ko', 'visit', 'proxy'], { ok: true }],
  ['병역준비역 우편 -> 가능', ['ready', 'other', 'ko', 'post', 'self'], { ok: true }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, alt: r.alt }));
}
const j = a => a.join(' ');
assert.ok(c('done', 'job', 'ko', 'visit', 'self').fee.includes('별도의 수수료는 없습니다'));
assert.ok(c('done', 'job', 'ko', 'gov24', 'self').fee.includes('확인하지 못했다'));
assert.ok(j(c('done', 'job', 'ko', 'visit', 'proxy').need).includes('위임장'));
assert.ok(j(c('done', 'job', 'ko', 'visit', 'family').need).includes('위임장은 필요 없다'));
assert.ok(j(c('done', 'job', 'en', 'visit', 'self').need).includes('여권'));
assert.ok(j(c('serving', 'career', 'ko', 'gov24', 'self').extra).includes('군 경력증명서'));
assert.ok(j(c('exempt', 'job', 'ko', 'kiosk', 'self').extra).includes('1989년 1월 1일'));
assert.ok(j(c('exempt', 'job', 'ko', 'gov24', 'self').extra).includes('처분사유'));
assert.ok(j(c('done', 'job', 'ko', 'gov24', 'self').extra).includes('주민등록표 초본'));
assert.ok(!j(c('ready', 'job', 'ko', 'gov24', 'self').extra).includes('주민등록표 초본'));
assert.ok(j(c('done', 'job', 'ko', 'gov24', 'self').extra).includes('제154조'));
assert.ok(j(c('serving_sub', 'other', 'ko', 'gov24', 'self').extra).includes('복무확인서'));
assert.ok(c('done', 'job', 'ko', 'gov24', 'self').period.includes('즉시'));
console.log('PASS 준비물·안내 문구 13건');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'ms-status': 'done', 'ms-purpose': 'job', 'ms-lang': 'ko', 'ms-method': 'gov24', 'ms-who': 'self' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ms-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].startsWith('발급 가능'));
