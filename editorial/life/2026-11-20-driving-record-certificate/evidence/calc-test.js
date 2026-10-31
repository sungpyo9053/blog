// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('< inside string literal');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const chk = window.drivingRecordCheck;
const has = (arr, s) => arr.some(x => x.indexOf(s) >= 0);
const cases = [
  ['본인 온라인 국문', { use: 'general', lang: 'ko', method: 'online', who: 'self' }, r => r.ok && r.route.includes('정부24') && r.fee.startsWith('무료')],
  ['대리 온라인 -> 불가', { use: 'general', lang: 'ko', method: 'online', who: 'proxy' }, r => !r.ok && r.route.includes('대리 신청이 안') && has(r.docs, '위임장')],
  ['대리 경찰서', { use: 'general', lang: 'ko', method: 'police', who: 'proxy' }, r => r.ok && r.docs.length === 3 && has(r.docs, '위임인')],
  ['본인 경찰서 영문 해외', { use: 'abroad', lang: 'en', method: 'police', who: 'self' }, r => r.ok && has(r.docs, '여권') && has(r.notes, '아포스티유')],
  ['해외인데 국문 -> 영문 안내', { use: 'abroad', lang: 'ko', method: 'online', who: 'self' }, r => has(r.notes, '영문 발급')],
  ['무인발급기 영문 -> 확인 못함', { use: 'general', lang: 'en', method: 'kiosk', who: 'self' }, r => has(r.notes, '영문 발급 가능 여부는 공식 자료에서 확인하지 못했')],
  ['무인발급기 대리 -> 확인 못함', { use: 'general', lang: 'ko', method: 'kiosk', who: 'proxy' }, r => !r.ok && has(r.notes, '대리 발급 가능 여부')],
  ['보험 경력', { use: 'insurance', lang: 'ko', method: 'online', who: 'self' }, r => has(r.notes, '금융위원회')],
  ['학원', { use: 'academy', lang: 'ko', method: 'police', who: 'self' }, r => has(r.notes, '제105조')],
];
for (const [name, o, ok] of cases) { const r = chk(o); assert.ok(ok(r), name + ' ' + JSON.stringify(r)); console.log('PASS', name, '|', r.route, '|', r.docs.join(', ')); }
// 전 조합 수수료는 항상 무료(공식 안내 외 금액을 만들지 않는지)
let n = 0;
for (const use of ['general', 'insurance', 'abroad', 'academy']) for (const lang of ['ko', 'en']) for (const method of ['online', 'police', 'kiosk']) for (const who of ['self', 'proxy']) { const r = chk({ use, lang, method, who }); assert.ok(r.fee.startsWith('무료') && !/[0-9],?[0-9]*원/.test(JSON.stringify(r))); n++; }
console.log('PASS 전 조합', n, '개 수수료 무료, 금액 표기 없음');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'drc-use': 'general', 'drc-lang': 'ko', 'drc-method': 'online', 'drc-who': 'self' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['drc-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('발급 경로') && outP.join().includes('무료'));
