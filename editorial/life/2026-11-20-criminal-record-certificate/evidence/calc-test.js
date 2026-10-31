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
const c = window.criminalRecordCheck;
const cases = [
  ['본인확인용 온라인 본인 -> 가능, 수수료 0, 14일', ['self', 'online', 'self', false, false], { ok: true, fee: 0 }],
  ['비자용 온라인 본인 -> 가능', ['visa', 'online', 'self', true, true], { ok: true, fee: 0 }],
  ['온라인 대리 -> 불가(FAQ 10-8)', ['self', 'online', 'proxy', false, false], { ok: false, alt: 'online-proxy' }],
  ['온라인 미성년 -> 불가(FAQ 10-10)', ['visa', 'online', 'minor', false, false], { ok: false, alt: 'online-minor' }],
  ['방문 본인 -> 가능', ['self', 'visit', 'self', false, false], { ok: true, where: '가까운 경찰관서 민원실' }],
  ['방문 대리 -> 가능', ['visa', 'visit', 'proxy', false, false], { ok: true }],
  ['방문 미성년 -> 가능', ['visa', 'visit', 'minor', false, false], { ok: true }],
  ['취업용 방문 대리 -> 불가', ['job', 'visit', 'proxy', false, false], { ok: false, alt: 'job-proxy' }],
  ['취업용 방문 미성년 -> 확인 못함', ['job', 'visit', 'minor', false, false], { ok: false, alt: 'job-minor' }],
  ['취업용 방문 본인 -> 즉시', ['job', 'visit', 'self', false, false], { ok: true, period: '청소년성보호법 신청서 기준 처리기간 즉시' }],
  ['취업용 온라인 -> 5일 인쇄', ['job', 'online', 'self', false, false], { ok: true, period: '기관 승인일부터 5일 안에 인쇄' }],
  ['기타 방문 대리 -> 확인 못함', ['other', 'visit', 'proxy', false, false], { ok: false, alt: 'other-proxy' }],
  ['해외 본인확인용 -> 불가', ['self', 'abroad', 'self', false, false], { ok: false, alt: 'abroad-purpose' }],
  ['해외 비자 본인 -> 재외공관', ['visa', 'abroad', 'self', false, false], { ok: true, where: '체류국의 대한민국 대사관·영사관(재외공관)' }],
  ['해외 비자 대리 -> 국내 경찰서', ['visa', 'abroad', 'proxy', false, false], { ok: true, where: '국내 대리인이 가까운 경찰서 민원실 방문' }],
  ['해외 미성년 -> 확인 못함', ['visa', 'abroad', 'minor', false, false], { ok: false, alt: 'abroad-minor' }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, alt: r.alt, period: r.period }));
}
assert.ok(c('visa', 'online', 'self', true, true).apostFee.includes('1,000원'));
assert.ok(c('visa', 'online', 'self', true, false).extra.join().includes('발급언어를 영문'));
assert.ok(c('self', 'visit', 'self', true, false).extra.join().includes('영문 회보서에 표시'));
assert.strictEqual(c('self', 'online', 'self', false, true).apostFee, '');
assert.ok(c('self', 'online', 'self', false, true).extra.join().includes('외국 입국·체류 허가용'));
assert.ok(c('self', 'online', 'self', false, false).extra.join().includes('제출할 수 없다'));
assert.ok(c('visa', 'visit', 'proxy', false, false).need.join().includes('위임장'));
assert.ok(c('visa', 'visit', 'proxy', false, false).need.join().includes('진단서'));
assert.ok(c('visa', 'visit', 'minor', false, false).need.join().includes('기본증명서(상세)'));
assert.ok(c('job', 'visit', 'self', false, false).need.join().includes('사업자등록증은 안 된다'));
assert.ok(c('job', 'online', 'self', true, false).extra.join().includes('확인하지 못했다'));
assert.ok(c('self', 'online', 'self', false, false).period.includes('14일'));
console.log('PASS 준비물·안내 문구 12건');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'cr-purpose': 'self', 'cr-method': 'online', 'cr-who': 'self' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['cr-out', 'cr-eng', 'cr-apost', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('수수료 없음'));
