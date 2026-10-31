// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'([^'\\]|\\.)*'/g)) if (m[0].includes('<')) throw new Error('< in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); console.log('JSON-LD FAQ', faq.mainEntity.length, '개');
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(h3faq, faq.mainEntity.length);
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const c = window.taxCertCheck;
const cases = [
  ['지방세 위택스 본인 체납없음 대금', ['local', 'web', 'self', 'none', 'payment', 'no'], { ok: true, time: '신청 즉시', valid: '발급일부터 30일' }],
  ['지방세 정부24 본인', ['local', 'gov24', 'self', 'none', 'other', 'no'], { ok: true, time: '즉시(근무시간 내 3시간)' }],
  ['지방세 세무서 → 불가', ['local', 'nts', 'self', 'none', 'other', 'no'], { ok: false }],
  ['지방세 대리 + 위택스 → 불가', ['local', 'web', 'proxy', 'none', 'other', 'no'], { ok: false }],
  ['지방세 대리 + 정부24 → 불가', ['local', 'gov24', 'proxy', 'none', 'other', 'no'], { ok: false }],
  ['지방세 대리 + 무인발급기 → 확인 필요', ['local', 'kiosk', 'proxy', 'none', 'other', 'no'], { ok: null }],
  ['지방세 대리 + 주민센터 → 가능', ['local', 'center', 'proxy', 'none', 'other', 'no'], { ok: true }],
  ['지방세 체납 있음 → 불가', ['local', 'center', 'self', 'arrears', 'other', 'no'], { ok: false }],
  ['지방세 유예액만 → 가능', ['local', 'center', 'self', 'deferred', 'other', 'no'], { ok: true }],
  ['대금으로 체납 정리(대금 용도) → 제출 생략', ['local', 'center', 'self', 'payoff', 'payment', 'no'], { ok: true, doc: '제출 생략 가능' }],
  ['대금으로 정리(대금 외 용도) → 체납 취급 불가', ['local', 'center', 'self', 'payoff', 'emig', 'no'], { ok: false }],
  ['국세 홈택스 일반 → 가능', ['national', 'web', 'self', 'none', 'payment', 'no'], { ok: true, time: '즉시(근무시간 내 3시간)', valid: '발급일부터 30일' }],
  ['국세 주민센터 일반 → 가능', ['national', 'center', 'self', 'none', 'alien', 'no'], { ok: true }],
  ['국세 해외이주 홈택스 → 불가', ['national', 'web', 'self', 'none', 'emig', 'no'], { ok: false, time: '총 10일(해외이주여권용)' }],
  ['국세 해외이주 세무서 → 10일', ['national', 'nts', 'self', 'none', 'emig', 'no'], { ok: true, time: '총 10일(해외이주여권용)' }],
  ['지방세 해외이주 주민센터 → 즉시', ['local', 'center', 'self', 'none', 'emig', 'no'], { ok: true, time: '즉시(근무시간 내 3시간)' }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, '|', r.place, '|', r.notes.length + '개 참고');
}
assert.ok(c('local', 'center', 'self', 'none', 'other', 'yes').valid.includes('납부기한까지'));
assert.ok(c('national', 'nts', 'self', 'none', 'other', 'yes').valid.includes('지정납부기한'));
assert.ok(c('local', 'center', 'proxy', 'none', 'other', 'no').prep.includes('위임장'));
assert.ok(c('local', 'center', 'self', 'none', 'other', 'no').fee.includes('시행규칙 제2조제2항'));
assert.ok(c('national', 'web', 'self', 'none', 'trust', 'no').notes.join().includes('지방세 납세증명서'));
assert.ok(c('local', 'center', 'self', 'arrears', 'other', 'no').notes.join().includes('다른 시군구'));
console.log('PASS 유효기간 단축·준비물·수수료·신탁·타 지자체 체납 문구');
// UI 렌더(최소 DOM 스텁)
const vals = { 'tc-tax': 'local', 'tc-method': 'web', 'tc-who': 'self', 'tc-arrears': 'none', 'tc-purpose': 'payment', 'tc-notice': 'no' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, style: {}, addEventListener() {},
  set innerHTML(v) { outP.length = 0; }, appendChild(o) { outP.push(o.textContent); } });
const els = {}; ['tc-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0] === '판정: 발급 가능');
